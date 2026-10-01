"""Run packaged MCP through the same product config and state resolver as the CLI."""
from syune.cli.app import main as cli_main


def main() -> None:
    cli_main(["mcp", "serve"])


if __name__ == "__main__":
    main()
