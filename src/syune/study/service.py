"""Synchronous local Study orchestration; no cognition or network activity."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from syune.core import MemoryTraceId, ObservationId, PerceivedSegmentId, PerceptionRunId, SourceId, SourceVersionId,utc_now
from syune.memory.repository import MemoryRepository
from .diff import compare_blocks
from .encoder import ENCODER_VERSION, StudyEncoder, observation_id
from .errors import StudyError, StudyErrorCode
from .model import (
    BlockChange, BlockChangeKind, Classification, MaterializationState, SourceRevisionId,
    StudyJobId, StudyResult, StudyRunId, StudyState, StudyStatus,
    source_fingerprint,
)
from .parsers import BLOCK_SCHEME_VERSION, PARSERS, PARSER_VERSION
from .registry import StudyRegistry
from syune.perception import AudioTimeRangeLocator,ComponentState,DeterminismClass,ImageRegionLocator,Modality,PageLocator,PerceivedSegment,PerceptionError,PerceptionMethod,PerceptionRouter,PerceptionRun,RepresentationType,RunStatus,SourceKind,TextLocator,VideoFrameLocator,VideoTimeRangeLocator,segment_fingerprint
from syune.memory import SourceLocator
from syune.core import ContentBlockId
from uuid import NAMESPACE_URL,uuid5
from io import BytesIO
from pypdf import PdfReader
from hashlib import sha256

PIPELINE_VERSION = "1"


class StudyService:
    def __init__(self, registry: StudyRegistry, memory: MemoryRepository,
                 library_root: str | Path | None = None,perception_router:PerceptionRouter|None=None):
        self.registry = registry
        self.memory = memory
        self.encoder = StudyEncoder(memory)
        self.library_root = Path(library_root).resolve() if library_root is not None else None
        self.perception_router=perception_router or PerceptionRouter()

    def _locator(self, path: str | Path) -> tuple[Path, str]:
        candidate = Path(path).expanduser()
        try:
            resolved = candidate.resolve(strict=True)
        except FileNotFoundError as exc:
            locator = str(candidate.absolute())
            self.registry.record_input_failure(locator, StudyErrorCode.SOURCE_NOT_FOUND, "source not found")
            raise StudyError(StudyErrorCode.SOURCE_NOT_FOUND, "source not found") from exc
        if not resolved.is_file():
            raise StudyError(StudyErrorCode.READ_FAILURE, "source is not a regular file")
        if self.library_root is not None and not resolved.is_relative_to(self.library_root):
            raise StudyError(StudyErrorCode.READ_FAILURE, "source outside configured library root")
        return resolved, str(resolved)

    def study(self, path: str | Path) -> StudyResult:
        source_path, locator = self._locator(path)
        parser = PARSERS.get(source_path.suffix.lower());multimodal=parser is None and self.perception_router.supports(source_path.suffix)
        if parser is None and not multimodal:
            self.registry.record_input_failure(locator, StudyErrorCode.UNSUPPORTED_FORMAT, "unsupported local format")
            raise StudyError(StudyErrorCode.UNSUPPORTED_FORMAT, "unsupported local format")
        try:
            with source_path.open("rb") as stream:
                data = stream.read(self.perception_router.limits.max_source_bytes + 1)
        except OSError as exc:
            self.registry.record_input_failure(locator, StudyErrorCode.READ_FAILURE, type(exc).__name__)
            raise StudyError(StudyErrorCode.READ_FAILURE, "cannot read source") from exc
        if len(data)>self.perception_router.limits.max_source_bytes:
            self.registry.record_input_failure(locator,StudyErrorCode.MEDIA_TOO_LARGE,"source byte limit exceeded")
            raise StudyError(StudyErrorCode.MEDIA_TOO_LARGE,"source byte limit exceeded")
        if source_path.suffix.lower()==".pdf":
            try:page_count=len(PdfReader(BytesIO(data),strict=False).pages)
            except Exception:page_count=0
            if page_count>self.perception_router.limits.max_document_pages:
                self.registry.record_input_failure(locator,StudyErrorCode.PAGE_LIMIT_EXCEEDED,"document page limit exceeded")
                raise StudyError(StudyErrorCode.PAGE_LIMIT_EXCEEDED,"document page limit exceeded")
        try:
            digest = source_fingerprint(data)
        except Exception as exc:
            self.registry.record_input_failure(locator, StudyErrorCode.FINGERPRINT_FAILURE, type(exc).__name__)
            raise StudyError(StudyErrorCode.FINGERPRINT_FAILURE, "cannot fingerprint source") from exc

        same = self.registry.by_fingerprint(digest)
        if same is not None and same.is_studied:
            self.registry.add_alias(same.revision_id, locator)
            summaries=self.registry.perception_summary(same.revision_id)
            if multimodal and summaries and summaries[-1][1]!="COMPLETE":
                return self._resume_perception(source_path,data,same)
            return StudyResult(Classification.ALREADY_STUDIED,
                               replace(self.registry.status(same.revision_id),
                                       classification=Classification.ALREADY_STUDIED),
                               materialization=self.materialization_status(same.revision_id))
        prior = self.registry.by_locator(locator)
        if same is not None:
            if (same.parser_version, same.pipeline_version, same.block_scheme_version, same.encoder_version) == (
                    (parser.version if parser else self.perception_router.version), PIPELINE_VERSION, BLOCK_SCHEME_VERSION, ENCODER_VERSION):
                revision = same
                classification = Classification.INCOMPLETE
                self.registry.add_alias(revision.revision_id, locator)
            else:
                # Preserve the incompatible incomplete run and start a new revision.
                revision = self._new_revision(
                    same.source_id, digest, Classification.INCOMPLETE,
                    same.revision_id, locator, parser.version if parser else self.perception_router.version,
                )
                classification = Classification.INCOMPLETE
        elif prior is not None:
            revision = self._new_revision(
                prior.source_id, digest, Classification.CHANGED_SOURCE,
                prior.revision_id, locator, parser.version if parser else self.perception_router.version,
            )
            classification = Classification.CHANGED_SOURCE
        else:
            revision = self._new_revision(
                SourceId.new(), digest, Classification.NEW_SOURCE,
                None, locator, parser.version if parser else self.perception_router.version,
            )
            classification = Classification.NEW_SOURCE

        try:
            if revision.state is not StudyState.PARSING:
                self.registry.transition(revision.revision_id, StudyState.PARSING)
            media_metadata=None;source_kind=None
            if parser:
                blocks = parser.parse(data, revision.revision_id)
                if len(blocks)>self.perception_router.limits.max_segments:
                    raise StudyError(StudyErrorCode.SEGMENT_LIMIT_EXCEEDED,"segment limit exceeded")
                source_kind=SourceKind.PDF if source_path.suffix.lower()==".pdf" else SourceKind.MARKDOWN if source_path.suffix.lower() in (".md",".markdown") else SourceKind.TEXT
                blocks=self._record_parser_perception(blocks,revision,source_kind,data)
            else:
                result=self.perception_router.perceive(source_path,data,revision.source_id,revision.source_version_id,revision.revision_id)
                media_metadata=result.metadata
                self.registry.record_perception(result.run,result.segments)
                blocks=tuple(self._perception_block(segment,n) for n,segment in enumerate(result.segments))
            if not blocks:
                raise StudyError(StudyErrorCode.NO_USABLE_TEXT, "no perceived blocks")
            self.registry.set_blocks(revision.revision_id, blocks)
            self.registry.transition(revision.revision_id, StudyState.PERCEIVED)
            # UNDERSTOOD in v1 means only structurally ready for encoding.
            self.registry.transition(revision.revision_id, StudyState.UNDERSTOOD)
            current_fingerprints = tuple((block.key, block.fingerprint) for block in blocks)
            previous = (self.registry.block_fingerprints(revision.previous_revision_id)
                        if revision.previous_revision_id else ())
            changes = compare_blocks(previous, current_fingerprints)
            self.encoder.ensure_source(
                revision.source_id, revision.source_version_id,
                source_path.name,digest,source_path.as_uri(),media_metadata.kind.value if media_metadata else source_kind.value,media_metadata.mime_type if media_metadata else ("application/pdf" if source_kind is SourceKind.PDF else "text/markdown" if source_kind is SourceKind.MARKDOWN else "text/plain"),
            )
            for block in blocks:
                oid = observation_id(revision.revision_id, block.key)
                from .encoder import trace_id
                tid = trace_id(revision.revision_id, block.key)
                if (self.registry.has_encoded_block(revision.revision_id, block.key)
                        and self.memory.exists(oid) and self.memory.exists(tid)):
                    continue
                observation, trace = self.encoder.encode(
                    block, revision.source_id, revision.source_version_id, PIPELINE_VERSION,
                )
                self.registry.record_encoded(revision.revision_id, block.key,
                                             str(observation), str(trace))
            pending = self.registry.status(revision.revision_id)
            if not self._all_memory_present(pending):
                raise StudyError(StudyErrorCode.ENCODING_FAILURE, "derived memory not materialized")
            self.registry.transition(revision.revision_id, StudyState.ENCODED)
            return StudyResult(classification, self.registry.status(revision.revision_id), changes,
                               MaterializationState.MATERIALIZED)
        except StudyError as exc:
            self.registry.record_failure(revision.revision_id, exc.code, str(exc))
            raise
        except PerceptionError as exc:
            code=StudyErrorCode[exc.code.name]
            self.registry.record_failure(revision.revision_id,code,str(exc))
            raise StudyError(code,str(exc)) from exc
        except Exception as exc:
            self.registry.record_failure(revision.revision_id, StudyErrorCode.ENCODING_FAILURE,
                                         f"{type(exc).__name__}: {exc}")
            raise StudyError(StudyErrorCode.ENCODING_FAILURE, "Study encoding failed") from exc

    def _perception_block(self,segment,order):
        locator=segment.locator
        if isinstance(locator,PageLocator):memory_locator=SourceLocator(page=locator.page,block=f"b{order:06d}")
        elif isinstance(locator,ImageRegionLocator):memory_locator=SourceLocator(block=f"b{order:06d}",region=f"{locator.coordinate_space}:{locator.x},{locator.y},{locator.width},{locator.height}")
        elif isinstance(locator,(AudioTimeRangeLocator,VideoTimeRangeLocator)):memory_locator=SourceLocator(timestamp_seconds=locator.start_ms/1000,block=f"b{order:06d}",span=f"ms:{locator.start_ms}-{locator.end_ms}")
        elif isinstance(locator,VideoFrameLocator):memory_locator=SourceLocator(timestamp_seconds=locator.timestamp_ms/1000,block=f"b{order:06d}",span=f"frame:{locator.frame_index}")
        else:memory_locator=SourceLocator(block=f"b{order:06d}",span=repr(locator))
        key=f"m{order:06d}-{str(segment.id)[:8]}"
        return __import__("syune.study.model",fromlist=["PerceivedBlock"]).PerceivedBlock(ContentBlockId(uuid5(NAMESPACE_URL,f"syune:block:{segment.source_revision_id}:{key}")),key,segment.source_revision_id,segment.representation.value.lower(),segment.content,order,segment.fingerprint,memory_locator,self.perception_router.version,(),segment.run_id,segment.id,segment.method.value)

    def _record_parser_perception(self,blocks,revision,kind,data):
        byte_size=len(data)
        offsets=[0]
        if kind is not SourceKind.PDF:
            for line in data.decode("utf-8-sig").splitlines(keepends=True):offsets.append(offsets[-1]+len(line))
        config=sha256(f"study-parser-locators-v2:{revision.parser_version}:{kind.value}".encode()).hexdigest();run_id=PerceptionRunId(uuid5(NAMESPACE_URL,f"syune:perception:{revision.revision_id}:{kind.value}:{config}"));segments=[];updated=[]
        modality=Modality.DOCUMENT if kind is SourceKind.PDF else Modality.TEXT
        for block in blocks:
            if block.locator.page:
                locator=PageLocator(block.locator.page)
            else:
                import re
                match=re.fullmatch(r"lines:(\d+)-(\d+)",block.locator.span or "")
                if match is None:raise ValueError("parser text locator missing")
                first,last=map(int,match.groups())
                locator=TextLocator(offsets[first-1],offsets[last])
            fingerprint=segment_fingerprint(revision.revision_id,locator,RepresentationType.EXTRACTED_TEXT,config,block.text);segment_id=PerceivedSegmentId(uuid5(NAMESPACE_URL,f"syune:segment:{fingerprint}"))
            segment=PerceivedSegment(segment_id,revision.source_id,revision.source_version_id,revision.revision_id,run_id,modality,locator,RepresentationType.EXTRACTED_TEXT,block.text,PerceptionMethod.DETERMINISTIC_EXTRACTION,fingerprint,utc_now());segments.append(segment)
            updated.append(replace(block,perception_run_id=run_id,perceived_segment_id=segment_id,perception_method=PerceptionMethod.DETERMINISTIC_EXTRACTION.value))
        now=utc_now();run=PerceptionRun(run_id,revision.source_id,revision.source_version_id,revision.revision_id,"study-parser",revision.parser_version,config,now,now,RunStatus.COMPLETE,tuple(x.id for x in segments),(("deterministic_extraction",ComponentState.COMPLETE),),(),(),(("bytes",byte_size),("segments",len(segments))),DeterminismClass.DETERMINISTIC)
        self.registry.record_perception(run,tuple(segments));return tuple(updated)

    def _resume_perception(self,path,data,revision):
        result=self.perception_router.perceive(path,data,revision.source_id,revision.source_version_id,revision.revision_id)
        self.registry.record_perception(result.run,result.segments)
        blocks=tuple(self._perception_block(segment,n) for n,segment in enumerate(result.segments));self.registry.set_blocks(revision.revision_id,blocks)
        for block in blocks:
            oid=observation_id(revision.revision_id,block.key)
            from .encoder import trace_id
            tid=trace_id(revision.revision_id,block.key)
            if self.registry.has_encoded_block(revision.revision_id,block.key) and self.memory.exists(oid) and self.memory.exists(tid):continue
            observation,trace=self.encoder.encode(block,revision.source_id,revision.source_version_id,PIPELINE_VERSION)
            self.registry.record_encoded(revision.revision_id,block.key,str(observation),str(trace))
        status=self.registry.status(revision.revision_id)
        return StudyResult(Classification.INCOMPLETE,replace(status,classification=Classification.INCOMPLETE),materialization=self.materialization_status(revision.revision_id))

    def _new_revision(self, source_id: SourceId, digest: str,
                      classification: Classification,
                      previous_revision_id: SourceRevisionId | None,
                      locator: str, parser_version: str) -> StudyStatus:
        return self.registry.create_revision(
            source_id=source_id, source_version_id=SourceVersionId.new(),
            revision_id=SourceRevisionId.new(), job_id=StudyJobId.new(),
            run_id=StudyRunId.new(), digest=digest, classification=classification,
            previous_revision_id=previous_revision_id, locator=locator,
            parser_version=parser_version, pipeline_version=PIPELINE_VERSION,
            block_scheme_version=BLOCK_SCHEME_VERSION,
            encoder_version=ENCODER_VERSION,
        )

    def status_by_source_id(self, source_id: SourceId) -> StudyStatus | None:
        return self.registry.by_source_id(source_id)

    def status_by_locator(self, path: str | Path) -> StudyStatus | None:
        return self.registry.by_locator(str(Path(path).expanduser().resolve()))

    def status_by_fingerprint(self, digest: str) -> StudyStatus | None:
        return self.registry.by_fingerprint(digest)

    def _present_count(self, status: StudyStatus) -> int:
        ids = status.derived_memory_ids
        return sum(self.memory.exists(ObservationId.parse(value) if index % 2 == 0
                                      else MemoryTraceId.parse(value))
                   for index, value in enumerate(ids))

    def _all_memory_present(self, status: StudyStatus) -> bool:
        return (status.blocks_total > 0 and status.blocks_encoded == status.blocks_total
                and len(status.derived_memory_ids) == status.blocks_total * 2
                and self.memory.exists(status.source_id)
                and self._present_count(status) == len(status.derived_memory_ids))

    def materialization_status(self, revision_id: SourceRevisionId) -> MaterializationState:
        status = self.registry.status(revision_id)
        if not status.is_studied:
            return MaterializationState.NOT_ENCODED
        if self._all_memory_present(status):
            return MaterializationState.MATERIALIZED
        present = self._present_count(status) + int(self.memory.exists(status.source_id))
        return MaterializationState.PARTIAL_MEMORY if present else MaterializationState.MISSING_MEMORY
