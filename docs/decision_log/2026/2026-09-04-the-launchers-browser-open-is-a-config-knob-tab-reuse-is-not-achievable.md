# 2026-09-04: The Launcher's Browser Open Is A Config Knob; Tab Reuse Is Not Achievable

Status: Accepted

The desktop shortcut opened a browser tab every time the dashboard started,
and a tester who keeps that tab in a browser folder and restarts the app often
was collecting a new one each time. There is no way for a launcher to reuse
the tab that is already open, so the app now takes a config setting,
`open_browser_on_launch`, that stops it opening one at all. It is on by
default and the console still prints the address, so the only person affected
is the one who turns it off.

**Tab reuse is not achievable from a launcher.** `Open-Dashboard` is
`Start-Process "http://<address>:<port>/"`, and shell-executing a URL always
creates a new tab. Neither Windows nor the browsers expose "focus the tab
already showing this URL", and `window.focus()` from a background tab is
blocked without user activation. The request as posed ("open only if the tab
is not there") has no API behind it. Suppressing the open is the only lever
that exists.

**What this protects, and what it does not.** Every stale tab is a live
hazard, not just clutter: the supported model is one active tab
([specs/notifications.md](specs/notifications.md)), because `message_queue` is
process-wide and each drain's payload reaches one client, so with two tabs
open a run toast or a PB celebration lands in whichever drain runs first. The
knob lets a user stop accumulating tabs, but it only helps the user who finds
it. The hazard still reaches everyone else, so this is the interim, not the
fix.

**Live-client detection is the eventual fix, and is deferred.** The server
always knows whether a tab is watching, since every open tab polls
continuously, so "skip the browser when a client is already connected" is
detectable. It does not serve the case that prompted this. Restarting the app
means closing the console, which kills the app and releases the mutex, so the
relaunch is a cold start and the surviving tab is a dead tab from the previous
session: at the moment the server becomes ready that tab has not checked in
yet, and it reconnects only on its next timer tick. Chromium throttles timers
in long-hidden tabs to roughly once a minute, so the launcher would have to
wait up to a minute after readiness before it could decide, on every cold
start, to serve a minority case. The knob has none of that cost.

**Rejected alternatives.** `data/settings.json` with a Settings-page control:
app-owned with a frozen three-key schema, and it would put a control on the
Settings page for something the app never does. A flag on the desktop
shortcut: passing it needs a bootstrap version bump, and the shortcut is
rewritten on every reinstall. Parsing `config.toml` in PowerShell: exactly
what `Get-ConfiguredEndpoint` exists to refuse, because TOML integer forms
(`8_051`, `0x1F73`) and pydantic coercion would make the launcher probe a port
the server did not bind. Two knobs (one for cold start, one for the
already-running branch): over-configuration for one behavior.

**The accepted smell.** `ConfigData` now carries a key the app never reads.
That is deliberate. `config.toml` is the only user-owned file both sides of
the install already agree on, and the launcher already asks the app's loader
to read it.

**The `Get-ConfiguredEndpoint` contract.** The one-line answer grew a third
field: `print(c.port, c.host, getattr(c, 'open_browser_on_launch', True))`.
The launcher splits the last stdout line into exactly three fields and reads
the third as on when it is the literal `True`; a two-field line is not
accepted, because a launcher never meets an older loader through a supported
path (the bootstrap runs `versions\<tag>\scripts\launcher.ps1` from the same
tag it reads the loader from) and a lenient parse would hide a broken
contract. The `getattr` is belt-and-braces against a hand-mixed install, kept
because the failure mode without it is this function's worst: a nonzero exit
takes the fallback and loses the port and host too, and a healthy app is then
declared dead on the wrong port.

**The snippet must contain no double quote.** Windows PowerShell 5.1, which
the desktop shortcut runs, re-quotes a native command's argument without
escaping the double quotes inside it, so the previous
`print(f"{c.port} {c.host}")` form arrived at python as `print(f{c.port}` and
exited with a `SyntaxError`. `Get-ConfiguredEndpoint` was therefore taking
its fallback on every launch, probing `8050` on `127.0.0.1` whatever
`config.toml` said, and any install with a non-default port or host would
have been reported as a dashboard that failed to start. The probe's first
form, `Get-ConfiguredPort` (`print(load_config().port)`, no double quote),
worked; the breakage arrived with the rename to `Get-ConfiguredEndpoint` and
its f-string, so the affected releases are `v2026.08.18` through the last one
cut before this fix. Backslash-escaping the quotes fixes 5.1 and breaks
PowerShell 7, which passes the backslashes through to python; both were
measured. The snippet now lives in a `$EndpointProbeSnippet` here-string,
uses `print` with commas instead of an f-string, and quotes the attribute
name with Python's single quotes, which survive both shells unchanged.

One consequence worth recording against
[2026-08-14](#2026-08-14-the-listen-address-is-configurable-loopback-by-default):
that entry's launcher half, deriving the probe and browser addresses from the
configured `host`, was inert in every installed launcher over that window,
because the fallback always reported `127.0.0.1`.

**Only stdout is captured, and not under `Stop`.** Two separate traps sit on
the same line. The first is ordering: stdout and stderr are separate pipes,
so merging them with `2>&1` gives no guaranteed order, and the "last line
wins" parse the original comment described as robust against a config warning
was not. Measured at roughly one run in sixty, the unknown-key warning
arrived after the print line, so the parse read the warning and fell back --
an intermittent wrong-port kill for anyone with a typo in `config.toml`.
Nothing read the stderr text, so it is discarded rather than ordered.

The second is the preference. The launcher sets
`$ErrorActionPreference = 'Stop'` at the top of the script, and 5.1 turns a
native command's redirected stderr into a terminating `NativeCommandError` on
its first line while that preference holds. The one line the loader is known
to write is the unknown-key warning, so any typo in `config.toml` reached the
catch-all and took the fallback. Paired with the redirect since the probe was
first written, and masked from `v2026.08.18` onward by the quoting bug above,
so fixing that unmasked it. Discarding stderr is still a redirect, so the
preference fix is needed either way. The capture now runs under a
function-local `Continue`, restored in the `finally`.

**These are 5.1-only failures, so a Python test cannot see them.** Both bugs
were invisible to a subprocess test, which quotes its arguments properly and
inherits no PowerShell preference. `windows-latest` ships Windows PowerShell
5.1, so the suite now dot-sources the real `Get-ConfiguredEndpoint` through
the PowerShell AST and calls it against a temporary install root, pinning the
three-field contract, the browser flag, and the unknown-key case in the shell
the shortcut actually runs.

**One launch of lag.** The launcher that performs an update is the previous
release's, selected by the bootstrap from the manifest before the update
check ran. The launch that installs the release carrying this change
therefore still opens a browser, and the setting takes effect from the next
one. Setting the key before that update is harmless: an older app names it in
the existing unknown-key warning and starts normally.
