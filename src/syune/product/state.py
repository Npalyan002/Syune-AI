"""Safe initialization and local compatibility checks."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from .config import SyuneConfig
from .schema import COMPONENT_SCHEMAS, ProductStateMetadata, STATE_SCHEMA_VERSION, SyuneInstanceId
from syune.release import RELEASE_VERSION

STATE_DIRS = ("memory", "study", "learning", "executive", "execution", "audit", "cache", "artifacts", "logs", "metadata")
DATABASES = {
    "memory": Path("memory/memory.sqlite3"),
    "study_perception": Path("study/study.sqlite3"),
    "learning": Path("learning/learning.sqlite3"),
    "execution": Path("execution/execution.sqlite3"),
    "audit": Path("audit/audit.sqlite3"),
}
REQUIRED_DATABASES = ("memory", "study_perception", "learning", "execution", "audit")


def metadata_path(root: Path) -> Path:
    return root / "metadata" / "state.json"


def _decode(raw: object) -> ProductStateMetadata:
    if not isinstance(raw, dict) or set(raw) != {
        "product_version", "state_schema_version", "initialized_at", "instance_id",
        "last_successful_open", "component_schemas",
    }:
        raise ValueError("corrupt product state metadata")
    value = ProductStateMetadata(raw["product_version"],raw["state_schema_version"],raw["initialized_at"],
        SyuneInstanceId.parse(raw["instance_id"]),raw["last_successful_open"],raw["component_schemas"])
    value.validate()
    return value


def load_metadata(root: Path) -> ProductStateMetadata:
    path = metadata_path(root)
    if not path.is_file():
        raise FileNotFoundError("SYUNE state is not initialized")
    try:
        return _decode(json.loads(path.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, TypeError, KeyError) as exc:
        raise ValueError("corrupt product state metadata") from exc


def _write_metadata(root: Path, value: ProductStateMetadata) -> None:
    path = metadata_path(root)
    temporary = path.with_suffix(".json.tmp")
    payload={"product_version":value.product_version,"state_schema_version":value.state_schema_version,
        "initialized_at":value.initialized_at,"instance_id":str(value.instance_id),
        "last_successful_open":value.last_successful_open,"component_schemas":value.component_schemas}
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(path)


def _initialize_databases(root: Path) -> None:
    # Memory and source registry are the lean product stores. The two legacy
    # databases remain schema-v1 compatibility artifacts, but their modules are
    # imported only during initialization and never on default runtime startup.
    from syune.memory import SQLiteMemoryRepository
    from syune.study import SqliteStudyRegistry
    from syune.learning import SQLiteLearningStore
    from syune.executive import SQLiteExecutionRepository
    from syune.audit import SQLiteAuditStore
    with SQLiteMemoryRepository(root / DATABASES["memory"]): pass
    with SqliteStudyRegistry(root / DATABASES["study_perception"]): pass
    with SQLiteLearningStore(root / DATABASES["learning"]): pass
    execution = SQLiteExecutionRepository(root / DATABASES["execution"])
    execution.close()
    with SQLiteAuditStore(root / DATABASES["audit"]): pass


def initialize_state(config: SyuneConfig) -> tuple[ProductStateMetadata, bool]:
    root = config.state.root
    root.mkdir(parents=True, exist_ok=True)
    allowed = set(STATE_DIRS) | {"config.toml"}
    unexpected = {item.name for item in root.iterdir()} - allowed
    if unexpected:
        raise ValueError("state root contains unknown entries; initialization stopped")
    existing = metadata_path(root)
    if existing.exists():
        metadata = load_metadata(root)
        missing = missing_databases(root)
        if missing:
            raise ValueError("initialized state is missing component databases: " + ", ".join(missing))
        _initialize_databases(root)  # validates only; repository constructors reject incompatible state.
        return metadata, False
    for name in STATE_DIRS:
        (root / name).mkdir(exist_ok=True)
    _initialize_databases(root)
    now = datetime.now(timezone.utc).isoformat()
    metadata = ProductStateMetadata(RELEASE_VERSION, STATE_SCHEMA_VERSION, now, SyuneInstanceId.new(), None,
                                    dict(COMPONENT_SCHEMAS))
    _write_metadata(root, metadata)
    return metadata, True


def record_successful_open(root: Path, metadata: ProductStateMetadata) -> ProductStateMetadata:
    value = ProductStateMetadata(metadata.product_version, metadata.state_schema_version,
        metadata.initialized_at, metadata.instance_id, datetime.now(timezone.utc).isoformat(),
        dict(metadata.component_schemas))
    _write_metadata(root, value)
    return value


def missing_databases(root: Path) -> list[str]:
    return [name for name in REQUIRED_DATABASES if not (root / DATABASES[name]).is_file()]


def upgrade_check(root: Path) -> dict[str, object]:
    metadata = load_metadata(root)
    missing = missing_databases(root)
    if missing: raise ValueError("initialized state is missing component databases: " + ", ".join(missing))
    return {
        "compatible": True,
        "current_product_version": RELEASE_VERSION,
        "state_product_version": metadata.product_version,
        "state_schema_version": metadata.state_schema_version,
        "supported_state_schema_version": STATE_SCHEMA_VERSION,
        "migration_required": False,
        "migration_available": False,
        "downgrade_supported": False,
    }
