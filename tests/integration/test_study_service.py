from hashlib import sha256
from io import BytesIO
from pathlib import Path

import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from syune.core import SourceId, SourceVersionId
from syune.memory import Claim, Concept, InMemoryReferenceRepository, MemoryTrace, Observation
from syune.study import (
    BlockChangeKind, Classification, SourceRevisionId, SqliteStudyRegistry,
    StudyError, StudyErrorCode, StudyJobId, StudyRunId, StudyService,
    StudyState, source_fingerprint,
)
from syune.study.diff import compare_blocks


def pdf_bytes(*texts: str) -> bytes:
    writer = PdfWriter()
    font = writer._add_object(DictionaryObject({
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Helvetica"),
    }))
    for text in texts:
        page = writer.add_blank_page(width=612, height=792)
        page[NameObject("/Resources")] = DictionaryObject({
            NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})
        })
        stream = DecodedStreamObject()
        stream.set_data(f"BT /F1 12 Tf 50 750 Td ({text}) Tj ET".encode("latin-1"))
        page[NameObject("/Contents")] = writer._add_object(stream)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def test_required_new_duplicate_rename_change_and_restart(tmp_path):
    source = tmp_path / "sample.md"
    original = "# Heading\n\nAlpha\n\nBeta\n"
    source.write_text(original, encoding="utf-8")
    initial_hash = sha256(source.read_bytes()).hexdigest()
    db = tmp_path / "state" / "study.sqlite"
    memory = InMemoryReferenceRepository()
    with SqliteStudyRegistry(db) as registry:
        service = StudyService(registry, memory, tmp_path)
        first = service.study(source)
        assert first.classification is Classification.NEW_SOURCE
        assert first.status.state is StudyState.ENCODED
        assert first.status.is_studied
        assert first.status.blocks_total == 3
        assert first.status.blocks_encoded == 3
        assert len(first.status.derived_memory_ids) == 6
        assert first.status.checkpoint == "b000002"
        assert source_fingerprint(source.read_bytes()) == initial_hash
        assert all(isinstance(value, str) for value in first.status.derived_memory_ids)
        assert not any(isinstance(x, (Claim, Concept)) for x in memory._entities.values())

        again = service.study(source)
        assert again.classification is Classification.ALREADY_STUDIED
        assert again.status.revision_id == first.status.revision_id
        assert again.status.derived_memory_ids == first.status.derived_memory_ids

        renamed = tmp_path / "renamed_sample.md"
        renamed.write_bytes(source.read_bytes())
        alias = service.study(renamed)
        assert alias.classification is Classification.ALREADY_STUDIED
        assert alias.status.revision_id == first.status.revision_id
        assert len(alias.status.locators) == 2
        assert alias.status.derived_memory_ids == first.status.derived_memory_ids
        assert service.status_by_source_id(first.status.source_id).revision_id == first.status.revision_id
        assert service.status_by_locator(renamed).revision_id == first.status.revision_id
        assert service.status_by_fingerprint(initial_hash).is_studied

        source.write_text("# Heading\n\nAlpha\n\nBeta changed\n", encoding="utf-8")
        changed = service.study(source)
        assert changed.classification is Classification.CHANGED_SOURCE
        assert changed.status.revision_id != first.status.revision_id
        assert changed.status.previous_revision_id == first.status.revision_id
        assert changed.status.source_id == first.status.source_id
        assert changed.status.is_studied
        assert BlockChangeKind.CHANGED in {c.kind for c in changed.block_changes}
        assert BlockChangeKind.UNCHANGED in {c.kind for c in changed.block_changes}
        assert registry.status(first.status.revision_id).is_studied
        assert sha256(renamed.read_bytes()).hexdigest() == initial_hash

    with SqliteStudyRegistry(db) as reopened:
        service = StudyService(reopened, InMemoryReferenceRepository(), tmp_path)
        restarted = service.study(renamed)
        assert restarted.classification is Classification.ALREADY_STUDIED
        assert restarted.status.revision_id == first.status.revision_id
        assert restarted.status.derived_memory_ids == first.status.derived_memory_ids


