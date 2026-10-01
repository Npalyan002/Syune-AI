"""Product and component compatibility inventory."""
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

STATE_SCHEMA_VERSION = 1
COMPONENT_SCHEMAS = {
    "memory": "1", "study_perception": "1", "learning": "1", "execution": "1",
    "profiles": "1", "council": "none", "planner": "none",
}


@dataclass(frozen=True, slots=True)
class SyuneInstanceId:
    value: UUID

    @classmethod
    def new(cls) -> "SyuneInstanceId": return cls(uuid4())
    @classmethod
    def parse(cls, value: str) -> "SyuneInstanceId": return cls(UUID(value))
    def __str__(self) -> str: return str(self.value)


@dataclass(frozen=True, slots=True)
class ProductStateMetadata:
    product_version: str
    state_schema_version: int
    initialized_at: str
    instance_id: SyuneInstanceId
    last_successful_open: str | None
    component_schemas: dict[str, str]

    def validate(self) -> None:
        if self.state_schema_version != STATE_SCHEMA_VERSION:
            raise ValueError(f"unsupported product state schema: {self.state_schema_version}")
        if not self.product_version.strip(): raise ValueError("product version required")
        initialized = datetime.fromisoformat(self.initialized_at)
        if initialized.tzinfo is None: raise ValueError("initialized timestamp must be timezone-aware")
        if self.last_successful_open is not None:
            opened = datetime.fromisoformat(self.last_successful_open)
            if opened.tzinfo is None: raise ValueError("open timestamp must be timezone-aware")
        if not isinstance(self.instance_id, SyuneInstanceId): raise TypeError("typed instance identity required")
        if self.component_schemas != COMPONENT_SCHEMAS:
            raise ValueError("unsupported component schema inventory")
