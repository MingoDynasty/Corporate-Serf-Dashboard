"""Serve the local ``/health`` identity endpoint."""

import os

from flask import Flask, Response, jsonify

from source.utilities.build_info import get_build_info

LAUNCH_TOKEN_ENV_VAR = "CSD_LAUNCH_TOKEN"


def register_health_endpoint(server: Flask) -> None:
    """
    Register ``/health`` on the app's Flask server.

    The launcher starts a new version, then polls this endpoint before it
    promotes that version: it accepts the new build only when the reported
    full ``sha`` is the expected one *and* the echoed launch token matches
    the one it passed in through the environment. A bare HTTP 200 is not
    proof of life, because an already-running instance or an unrelated
    service on the port can answer it.

    The gate is on the SHA, not the tag: a build on trial has not been
    promoted yet, so its manifest still names the previous version and is
    ignored (see ``build_info``) — it identifies itself from its stamp and
    reports ``tag: None``.

    No authentication: the endpoint reports build identity only, and is
    reachable by anything that can reach the configured ``host`` (see the
    2026-08-14 decision-log entry, which made the listen address a
    setting). Keep it that way -- nothing here may become sensitive
    without an auth story to go with it.
    """

    # SPIKE ARTIFACT (D7 codex-exec review spike, 2026-08-30): disposable
    # marker comment. This branch is never merged.
    @server.route("/health")
    def health() -> Response:
        """Report the running build's identity and the launch token."""
        build_info = get_build_info()
        return jsonify(
            {
                "tag": build_info.tag,
                "sha": build_info.sha,
                "commit_date": build_info.commit_date,
                "source": build_info.source,
                "launch_token": os.environ.get(LAUNCH_TOKEN_ENV_VAR),
            }
        )

    # SPIKE ARTIFACT (D7 codex-exec review spike, 2026-08-30): disposable.
    @server.route("/health/ready")
    def ready() -> Response:
        """Report that the server is up."""
        return jsonify({"ready": True})
