# 2026-09-01: Configured Ports And Poll Intervals Are Bounded At Load

Status: Accepted

A port a machine could never serve, such as 70000, used to get all the way to
the socket and fail with a raw Python traceback. It now fails as the
configuration file is read, with one line naming that file and exit code 1.
The accepted range is 1 through 65535, and the poll interval must be between 1
and the largest delay a browser timer can hold. The example configuration file
states both rules beside the settings they govern.

Provenance: retires the "Out-of-range port crashes with a raw traceback" entry
adopted into `docs/tech_debt.md` from the 2026-08-12 engineering audit corpus
(PR #258); fixed in PR #266.

**The bounds.** `ConfigData.port` is `Annotated[int, Field(ge=1, le=65535)]`
and `polling_interval` is `Annotated[int, Field(gt=0, le=2_147_483_647)]`, both
shaped like the `kovaaks_api_timeout_seconds` bound that preceded them. Nothing
else in `ConfigData` gained a constraint: `sens_round_decimal_places` and the
cache TTLs stay unbounded, deliberately. The scope is these two fields, so a
bad `host` keeps its own later, differently-worded failure at the bind rather
than joining this exit.

**Why validation, not a bind-path fix.** An unbounded `port` reached
`sock.bind()`, which raises `OverflowError` ("bind(): port must be 0-65535")
rather than `OSError`, so neither `_bind_face`'s `except OSError` nor
`bind_server_socket`'s errno-classifying one caught it. Bounding the field
turns the same input into a `ValidationError`, which `main()`'s existing
configuration handler already converts into the curated "Configuration error:
could not load `<path>` -- copy example.toml to config.toml." exit. The
collapsed one-message design is unchanged: the ranges are stated in
`example.toml`, where the user is already looking when they edit the setting.

**Why configured `0` is refused.** Port `0` is valid to the socket layer and
still supported there: `bind_server_socket(0)` asks the OS for a free port and
is unchanged, which direct callers and the socket tests rely on. It is not a
usable configured endpoint, though, because the installed launcher reads the
configured port before startup (`Get-ConfiguredEndpoint`), polls
`http://<probe>:<port>/health` on that exact port to decide the app is ready,
and opens the browser on it. An OS-chosen port is one the launcher cannot
discover, so the app would serve while the launcher declared a readiness
timeout.

**Why `polling_interval` is bounded at both ends.** The value is handed
straight to `window.setInterval` -- Dash 4.4.1's Interval calls
`setInterval(this.reportInterval, props.interval)` with no clamping -- and that
delay is a signed 32-bit int. Both ends of the range therefore produce the same
silent request flood: a non-positive period, and one above `2147483647`, which
overflows and fires immediately. Measured in Chromium, `2147483647` never
fired and `2147483648` fired at 0 ms.

The upper bound is browser representability, not a product cap. A *product*
cap -- one tight enough to keep the run-event freshness window small -- stays
rejected on the PB-celebration proposal's reasoning: that window already
absorbs an arbitrarily slow poll by adding the configured period to its cap,
and a tight cap would refuse config files that load today for the sake of a
toast. `2147483647` ms is about 24.8 days, so it refuses only values the
browser could not have honoured anyway.
