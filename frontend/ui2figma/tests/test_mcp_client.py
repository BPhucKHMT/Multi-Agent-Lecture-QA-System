from pathlib import Path

import pytest

from frontend.ui2figma.mcp_client import (
    VSCodeMCPServerConfig,
    load_vscode_mcp_server_config,
    resolve_tool_name,
    resolve_launch_command_and_args,
    resolve_launch_command,
)
from frontend.ui2figma.run_text_to_ui import build_mcp_client


def test_load_vscode_mcp_server_config_reads_nested_mcp_structure(tmp_path: Path):
    config_path = tmp_path / "mcp.json"
    config_path.write_text(
        """
{
  "mcp": {
    "servers": {
      "Framelink_Figma_MCP": {
        "type": "stdio",
        "command": "npx",
        "args": ["-y", "figma-developer-mcp", "token", "--stdio"],
        "env": {"FIGMA_TEAM": "demo"}
      }
    }
  }
}
""".strip(),
        encoding="utf-8",
    )

    server = load_vscode_mcp_server_config(config_path, "Framelink_Figma_MCP")

    assert isinstance(server, VSCodeMCPServerConfig)
    assert server.command == "npx"
    assert server.args[:2] == ["-y", "figma-developer-mcp"]
    assert server.env["FIGMA_TEAM"] == "demo"


def test_load_vscode_mcp_server_config_reads_top_level_servers_structure(tmp_path: Path):
    config_path = tmp_path / "mcp.json"
    config_path.write_text(
        """
{
  "servers": {
    "Framelink_Figma_MCP": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "figma-developer-mcp", "figd_example_token", "--stdio"]
    }
  }
}
""".strip(),
        encoding="utf-8",
    )

    server = load_vscode_mcp_server_config(config_path, "Framelink_Figma_MCP")
    assert server.command == "npx"
    assert "--figma-api-key" in server.args


def test_load_vscode_mcp_server_config_raises_for_missing_server(tmp_path: Path):
    config_path = tmp_path / "mcp.json"
    config_path.write_text('{"mcp":{"servers":{}}}', encoding="utf-8")

    with pytest.raises(ValueError):
        load_vscode_mcp_server_config(config_path, "Framelink_Figma_MCP")


def test_resolve_tool_name_prefers_exact_normalized_match():
    tool_name = resolve_tool_name(
        op_name="create_frame",
        available_tools=["foo", "create-frame", "create_text"],
    )
    assert tool_name == "create-frame"


def test_build_mcp_client_returns_placeholder_by_default():
    client = build_mcp_client(
        mcp_source="placeholder",
        mcp_server_name="Framelink_Figma_MCP",
        mcp_config_path=None,
    )
    assert hasattr(client, "run")


def test_resolve_launch_command_prefers_cmd_on_windows(monkeypatch):
    monkeypatch.setattr("frontend.ui2figma.mcp_client.os.name", "nt")
    monkeypatch.setattr(
        "frontend.ui2figma.mcp_client.shutil.which",
        lambda candidate: (
            "C:\\Program Files\\nodejs\\npx.cmd"
            if candidate == "npx.cmd"
            else "C:\\Program Files\\nodejs\\npx"
        ),
    )

    resolved = resolve_launch_command("npx")
    assert resolved.endswith("npx.cmd")


def test_load_vscode_mcp_server_config_upgrades_positional_figma_token(tmp_path: Path):
    config_path = tmp_path / "mcp.json"
    config_path.write_text(
        """
{
  "mcp": {
    "servers": {
      "Framelink_Figma_MCP": {
        "type": "stdio",
        "command": "npx",
        "args": ["-y", "figma-developer-mcp", "figd_example_token", "--stdio"]
      }
    }
  }
}
""".strip(),
        encoding="utf-8",
    )

    server = load_vscode_mcp_server_config(config_path, "Framelink_Figma_MCP")
    assert "--figma-api-key" in server.args
    assert "figd_example_token" in server.args


def test_resolve_launch_command_and_args_rewrites_npx_figma_when_binary_exists(monkeypatch):
    monkeypatch.setattr("frontend.ui2figma.mcp_client.os.name", "nt")
    monkeypatch.setenv("APPDATA", "C:\\does-not-exist")

    def fake_which(candidate: str):
        if candidate == "figma-developer-mcp.cmd":
            return "C:\\Users\\ADMIN\\AppData\\Roaming\\npm\\figma-developer-mcp.cmd"
        if candidate == "npx.cmd":
            return "C:\\Program Files\\nodejs\\npx.cmd"
        return None

    monkeypatch.setattr("frontend.ui2figma.mcp_client.shutil.which", fake_which)

    command, args = resolve_launch_command_and_args(
        command="npx",
        args=["-y", "figma-developer-mcp", "--figma-api-key", "figd_token", "--stdio"],
    )

    assert command.endswith("figma-developer-mcp.cmd")
    assert args == ["--figma-api-key", "figd_token", "--stdio"]
