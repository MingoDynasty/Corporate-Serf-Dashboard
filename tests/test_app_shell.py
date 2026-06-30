from collections import deque

from source import app_shell


def _find_component_by_id(root, component_id):
    components = deque([root])
    while components:
        component = components.popleft()
        if getattr(component, "id", None) == component_id:
            return component

        children = getattr(component, "children", None)
        if children is None:
            continue
        if isinstance(children, list):
            components.extend(children)
        else:
            components.append(children)

    raise AssertionError(f"Component not found: {component_id}")


def test_navbar_burger_open_state_persists_across_refresh():
    shell = app_shell.layout()

    burger = _find_component_by_id(shell, "burger")

    assert burger.persistence is True
    assert burger.persistence_type == "local"
    assert burger.persisted_props == ["opened"]