def test_txt_and_pdf_end_to_end(tmp_path):
    txt = tmp_path / "notes.txt"
    txt.write_text("First\n\nSecond\n", encoding="utf-8")
    pdf = tmp_path / "pages.pdf"
    pdf.write_bytes(pdf_bytes("Page one", "Page two"))
    memory = InMemoryReferenceRepository()
    with SqliteStudyRegistry(tmp_path / "state.sqlite") as registry:
        service = StudyService(registry, memory, tmp_path)
        txt_result = service.study(txt)
        pdf_result = service.study(pdf)
        assert txt_result.status.is_studied
        assert pdf_result.status.is_studied
        assert pdf_result.status.blocks_total == 2
        assert registry.perception_summary(txt_result.status.revision_id)[-1][1] == "COMPLETE"
        assert registry.perception_summary(pdf_result.status.revision_id)[-1][1] == "COMPLETE"
        pdf_observations = [
            entity for entity in memory._entities.values()
            if isinstance(entity, Observation) and entity.provenance.source_id == pdf_result.status.source_id
        ]
        assert {item.provenance.locator.page for item in pdf_observations} == {1, 2}
        assert all(item.provenance.process_id.startswith("study:perception:") for item in pdf_observations)
        traces = [entity for entity in memory._entities.values() if isinstance(entity, MemoryTrace)]
        assert all(trace.provenance.source_id for trace in traces)
        assert not any(isinstance(x, Claim) for x in memory._entities.values())


def test_failure_persists_and_is_not_studied(tmp_path):
    source = tmp_path / "empty.txt"
    source.write_bytes(b"")
    db = tmp_path / "state.sqlite"
    with SqliteStudyRegistry(db) as registry:
        with pytest.raises(StudyError) as error:
            StudyService(registry, InMemoryReferenceRepository(), tmp_path).study(source)
        assert error.value.code is StudyErrorCode.NO_USABLE_TEXT
        status = registry.by_locator(str(source.resolve()))
        assert status.state is StudyState.FAILED
        assert not status.is_studied
    with SqliteStudyRegistry(db) as registry:
        assert registry.by_locator(str(source.resolve())).error_code == "NO_USABLE_TEXT"


def test_incomplete_job_resumes_with_same_identity(tmp_path):
    source = tmp_path / "partial.txt"
    source.write_text("A\n\nB\n", encoding="utf-8")
    digest = source_fingerprint(source.read_bytes())
    db = tmp_path / "state.sqlite"
    with SqliteStudyRegistry(db) as registry:
        old = registry.create_revision(
            source_id=SourceId.new(), source_version_id=SourceVersionId.new(),
            revision_id=SourceRevisionId.new(), job_id=StudyJobId.new(),
            run_id=StudyRunId.new(), digest=digest,
            classification=Classification.NEW_SOURCE, previous_revision_id=None,
            locator=str(source.resolve()), parser_version="1",
            pipeline_version="1", block_scheme_version="1", encoder_version="1",
        )
        registry.transition(old.revision_id, StudyState.PARSING)
    with SqliteStudyRegistry(db) as registry:
        result = StudyService(registry, InMemoryReferenceRepository(), tmp_path).study(source)
        assert result.classification is Classification.INCOMPLETE
        assert result.status.revision_id == old.revision_id
        assert result.status.is_studied


def test_version_incompatible_incomplete_run_preserved(tmp_path):
    source = tmp_path / "partial.txt"
    source.write_text("A", encoding="utf-8")
    db = tmp_path / "state.sqlite"
    with SqliteStudyRegistry(db) as registry:
        old = registry.create_revision(
            source_id=SourceId.new(), source_version_id=SourceVersionId.new(),
            revision_id=SourceRevisionId.new(), job_id=StudyJobId.new(),
            run_id=StudyRunId.new(), digest=source_fingerprint(source.read_bytes()),
            classification=Classification.NEW_SOURCE, previous_revision_id=None,
            locator=str(source.resolve()), parser_version="0",
            pipeline_version="1", block_scheme_version="1", encoder_version="1",
        )
        result = StudyService(registry, InMemoryReferenceRepository(), tmp_path).study(source)
        assert result.classification is Classification.INCOMPLETE
        assert result.status.revision_id != old.revision_id
        assert result.status.previous_revision_id == old.revision_id
        assert registry.status(old.revision_id).state is StudyState.REGISTERED


