# Text-to-UI Figma Orchestrator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a markdown-to-Figma pipeline (via MCP) that stops at a manual review gate and only enables UI code generation after explicit `OK`.

**Architecture:** A small `frontend/ui2figma` module will parse structured markdown into a typed UI spec, map that spec to Figma operations, execute operations through MCP, and produce a sync report. An orchestrator coordinates parse → map → sync → review gate flow, returning `ready_for_codegen` only when approved.

**Tech Stack:** Python 3.12, pytest, pydantic, existing MCP server integration (Framelink Figma MCP), markdown parsing.

---

## File Structure

- Create: `frontend/ui2figma/__init__.py` — export public orchestrator APIs.
- Create: `frontend/ui2figma/spec_models.py` — typed schema for `UISpec`.
- Create: `frontend/ui2figma/spec_parser.py` — markdown -> `UISpec` parsing + validation errors.
- Create: `frontend/ui2figma/figma_mapper.py` — `UISpec` -> list of Figma operations.
- Create: `frontend/ui2figma/mcp_executor.py` — execute operations and build sync report.
- Create: `frontend/ui2figma/review_gate.py` — enforce `OK/revise` decision logic.
- Create: `frontend/ui2figma/orchestrator.py` — high-level pipeline entrypoint.
- Create: `frontend/ui2figma/tests/test_spec_parser.py`
- Create: `frontend/ui2figma/tests/test_figma_mapper.py`
- Create: `frontend/ui2figma/tests/test_review_gate.py`
- Create: `frontend/ui2figma/tests/test_orchestrator.py`

### Task 1: UISpec schema + parser contract

**Files:**
- Create: `frontend/ui2figma/spec_models.py`
- Create: `frontend/ui2figma/spec_parser.py`
- Test: `frontend/ui2figma/tests/test_spec_parser.py`

- [ ] **Step 1: Write the failing test**

```python
# frontend/ui2figma/tests/test_spec_parser.py
import pytest
from frontend.ui2figma.spec_parser import parse_ui_spec


def test_parse_ui_spec_extracts_screen_and_components():
    markdown = """
# project: demo
## screen: Home
- component: header title="Dashboard"
- component: button text="Get Started"
states: default, loading
"""
    spec = parse_ui_spec(markdown)
    assert spec.meta.project == "demo"
    assert spec.screens[0].name == "Home"
    assert spec.screens[0].components[0].type == "header"
    assert spec.screens[0].states == ["default", "loading"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest frontend\ui2figma\tests\test_spec_parser.py::test_parse_ui_spec_extracts_screen_and_components -q`  
Expected: FAIL with `ModuleNotFoundError` or missing `parse_ui_spec`.

- [ ] **Step 3: Write minimal implementation**

```python
# frontend/ui2figma/spec_models.py
from pydantic import BaseModel, Field


class ComponentSpec(BaseModel):
    type: str
    props: dict = Field(default_factory=dict)


class ScreenSpec(BaseModel):
    id: str
    name: str
    components: list[ComponentSpec] = Field(default_factory=list)
    states: list[str] = Field(default_factory=list)


class MetaSpec(BaseModel):
    project: str
    version: str = "v1"


class UISpec(BaseModel):
    meta: MetaSpec
    screens: list[ScreenSpec]
```

