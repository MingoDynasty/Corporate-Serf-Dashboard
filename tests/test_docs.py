"""Documentation hygiene checks.

Enforces the docs lifecycle from AGENTS.md "Shipping a proposal" and
"Documentation Habits": proposal files declare a Status line, capability
specs under docs/specs/ do not (they are current-state docs, not lifecycle
docs), no markdown doc links to a file that has been deleted (e.g. a
proposal distilled into the decision log), and heading-anchor links point at
headings that exist in the target document.
"""

import re
from pathlib import Path
from urllib.parse import unquote, urlparse

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

# Inline markdown links/images: [text](target) — captures the target up to
# whitespace or the closing paren, which also handles optional "title" parts.
INLINE_LINK_PATTERN = re.compile(r"\]\(([^)\s]+)[^)]*\)")

# Reference-style link definitions: `[id]: target` at the start of a line
# (up to 3 leading spaces per CommonMark). Excludes footnotes (`[^1]: ...`).
REFERENCE_DEF_PATTERN = re.compile(r"^ {0,3}\[[^\]^][^\]]*\]:\s+(\S+)", re.MULTILINE)

# ATX headings, the only heading style these docs use.
HEADING_PATTERN = re.compile(r"^ {0,3}#{1,6}\s+(.+?)\s*$", re.MULTILINE)

STATUS_PATTERN = re.compile(r"status\s*:", re.IGNORECASE)
STATUS_SEARCH_LINES = 15


def _relative_link_targets(doc: Path) -> list[str]:
    # Fenced code is example text, not live links, so it is stripped here the
    # same way heading collection strips it.
    text = _strip_fenced_code(doc.read_text(encoding="utf-8"))
    targets = []
    for pattern in (INLINE_LINK_PATTERN, REFERENCE_DEF_PATTERN):
        for match in pattern.finditer(text):
            target = match.group(1)
            if urlparse(target).scheme or target.startswith("mailto:"):
                continue
            targets.append(target)
    return targets


def _strip_fenced_code(text: str) -> str:
    """Drop fenced code blocks so example links and `# comment` lines are
    not read as live links or headings."""
    kept = []
    fence = None
    for line in text.splitlines():
        stripped = line.lstrip()
        if fence is None and stripped[:3] in ("```", "~~~"):
            fence = stripped[:3]
        elif fence is not None and stripped.startswith(fence):
            fence = None
        elif fence is None:
            kept.append(line)
    return "\n".join(kept)


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
    text = _strip_fenced_code(doc.read_text(encoding="utf-8"))
    for match in HEADING_PATTERN.finditer(text):
        base = _github_anchor(match.group(1))
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


def test_link_targets_skip_fenced_code_examples(tmp_path):
    doc = tmp_path / "fenced.md"
    doc.write_text(
        "# Title\n\n[real](other.md#anchor)\n\n"
        "```markdown\n[example](#not-a-heading)\n```\n",
        encoding="utf-8",
    )
    assert _relative_link_targets(doc) == ["other.md#anchor"]


def test_heading_anchor_dedup_matches_github(tmp_path):
    doc = tmp_path / "dup.md"
    doc.write_text("# Foo\n\n# Foo-1\n\n# Foo\n", encoding="utf-8")
    assert _heading_anchors(doc) == {"foo", "foo-1", "foo-2"}


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
