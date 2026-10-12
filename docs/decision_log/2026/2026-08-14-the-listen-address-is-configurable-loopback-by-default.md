# 2026-08-14: The Listen Address Is Configurable, Loopback By Default

Status: Accepted

The app now reads a `host` setting from `config.toml`, and still serves this
machine only unless that setting says otherwise. Setting it to `0.0.0.0` lets
other devices on the same network open the dashboard, which is the only way to
reach it from a phone or a second PC. The app has no login, so every device
that can reach the chosen address can read the run data and change the
settings. An install that does not set `host` behaves exactly as it did
before.

Decision: `ConfigData` gains `host: str = "127.0.0.1"`, and both server paths
honor it — `bind_server_socket(port, host)` for the waitress path, and the
`config.debug` Flask path via `app.run(host=config.host, ...)`. On the default
host the bind is byte-for-byte the previous behavior: both loopback faces,
`SO_EXCLUSIVEADDRUSE`, two-bucket failure semantics. A non-default host is
bound **alone**, with no `::1` companion.

**`host` must be an IP literal**, never a name; the address family is taken
from the literal, so `::` binds as IPv6 rather than failing as a malformed
IPv4 address. Resolution is what makes a name dangerous here: it picks one
face of whatever it resolves to, so `localhost` would bind `::1` alone on
this machine and `127.0.0.1` alone where the resolver orders IPv4 first,
holding one loopback face and leaving the other free to squat — the very
ambiguity the default's dual-face bind exists to close, reintroduced through
the most natural spelling of "same as the default". The empty string is the
same trap in different clothing: `getaddrinfo("", ...)` yields `AF_INET6`, so
`host = ""` — the natural way to hand-write "unset" — would publish the app
on `::`, every IPv6 interface included, with none of the warnings that gate an
explicit `0.0.0.0`. Both exit naming the setting. This costs nothing the
documentation promised: `README.md`, `example.toml`, and this entry all
specify literals.

Why loopback remains the default: there is no authentication anywhere in the
app. Settings are writable from the UI, so a reachable instance is not
read-only exposure. Defaulting to the LAN would hand that to every device on
whatever network the machine joins next, including untrusted ones.

Why a non-default host is bound alone: the `::1` companion in the
[2026-07-19 exclusive-bind entry](2026-07-19-the-app-binds-its-port-exclusively-and-exits-if-it-is-taken.md)
and its 2026-07-20 addendum exists to stop `localhost` resolving to a face the
app does not hold. A user naming one address outright has no such ambiguity to
close, and binding a speculative second address is not something a config
value should do silently.

Verified consequence of `0.0.0.0`: nothing answers on `::1`, so a client that
insists on IPv6 loopback is refused; `localhost` and `127.0.0.1` both connect,
because resolvers and browsers fall back to the IPv4 address.

**The launcher derives its addresses from `host`.** A fixed `127.0.0.1` probe
would have made a single-address bind unlaunchable from the installed
shortcut: no listener on `127.0.0.1` means `Wait-AppReady` times out and kills
a perfectly healthy server. `scripts/launcher.ps1` therefore reads `host`
alongside `port` — through the same "ask the app's own loader" contract, so
there is still no second TOML parser — and maps it to two destinations. The
`/health` probe stays resolver-free per the
[2026-08-09 entry](2026-08-09-human-facing-urls-say-localhost-machine-probes-stay-on-127001.md):
`0.0.0.0` probes `127.0.0.1`, `::` probes `[::1]` (Windows sets
`IPV6_V6ONLY`, so the IPv6 wildcard serves no IPv4 face), and any other host
is probed at the literal address it names. The browser URL says `localhost`
only on the **default** host, where the app holds both loopback faces and
whichever one the resolver picks is therefore ours. Under any other host the
app owns at most one face and an unrelated process can hold the other:
verified on Windows, an app bound to `0.0.0.0` alongside a stranger holding
`::1` sends `localhost` to the stranger, after the launcher's own IPv4 health
check has already passed. Every non-default host therefore opens at the same
literal address the readiness probe proved reachable. IPv6 literals are
bracketed for both.

Failure taxonomy — two buckets, not three. A host that is not an IP literal is
rejected before any bind, naming the setting. A well-formed literal that no
local interface holds — a mistyped LAN address, or one lost to a DHCP change —
fails the bind with `EADDRNOTAVAIL`, and that reports the **host**, not the
port: no port is free on an address this machine does not have, so the
port-taken message would send the user after the wrong setting.

Relationship to prior entries: nothing is superseded. The exclusive-bind
decision stands unchanged — the app still creates and binds its own sockets,
still sets `SO_EXCLUSIVEADDRUSE`, and still exits rather than half-serving a
port. What changes is only which address it claims. The
[2026-08-09 human-facing-URL entry](2026-08-09-human-facing-urls-say-localhost-machine-probes-stay-on-127001.md)
reasoning that "whichever face the resolver hands `localhost` is ours" is
narrowed to the default host, and holds there.

`debug` and `host` interact, and nothing enforces it. Flask sets
`use_debugger` from `debug` and Dash forwards `host` straight through, so
`debug = true` with a non-default host puts the PIN-gated Werkzeug console on
that network — an execution surface, not just the read-and-change-settings
ceiling the rest of this entry reasons about. The combination warns at startup
and is called out beside `debug` in `example.toml`, but is not refused:
`debug` is documented dev-only and both are the operator's own settings.
Refusing it outright stays available if that judgment turns out wrong.

Out of scope: authentication, TLS, and any in-app affordance for turning LAN
access on. On Windows a bind is also not sufficient by itself — an inbound
firewall rule is required, which is the operator's business and is documented
in `README.md` rather than automated.
