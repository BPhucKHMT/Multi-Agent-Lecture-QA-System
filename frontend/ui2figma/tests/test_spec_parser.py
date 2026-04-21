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
