"""Study workflow types; operational state is not epistemic truth."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from hashlib import sha256

from syune.core import ContentBlockId, OpaqueId, PerceivedSegmentId, PerceptionRunId, SourceId, SourceVersionId
from syune.memory import SourceLocator


class StudyJobId(OpaqueId):
    __slots__ = ()


class StudyRunId(OpaqueId):
    __slots__ = ()


class SourceRevisionId(OpaqueId):
    __slots__ = ()


class StudyState(str, Enum):
    DISCOVERED = "DISCOVERED"
    REGISTERED = "REGISTERED"
    PARSING = "PARSING"
    PERCEIVED = "PERCEIVED"
    UNDERSTOOD = "UNDERSTOOD"  # structural interpretation only in v1
    ENCODED = "ENCODED"
    CONSOLIDATING = "CONSOLIDATING"
    CONSOLIDATED = "CONSOLIDATED"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    REJECTED = "REJECTED"
    RETRACTED = "RETRACTED"


class Classification(str, Enum):
    NEW_SOURCE = "NEW_SOURCE"
    ALREADY_STUDIED = "ALREADY_STUDIED"
    CHANGED_SOURCE = "CHANGED_SOURCE"
    INCOMPLETE = "INCOMPLETE"


class MaterializationState(str, Enum):
    MATERIALIZED = "MATERIALIZED"
    PARTIAL_MEMORY = "PARTIAL_MEMORY"
    MISSING_MEMORY = "MISSING_MEMORY"
    NOT_ENCODED = "NOT_ENCODED"


class BlockChangeKind(str, Enum):
    UNCHANGED = "UNCHANGED"
    NEW = "NEW"
    CHANGED = "CHANGED"
    REMOVED = "REMOVED"


@dataclass(frozen=True, slots=True)
class PerceivedBlock:
    id: ContentBlockId
    key: str
    source_revision_id: SourceRevisionId
    content_kind: str
    text: str
    order: int
    fingerprint: str
    locator: SourceLocator
    parser_version: str
    heading_path: tuple[str, ...] = ()
    perception_run_id: PerceptionRunId | None = None
    perceived_segment_id: PerceivedSegmentId | None = None
    perception_method: str | None = None
    schema_version: str = "1"

    def __post_init__(self) -> None:
        if type(self.id) is not ContentBlockId or type(self.source_revision_id) is not SourceRevisionId:
            raise TypeError("typed block and revision IDs required")
        if not self.key or not self.content_kind or not self.text.strip() or not self.parser_version:
            raise ValueError("block text and metadata must be nonempty")
        if type(self.order) is not int or self.order < 0:
            raise ValueError("block order must be nonnegative")
        if len(self.fingerprint) != 64 or any(c not in "0123456789abcdef" for c in self.fingerprint):
            raise ValueError("block fingerprint must be SHA-256 hex")
        if not isinstance(self.locator, SourceLocator):
            raise TypeError("block locator required")
        if not isinstance(self.heading_path, tuple):
            raise TypeError("heading path must be a tuple")


@dataclass(frozen=True, slots=True)
class BlockChange:
    kind: BlockChangeKind
    previous_key: str | None
    current_key: str | None


@dataclass(frozen=True, slots=True)
class StudyStatus:
    source_id: SourceId
    source_version_id: SourceVersionId
    revision_id: SourceRevisionId
    job_id: StudyJobId
    run_id: StudyRunId
    classification: Classification
    state: StudyState
    sha256: str
    previous_revision_id: SourceRevisionId | None
    locators: tuple[str, ...]
    parser_version: str
    pipeline_version: str
    block_scheme_version: str
    encoder_version: str
    blocks_total: int
    blocks_processed: int
    blocks_encoded: int
    derived_memory_ids: tuple[str, ...]
    checkpoint: str | None
    error_code: str | None
    error_message: str | None
    first_seen: datetime
    last_processed: datetime | None

    @property
    def is_studied(self) -> bool:
        return self.state is StudyState.ENCODED and self.blocks_total > 0 and self.blocks_encoded == self.blocks_total


@dataclass(frozen=True, slots=True)
class StudyResult:
    classification: Classification
    status: StudyStatus
    block_changes: tuple[BlockChange, ...] = ()
    materialization: MaterializationState = MaterializationState.NOT_ENCODED


def source_fingerprint(data: bytes) -> str:
    return sha256(data).hexdigest()


def block_fingerprint(text: str) -> str:
    return sha256(text.replace("\r\n", "\n").encode("utf-8")).hexdigest()
