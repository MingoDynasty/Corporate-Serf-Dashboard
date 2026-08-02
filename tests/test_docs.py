"""Documentation hygiene checks.

Enforces the docs lifecycle from AGENTS.md "Shipping a proposal" and
"Documentation Habits": proposal files declare a Status line and lead with
the TL;DR / Decisions needed / Problem sections in that order, capability
specs under docs/specs/ do not declare a Status line (they are current-state
docs, not lifecycle docs), no markdown doc links to a file that has been
deleted (e.g. a proposal distilled into the decision log), and
heading-anchor links point at headings that exist in the target document.
"""

import re
from pathlib import Path
from urllib.parse import unquote, urlparse

from markdown_it import MarkdownIt

REPO_ROOT = Path(__file__).resolve().parent.parent
SPECS_DIR = REPO_ROOT / "docs" / "specs"

DOC_FILES = sorted(
    [
        *(REPO_ROOT / "docs").rglob("*.md"),
        REPO_ROOT / "README.md",
        REPO_ROOT / "AGENTS.md",
        REPO_ROOT / "CLAUDE.md",
    ]
)

STATUS_PATTERN = re.compile(r"status\s*:", re.IGNORECASE)
STATUS_SEARCH_LINES = 15

REQUIRED_LEADING_SECTIONS = ("TL;DR", "Decisions needed", "Problem")


def _inline_plain_text(token) -> str:
    """The rendered text of an inline token — what the reader sees.

    Link and emphasis markup contributes nothing itself (their text
    children carry the content), code spans and entity-decoded text
    contribute their content, line breaks read as spaces, and raw
    inline HTML is dropped. This is the text GitHub slugs anchors from.
    """
    parts = []
    for child in token.children or []:
        if child.type in ("text", "code_inline"):
            parts.append(child.content)
        elif child.type in ("softbreak", "hardbreak"):
            parts.append(" ")
        elif child.children:
            parts.append(_inline_plain_text(child))
    return "".join(parts)


def _visible_headings(text: str) -> list[tuple[str, str]]:
    """Collect (tag, text) heading pairs as the rendered page shows them.

    Reads the CommonMark parser's heading tokens rather than scanning
    text or rendered HTML (earlier attempts at both kept missing spec
    edges: fence forms, comment placement, code spans, raw-text
    elements). Everything that hides a heading falls out of the token
    stream by construction: fenced code parses as code tokens; comment
    blocks, script/style raw text, and other block-level raw HTML parse
    as html_block tokens, never headings; and an inline comment can't
    swallow a heading, because a heading line interrupts the paragraph
    that would have to contain it. Heading text is the rendered plain
    text, not the inline Markdown source.
    """
    tokens = MarkdownIt("commonmark").parse(text)
    return [
        (open_tok.tag, _inline_plain_text(inline).strip())
        for open_tok, inline in zip(tokens, tokens[1:])
        if open_tok.type == "heading_open"
    ]


def _visible_h2_headings(text: str) -> list[str]:
    """Collect H2 headings as the reader of the rendered page sees them."""
    return [content for tag, content in _visible_headings(text) if tag == "h2"]


def _relative_link_targets(doc: Path) -> list[str]:
    """Collect relative link and image targets as the rendered page has
    them, deduplicated in document order.

    Reads the CommonMark parser's tokens for the same reason
    _visible_headings does: targets inside fenced code, comments, or other
    raw HTML are example text, never rendered links, and fall out of the
    token stream by construction. Reference-style definitions come from
    the parse environment, so an unused definition is still checked.
    External targets (any scheme, mailto included) are filtered out.
    """
    env: dict = {}
    tokens = MarkdownIt("commonmark").parse(doc.read_text(encoding="utf-8"), env)
    targets = []
    for token in tokens:
        if token.type != "inline":
            continue
        for child in token.children or []:
            if child.type == "link_open":
                targets.append(child.attrGet("href"))
            elif child.type == "image":
                targets.append(child.attrGet("src"))
    targets.extend(ref["href"] for ref in env.get("references", {}).values())
    return [
        target
        for target in dict.fromkeys(targets)
        if target and not urlparse(target).scheme
    ]


def _github_anchor(heading: str) -> str:
    """GitHub's auto-anchor for a heading: lowercase, punctuation dropped,
    spaces hyphenated (consecutive spaces each keep their hyphen)."""
    cleaned = re.sub(r"[^\w\- ]", "", heading.lower())
    return cleaned.replace(" ", "-")


