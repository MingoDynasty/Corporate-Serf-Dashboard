# 2026-08-09: Human-Facing URLs Say localhost, Machine Probes Stay On 127.0.0.1

Status: Accepted

The launcher used to open the browser at `http://127.0.0.1:<port>/` while the
README and the development run said `http://localhost:<port>/`. Those are two
different browser origins, so the dashboard opened from the desktop shortcut
and the same install reached by typing `localhost` kept two separate sets of
saved UI preferences. Every URL a person sees or clicks now says `localhost`.
The launcher's internal health check still uses `127.0.0.1`, because a
machine-to-machine check should not depend on how the machine resolves names.

Decision: Human-facing URLs — the browser the launcher opens
(`scripts/launcher.ps1`, `Open-Dashboard`), the "Dashboard running at ..."
line it prints, and the URLs in `README.md` and `docs/` — use
`http://localhost:<port>/`. Machine-to-machine URLs stay on the literal
`127.0.0.1`: the launcher's `/health` readiness probe in `Wait-AppReady` is
deliberately resolver-free, and is not to be swept into consistency with the
human surfaces. `source/app.py` is untouched — its bind logic and port-taken
error text are about which addresses the server claims, not about which name
the browser is handed.

Why: the app persists UI state in `window.localStorage`, which is keyed by
origin — the Mantine color scheme written by the head script in
`source/app_shell.py`, the navbar Burger's `persistence_type="local"`, and the
chart-option switches in `source/pages/home.py` (Dash persistence defaults to
local storage). `localhost:<port>` and `127.0.0.1:<port>` are distinct
origins, so the two entry points to one install were accumulating disjoint
toggle state. Unifying on the name the docs and the development run already
use collapses that to one origin.

Why this is safe despite the shadowing history: the
[2026-07-19 exclusive-bind entry](2026-07-19-the-app-binds-its-port-exclusively-and-exits-if-it-is-taken.md)
and its 2026-07-20 addendum bind **both** loopback faces (`127.0.0.1` and
`::1`) with `SO_EXCLUSIVEADDRUSE`, and the addendum's failure semantics are
two-bucket: a port free on only one face is refused outright rather than
half-served. So a half-bound instance cannot exist, and while the app is
serving, whichever face the resolver hands `localhost` is ours — the old
"browser gets a stranger's 404" failure needed an IPv6 face we did not hold.
The launcher's start and update paths open the browser only after
`Wait-AppReady` succeeds, and the already-running path opens it at an instance
that passed its own launcher's probe — so that one IPv4 probe vouches for both
faces. On a machine with no IPv6 the app serves IPv4 alone and `localhost`
resolves to IPv4 anyway.

Consequences: Nothing is superseded; the bind decision stands unchanged. The
maintainer's existing install has persisted toggles under the `127.0.0.1`
origin, which appear reset once after this change and are re-set by hand — per
the single-user policy, no migration code. Future URL surfaces pick a side by
audience: shown to a person, `localhost`; consumed by a script, `127.0.0.1`.
