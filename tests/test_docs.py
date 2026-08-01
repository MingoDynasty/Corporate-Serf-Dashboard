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


def _strip_html_comments(line: str, in_comment: bool) -> tuple[str, bool]:
    """Return the line's visible text and the comment state after it.

    Handles openers and closers anywhere in the line, including several
    per line (`a <!-- x --> b <!-- y`); comment text itself is dropped.
    """
    visible: list[str] = []
    rest = line
    while True:
        if in_comment:
            end = rest.find("-->")
            if end == -1:
                return "".join(visible), True
            rest = rest[end + 3 :]
            in_comment = False
        else:
            start = rest.find("<!--")
            if start == -1:
                visible.append(rest)
                return "".join(visible), False
            visible.append(rest[:start])
            rest = rest[start + 4 :]
            in_comment = True


def _visible_h2_headings(text: str) -> list[str]:
    """Collect H2 headings as a Markdown reader would see them.

    Line-oriented scan so a template or example embedded in a proposal
    doesn't count as a section: skips CommonMark fenced code blocks
    (backtick or tilde, three or more, closer at least as long as the
    opener, up to 3 leading spaces; an unclosed fence consumes the rest
    of the document) and HTML comments, wherever in a line they open.
    Comments are not parsed inside fenced code; fence markers are not
    parsed inside comments; the tail of a line that closes a multi-line
    comment is HTML-block content, never a heading.
    """
    headings: list[str] = []
    fence_char = ""
    fence_len = 0
    in_comment = False
    for line in text.splitlines():
        if fence_char:
            indent = len(line) - len(line.lstrip(" "))
            stripped = line.strip()
            closer = stripped.rstrip(fence_char)
            if (
                indent <= 3
                and stripped.startswith(fence_char * fence_len)
                and not closer
            ):
                fence_char = ""
                fence_len = 0
            continue
        was_in_comment = in_comment
        visible, in_comment = _strip_html_comments(line, in_comment)
        if was_in_comment:
            continue
        stripped = visible.strip()
        indent = len(visible) - len(visible.lstrip(" "))
        if indent <= 3 and stripped[:3] in ("```", "~~~"):
            fence_char = stripped[0]
            fence_len = len(stripped) - len(stripped.lstrip(fence_char))
            continue
        if visible.startswith("## "):
            headings.append(visible[3:].strip())
    return headings


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


def test_heading_scan_skips_fenced_and_commented_headings():
    """Only rendered H2s count: embedded examples must not satisfy (or
    break) the leading-section check, whatever hides them — paired
    backtick/tilde/long fences, HTML comments (including ones opened
    after visible text on the same line), or an unclosed fence, which
    CommonMark extends through end of document."""
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
            "Notes <!--",
            "## Hidden in comment opened after text",
            "-->## Not a heading: tail of the line closing a comment",
            "## Real B <!-- trailing opener",
            "## Hidden while that comment is still open",
            "--> <!--",
            "## Hidden after same-line close and reopen",
            "-->",
            "## Real C",
            "",
            "```",
            "## Hidden in unclosed fence at EOF",
        ]
    )
    assert _visible_h2_headings(doc) == ["Real A", "Real B", "Real C"]