def _heading_anchors(doc: Path) -> set[str]:
    # Duplicate handling mirrors github-slugger: every emitted anchor is
    # reserved, and a duplicate base increments its suffix until the composed
    # anchor is free (headings Foo, Foo-1, Foo yield foo, foo-1, foo-2).
    counts: dict[str, int] = {}
    anchors: set[str] = set()
    for _tag, content in _visible_headings(doc.read_text(encoding="utf-8")):
        base = _github_anchor(content)
        anchor = base
        while anchor in anchors:
            counts[base] = counts.get(base, 0) + 1
            anchor = f"{base}-{counts[base]}"
        anchors.add(anchor)
    return anchors


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


def test_doc_anchor_links_resolve():
    broken = []
    anchors_by_doc: dict[Path, set[str]] = {}
    for doc in DOC_FILES:
        for target in _relative_link_targets(doc):
            path, _, fragment = target.partition("#")
            if not fragment:
                continue
            target_doc = (doc.parent / unquote(path)).resolve() if path else doc
            if target_doc.suffix != ".md" or not target_doc.is_file():
                # Missing files are test_doc_relative_links_resolve's job.
                continue
            if target_doc not in anchors_by_doc:
                anchors_by_doc[target_doc] = _heading_anchors(target_doc)
            if unquote(fragment) not in anchors_by_doc[target_doc]:
                broken.append(f"{doc.relative_to(REPO_ROOT)} -> {target}")
    assert not broken, (
        "Anchor links pointing at headings that do not exist (renamed or "
        "deleted heading?):\n" + "\n".join(broken)
    )


def test_link_targets_match_rendered_visibility(tmp_path):
    """Only rendered links count: fenced examples and commented-out links
    are invisible; inline links, images, and reference definitions (used
    or not) are collected once each, external schemes filtered."""
    doc = tmp_path / "links.md"
    doc.write_text(
        "# Title\n\n"
        "[real](other.md#anchor) and [used][r] and ![shot](img/pic.png)\n\n"
        "[external](https://example.com/x.md) <https://example.com>\n\n"
        "```markdown\n[example](#not-a-heading)\n[fenced](fenced.md)\n```\n\n"
        "<!-- [commented](gone.md) -->\n\n"
        "[r]: ref.md\n"
        "[unused]: unused.md\n",
        encoding="utf-8",
    )
    assert _relative_link_targets(doc) == [
        "other.md#anchor",
        "ref.md",
        "img/pic.png",
        "unused.md",
    ]


def test_heading_anchor_dedup_matches_github(tmp_path):
    doc = tmp_path / "dup.md"
    doc.write_text("# Foo\n\n# Foo-1\n\n# Foo\n", encoding="utf-8")
    assert _heading_anchors(doc) == {"foo", "foo-1", "foo-2"}


def test_heading_anchors_slug_rendered_text(tmp_path):
    """GitHub slugs the visible heading text, not the Markdown source:
    link destinations and markup must not leak into the anchor, and
    entities decode before slugging."""
    doc = tmp_path / "inline.md"
    doc.write_text(
        "# [Install](setup.md)\n\n"
        "# Configure `config.toml` &amp; go\n\n"
        "# *Emphasis* and **strong**\n",
        encoding="utf-8",
    )
    assert _heading_anchors(doc) == {
        "install",
        "configure-configtoml--go",
        "emphasis-and-strong",
    }


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
        "Proposal docs must open with '## TL;DR', '## Decisions needed', "
        "'## Problem' in that order (see the AGENTS.md proposal template):\n"
        + "\n".join(bad)
    )


def test_spec_docs_do_not_declare_status():
    specs = sorted(SPECS_DIR.rglob("*.md"))
    assert specs, "docs/specs/ should hold at least one capability spec"
    flagged = []
    for doc in specs:
        lines = doc.read_text(encoding="utf-8").splitlines()[:STATUS_SEARCH_LINES]
        if any(STATUS_PATTERN.search(line) for line in lines):
            flagged.append(str(doc.relative_to(REPO_ROOT)))
    assert not flagged, (
        "Spec docs state current behavior and must not carry a proposal-style "
        f"'Status:' line: {flagged}"
    )


def test_heading_scan_matches_rendered_visibility():
    """Only rendered H2s count: embedded examples must not satisfy (or
    break) the leading-section check. Fenced code hides headings (all
    fence forms, including one left unclosed, which CommonMark extends
    through end of document); raw HTML comment blocks hide headings; so
    does literal heading markup inside raw-text elements like script.
    Markers inside code spans or fenced code are escaped in the output
    and hide nothing — and an unclosed marker after visible text is
    escaped too (not a comment), so headings after it stay visible."""
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
            "<script>",
            "<h2>Hidden in script raw text</h2>",
            "</script>",
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
