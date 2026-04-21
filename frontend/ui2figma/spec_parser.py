import re

from frontend.ui2figma.spec_models import ComponentSpec, MetaSpec, ScreenSpec, UISpec


def _screen_id(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-") or "screen"


def parse_ui_spec(markdown: str) -> UISpec:
    project_match = re.search(r"^#\s*project:\s*(.+)$", markdown, flags=re.MULTILINE)
    screen_match = re.search(r"^##\s*screen:\s*(.+)$", markdown, flags=re.MULTILINE)
    state_match = re.search(r"^states:\s*(.+)$", markdown, flags=re.MULTILINE)
    component_lines = re.findall(r"^- component:\s*([a-zA-Z0-9_-]+)(.*)$", markdown, flags=re.MULTILINE)

    project = project_match.group(1).strip() if project_match else "default"
    screen_name = screen_match.group(1).strip() if screen_match else "Screen"
    states = [state.strip() for state in (state_match.group(1).split(",") if state_match else ["default"])]

    components: list[ComponentSpec] = []
    for component_type, raw_props in component_lines:
        props = {}
        for key, value in re.findall(r'([a-zA-Z_][a-zA-Z0-9_]*)="([^"]*)"', raw_props):
            props[key] = value
        components.append(ComponentSpec(type=component_type, props=props))

    return UISpec(
        meta=MetaSpec(project=project),
        screens=[
            ScreenSpec(
                id=_screen_id(screen_name),
                name=screen_name,
                components=components,
                states=states,
            )
        ],
    )
