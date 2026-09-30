"""Documentation hygiene checks.

Enforces the docs lifecycle from AGENTS.md "Shipping a proposal" and
"Documentation Habits": proposal files live under docs/proposals/, declare a
Status line, and lead with the TL;DR / Decisions needed / Problem sections
in that order, capability specs under docs/specs/ do not declare a Status
line (they are current-state docs, not lifecycle docs), no markdown doc
links to a file that has been deleted (e.g. a proposal distilled into the
decision log), and heading-anchor links point at headings that exist in the
target document. From "Doc style — two readers, two layers": every spec and
every decision-log entry since the rule landed opens with a 2–4 sentence
summary, as ``count_sentences`` counts them.
"""

import re
from pathlib import Path
from urllib.parse import unquote, urlparse

import pytest
from markdown_it import MarkdownIt

REPO_ROOT = Path(__file__).resolve().parent.parent
SPECS_DIR = REPO_ROOT / "docs" / "specs"
PROPOSALS_DIR = REPO_ROOT / "docs" / "proposals"
DECISION_LOG = REPO_ROOT / "docs" / "decision_log.md"

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

SUMMARY_MIN_SENTENCES = 2
SUMMARY_MAX_SENTENCES = 4
# The two-layer doc style landed in a0c5044 on this date; older decision-log
# entries predate it and have no summary to count.
SUMMARY_CUTOVER_DATE = "2026-08-01"
# Named, never matched by shape, so a ``Decision:`` opener can't become a way
# around the gate. This entry carries the cutover date, but its commit 22ea0f8
# (02:53 -0700) predates the rule's a0c5044 (10:06 -0700) the same day.
SUMMARY_EXEMPT_ENTRIES = frozenset(
    {"2026-08-01: No Username Stays Fully Offline — User-Independent Totals Rejected"}
)

_H2_LINE = re.compile(r"^## (.+)$", re.MULTILINE)
_ENTRY_DATE = re.compile(r"\d{4}-\d{2}-\d{2}(?=:)")
_ABBREVIATION = re.compile(r"\b(e\.g|i\.e|vs|etc|approx|cf)\.", re.IGNORECASE)
_SENTENCE_BREAK = re.compile(r"(?<=[.!?])[\"')\]*]*\s+(?=[A-Z\"'`*(\[])")


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


def test_proposal_docs_live_in_proposals_dir():
    """The directory is the classifier: a lifecycle doc anywhere else under
    docs/ is misplaced, whether its name says proposal or only its Status
    line does. Specs are current-state docs and carry no Status line."""
    misplaced = []
    for doc in (REPO_ROOT / "docs").rglob("*.md"):
        if doc.is_relative_to(PROPOSALS_DIR) or doc.is_relative_to(SPECS_DIR):
            continue
        lines = doc.read_text(encoding="utf-8").splitlines()[:STATUS_SEARCH_LINES]
        if "proposal" in doc.name or any(STATUS_PATTERN.search(line) for line in lines):
            misplaced.append(str(doc.relative_to(REPO_ROOT)))
    assert not misplaced, (
        "Proposal docs live under docs/proposals/ (see AGENTS.md "
        f'"Documentation Habits"): {misplaced}'
    )


def test_proposal_docs_declare_status():
    missing = []
    for doc in PROPOSALS_DIR.rglob("*.md"):
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
    for doc in PROPOSALS_DIR.rglob("*.md"):
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


