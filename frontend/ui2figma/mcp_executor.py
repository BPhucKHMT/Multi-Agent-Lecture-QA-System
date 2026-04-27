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
