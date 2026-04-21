import subprocess
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, os.fspath(PROJECT_ROOT))

from src.rag_core.tools.sandbox import execute_python_code

def test_execute_python_code_success():
    result = execute_python_code("print('Hello Math')")
    assert result["success"] is True
    assert "Hello Math" in result["stdout"]

def test_execute_python_code_security():
    result = execute_python_code("import os\nos.system('echo hi')")
    assert result["success"] is False
    assert "chứa mã nguy hiểm bị cấm" in result["stderr"]


def test_sandbox_allows_os_path():
    result = execute_python_code("import os\nprint(os.path.exists('.'))")
    assert result["success"] is True


def test_sandbox_blocks_os_system():
    result = execute_python_code("import os\nos.system('echo hack')")
    assert result["success"] is False


def test_sandbox_allows_pathlib():
    result = execute_python_code("from pathlib import Path\nprint(Path('.').resolve())")
    assert result["success"] is True


def test_sandbox_blocks_dynamic_import_os_system():
    result = execute_python_code('__import__("os").system("echo hack")')
    assert result["success"] is False


def test_sandbox_blocks_importlib_import_module():
    result = execute_python_code('import importlib\nimportlib.import_module("os").system("echo hack")')
    assert result["success"] is False


def test_sandbox_blocks_getattr_os_system():
    result = execute_python_code('import os\ngetattr(os, "system")("echo hack")')
    assert result["success"] is False


def test_sandbox_blocks_getattr_os_system_with_computed_name():
    result = execute_python_code('import os\nfn = getattr(os, "sy" + "stem")\nfn("echo hack")')
    assert result["success"] is False


def test_sandbox_blocks_getattr_importlib_import_module():
    result = execute_python_code('import importlib\ngetattr(importlib, "import_module")("os").system("echo hack")')
    assert result["success"] is False


def test_sandbox_blocks_builtins_dict_import():
    result = execute_python_code('import builtins\nbuiltins.__dict__["__import__"]("os").system("echo hack")')
    assert result["success"] is False


def test_execute_python_code_handles_unicode_decode_error(monkeypatch):
    def _raise_decode_error(*_args, **_kwargs):
        raise UnicodeDecodeError("utf-8", b"\x92", 0, 1, "invalid start byte")

    monkeypatch.setattr(subprocess, "run", _raise_decode_error)

    result = execute_python_code("print('hello')")

    assert result["success"] is False
    assert "giải mã output" in result["stderr"]
    assert "UnicodeDecodeError" not in result["stderr"]


def test_execute_python_code_supports_utf8_stdout_text():
    result = execute_python_code('print("Kết luận ngắn: đạo hàm bậc hai đổi dấu.")')
    assert result["success"] is True
    assert "Kết luận ngắn" in result["stdout"]
