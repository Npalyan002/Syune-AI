"""Stable public error envelope; implementation exceptions never cross this boundary."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .version import PUBLIC_API_VERSION


class ErrorCategory(str, Enum):
    INVALID_REQUEST = "INVALID_REQUEST"
    NOT_INITIALIZED = "NOT_INITIALIZED"
    NOT_FOUND = "NOT_FOUND"
    UNAVAILABLE = "UNAVAILABLE"
    DEGRADED = "DEGRADED"
    BLOCKED = "BLOCKED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    CONFLICT = "CONFLICT"
    LIMIT_EXCEEDED = "LIMIT_EXCEEDED"
    UNSUPPORTED_VERSION = "UNSUPPORTED_VERSION"
    INTERNAL = "INTERNAL"


@dataclass(eq=False)
class SyuneError(Exception):
    code: str
    message: str
    category: ErrorCategory
    retryable: bool = False
    blocked: bool = False
    details: dict[str, Any] = field(default_factory=dict)
    correlation_id: str | None = None
    resource_id: str | None = None
    operation_id: str | None = None
    public_api_version: str = PUBLIC_API_VERSION

    def __post_init__(self) -> None:
        Exception.__init__(self, self.message)

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code, "message": self.message, "category": self.category.value,
            "retryable": self.retryable, "blocked": self.blocked, "details": self.details,
            "correlation_id": self.correlation_id, "public_api_version": self.public_api_version,
            "resource_id": self.resource_id, "operation_id": self.operation_id,
        }
