def evaluate_review_decision(decision: str) -> dict:
    normalized = str(decision or "").strip().lower()
    if normalized == "ok":
        return {"ready_for_codegen": True, "status": "approved"}
    if normalized == "revise":
        return {"ready_for_codegen": False, "status": "needs_revision"}
    raise ValueError("Review decision must be 'OK' or 'revise'.")
