import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from frontend.ui2figma.mcp_client import (
    DEFAULT_VSCODE_MCP_CONFIG,
    StdioMCPClient,
    load_vscode_mcp_server_config,
)
from frontend.ui2figma.orchestrator import run_text_to_figma_pipeline


class PlaceholderMCPClient:
    def run(self, _op: dict) -> dict:
        return {"status": "created"}


def build_mcp_client(
    mcp_source: str,
    mcp_server_name: str,
    mcp_config_path: Path | None,
):
    if mcp_source == "placeholder":
        return PlaceholderMCPClient()
    if mcp_source == "vscode-global":
        config = load_vscode_mcp_server_config(
            config_path=mcp_config_path or DEFAULT_VSCODE_MCP_CONFIG,
            server_name=mcp_server_name,
        )
        return StdioMCPClient(config)
    raise ValueError(f"Unsupported mcp source: {mcp_source}")


def run_from_file(
    spec_path: Path,
    review_decision: str,
    mcp_source: str = "placeholder",
    mcp_server_name: str = "Framelink_Figma_MCP",
    mcp_config_path: Path | None = None,
) -> dict:
    markdown_spec = spec_path.read_text(encoding="utf-8")
    client = build_mcp_client(
        mcp_source=mcp_source,
        mcp_server_name=mcp_server_name,
        mcp_config_path=mcp_config_path,
    )
    return run_text_to_figma_pipeline(markdown_spec, client, review_decision)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", required=True, help="Path toi ui-spec markdown")
    parser.add_argument("--review", required=True, choices=["OK", "revise"])
    parser.add_argument("--mcp-source", choices=["placeholder", "vscode-global"], default="placeholder")
    parser.add_argument("--mcp-server-name", default="Framelink_Figma_MCP")
    parser.add_argument("--mcp-config-path", default=None, help="Path toi VS Code mcp.json")
    args = parser.parse_args()

    result = run_from_file(
        spec_path=Path(args.spec),
        review_decision=args.review,
        mcp_source=args.mcp_source,
        mcp_server_name=args.mcp_server_name,
        mcp_config_path=Path(args.mcp_config_path) if args.mcp_config_path else None,
    )
    print(result)


if __name__ == "__main__":
    main()
