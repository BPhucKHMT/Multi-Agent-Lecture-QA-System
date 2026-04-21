from frontend.ui2figma.spec_models import UISpec


def map_spec_to_figma_ops(spec: UISpec) -> list[dict]:
    ops: list[dict] = []
    for screen in spec.screens:
        frame_id = f"frame:{screen.id}"
        ops.append(
            {
                "op": "create_frame",
                "id": frame_id,
                "name": screen.name,
                "layout": "AUTO_LAYOUT_VERTICAL",
            }
        )
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
                ops.append(
                    {
                        "op": "unmapped_component",
                        "parent_id": frame_id,
                        "component_type": component.type,
                    }
                )
    return ops
