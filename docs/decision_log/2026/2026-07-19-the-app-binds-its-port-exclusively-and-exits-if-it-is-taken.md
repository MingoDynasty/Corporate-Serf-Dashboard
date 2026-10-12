# 2026-07-19: The App Binds Its Port Exclusively And Exits If It Is Taken

Status: Accepted

Decision: `source/app.py` creates and binds the listening socket itself
(`bind_server_socket`), sets `SO_EXCLUSIVEADDRUSE` where the platform has it,
and hands the bound socket to waitress as `serve(app.server, sockets=[sock],
threads=8)`. A failed bind prints an actionable message naming the port and
`config.toml`, then exits 1. Do not "simplify" this back to
`serve(app.server, host=..., port=...)` — that reintroduces the bug below.

Why: on Windows, a socket bound with `SO_REUSEADDR` (waitress's default for
sockets it creates) does not reserve the address. A second process can bind
the same `127.0.0.1:<port>` while the first is serving it, and Windows then
splits incoming connections nondeterministically between the two. The visible
symptom is a second copy of the dashboard silently answering some requests
with its own state — observed live during the release-launcher work, where
the launcher's `/health` token gate correctly refused to promote the build
but the user got a 120-second hang instead of an error. It is also the
long-standing "one dev run shadowing another on localhost" trap. POSIX
already refuses the second bind, so the flag is the Windows-only half of a
behavior we want everywhere.

Mechanism, verified against waitress 3.0.2: a socket passed through
`sockets=` is constructed with `bind_socket=False`, so waitress never binds
it, and `accept_connections()` calls `listen()` — hand it over **bound but
not listening**. Waitress then calls `set_reuse_addr()` on it unconditionally;
on an exclusively-bound socket that `setsockopt` fails with `WSAEINVAL`
(10022) and waitress swallows the error, so exclusivity survives. Confirmed
empirically: with the flag set, a second bind of the same port is refused
whether the second binder asks for a plain bind (`WSAEADDRINUSE` 10048),
`SO_REUSEADDR` (`WSAEACCES` 10013), or `SO_EXCLUSIVEADDRUSE` (10048).

Alternatives rejected: probing `/health` for a foreign responder before
binding (racy — the port can be taken between probe and bind — and blind to
non-app squatters like Steam on 8080); a launcher-side check (the launcher
already fails safe on a shadowed health answer, and with this change the
duplicate exits immediately, which its "exited" path already handles).

Scope: the `config.debug` Flask development-server path is unchanged; it is a
dev-only convenience. The bind happens immediately before `serve()`, so a
duplicate instance still does its ~2s of startup work before exiting.

POSIX footnote: binding the socket ourselves means waitress's pre-bind
`SO_REUSEADDR` no longer applies, and on POSIX that flag is what lets a
server rebind a port whose old connections are still in `TIME_WAIT`. A fast
restart there could now be refused. Windows is unaffected — verified that an
immediate rebind succeeds with a genuine `TIME_WAIT` pair on the port. We
accept this because nothing serves on POSIX: the app targets Windows and CI
runs `windows-latest` only. If that ever changes, set `SO_REUSEADDR` before
`bind()` on non-Windows platforms — on POSIX it permits the `TIME_WAIT`
rebind without letting a second live server share the port, so it restores
the old behavior without weakening the Windows guarantee.

Addendum, 2026-07-20: both loopback faces are bound, not just IPv4.
`bind_server_socket` now returns a list — `127.0.0.1` and `::1`, same port,
each claimed with the same `SO_EXCLUSIVEADDRUSE` treatment — and both go to
waitress as `sockets=`. The IPv4-only bind left the decision half-enforced:
on Windows `localhost` may resolve to `::1` first, so an unrelated process
holding the IPv6 face still captured every browser request to
`http://localhost:<port>/` while the dashboard sat unreachable on IPv4.
Observed live during the PR #153 session — another project's server held
wildcard `::` while the dashboard held `127.0.0.1`, and the browser got the
stranger's 404 page. (The squatter was *not* a `config.debug` run of this
app: werkzeug picks the address family with a colon heuristic, so its
`host="localhost"` always binds `AF_INET` `127.0.0.1` — verified against the
pinned werkzeug.) Claiming `::1` ourselves collapses that to the two outcomes
the original decision wanted: a specific bind takes routing precedence over
someone else's wildcard `::`, and if the face is genuinely taken the app
exits loudly instead of being silently shadowed.

Do not "simplify" the two sockets into one dual-stack `AF_INET6` socket with
`IPV6_V6ONLY=0`. That shape does not work here at all: v4-mapped addressing
applies only to wildcard binds, so a dual-stack socket bound to `::1` accepts
no `127.0.0.1` traffic whatsoever. Two explicit sockets are the only correct
shape, and they keep the per-face exclusivity semantics verified above.

Failure semantics stay deliberately two-bucket. Either face already taken
(`EADDRINUSE`) closes whatever was bound and takes the existing exit-1 path,
now with a message saying the port must be free on both addresses — a port
free on only one face is refused outright rather than half-served. IPv6
genuinely absent (`EAFNOSUPPORT` creating the socket, or `EADDRNOTAVAIL`
binding `::1`) logs one info line and serves IPv4 alone; on such a machine
`localhost` resolves to IPv4 anyway, so the ambiguity disappears with the
interface. Re-verified against waitress 3.0.2 that the multi-socket path
gives each socket the same treatment as the single-socket contract above:
`create_server` loops over `adj.sockets` constructing every `AF_INET`/
`AF_INET6` socket with `bind_socket=False`, calls the swallowed
`set_reuse_addr()` per socket, and calls `listen()` per socket in
`accept_connections()`; with two entries it returns a `MultiSocketServer`
driving both from one loop.
