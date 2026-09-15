"""Keep the em dash out of every string the app's source authors.

The walk reads the AST rather than a list of constants, because the riskiest
copy (run verdicts, fill statuses, import refusals) is built inline in
f-strings, whose literal parts arrive as string constants. Docstrings are
skipped and comments never reach the AST. Only ``source/`` is walked: a dash
typed into a renderer under ``assets/`` is review territory. The three-period
ellipsis is deliberately not gated, since clientside JavaScript spreads
(``...navbar``) and a log line use it legitimately.
"""

import ast
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parent.parent / "source"
EM_DASH = "—"

# (module, enclosing function, whole string). The one ratified em dash is the
# empty value under Last played when no scenario is selected.
ALLOWED_EM_DASHES = {
    ("source/pages/home.py", "get_scenario_num_runs", EM_DASH),
}


def _docstring_ids(tree: ast.AST) -> set[int]:
    docstrings = set()
    for node in ast.walk(tree):
        if not isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            continue
        first = node.body[0] if node.body else None
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            docstrings.add(id(first.value))
    return docstrings


def em_dash_strings(source: str) -> list[tuple[str, str]]:
    """List ``(enclosing function, string)`` for each non-docstring em dash."""
    tree = ast.parse(source)
    docstrings = _docstring_ids(tree)
    found: list[tuple[str, str]] = []

    def visit(node: ast.AST, function: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                visit(child, child.name)
                continue
            if (
                isinstance(child, ast.Constant)
                and isinstance(child.value, str)
                and id(child) not in docstrings
                and EM_DASH in child.value
            ):
                found.append((function, child.value))
            visit(child, function)

    visit(tree, "<module>")
    return found


def _source_em_dashes() -> set[tuple[str, str, str]]:
    return {
        (path.relative_to(SOURCE_ROOT.parent).as_posix(), function, value)
        for path in sorted(SOURCE_ROOT.rglob("*.py"))
        for function, value in em_dash_strings(path.read_text(encoding="utf-8"))
    }


def test_source_strings_carry_no_em_dash_outside_the_allowlist():
    assert sorted(_source_em_dashes() - ALLOWED_EM_DASHES) == []


def test_the_allowlisted_glyph_is_still_found():
    # Proves the walk sees real source: a walk that skipped too much would
    # pass the guard above vacuously.
    assert ALLOWED_EM_DASHES <= _source_em_dashes()


def test_the_walk_reads_fstring_parts_and_skips_docstrings():
    source = '''
"""Module docstring — skipped."""


def build(score):
    """Function docstring — skipped."""
    return f"{score} — points"


class Holder:
    """Class docstring — skipped."""

    label = "plain — constant"
'''
    assert em_dash_strings(source) == [
        ("build", " — points"),
        ("<module>", "plain — constant"),
    ]
