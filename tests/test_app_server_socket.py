"""The app claims its port exclusively, so a second copy cannot serve it too."""

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# Bind a free port, then try to bind that same port a second time -- the
# duplicate instance this guards against, minus the rest of the app.
SECOND_BIND_SNIPPET = """
from source.app import bind_server_socket

first = bind_server_socket(0)
print(f"port={first.getsockname()[1]}")
bind_server_socket(first.getsockname()[1])
print("second bind unexpectedly succeeded")
"""


def _run_in_app(snippet: str) -> subprocess.CompletedProcess[str]:
    """Run a snippet against ``source.app`` in a child process.

    Importing ``source.app`` configures process-wide logging and creates
    ``data/logs``, so it stays out of the test process.
    """
    return subprocess.run(
        [sys.executable, "-c", snippet],
        cwd=REPO_ROOT,
        env={**os.environ, "PYTHONPATH": str(REPO_ROOT)},
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )


def test_bind_server_socket_returns_a_bound_loopback_socket() -> None:
    result = _run_in_app(
        "import socket;"
        " from source.app import bind_server_socket;"
        " sock = bind_server_socket(0);"
        " host, port = sock.getsockname();"
        " print(host, port != 0,"
        " sock.getsockopt(socket.SOL_SOCKET, socket.SO_ACCEPTCONN))"
    )

    assert result.returncode == 0, result.stderr
    host, bound, accepting = result.stdout.split()
    assert host == "127.0.0.1"
    assert bound == "True"
    # Bound but *not* listening: waitress calls listen() itself for sockets
    # handed to it through ``sockets=``.
    assert accepting == "0"


def test_second_bind_of_a_claimed_port_exits_with_an_actionable_error() -> None:
    result = _run_in_app(SECOND_BIND_SNIPPET)

    assert "second bind unexpectedly succeeded" not in result.stdout
    assert result.returncode == 1, result.stderr

    port = result.stdout.split("port=")[1].split()[0]
    assert f"port {port} is already in use" in result.stderr
    assert "config.toml" in result.stderr