def count_sentences(paragraph: str) -> int:
    """Count the sentences of a layer-1 summary paragraph.

    The count is the definition of a sentence for the 2–4 cap, so a summary
    this miscounts is fixed by rephrasing the prose, never by teaching the
    counter a new case. Code spans are blanked, so their periods don't count;
    links keep only their text; the dots of the common abbreviations, of
    decimals, and of versions are dropped. A sentence ends at terminal
    punctuation, plus any closing quote, bracket, or star, followed by
    whitespace and a capital, quote, backtick, star, or bracket.

    The count is a floor: a sentence that opens with a digit or a lowercase
    word doesn't split from the one before it. Review still holds the cap
    and the other layer-1 rules.
    """
    text = " ".join(paragraph.split())
    # Uppercase, so a sentence that opens with a code span still splits.
    text = re.sub(r"`[^`]*`", "CODE", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = _ABBREVIATION.sub(r"\1", text)
    text = re.sub(r"(\d)\.(\d)", r"\1\2", text)
    return len([part for part in _SENTENCE_BREAK.split(text) if part.strip()])


def _paragraphs(text: str) -> list[str]:
    return [part for part in re.split(r"\n\s*\n", text.strip()) if part.strip()]


def spec_summary(text: str) -> str:
    """Return a spec's layer-1 summary: the first paragraph after its H1."""
    lines = text.splitlines()
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    paragraphs = _paragraphs("\n".join(lines))
    return paragraphs[0] if paragraphs else ""


def log_summaries(text: str) -> dict[str, str]:
    """Map each gated decision-log heading to its layer-1 summary.

    An entry is gated when its heading date is on or after
    ``SUMMARY_CUTOVER_DATE`` and it isn't named in ``SUMMARY_EXEMPT_ENTRIES``.
    Its summary is the first paragraph after the heading once the whole
    ``Status:`` paragraph is skipped: a Status line wraps when it carries a
    supersession note, and stopping at its first line reads the note as the
    summary. Regions are cut from the source text, never from a render, so
    the gate has no Markdown rendering edge cases to chase.
    """
    headings = list(_H2_LINE.finditer(text))
    summaries = {}
    for heading, following in zip(headings, [*headings[1:], None]):
        title = heading.group(1).strip()
        date = _ENTRY_DATE.match(title)
        if not date or date.group() < SUMMARY_CUTOVER_DATE:
            continue
        if title in SUMMARY_EXEMPT_ENTRIES:
            continue
        end = following.start() if following else len(text)
        paragraphs = _paragraphs(text[heading.end() : end])
        if paragraphs and paragraphs[0].startswith("Status:"):
            paragraphs = paragraphs[1:]
        summaries[title] = paragraphs[0] if paragraphs else ""
    return summaries


def test_layer1_summaries_hold_two_to_four_sentences():
    counts = {
        spec.relative_to(REPO_ROOT).as_posix(): count_sentences(
            spec_summary(spec.read_text(encoding="utf-8"))
        )
        for spec in sorted(SPECS_DIR.rglob("*.md"))
    }
    log = DECISION_LOG.read_text(encoding="utf-8")
    counts.update(
        {
            f"decision_log.md: {title}": count_sentences(summary)
            for title, summary in log_summaries(log).items()
        }
    )
    bad = [
        f"{name}: {count} sentences"
        for name, count in counts.items()
        if not SUMMARY_MIN_SENTENCES <= count <= SUMMARY_MAX_SENTENCES
    ]
    assert not bad, (
        f"Layer-1 summaries hold {SUMMARY_MIN_SENTENCES}-{SUMMARY_MAX_SENTENCES} "
        "sentences as count_sentences counts them; a miscount is fixed by "
        "rephrasing the summary (AGENTS.md 'Doc style — two readers, two "
        "layers'):\n" + "\n".join(bad)
    )


def test_summary_exemptions_name_real_entries():
    # A renamed or deleted exempt entry would leave a dead name behind, and a
    # typo here would exempt nothing while looking like it exempts something.
    titles = {
        heading.group(1).strip()
        for heading in _H2_LINE.finditer(DECISION_LOG.read_text(encoding="utf-8"))
    }
    assert SUMMARY_EXEMPT_ENTRIES <= titles


ABBREVIATIONS = ("e.g.", "i.e.", "vs.", "etc.", "cf.", "approx.", "E.g.")


@pytest.mark.parametrize(
    ("paragraph", "expected"),
    [
        pytest.param("Run `app.py` or `x. Y` first. It starts.", 2, id="code-span"),
        pytest.param(
            "Read [the guide](../user_guide.md#v2.0.1) first. Then run it.",
            2,
            id="link-url-periods",
        ),
        pytest.param(
            "Shipped in v2026.08.18, 1.5x faster. Nothing else.", 2, id="version"
        ),
        *(
            pytest.param(
                f"Pick a game, {abbr} Valorant, and play. Then rest.", 2, id=abbr
            )
            for abbr in ABBREVIATIONS
        ),
        pytest.param('It said "stop." Then it stopped.', 2, id="closing-quote"),
        pytest.param("It fails (as logged.) Then it recovers.", 2, id="closing-paren"),
        pytest.param("One idea. **Bold** opens the second.", 2, id="bold-opener"),
        pytest.param(
            "One idea wraps\nacross lines. The\nsecond.", 2, id="two-sentences"
        ),
        pytest.param("One. Two? Three! Four. Five.", 5, id="five-sentences"),
        pytest.param(
            "It parsed files. 8,064 of them passed.", 1, id="digit-undercounts"
        ),
    ],
)
def test_count_sentences(paragraph, expected):
    assert count_sentences(paragraph) == expected


def test_spec_summary_is_the_first_paragraph_after_the_h1():
    spec = "# Capability\n\nOne summary. Two.\n\nStatements below link the log.\n"
    assert spec_summary(spec) == "One summary. Two."


def test_log_summary_skips_the_whole_wrapped_status_paragraph():
    log = (
        "# Decision Log\n\n## Status Values\n\n- `Accepted`: current.\n\n"
        "## 2026-09-01: Wrapped Status\n\n"
        "Status: Superseded in part by the\n"
        "[2026-09-02 entry](#x): the sentence. No longer holds. Rest stands.\n\n"
        "One summary sentence. Two summary sentences.\n\n"
        "**Payload.** Dense. Detail. Here. And. More.\n"
    )
    assert log_summaries(log) == {
        "2026-09-01: Wrapped Status": "One summary sentence. Two summary sentences."
    }


def test_log_summary_scope_starts_at_the_cutover_and_skips_the_exemption():
    exempt = min(SUMMARY_EXEMPT_ENTRIES)
    log = (
        "## 2026-09-01: Gated\n\nStatus: Accepted\n\nOne. Two.\n\n"
        f"## {exempt}\n\nStatus: Accepted\n\nDecision: one only.\n\n"
        "## 2026-07-31: Legacy\n\nStatus: Accepted\n\nDecision: a. B. C. D. E.\n"
    )
    assert log_summaries(log) == {"2026-09-01: Gated": "One. Two."}