```python
# frontend/ui2figma/spec_parser.py
import re
from frontend.ui2figma.spec_models import UISpec, MetaSpec, ScreenSpec, ComponentSpec


def parse_ui_spec(markdown: str) -> UISpec:
    project_match = re.search(r"^#\s*project:\s*(.+)$", markdown, flags=re.MULTILINE)
    screen_match = re.search(r"^##\s*screen:\s*(.+)$", markdown, flags=re.MULTILINE)
    state_match = re.search(r"^states:\s*(.+)$", markdown, flags=re.MULTILINE)
    component_lines = re.findall(r"^- component:\s*([a-zA-Z0-9_-]+)(.*)$", markdown, flags=re.MULTILINE)

    project = project_match.group(1).strip() if project_match else "default"
    screen_name = screen_match.group(1).strip() if screen_match else "Screen"
    states = [s.strip() for s in (state_match.group(1).split(",") if state_match else ["default"])]

    components = []
    for component_type, raw_props in component_lines:
        props = {}
        for key, value in re.findall(r'([a-zA-Z_][a-zA-Z0-9_]*)="([^"]*)"', raw_props):
            props[key] = value
        components.append(ComponentSpec(type=component_type, props=props))

    return UISpec(
        meta=MetaSpec(project=project),
        screens=[ScreenSpec(id=screen_name.lower(), name=screen_name, components=components, states=states)],
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest frontend\ui2figma\tests\test_spec_parser.py::test_parse_ui_spec_extracts_screen_and_components -q`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/ui2figma/spec_models.py frontend/ui2figma/spec_parser.py frontend/ui2figma/tests/test_spec_parser.py
git commit -m "feat: add ui spec parser contract"
```

### Task 2: Map UISpec to Figma operations

**Files:**
- Create: `frontend/ui2figma/figma_mapper.py`
- Test: `frontend/ui2figma/tests/test_figma_mapper.py`

- [ ] **Step 1: Write the failing test**

```python
# frontend/ui2figma/tests/test_figma_mapper.py
from frontend.ui2figma.spec_models import UISpec, MetaSpec, ScreenSpec, ComponentSpec
from frontend.ui2figma.figma_mapper import map_spec_to_figma_ops


def test_map_spec_to_figma_ops_generates_frame_and_children():
    spec = UISpec(
        meta=MetaSpec(project="demo"),
        screens=[
            ScreenSpec(
                id="home",
                name="Home",
                components=[ComponentSpec(type="header", props={"title": "Dashboard"})],
                states=["default"],
            )
        ],
    )
    ops = map_spec_to_figma_ops(spec)
    assert ops[0]["op"] == "create_frame"
    assert ops[0]["name"] == "Home"
    assert ops[1]["op"] == "create_text"
    assert ops[1]["text"] == "Dashboard"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest frontend\ui2figma\tests\test_figma_mapper.py::test_map_spec_to_figma_ops_generates_frame_and_children -q`  
Expected: FAIL because `map_spec_to_figma_ops` is missing.

- [ ] **Step 3: Write minimal implementation**

```python
# frontend/ui2figma/figma_mapper.py
from frontend.ui2figma.spec_models import UISpec


def map_spec_to_figma_ops(spec: UISpec) -> list[dict]:
    ops: list[dict] = []
    for screen in spec.screens:
        frame_id = f"frame:{screen.id}"
        ops.append({"op": "create_frame", "id": frame_id, "name": screen.name, "layout": "AUTO_LAYOUT_VERTICAL"})
        for component in screen.components:
            if component.type == "header":
                ops.append(
                    {
                        "op": "create_text",
                        "parent_id": frame_id,
                        "text": component.props.get("title", ""),
                        "style": "heading",
                    }
                )
            elif component.type == "button":
                ops.append(
                    {
                        "op": "create_button",
                        "parent_id": frame_id,
                        "text": component.props.get("text", "Button"),
                    }
                )
            else:
                ops.append({"op": "unmapped_component", "parent_id": frame_id, "component_type": component.type})
    return ops
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest frontend\ui2figma\tests\test_figma_mapper.py::test_map_spec_to_figma_ops_generates_frame_and_children -q`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/ui2figma/figma_mapper.py frontend/ui2figma/tests/test_figma_mapper.py
git commit -m "feat: add figma operation mapper for ui spec"
```

### Task 3: MCP execution + sync report

**Files:**
- Create: `frontend/ui2figma/mcp_executor.py`
- Test: `frontend/ui2figma/tests/test_orchestrator.py`

- [ ] **Step 1: Write the failing test**

