"""Stable product CLI; parsing remains separate from domain services."""
from __future__ import annotations

import argparse
import json
import logging
import sys

from syune import __version__
from syune.product.config import load_config

SUCCESS, INTERNAL_ERROR, INVALID_INPUT, NOT_INITIALIZED, UNHEALTHY, BLOCKED = range(6)


def _common() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--state-root", default=argparse.SUPPRESS)
    parser.add_argument("--config", default=argparse.SUPPRESS)
    parser.add_argument("--log-level", choices=("ERROR", "WARNING", "INFO", "DEBUG"), default=argparse.SUPPRESS)
    parser.add_argument("--json", action="store_true", dest="json_output", default=argparse.SUPPRESS)
    parser.add_argument("--debug", action="store_true", default=argparse.SUPPRESS)
    return parser


def _parser() -> argparse.ArgumentParser:
    common = _common()
    parser = argparse.ArgumentParser(prog="syune", parents=[common], description="SYUNE local product lifecycle")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("init", "health", "status", "version"):
        commands.add_parser(name, parents=[common], add_help=True)
    config = commands.add_parser("config", parents=[common], add_help=True)
    config_commands = config.add_subparsers(dest="config_command", required=True)
    config_commands.add_parser("show", parents=[common], add_help=True)
    config_commands.add_parser("validate", parents=[common], add_help=True)
    upgrade = commands.add_parser("upgrade", parents=[common], add_help=True)
    upgrade.add_subparsers(dest="upgrade_command", required=True).add_parser("check", parents=[common], add_help=True)
    mcp = commands.add_parser("mcp", parents=[common], add_help=True)
    mcp.add_subparsers(dest="mcp_command", required=True).add_parser("serve", parents=[common], add_help=True)
    return parser


def _emit(value: dict[str, object], structured: bool) -> None:
    if structured:
        print(json.dumps(value, sort_keys=True))
        return
    for key, item in value.items():
        if isinstance(item, dict):
            print(f"{key}:")
            for child, state in item.items(): print(f"  {child}: {state}")
        else: print(f"{key}: {item}")


def _status(config) -> dict[str, object]:
    from syune.product.state import load_metadata, missing_databases
    metadata = load_metadata(config.state.root)
    missing = missing_databases(config.state.root)
    if missing: raise ValueError("initialized state is missing component databases: " + ", ".join(missing))
    return {
        "version": __version__, "state_root": str(config.state.root), "initialized": True,
        "instance_id": str(metadata.instance_id), "state_schema_version": metadata.state_schema_version,
        "component_schemas": metadata.component_schemas,
        "optional_capabilities": {"external_providers": "unconfigured", "multimodal_local": "available"},
        "read_only": config.mcp.shadow_read_only, "last_successful_open": metadata.last_successful_open,
        "study_roots": [str(x) for x in config.study.roots], "telemetry": "OFF",
    }


def run(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        config = load_config(cli_state_root=getattr(args,"state_root",None), cli_config=getattr(args,"config",None),
                             cli_log_level=getattr(args,"log_level",None))
        structured = getattr(args,"json_output",False)
        logging.basicConfig(level=getattr(logging, config.logging.level), format="%(levelname)s %(message)s")
        if args.command == "version":
            _emit({"version": __version__}, structured); return SUCCESS
        if args.command == "config":
            value = config.public_dict()
            if args.config_command == "validate": value = {"valid": True, "config": value}
            _emit(value, structured); return SUCCESS
        if args.command == "init":
            from syune.product.state import initialize_state
            metadata, created = initialize_state(config)
            _emit({"initialized": True, "created": created, "state_root": str(config.state.root),
                   "instance_id": str(metadata.instance_id), "state_schema_version": metadata.state_schema_version}, structured)
            return SUCCESS
        if args.command == "status":
            _emit(_status(config), structured); return SUCCESS
        if args.command == "health":
            from syune.product.runtime import SyuneRuntime
            with SyuneRuntime.open(config) as runtime: result = runtime.health()
            _emit(result, structured)
            return SUCCESS if result["overall"] == "HEALTHY" else UNHEALTHY
        if args.command == "upgrade":
            from syune.product.state import upgrade_check
            _emit(upgrade_check(config.state.root), structured); return SUCCESS
        if args.command == "mcp":
            from syune import Syune
            from syune.gateway.mcp import create_lean_mcp_server
            with Syune.open(state_root=config.state.root,
                            mode="SHADOW" if config.mcp.shadow_read_only else "NORMAL") as client:
                create_lean_mcp_server(client).run(transport="stdio")
            return SUCCESS
        return INVALID_INPUT
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr); return NOT_INITIALIZED
    except (ValueError, PermissionError) as exc:
        print(str(exc), file=sys.stderr); return INVALID_INPUT
    except Exception as exc:
        if getattr(args, "debug", False): raise
        print(f"internal failure: {type(exc).__name__}", file=sys.stderr); return INTERNAL_ERROR


def main(argv: list[str] | None = None) -> None:
    raise SystemExit(run(argv))


if __name__ == "__main__": main()
