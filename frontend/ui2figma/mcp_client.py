import json
import os
import queue
import shutil
import subprocess
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


DEFAULT_VSCODE_MCP_CONFIG = Path.home() / "AppData" / "Roaming" / "Code" / "User" / "mcp.json"


@dataclass
class VSCodeMCPServerConfig:
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)


def _normalize_tool_name(name: str) -> str:
    return name.lower().replace("-", "_").replace(":", "_").strip()


def resolve_tool_name(op_name: str, available_tools: list[str]) -> str | None:
    target = _normalize_tool_name(op_name)
    normalized = {tool: _normalize_tool_name(tool) for tool in available_tools}

    for tool, normalized_name in normalized.items():
        if normalized_name == target:
            return tool

    if target.startswith("create_"):
        suffix = target.replace("create_", "", 1)
        for tool, normalized_name in normalized.items():
            if normalized_name.startswith("create_") and suffix in normalized_name:
                return tool

    return None


def resolve_launch_command(command: str) -> str:
    if os.name == "nt":
        command_with_cmd = shutil.which(f"{command}.cmd")
        if command_with_cmd:
            return command_with_cmd
    return shutil.which(command) or command


def resolve_launch_command_and_args(command: str, args: list[str]) -> tuple[str, list[str]]:
    if command == "npx" and args:
        package_name = args[1] if len(args) > 1 and args[0] in {"-y", "--yes"} else args[0]
        if package_name == "figma-developer-mcp":
            cleaned_args = [arg for arg in args if arg not in {"-y", "--yes", "figma-developer-mcp"}]
            global_entrypoint = Path(os.getenv("APPDATA", "")) / "npm" / "node_modules" / "figma-developer-mcp" / "dist" / "bin.js"
            node_binary = resolve_launch_command("node")
            if global_entrypoint.exists() and node_binary != "node":
                return node_binary, [str(global_entrypoint), *cleaned_args]
            figma_binary = resolve_launch_command("figma-developer-mcp")
            if figma_binary != "figma-developer-mcp":
                return figma_binary, cleaned_args
    return resolve_launch_command(command), args


def _normalize_figma_server_args(args: list[str]) -> list[str]:
    if "--figma-api-key" in args or "--figma-oauth-token" in args:
        return args

    upgraded: list[str] = []
    token_value: str | None = None
    for arg in args:
        if arg.startswith("figd_") and token_value is None:
            token_value = arg
            continue
        upgraded.append(arg)

    if token_value is None:
        return args

    insert_index = len(upgraded)
    if "--stdio" in upgraded:
        insert_index = upgraded.index("--stdio")
    return upgraded[:insert_index] + ["--figma-api-key", token_value] + upgraded[insert_index:]


def load_vscode_mcp_server_config(config_path: Path, server_name: str) -> VSCodeMCPServerConfig:
    if not config_path.exists():
        raise ValueError(f"MCP config not found: {config_path}")

    data = json.loads(config_path.read_text(encoding="utf-8"))
    servers = (data.get("mcp") or {}).get("servers") or data.get("servers") or {}
    server = servers.get(server_name)
    if not server:
        raise ValueError(f"MCP server '{server_name}' not found in {config_path}")
    if server.get("type") != "stdio":
        raise ValueError(f"MCP server '{server_name}' is not stdio type")
    command = server.get("command")
    if not command:
        raise ValueError(f"MCP server '{server_name}' missing command")

    args = [str(arg) for arg in (server.get("args") or [])]
    if server_name == "Framelink_Figma_MCP":
        args = _normalize_figma_server_args(args)

    return VSCodeMCPServerConfig(
        command=command,
        args=args,
        env={str(k): str(v) for k, v in (server.get("env") or {}).items()},
    )