```python
# frontend/ui2figma/tests/test_orchestrator.py
from frontend.ui2figma.mcp_executor import execute_ops


def test_execute_ops_collects_created_and_unmapped_items():
    class FakeClient:
        def run(self, op):
            if op["op"] == "unmapped_component":
                return {"status": "skipped"}
            return {"status": "created", "node_id": "123"}

    report = execute_ops(
        FakeClient(),
        [{"op": "create_frame", "name": "Home"}, {"op": "unmapped_component", "component_type": "chart"}],
    )
    assert report["created"] == 1
    assert report["unmapped"] == ["chart"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest frontend\ui2figma\tests\test_orchestrator.py::test_execute_ops_collects_created_and_unmapped_items -q`  
Expected: FAIL because `execute_ops` is missing.

- [ ] **Step 3: Write minimal implementation**

```python
# frontend/ui2figma/mcp_executor.py
def execute_ops(client, ops: list[dict]) -> dict:
    report = {"created": 0, "updated": 0, "warnings": [], "unmapped": []}
    for op in ops:
        if op["op"] == "unmapped_component":
            report["unmapped"].append(op.get("component_type", "unknown"))
            continue
        result = client.run(op)
        if result.get("status") == "created":
            report["created"] += 1
        elif result.get("status") == "updated":
            report["updated"] += 1
        else:
            report["warnings"].append({"op": op, "result": result})
    return report
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest frontend\ui2figma\tests\test_orchestrator.py::test_execute_ops_collects_created_and_unmapped_items -q`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/ui2figma/mcp_executor.py frontend/ui2figma/tests/test_orchestrator.py
git commit -m "feat: add mcp execution report for figma sync"
```

### Task 4: Review gate + orchestrator flow

**Files:**
- Create: `frontend/ui2figma/review_gate.py`
- Create: `frontend/ui2figma/orchestrator.py`
- Create: `frontend/ui2figma/__init__.py`
- Test: `frontend/ui2figma/tests/test_review_gate.py`
- Test: `frontend/ui2figma/tests/test_orchestrator.py`

- [ ] **Step 1: Write the failing tests**

```python
# frontend/ui2figma/tests/test_review_gate.py
import pytest
from frontend.ui2figma.review_gate import evaluate_review_decision


def test_evaluate_review_decision_accepts_ok():
    result = evaluate_review_decision("OK")
    assert result["ready_for_codegen"] is True


def test_evaluate_review_decision_rejects_unknown():
    with pytest.raises(ValueError):
        evaluate_review_decision("approve")
```

```python
# frontend/ui2figma/tests/test_orchestrator.py
from frontend.ui2figma.orchestrator import run_text_to_figma_pipeline


def test_pipeline_returns_ready_false_when_review_is_revise(monkeypatch):
    monkeypatch.setattr("frontend.ui2figma.orchestrator.parse_ui_spec", lambda _: object())
    monkeypatch.setattr("frontend.ui2figma.orchestrator.map_spec_to_figma_ops", lambda _: [])
    monkeypatch.setattr("frontend.ui2figma.orchestrator.execute_ops", lambda _client, _ops: {"created": 0, "updated": 0, "warnings": [], "unmapped": []})

    result = run_text_to_figma_pipeline("spec", mcp_client=object(), review_decision="revise")
    assert result["ready_for_codegen"] is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest frontend\ui2figma\tests\test_review_gate.py frontend\ui2figma\tests\test_orchestrator.py -q`  
Expected: FAIL for missing review/orchestrator modules.

- [ ] **Step 3: Write minimal implementation**

```python
# frontend/ui2figma/review_gate.py
def evaluate_review_decision(decision: str) -> dict:
    normalized = str(decision or "").strip().lower()
    if normalized == "ok":
        return {"ready_for_codegen": True, "status": "approved"}
    if normalized == "revise":
        return {"ready_for_codegen": False, "status": "needs_revision"}
    raise ValueError("Review decision must be 'OK' or 'revise'.")
