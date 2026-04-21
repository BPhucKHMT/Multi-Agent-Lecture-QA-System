from frontend.ui2figma.figma_mapper import map_spec_to_figma_ops
from frontend.ui2figma.spec_models import ComponentSpec, MetaSpec, ScreenSpec, UISpec


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
