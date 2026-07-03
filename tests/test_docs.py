"""Documentation hygiene checks.

Enforces the docs lifecycle from AGENTS.md "Shipping a proposal": proposal
files declare a Status line, and no markdown doc links to a file that has
been deleted (e.g. a proposal distilled into the decision log).
"""

import re
from pathlib import Path
from urllib.parse import unquote, urlparse

REPO_ROOT = Path(__file__).resolve().parent.parent

DOC_FILES = sorted(
    [
        *(REPO_ROOT / "docs").glob("*.md"),
        REPO_ROOT / "README.md",
        REPO_ROOT / "AGENTS.md",
        REPO_ROOT / "CLAUDE.md",
    ]
)

# Inline markdown links/images: [text](target) — captures the target up to
# whitespace or the closing paren, which also handles optional "title" parts.
LINK_PATTERN = re.compile(r"\]\(([^)\s]+)[^)]*\)")

STATUS_PATTERN = re.compile(r"status\s*:", re.IGNORECASE)
STATUS_SEARCH_LINES = 15


def _relative_link_targets(doc: Path) -> list[str]:
    text = doc.read_text(encoding="utf-8")
    targets = []
    for match in LINK_PATTERN.finditer(text):
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
    for doc in (REPO_ROOT / "docs").glob("*proposal*.md"):
        lines = doc.read_text(encoding="utf-8").splitlines()[:STATUS_SEARCH_LINES]
        if not any(STATUS_PATTERN.search(line) for line in lines):
            missing.append(str(doc.relative_to(REPO_ROOT)))
    assert not missing, (
        f"Proposal docs missing a 'Status:' line in the first "
        f"{STATUS_SEARCH_LINES} lines: {missing}"
    )
