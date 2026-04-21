# Root Frontend Folder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a root-level `frontend/` workspace with placeholder guidance so developers can use `cd frontend` without affecting the existing Streamlit frontend in `src/frontend`.

**Architecture:** Keep current runtime untouched and add an isolated folder + docs entrypoint only. Use one focused filesystem test to enforce the new workspace contract (`frontend` directory and README existence). This keeps scope minimal and prevents accidental coupling with current Streamlit flow.

**Tech Stack:** Python 3.12, pytest, Markdown documentation.

---

## File Structure

- Create: `frontend/README.md` — placeholder guide for the future frontend workspace.
- Create: `tests/test_root_frontend_workspace.py` — validates root workspace contract.
- Modify: `README.md` — add a short note that `frontend/` is reserved for new UI work while `src/frontend` remains Streamlit.

### Task 1: Add failing workspace contract test

**Files:**
- Create: `tests/test_root_frontend_workspace.py`
- Test: `tests/test_root_frontend_workspace.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path


def test_root_frontend_workspace_exists_with_readme():
    root = Path(__file__).resolve().parents[1]
    frontend_dir = root / "frontend"
    readme_file = frontend_dir / "README.md"

    assert frontend_dir.is_dir(), "Expected root-level frontend/ directory."
    assert readme_file.is_file(), "Expected frontend/README.md placeholder guide."
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests\test_root_frontend_workspace.py::test_root_frontend_workspace_exists_with_readme -q`  
Expected: FAIL with assertion that `frontend/` or `frontend/README.md` does not exist.

- [ ] **Step 3: Commit**

```bash
git add tests/test_root_frontend_workspace.py
git commit -m "test: add failing contract for root frontend workspace"
```

### Task 2: Create root frontend placeholder workspace

**Files:**
- Create: `frontend/README.md`
- Modify: `README.md`
- Test: `tests/test_root_frontend_workspace.py`

- [ ] **Step 1: Write minimal implementation**

```markdown
<!-- frontend/README.md -->
# Frontend Workspace (Placeholder)

Thư mục này dành cho frontend mới tách riêng khỏi `src/frontend` (Streamlit hiện tại).

## Cách dùng hiện tại

```bash
cd frontend
```

Hiện tại chưa khởi tạo framework (Vite/Next/...).
Khi chốt stack, sẽ setup trực tiếp trong thư mục này.
```

```markdown
<!-- README.md: add short note near run section -->
## Frontend structure

- `src/frontend`: giao diện Streamlit đang chạy hiện tại.
- `frontend/`: workspace mới (placeholder) cho frontend tách riêng trong phase tiếp theo.
```

- [ ] **Step 2: Run test to verify it passes**

Run: `python -m pytest tests\test_root_frontend_workspace.py -q`  
Expected: PASS.

- [ ] **Step 3: Run relevant regression check**

Run: `python -m pytest tests\api\test_chat_stream.py -q`  
Expected: PASS (xác nhận thay đổi docs/folder không ảnh hưởng luồng API stream đã có).

- [ ] **Step 4: Commit**

```bash
git add frontend/README.md README.md tests/test_root_frontend_workspace.py
git commit -m "feat: add root frontend workspace placeholder"
```

### Task 3: Final verification and handoff

**Files:**
- Modify: none
- Test: `tests/test_root_frontend_workspace.py`, `tests/api/test_chat_stream.py`

- [ ] **Step 1: Verify workspace command flow**

Run: `cd frontend`  
Expected: command succeeds from repository root.

- [ ] **Step 2: Verify tests**

Run: `python -m pytest tests\test_root_frontend_workspace.py tests\api\test_chat_stream.py -q`  
Expected: all tests PASS.

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "chore: verify root frontend workspace rollout"
```