```

```python
# frontend/ui2figma/orchestrator.py
from frontend.ui2figma.spec_parser import parse_ui_spec
from frontend.ui2figma.figma_mapper import map_spec_to_figma_ops
from frontend.ui2figma.mcp_executor import execute_ops
from frontend.ui2figma.review_gate import evaluate_review_decision


def run_text_to_figma_pipeline(markdown_spec: str, mcp_client, review_decision: str) -> dict:
    spec = parse_ui_spec(markdown_spec)
    ops = map_spec_to_figma_ops(spec)
    sync_report = execute_ops(mcp_client, ops)
    review_result = evaluate_review_decision(review_decision)
    return {"sync_report": sync_report, **review_result}
```

```python
# frontend/ui2figma/__init__.py
from .orchestrator import run_text_to_figma_pipeline

__all__ = ["run_text_to_figma_pipeline"]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest frontend\ui2figma\tests\test_review_gate.py frontend\ui2figma\tests\test_orchestrator.py -q`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/ui2figma/review_gate.py frontend/ui2figma/orchestrator.py frontend/ui2figma/__init__.py frontend/ui2figma/tests/test_review_gate.py frontend/ui2figma/tests/test_orchestrator.py
git commit -m "feat: add review-gated text-to-figma orchestrator"
```

### Task 5: End-to-end smoke command and regression run

**Files:**
- Create: `scripts\run_text_to_ui.py`
- Modify: `README.md` (add usage section)
- Test: `frontend/ui2figma/tests/test_orchestrator.py`

- [ ] **Step 1: Write the failing smoke test**

```python
# append to frontend/ui2figma/tests/test_orchestrator.py
from frontend.ui2figma.orchestrator import run_text_to_figma_pipeline


def test_pipeline_ready_for_codegen_only_after_ok(monkeypatch):
    monkeypatch.setattr("frontend.ui2figma.orchestrator.parse_ui_spec", lambda _: object())
    monkeypatch.setattr("frontend.ui2figma.orchestrator.map_spec_to_figma_ops", lambda _: [])
    monkeypatch.setattr("frontend.ui2figma.orchestrator.execute_ops", lambda _client, _ops: {"created": 1, "updated": 0, "warnings": [], "unmapped": []})
    result = run_text_to_figma_pipeline("spec", mcp_client=object(), review_decision="OK")
    assert result["ready_for_codegen"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest frontend\ui2figma\tests\test_orchestrator.py::test_pipeline_ready_for_codegen_only_after_ok -q`  
Expected: FAIL before wiring final behavior.

- [ ] **Step 3: Write minimal implementation and CLI entrypoint**

```python
# frontend/ui2figma/run_text_to_ui.py
import argparse
from pathlib import Path
from frontend.ui2figma.orchestrator import run_text_to_figma_pipeline


class PlaceholderMCPClient:
    def run(self, _op: dict):
        return {"status": "created"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", required=True, help="Path tới ui-spec markdown")
    parser.add_argument("--review", required=True, choices=["OK", "revise"])
    args = parser.parse_args()

    markdown_spec = Path(args.spec).read_text(encoding="utf-8")
    result = run_text_to_figma_pipeline(markdown_spec, PlaceholderMCPClient(), args.review)
    print(result)


if __name__ == "__main__":
    main()
```

README.md section:

```text
## Text-to-UI (Markdown -> Figma)

python scripts\run_text_to_ui.py --spec path\to\ui-spec.md --review OK

Use --review revise để giữ pipeline ở trạng thái chưa cho phép codegen.
```

- [ ] **Step 4: Run targeted tests + smoke command**

Run: `python -m pytest frontend\ui2figma\tests -q`  
Expected: PASS.

Run: `python scripts\run_text_to_ui.py --spec sample_ui_spec.md --review OK`  
Expected: output dict có `ready_for_codegen: True`.

- [ ] **Step 5: Commit**

```bash
git add frontend/ui2figma/run_text_to_ui.py README.md frontend/ui2figma/tests frontend/ui2figma
git commit -m "feat: add text-to-ui figma pipeline smoke flow"
```


