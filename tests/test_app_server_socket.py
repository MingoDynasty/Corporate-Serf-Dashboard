"""The app claims both loopback faces exclusively, on the one port."""

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
port = first[0].getsockname()[1]
print(f"port={port}")
bind_server_socket(port)
print("second bind unexpectedly succeeded")
"""

# An IPv6-less machine: AF_INET6 socket creation fails the way Windows reports
# a missing protocol family. IPv4 must still be served. ``source.app`` is
# imported before the patch so that the import graph (dash -> asyncio -> ssl,
# which subclasses ``socket.socket``) still sees the real class.
NO_IPV6_SNIPPET = """
import errno
import socket

from source.app import bind_server_socket

real_socket = socket.socket


def no_ipv6(family=socket.AF_INET, *args, **kwargs):
    if family == socket.AF_INET6:
        raise OSError(errno.EAFNOSUPPORT, "address family not supported")
    return real_socket(family, *args, **kwargs)


socket.socket = no_ipv6

sockets = bind_server_socket(0)
print(len(sockets), sockets[0].family == socket.AF_INET)
"""


def _one_face_snippet(family: str, address: str) -> str:
    """Squat one loopback face, then ask the app for that port.

    The app must refuse the port outright rather than serving on whichever
    face happened to still be free.
    """
    return f"""
import socket

from source.app import bind_server_socket

squatter = socket.socket(socket.{family}, socket.SOCK_STREAM)
squatter.bind(("{address}", 0))
port = squatter.getsockname()[1]
print(f"port={{port}}")
bind_server_socket(port)
print("bind unexpectedly succeeded")
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


def test_bind_server_socket_returns_both_bound_loopback_faces() -> None:
    result = _run_in_app(
        "import socket;"
        " from source.app import bind_server_socket;"
        " socks = bind_server_socket(0);"
        " print(sorted(s.getsockname()[0] for s in socks),"
        " sorted(s.family.name for s in socks),"
        " len({s.getsockname()[1] for s in socks}),"
        " socks[0].getsockname()[1] != 0,"
        " [s.getsockopt(socket.SOL_SOCKET, socket.SO_ACCEPTCONN) for s in socks])"
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith(
        "['127.0.0.1', '::1'] ['AF_INET', 'AF_INET6'] 1 True "
    ), result.stdout
    # Bound but *not* listening: waitress calls listen() itself for sockets
    # handed to it through ``sockets=``.
    assert result.stdout.rstrip().endswith("[0, 0]"), result.stdout


def test_second_bind_of_a_claimed_port_exits_with_an_actionable_error() -> None:
    result = _run_in_app(SECOND_BIND_SNIPPET)

    assert "second bind unexpectedly succeeded" not in result.stdout
    assert result.returncode == 1, result.stderr

    port = result.stdout.split("port=")[1].split()[0]
    assert f"port {port} is already in use" in result.stderr
    assert "127.0.0.1" in result.stderr and "::1" in result.stderr
    assert "config.toml" in result.stderr


def test_a_port_taken_on_only_the_ipv4_face_is_refused() -> None:
    result = _run_in_app(_one_face_snippet("AF_INET", "127.0.0.1"))

    assert "bind unexpectedly succeeded" not in result.stdout
    assert result.returncode == 1, result.stderr
    port = result.stdout.split("port=")[1].split()[0]
    assert f"port {port} is already in use" in result.stderr


def test_a_port_taken_on_only_the_ipv6_face_is_refused() -> None:
    result = _run_in_app(_one_face_snippet("AF_INET6", "::1"))

    assert "bind unexpectedly succeeded" not in result.stdout
    assert result.returncode == 1, result.stderr
    port = result.stdout.split("port=")[1].split()[0]
    assert f"port {port} is already in use" in result.stderr


def test_a_machine_without_ipv6_is_served_on_ipv4_alone() -> None:
    result = _run_in_app(NO_IPV6_SNIPPET)

    assert result.returncode == 0, result.stderr
    assert "1 True" in result.stdout