class StdioMCPClient:
    def __init__(self, server_config: VSCodeMCPServerConfig, timeout_seconds: float = 120.0):
        self.server_config = server_config
        self.timeout_seconds = timeout_seconds
        self._proc: subprocess.Popen[bytes] | None = None
        self._request_id = 0
        self._tools: list[str] | None = None
        self._initialized = False
        self._message_queue: "queue.Queue[dict[str, Any]]" = queue.Queue()
        self._reader_thread: threading.Thread | None = None

    def _start(self) -> None:
        if self._proc:
            return
        env = os.environ.copy()
        env.update(self.server_config.env)
        launch_command, launch_args = resolve_launch_command_and_args(
            self.server_config.command,
            self.server_config.args,
        )
        self._proc = subprocess.Popen(
            [launch_command, *launch_args],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )
        self._reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
        self._reader_thread.start()

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def _send_message(self, payload: dict[str, Any]) -> None:
        if not self._proc or not self._proc.stdin:
            raise RuntimeError("MCP process stdin is not available")
        body = json.dumps(payload, ensure_ascii=False)
        self._proc.stdin.write((body + "\n").encode("utf-8"))
        self._proc.stdin.flush()

    def _read_message_from_stdout(self) -> dict[str, Any]:
        if not self._proc or not self._proc.stdout:
            raise RuntimeError("MCP process stdout is not available")
        while True:
            line = self._proc.stdout.readline()
            if not line:
                raise RuntimeError("MCP process closed stdout unexpectedly")
            decoded = line.decode("utf-8", errors="ignore").strip()
            if not decoded:
                continue
            try:
                return json.loads(decoded)
            except json.JSONDecodeError:
                continue

    def _reader_loop(self) -> None:
        try:
            while True:
                message = self._read_message_from_stdout()
                self._message_queue.put(message)
        except Exception as error:  # noqa: BLE001
            self._message_queue.put({"__reader_error__": str(error)})

    def _request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        request_id = self._next_id()
        self._send_message(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": params or {},
            }
        )
        while True:
            try:
                response = self._message_queue.get(timeout=self.timeout_seconds)
            except queue.Empty as error:
                stderr_tail = ""
                if self._proc and self._proc.poll() is not None and self._proc.stderr:
                    try:
                        stderr_tail = self._proc.stderr.read().decode("utf-8", errors="ignore").strip()
                    except Exception:  # noqa: BLE001
                        stderr_tail = ""
                detail = f"MCP request timeout for method '{method}'"
                if stderr_tail:
                    detail = f"{detail}; stderr: {stderr_tail}"
                raise RuntimeError(detail) from error
            if "__reader_error__" in response:
                stderr_tail = ""
                if self._proc and self._proc.poll() is not None and self._proc.stderr:
                    try:
                        stderr_tail = self._proc.stderr.read().decode("utf-8", errors="ignore").strip()
                    except Exception:  # noqa: BLE001
                        stderr_tail = ""
                detail = f"MCP reader failed: {response['__reader_error__']}"
                if stderr_tail:
                    detail = f"{detail}; stderr: {stderr_tail}"
                raise RuntimeError(detail)
            if response.get("id") == request_id:
                return response

    def _notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        self._send_message(
            {
                "jsonrpc": "2.0",
                "method": method,
                "params": params or {},
            }
        )

    def _initialize_if_needed(self) -> None:
        if self._initialized:
            return

        self._start()
        init_response = self._request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "ui2figma-runner", "version": "1.0.0"},
            },
        )
        if init_response.get("error"):
            raise RuntimeError(f"MCP initialize failed: {init_response['error']}")

        self._notify("notifications/initialized", {})
        self._initialized = True

    def _load_tools(self) -> list[str]:
        if self._tools is not None:
            return self._tools

        self._initialize_if_needed()
        response = self._request("tools/list", {})
        if response.get("error"):
            raise RuntimeError(f"MCP tools/list failed: {response['error']}")

        tools = (response.get("result") or {}).get("tools") or []
        self._tools = [tool.get("name", "") for tool in tools if tool.get("name")]
        return self._tools

    def run(self, op: dict[str, Any]) -> dict[str, Any]:
        op_name = op.get("op")
        if not op_name:
            return {"status": "warning", "error": "missing_op_name"}

        try:
            tool_name = resolve_tool_name(op_name, self._load_tools())
            if not tool_name:
                return {
                    "status": "warning",
                    "error": "tool_not_found",
                    "op": op_name,
                    "available_tools": self._tools or [],
                }

            args = {k: v for k, v in op.items() if k != "op"}
            response = self._request("tools/call", {"name": tool_name, "arguments": args})
            if response.get("error"):
                return {"status": "warning", "error": response["error"], "tool": tool_name}

            result = response.get("result") or {}
            if result.get("isError"):
                return {"status": "warning", "error": result.get("content"), "tool": tool_name}

            status = "created" if str(op_name).startswith("create_") else "updated"
            return {"status": status, "tool": tool_name}
        except Exception as error:  # noqa: BLE001
            return {"status": "warning", "error": str(error), "op": op_name}

    def close(self) -> None:
        if not self._proc:
            return
        try:
            if self._proc.poll() is None:
                self._proc.terminate()
                self._proc.wait(timeout=3)
        except Exception:  # noqa: BLE001
            if self._proc and self._proc.poll() is None:
                self._proc.kill()
        finally:
            self._proc = None

    def __del__(self) -> None:
        self.close()
