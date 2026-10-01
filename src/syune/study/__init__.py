"""Deterministic local Study System v1. Perception is not factual truth."""
from .errors import StudyError, StudyErrorCode
from .model import (
    BlockChange, BlockChangeKind, Classification, MaterializationState, PerceivedBlock,
    SourceRevisionId, StudyJobId, StudyResult, StudyRunId, StudyState,
    StudyStatus, block_fingerprint, source_fingerprint,
)
from .parsers import MarkdownParser, PdfTextParser, SourceParser, TxtParser
from .registry import SqliteStudyRegistry, StudyRegistry
from .service import StudyService

__all__ = [
    "BlockChange", "BlockChangeKind", "Classification", "MaterializationState", "PerceivedBlock",
    "SourceRevisionId", "StudyJobId", "StudyResult", "StudyRunId",
    "StudyState", "StudyStatus", "StudyError", "StudyErrorCode",
    "block_fingerprint", "source_fingerprint", "MarkdownParser",
    "PdfTextParser", "SourceParser", "TxtParser", "SqliteStudyRegistry",
    "StudyRegistry", "StudyService",
]
