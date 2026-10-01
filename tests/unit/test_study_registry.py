from uuid import UUID

import pytest

from syune.core import SourceId, SourceVersionId
from syune.study import (
    Classification, SourceRevisionId, SqliteStudyRegistry,
    StudyError, StudyErrorCode, StudyJobId, StudyRunId, StudyState,
)


def create(registry, locator, digest="a" * 64, parser_version="1"):
    return registry.create_revision(
        source_id=SourceId(UUID(int=1)), source_version_id=SourceVersionId(UUID(int=2)),
        revision_id=SourceRevisionId(UUID(int=3)), job_id=StudyJobId(UUID(int=4)),
        run_id=StudyRunId(UUID(int=5)), digest=digest,
        classification=Classification.NEW_SOURCE, previous_revision_id=None,
        locator=locator, parser_version=parser_version,
        pipeline_version="1", block_scheme_version="1", encoder_version="1",
    )


def test_registry_reopen_alias_status_and_failure(tmp_path):
    path = tmp_path / "study.sqlite"
    alias = str(tmp_path / "renamed.txt")
    with SqliteStudyRegistry(path) as registry:
        status = create(registry, str(tmp_path / "first.txt"))
        registry.add_alias(status.revision_id, alias)
        registry.transition(status.revision_id, StudyState.PARSING)
        assert registry.transition_history(status.revision_id)[:2] == (
            ("DISCOVERED", "REGISTERED"), ("REGISTERED", "PARSING"),
        )
        registry.record_failure(status.revision_id, StudyErrorCode.PARSE_FAILURE, "invalid text")
    with SqliteStudyRegistry(path) as reopened:
        status = reopened.by_fingerprint("a" * 64)
        assert status.state is StudyState.FAILED
        assert status.error_code == StudyErrorCode.PARSE_FAILURE.value
        assert not status.is_studied
        assert len(status.locators) == 2
        assert reopened.by_locator(alias).revision_id == status.revision_id
        assert reopened.by_source_id(status.source_id).revision_id == status.revision_id


def test_registry_validates_transitions_and_recovers_failed_run(tmp_path):
    with SqliteStudyRegistry(tmp_path / "study.sqlite") as registry:
        status = create(registry, "a.txt")
        with pytest.raises(StudyError) as error:
            registry.transition(status.revision_id, StudyState.ENCODED)
        assert error.value.code is StudyErrorCode.INVALID_TRANSITION
        registry.transition(status.revision_id, StudyState.PARSING)
        registry.record_failure(status.revision_id, StudyErrorCode.PARSE_FAILURE, "retry")
        registry.transition(status.revision_id, StudyState.PARSING)
        assert registry.status(status.revision_id).state is StudyState.PARSING


def test_input_failure_is_durable(tmp_path):
    path = tmp_path / "study.sqlite"
    with SqliteStudyRegistry(path) as registry:
        registry.record_input_failure("missing.txt", StudyErrorCode.SOURCE_NOT_FOUND, "source not found")
    with SqliteStudyRegistry(path) as registry:
        assert registry.input_failure("missing.txt")[0] == "SOURCE_NOT_FOUND"
