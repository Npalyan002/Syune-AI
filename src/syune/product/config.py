"""Typed local configuration with defaults < file < environment < CLI precedence."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import os
import sys
from typing import Mapping
from pathlib import Path, PurePosixPath, PureWindowsPath
import tomllib

LOG_LEVELS = frozenset({"ERROR", "WARNING", "INFO", "DEBUG"})


def _default_state_root_for(platform: str, environment: Mapping[str, str], home: str) -> str:
    if platform == "win32":
        base = environment.get("LOCALAPPDATA")
        return str((PureWindowsPath(base) if base else PureWindowsPath(home) / "AppData" / "Local") / "SYUNE" / "default")
    if platform == "darwin" and not environment.get("XDG_STATE_HOME"):
        return str(PurePosixPath(home) / "Library" / "Application Support" / "SYUNE" / "default")
    base = environment.get("XDG_STATE_HOME")
    return str((PurePosixPath(base) if base else PurePosixPath(home) / ".local" / "state") / "syune" / "default")


def default_state_root() -> Path:
    return Path(_default_state_root_for(sys.platform, os.environ, str(Path.home())))

def _absolute(value: str | Path, name: str) -> Path:
    raw = Path(value).expanduser()
    if not raw.is_absolute():
        raise ValueError(f"{name} must be an absolute path")
    return raw.resolve(strict=False)


@dataclass(frozen=True, slots=True)
class StateConfig:
    root: Path


@dataclass(frozen=True, slots=True)
class StudyConfig:
    roots: tuple[Path, ...] = ()


@dataclass(frozen=True, slots=True)
class RetrievalConfig:
    max_results: int = 16


@dataclass(frozen=True, slots=True)
class LoggingConfig:
    level: str = "INFO"


@dataclass(frozen=True, slots=True)
class McpConfig:
    shadow_read_only: bool = False

@dataclass(frozen=True, slots=True)
class FeaturesConfig:
    """Default product surface. Research subsystems are explicit opt-ins."""
    model_gateway: bool = True
    semantic_retrieval: bool = False
    learning: bool = False
    research_cognition: bool = False


@dataclass(frozen=True, slots=True)
class SyuneConfig:
    state: StateConfig
    study: StudyConfig = StudyConfig()
    retrieval: RetrievalConfig = RetrievalConfig()
    logging: LoggingConfig = LoggingConfig()
    mcp: McpConfig = McpConfig()
    features: FeaturesConfig = FeaturesConfig()
    config_file: Path | None = None
    telemetry: bool = False

    def __post_init__(self) -> None:
        if not 1 <= self.retrieval.max_results <= 100:
            raise ValueError("retrieval.max_results must be 1..100")
        if self.logging.level not in LOG_LEVELS:
            raise ValueError("logging.level must be ERROR, WARNING, INFO, or DEBUG")
        if self.telemetry:
            raise ValueError("telemetry is unavailable and must remain off")
        for root in self.study.roots:
            if not root.is_dir():
                raise ValueError(f"Study root is not an existing directory: {root}")

    def public_dict(self) -> dict[str, object]:
        value = asdict(self)
        value["state"]["root"] = str(self.state.root)
        value["study"]["roots"] = [str(x) for x in self.study.roots]
        value["config_file"] = str(self.config_file) if self.config_file else None
        return value


def _table(path: Path | None) -> dict:
    if path is None or not path.exists():
        return {}
    if not path.is_file():
        raise ValueError("config path must be a file")
    try:
        with path.open("rb") as stream:
            value = tomllib.load(stream)
    except tomllib.TOMLDecodeError as exc:
        raise ValueError("malformed TOML config") from exc
    allowed = {"state", "study", "retrieval", "logging", "mcp", "features"}
    if set(value) - allowed or any(not isinstance(section, dict) for section in value.values()):
        raise ValueError("unknown or invalid config section")
    keys = {"state": {"root"}, "study": {"roots"}, "retrieval": {"max_results"},
            "logging": {"level"}, "mcp": {"shadow_read_only"},
            "features": {"model_gateway", "semantic_retrieval", "learning", "research_cognition"}}
    for section, settings in value.items():
        if set(settings) - keys[section]:
            raise ValueError(f"unknown config key in {section}")
    return value


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    if raw not in ("0", "1"):
        raise ValueError(f"{name} must be 0 or 1")
    return raw == "1"


def load_config(*, cli_state_root: str | Path | None = None, cli_config: str | Path | None = None,
                cli_log_level: str | None = None) -> SyuneConfig:
    initial_root = _absolute(cli_state_root or os.environ.get("SYUNE_STATE_ROOT") or default_state_root(), "state root")
    config_value = cli_config or os.environ.get("SYUNE_CONFIG")
    config_path = _absolute(config_value, "config") if config_value else initial_root / "config.toml"
    data = _table(config_path)
    state_root = _absolute(data.get("state", {}).get("root", initial_root), "state root")
    if os.environ.get("SYUNE_STATE_ROOT"):
        state_root = _absolute(os.environ["SYUNE_STATE_ROOT"], "state root")
    if cli_state_root is not None:
        state_root = _absolute(cli_state_root, "state root")
    roots = data.get("study", {}).get("roots", [])
    if type(roots) is not list or any(type(x) is not str for x in roots):
        raise ValueError("study.roots must be a list of absolute paths")
    if "SYUNE_STUDY_ROOTS" in os.environ:
        roots = [x for x in os.environ["SYUNE_STUDY_ROOTS"].split(os.pathsep) if x]
    typed_roots = tuple(_absolute(x, "Study root") for x in roots)
    max_results = data.get("retrieval", {}).get("max_results", 16)
    if type(max_results) is not int:
        raise ValueError("retrieval.max_results must be an integer")
    if "SYUNE_MAX_RECALL_RESULTS" in os.environ:
        try: max_results = int(os.environ["SYUNE_MAX_RECALL_RESULTS"])
        except ValueError as exc: raise ValueError("SYUNE_MAX_RECALL_RESULTS must be an integer") from exc
    level = os.environ.get("SYUNE_LOG_LEVEL", data.get("logging", {}).get("level", "INFO"))
    if cli_log_level is not None: level = cli_log_level
    shadow = data.get("mcp", {}).get("shadow_read_only", False)
    if type(shadow) is not bool: raise ValueError("mcp.shadow_read_only must be true or false")
    shadow = _env_bool("SYUNE_MCP_SHADOW_READ_ONLY", shadow)
    raw_features = data.get("features", {})
    for key, value in raw_features.items():
        if type(value) is not bool: raise ValueError(f"features.{key} must be true or false")
    features = FeaturesConfig(
        _env_bool("SYUNE_MODEL_GATEWAY", raw_features.get("model_gateway", True)),
        _env_bool("SYUNE_SEMANTIC_RETRIEVAL", raw_features.get("semantic_retrieval", False)),
        _env_bool("SYUNE_LEARNING", raw_features.get("learning", False)),
        _env_bool("SYUNE_RESEARCH_COGNITION", raw_features.get("research_cognition", False)),
    )
    return SyuneConfig(StateConfig(state_root), StudyConfig(typed_roots), RetrievalConfig(max_results),
                       LoggingConfig(str(level).upper()), McpConfig(shadow), features,
                       config_path if config_path.exists() else None, False)
