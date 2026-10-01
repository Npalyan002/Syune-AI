"""Structured Phase 07 learning errors."""
from enum import Enum


class LearningErrorCode(str, Enum):
    INVALID_SIGNAL = "INVALID_SIGNAL"
    UNKNOWN_TARGET = "UNKNOWN_TARGET"
    DUPLICATE_SIGNAL = "DUPLICATE_SIGNAL"
    INVALID_POLICY = "INVALID_POLICY"
    INCOMPATIBLE_SCHEMA = "INCOMPATIBLE_SCHEMA"
    CONSOLIDATION_FAILED = "CONSOLIDATION_FAILED"
    ROLLBACK_NOT_FOUND = "ROLLBACK_NOT_FOUND"
    ALREADY_ROLLED_BACK = "ALREADY_ROLLED_BACK"


class LearningError(Exception):
    def __init__(self, code: LearningErrorCode, message: str):
        self.code = code
        super().__init__(message)
