import atexit
import tempfile
import subprocess
import ast
import os
import re
import sys

FORBIDDEN_MODULES = {"subprocess", "shutil", "socket"}
FORBIDDEN_CALLS = {
    "os": {
        "system",
        "popen",
        "execv",
        "execve",
        "execvp",
        "execvpe",
        "execl",
        "execle",
        "execlp",
        "execlpe",
        "remove",
        "unlink",
        "rmdir",
        "removedirs",
    },
    "sys": {"exit"},
}
FORBIDDEN_BUILTINS = {"__import__", "eval", "exec"}
FORBIDDEN_DYNAMIC_IMPORT_CALLS = {"import_module"}
FORBIDDEN_REFLECTIVE_ATTRS = set().union(
    FORBIDDEN_BUILTINS,
    FORBIDDEN_DYNAMIC_IMPORT_CALLS,
    *FORBIDDEN_CALLS.values(),
)

# Pattern nhận diện code có training loop deep learning — không phù hợp chạy trong sandbox
# Mỗi tuple: (primary_pattern, secondary_pattern_or_None)
# is_long_running = True khi primary match VÀ (secondary là None HOẶC secondary match)
_HEAVY_PATTERNS = [
    (r"model\.fit\(", r"(?:tensorflow|keras|torch)"),
    (r"trainer\.train\(", None),
    (r"for\s+epoch\s+in\s+range\(", r"(?:torch|tensorflow|keras)"),
    (r"\.train\(\s*\)", r"(?:torch|nn\.Module)"),
]


def is_long_running(code: str) -> bool:
    """Nhận diện code có training loop DL — không phù hợp chạy trong sandbox."""
    for primary, secondary in _HEAVY_PATTERNS:
        if re.search(primary, code):
            if secondary is None or re.search(secondary, code):
                return True
    return False


def _string_literal(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _subscript_string(slice_node: ast.AST) -> str | None:
    if hasattr(ast, "Index") and isinstance(slice_node, ast.Index):
        slice_node = slice_node.value
    return _string_literal(slice_node)

def is_safe(code: str) -> bool:
    try:
        tree = ast.parse(code)
        module_aliases = {module: set() for module in FORBIDDEN_CALLS}
        direct_call_aliases = {module: set() for module in FORBIDDEN_CALLS}
        importlib_aliases = set()
        importlib_direct_aliases = set()
        builtins_aliases = {"__builtins__"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    base_module = name.name.split('.')[0]
                    if base_module in FORBIDDEN_MODULES:
                        return False
                    if base_module in FORBIDDEN_CALLS:
                        module_aliases[base_module].add(name.asname or base_module)
                    if base_module == "importlib":
                        importlib_aliases.add(name.asname or base_module)
                    if base_module == "builtins":
                        builtins_aliases.add(name.asname or base_module)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    base_module = node.module.split('.')[0]
                    if base_module in FORBIDDEN_MODULES:
                        return False
                    if base_module in FORBIDDEN_CALLS:
                        for imported in node.names:
                            if imported.name == "*":
                                return False
                            if imported.name in FORBIDDEN_CALLS[base_module]:
                                direct_call_aliases[base_module].add(imported.asname or imported.name)
                    if base_module == "importlib":
                        for imported in node.names:
                            if imported.name == "*":
                                return False
                            if imported.name in FORBIDDEN_DYNAMIC_IMPORT_CALLS:
                                importlib_direct_aliases.add(imported.asname or imported.name)
            elif isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
                    if func.value.id in importlib_aliases and func.attr in FORBIDDEN_DYNAMIC_IMPORT_CALLS:
                        return False
                    for module, aliases in module_aliases.items():
                        if func.value.id in aliases and func.attr in FORBIDDEN_CALLS[module]:
                            return False
                elif isinstance(func, ast.Name):
                    if func.id in FORBIDDEN_BUILTINS:
                        return False
                    if func.id == "getattr" and len(node.args) >= 2:
                        target_name = node.args[0].id if isinstance(node.args[0], ast.Name) else None
                        attr_name = _string_literal(node.args[1])
                        if target_name in module_aliases["os"] or target_name in module_aliases["sys"]:
                            if attr_name is None:
                                return False
                        if target_name in importlib_aliases or target_name in builtins_aliases:
                            if attr_name is None:
                                return False
                        if attr_name in FORBIDDEN_REFLECTIVE_ATTRS:
                            return False
                    for aliases in direct_call_aliases.values():
                        if func.id in aliases:
                            return False
                    if func.id in importlib_direct_aliases:
                        return False
                elif isinstance(func, ast.Subscript):
                    if (
                        isinstance(func.value, ast.Attribute)
                        and func.value.attr == "__dict__"
                        and isinstance(func.value.value, ast.Name)
                        and func.value.value.id in builtins_aliases
                    ):
                        key_name = _subscript_string(func.slice)
                        if key_name in FORBIDDEN_BUILTINS:
                            return False
    except SyntaxError:
        pass
    return True

def execute_python_code(code: str, timeout: int = 20) -> dict:
    if not is_safe(code):
        return {
            "success": False,
            "stdout": "",
            "stderr": "Lỗi: Code chứa mã nguy hiểm bị cấm."
        }
    
    with tempfile.NamedTemporaryFile('w', suffix='.py', delete=False, encoding='utf-8') as f:
        f.write(code)
        temp_path = f.name
        
    try:
        child_env = os.environ.copy()
        child_env["PYTHONIOENCODING"] = "utf-8"
        child_env["PYTHONUTF8"] = "1"
        result = subprocess.run(
            [sys.executable, temp_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding='utf-8',
            errors='replace',
            env=child_env,
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except UnicodeDecodeError:
        return {
            "success": False,
            "stdout": "",
            "stderr": "Lỗi: Không thể giải mã output subprocess."
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Lỗi: Quá thời gian thực hiện ({timeout}s)."
        }
    except Exception as e:
        return {
            "success": False,
            "stdout": "",
            "stderr": str(e)
        }
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
