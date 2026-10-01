"""Canonical deterministic JSON serialization for public contracts."""
from dataclasses import fields, is_dataclass
from datetime import datetime, timezone
from enum import Enum
import json
from pathlib import Path
from uuid import UUID


def to_primitive(value):
    if isinstance(value, Enum): return value.value
    if isinstance(value, datetime):
        if value.tzinfo is None: raise ValueError("public timestamps must be timezone-aware")
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(value, UUID): return str(value)
    if isinstance(value, Path): return str(value)
    if is_dataclass(value):
        if type(value).__name__.endswith("Id") and hasattr(value, "value"):
            return f"{type(value).__name__}:{value}"
        return {item.name: to_primitive(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, dict): return {str(key): to_primitive(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)): return [to_primitive(item) for item in value]
    return value


def canonical_json(value) -> str:
    return json.dumps(to_primitive(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
