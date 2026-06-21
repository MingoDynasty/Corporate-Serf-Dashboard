"""Logging helpers for KovaaK's API request failures."""

import requests


def request_exception_summary(exc: requests.RequestException) -> str:
    """Return a concise description for expected request failures."""
    details = str(exc)
    if details:
        return details

    response = getattr(exc, "response", None)
    status_code = getattr(response, "status_code", None)
    if status_code is None:
        return exc.__class__.__name__

    reason = getattr(response, "reason", "")
    url = getattr(response, "url", "")
    summary = f"HTTP {status_code}"
    if reason:
        summary = f"{summary} {reason}"
    if url:
        summary = f"{summary} for {url}"
    return summary
