from frontend.ui2figma.figma_mapper import map_spec_to_figma_ops
from frontend.ui2figma.mcp_executor import execute_ops
from frontend.ui2figma.review_gate import evaluate_review_decision
from frontend.ui2figma.spec_parser import parse_ui_spec


def run_text_to_figma_pipeline(markdown_spec: str, mcp_client, review_decision: str) -> dict:
    spec = parse_ui_spec(markdown_spec)
    ops = map_spec_to_figma_ops(spec)
    sync_report = execute_ops(mcp_client, ops)
    review_result = evaluate_review_decision(review_decision)
    return {"sync_report": sync_report, **review_result}
