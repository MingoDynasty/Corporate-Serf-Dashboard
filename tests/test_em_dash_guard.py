"""Keep the em dash out of every string the app's source authors.

The walk reads the AST rather than a list of constants, because the riskiest
copy (run verdicts, fill statuses, import refusals) is built inline in
f-strings, whose literal parts arrive as string constants. Docstrings are
skipped and comments never reach the AST. Only ``source/`` is walked: a dash
typed into a renderer under ``assets/`` is review territory. The three-period
ellipsis is deliberately not gated, since clientside JavaScript spreads
(``...navbar``) and a log line use it legitimately.

No string is allowed one. The last that was, Last played's empty value in the
Scenario Stats card, left with the row.
"""

import ast
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parent.parent / "source"
EM_DASH = "—"
# The separator copy rule 2 chains readout fragments with, in place of the em
# dash. The walk finding it in real source is what proves the walk reads
# real source, now that it finds no em dash there.
MIDDLE_DOT = " · "


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


def strings_with(source: str, glyph: str) -> list[tuple[str, str]]:
    """List ``(enclosing function, string)`` for each non-docstring holding ``glyph``."""
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
                and glyph in child.value
            ):
                found.append((function, child.value))
            visit(child, function)

    visit(tree, "<module>")
    return found


def _source_strings_with(glyph: str) -> set[tuple[str, str, str]]:
    return {
        (path.relative_to(SOURCE_ROOT.parent).as_posix(), function, value)
        for path in sorted(SOURCE_ROOT.rglob("*.py"))
        for function, value in strings_with(path.read_text(encoding="utf-8"), glyph)
    }


def test_source_strings_carry_no_em_dash():
    assert sorted(_source_strings_with(EM_DASH)) == []


def test_the_walk_reads_real_source():
    """A walk that read none of ``source/`` would pass the guard above vacuously.

    The same walk, over the same files, finds the middle dot the latest-run
    card's first line is chained with, inline in its layout, and one in an
    f-string's literal part.
    """
    module = "source/components/latest_run_card.py"
    found = _source_strings_with(MIDDLE_DOT)

    assert (module, "latest_run_card", MIDDLE_DOT) in found
    assert (module, "_session_line", MIDDLE_DOT) in found


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
    assert strings_with(source, EM_DASH) == [
        ("build", " — points"),
        ("<module>", "plain — constant"),
    ]
