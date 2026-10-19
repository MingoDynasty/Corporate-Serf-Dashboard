"""File names built from text someone outside the code chose."""

import hashlib


def safe_file_key(value: str) -> str:
    """Return a file-name stem for ``value``: a readable prefix and a short digest.

    Sanitizing alone is lossy: every character outside the preserved set folds
    to ``_``, so distinct values like ``a.b`` and ``a_b`` produced one key and
    silently shared (and overwrote) each other's files. The sanitized prefix
    stays so a folder of these files remains human-readable, and a short digest
    of the raw value makes distinct values distinct, including values Windows
    file names would fold together by case. sha256 is used rather than
    ``hash()`` because the key must be stable across runs.
    """
    sanitized = "".join(
        char if char.isalnum() or char in ("-", "_") else "_" for char in value
    )
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:8]
    return f"{sanitized}-{digest}"
