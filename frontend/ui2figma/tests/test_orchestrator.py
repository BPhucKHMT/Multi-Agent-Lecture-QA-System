from frontend.ui2figma.mcp_executor import execute_ops
from frontend.ui2figma.orchestrator import run_text_to_figma_pipeline


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


def test_pipeline_returns_ready_false_when_review_is_revise(monkeypatch):
    monkeypatch.setattr("frontend.ui2figma.orchestrator.parse_ui_spec", lambda _: object())
    monkeypatch.setattr("frontend.ui2figma.orchestrator.map_spec_to_figma_ops", lambda _: [])
    monkeypatch.setattr(
        "frontend.ui2figma.orchestrator.execute_ops",
        lambda _client, _ops: {"created": 0, "updated": 0, "warnings": [], "unmapped": []},
    )

    result = run_text_to_figma_pipeline("spec", mcp_client=object(), review_decision="revise")
    assert result["ready_for_codegen"] is False


def test_pipeline_ready_for_codegen_only_after_ok(monkeypatch):
    monkeypatch.setattr("frontend.ui2figma.orchestrator.parse_ui_spec", lambda _: object())
    monkeypatch.setattr("frontend.ui2figma.orchestrator.map_spec_to_figma_ops", lambda _: [])
    monkeypatch.setattr(
        "frontend.ui2figma.orchestrator.execute_ops",
        lambda _client, _ops: {"created": 1, "updated": 0, "warnings": [], "unmapped": []},
    )
    result = run_text_to_figma_pipeline("spec", mcp_client=object(), review_decision="OK")
    assert result["ready_for_codegen"] is True
