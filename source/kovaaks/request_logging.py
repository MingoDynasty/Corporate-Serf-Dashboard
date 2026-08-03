"""Logging helpers for KovaaK's API request failures."""

import re

import requests

# ``str(exc)`` for requests/urllib3 failures embeds the prepared URL with its
# query string, and the response-derived summary below carries ``response.url``
# for the same reason. Both are leaks for a request whose parameters are user
# data the app never persists, because ``data/logs/debug.log`` ships with bug
# reports.
_QUERY_STRING_PATTERN = re.compile(r"\?\S*")


def request_exception_summary(
    exc: requests.RequestException,
    *,
    redact_query: bool = False,
) -> str:
    """Return a concise description for expected request failures.

    ``redact_query`` replaces any query string in the summary with a
    placeholder, for callers whose request parameters must stay out of the log.
    """
    summary = _summarize(exc)
    if redact_query:
        return _QUERY_STRING_PATTERN.sub("?<redacted>", summary)
    return summary


def _summarize(exc: requests.RequestException) -> str:
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
