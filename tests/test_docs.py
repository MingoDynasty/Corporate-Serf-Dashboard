"""Documentation hygiene checks.

Enforces the docs lifecycle from AGENTS.md "Shipping a proposal" and the
proposal template: proposal files declare a Status line and lead with the
TL;DR / Decision points / Problem sections in that order, and no markdown
doc links to a file that has been deleted (e.g. a proposal distilled into
the decision log).
"""

import re
from pathlib import Path
from urllib.parse import unquote, urlparse

from markdown_it import MarkdownIt

REPO_ROOT = Path(__file__).resolve().parent.parent

DOC_FILES = sorted(
    [
        *(REPO_ROOT / "docs").rglob("*.md"),
        REPO_ROOT / "README.md",
        REPO_ROOT / "AGENTS.md",
        REPO_ROOT / "CLAUDE.md",
    ]
)

# Inline markdown links/images: [text](target) — captures the target up to
# whitespace or the closing paren, which also handles optional "title" parts.
INLINE_LINK_PATTERN = re.compile(r"\]\(([^)\s]+)[^)]*\)")

# Reference-style link definitions: `[id]: target` at the start of a line
# (up to 3 leading spaces per CommonMark). Excludes footnotes (`[^1]: ...`).
REFERENCE_DEF_PATTERN = re.compile(r"^ {0,3}\[[^\]^][^\]]*\]:\s+(\S+)", re.MULTILINE)

STATUS_PATTERN = re.compile(r"status\s*:", re.IGNORECASE)
STATUS_SEARCH_LINES = 15

REQUIRED_LEADING_SECTIONS = ("TL;DR", "Decision points", "Problem")


# What a browser hides: comment markers that survived into the rendered
# HTML (an unclosed comment hides everything to the end of the page).
# Escaped markers from code spans and fenced code (&lt;!--) don't match.
HTML_COMMENT_PATTERN = re.compile(r"<!--.*?(?:-->|\Z)", re.DOTALL)
H2_ELEMENT_PATTERN = re.compile(r"<h2>(.*?)</h2>", re.DOTALL)


def _visible_h2_headings(text: str) -> list[str]:
    """Collect H2 headings as the reader of the rendered page sees them.

    Renders with a CommonMark parser, then drops HTML comments from the
    output the way a browser does. Earlier hand-rolled scans here kept
    missing spec edges (tilde/long/unclosed fences, mid-line comments,
    code spans); rendering makes them all fall out by construction —
    code spans and fenced code render with their contents escaped, so
    markers inside them never hide anything, while raw HTML comments
    hide whatever falls inside them, headings included.
    """
    html = MarkdownIt("commonmark").render(text)
    visible = HTML_COMMENT_PATTERN.sub("", html)
    return [m.group(1).strip() for m in H2_ELEMENT_PATTERN.finditer(visible)]


def _relative_link_targets(doc: Path) -> list[str]:
    text = doc.read_text(encoding="utf-8")
    targets = []
    for pattern in (INLINE_LINK_PATTERN, REFERENCE_DEF_PATTERN):
        for match in pattern.finditer(text):
            target = match.group(1)
            if urlparse(target).scheme or target.startswith(("#", "mailto:")):
                continue
            targets.append(target)
    return targets


def test_doc_relative_links_resolve():
    broken = []
    for doc in DOC_FILES:
        for target in _relative_link_targets(doc):
            path = unquote(target.split("#", 1)[0])
            if path and not (doc.parent / path).exists():
                broken.append(f"{doc.relative_to(REPO_ROOT)} -> {target}")
    assert not broken, "Dangling doc links (deleted or moved target?):\n" + "\n".join(
        broken
    )


def test_proposal_docs_declare_status():
    missing = []
    for doc in (REPO_ROOT / "docs").rglob("*proposal*.md"):
        lines = doc.read_text(encoding="utf-8").splitlines()[:STATUS_SEARCH_LINES]
        if not any(STATUS_PATTERN.search(line) for line in lines):
            missing.append(str(doc.relative_to(REPO_ROOT)))
    assert not missing, (
        f"Proposal docs missing a 'Status:' line in the first "
        f"{STATUS_SEARCH_LINES} lines: {missing}"
    )


def test_proposal_docs_lead_with_required_sections():
    """Placement, not just presence: the maintainer read-path comes first."""
    bad = []
    for doc in (REPO_ROOT / "docs").rglob("*proposal*.md"):
        headings = _visible_h2_headings(doc.read_text(encoding="utf-8"))
        leading = tuple(headings[: len(REQUIRED_LEADING_SECTIONS)])
        if leading != REQUIRED_LEADING_SECTIONS:
            bad.append(f"{doc.relative_to(REPO_ROOT)}: first H2s are {list(leading)}")
    assert not bad, (
        "Proposal docs must open with '## TL;DR', '## Decision points', "
        "'## Problem' in that order (see the AGENTS.md proposal template):\n"
        + "\n".join(bad)
    )


def test_heading_scan_matches_rendered_visibility():
    """Only rendered H2s count: embedded examples must not satisfy (or
    break) the leading-section check. Fenced code hides headings (all
    fence forms, including one left unclosed, which CommonMark extends
    through end of document), and so do raw HTML comments. Markers
    inside code spans or fenced code are escaped in the output and hide
    nothing — and an unclosed marker after visible text is escaped too
    (not a comment), so headings after it stay visible."""
    doc = "\n".join(
        [
            "# Title",
            "",
            "## Real A",
            "",
            "```markdown",
            "## Hidden in backtick fence",
            "```",
            "~~~",
            "## Hidden in tilde fence",
            "~~~",
            "````md",
            "```",
            "## Hidden in long fence with inner short fence",
            "````",
            "<!--",
            "## Hidden in comment block",
            "-->",
            "<!-- ## Hidden in one-line comment -->",
            "",
            "`<!--`",
            "",
            "## Real B, between code-span comment markers",
            "",
            "`-->`",
            "",
            "Notes <!--",
            "",
            "## Real C, after an unclosed marker that renders escaped",
            "",
            "```",
            "## Hidden in unclosed fence at EOF",
        ]
    )
    assert _visible_h2_headings(doc) == [
        "Real A",
        "Real B, between code-span comment markers",
        "Real C, after an unclosed marker that renders escaped",
    ]