def test_structural_block_diff_all_kinds():
    previous = (("a", "1"), ("b", "2"), ("c", "3"), ("d", "4"))
    current = (("a2", "1"), ("x", "9"), ("c2", "3"), ("e", "5"))
    changes = compare_blocks(previous, current)
    assert BlockChangeKind.UNCHANGED in {x.kind for x in changes}
    assert BlockChangeKind.CHANGED in {x.kind for x in changes}
    assert BlockChangeKind.NEW in {x.kind for x in compare_blocks((), current)}
    assert BlockChangeKind.REMOVED in {x.kind for x in compare_blocks(previous, ())}


def test_missing_and_unsupported_sources_record_structured_failures(tmp_path):
    with SqliteStudyRegistry(tmp_path / "state.sqlite") as registry:
        service = StudyService(registry, InMemoryReferenceRepository(), tmp_path)
        missing = tmp_path / "missing.txt"
        with pytest.raises(StudyError) as error:
            service.study(missing)
        assert error.value.code is StudyErrorCode.SOURCE_NOT_FOUND
        assert registry.input_failure(str(missing.absolute()))[0] == "SOURCE_NOT_FOUND"
        unsupported = tmp_path / "data.bin"
        unsupported.write_bytes(b"bytes")
        with pytest.raises(StudyError) as error:
            service.study(unsupported)
        assert error.value.code is StudyErrorCode.UNSUPPORTED_FORMAT
        assert registry.input_failure(str(unsupported.resolve()))[0] == "UNSUPPORTED_FORMAT"


def test_checkpointed_partial_encoding_resumes_after_restart(tmp_path):
    class FailingMemory(InMemoryReferenceRepository):
        def __init__(self):
            super().__init__()
            self.observation_count = 0

        def put(self, entity):
            if isinstance(entity, Observation):
                self.observation_count += 1
                if self.observation_count == 2:
                    raise RuntimeError("synthetic interruption")
            super().put(entity)

    source = tmp_path / "partial.md"
    source.write_text("First\n\nSecond\n", encoding="utf-8")
    db = tmp_path / "state.sqlite"
    with SqliteStudyRegistry(db) as registry:
        with pytest.raises(StudyError) as error:
            StudyService(registry, FailingMemory(), tmp_path).study(source)
        assert error.value.code is StudyErrorCode.ENCODING_FAILURE
        failed = registry.by_locator(str(source.resolve()))
        assert failed.state is StudyState.FAILED
        assert failed.blocks_total == 2
        assert failed.blocks_encoded == 1
        assert failed.checkpoint == "b000000"
        assert not failed.is_studied
        revision_id = failed.revision_id
    with SqliteStudyRegistry(db) as registry:
        recovered = StudyService(registry, InMemoryReferenceRepository(), tmp_path).study(source)
        assert recovered.classification is Classification.INCOMPLETE
        assert recovered.status.revision_id == revision_id
        assert recovered.status.blocks_encoded == 2
        assert recovered.status.is_studied
        assert ("FAILED", "PARSING") in registry.transition_history(revision_id)
        assert registry.transition_history(revision_id)[-1] == ("UNDERSTOOD", "ENCODED")


def test_pdf_no_text_failure_is_persisted(tmp_path):
    source = tmp_path / "empty.pdf"
    source.write_bytes(pdf_bytes(""))
    db = tmp_path / "state.sqlite"
    with SqliteStudyRegistry(db) as registry:
        with pytest.raises(StudyError) as error:
            StudyService(registry, InMemoryReferenceRepository(), tmp_path).study(source)
        assert error.value.code is StudyErrorCode.NO_USABLE_TEXT
        status = registry.by_locator(str(source.resolve()))
        assert status.state is StudyState.FAILED
        assert not status.is_studied
