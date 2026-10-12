# 2026-08-21: The Launcher Narrates A Slow Start And Keeps Its 120-Second Ceiling

Status: Accepted

The launcher used to print one "Starting" line and then nothing while it
waited for the app, so a slow first start looked exactly like a hang. It now
stays quiet for the first few seconds and, if the app is still not up, prints
how many seconds have passed, repeating every few seconds until the app
answers or the wait gives up. A start that finishes quickly prints nothing
new. The two-minute limit on the wait is unchanged, on purpose.

Decision: the heartbeat lives inside `Wait-AppReady` in `scripts/launcher.ps1`,
so both call sites get it: the normal start and pending-update activation.
The output contract, ratified 2026-08-20 and shipped in PR #243:

- Ready before the ~5 s gate: nothing new. The fast path's console output is
  byte-identical to what it was before.
- Still waiting at the gate: `Still starting Corporate Serf Dashboard ... N
  seconds elapsed.`, then another line every ~5 s.
- Ready after at least one heartbeat: `Corporate Serf Dashboard is ready
  after N seconds.` No heartbeat shown means no completion line. The
  `exited` and `timeout` outcomes never print a completion line; their
  callers report the failure as before.
- The `Dashboard running at http://...` line is unchanged, and still prints
  on every successful launch by either startup path, once the app is ready.
  It was never reached on a failed start: a normal start that returns
  `timeout` or `exited` stops at `Stop-Fatal` before it.
- No reassurance or explanation sentences. The elapsed counter is the whole
  feature. Gate and interval are implementer-tunable around ~5 s; both are
  5 s today.

Why the gate is ~5 s: 14 installed starts measured 2026-08-20 on the
development machine ranged 0.12–5.62 s, median 2.18 s. The samples are
warm-biased and single-machine. A slow-but-healthy warm start may therefore
occasionally show a single heartbeat line; that is accepted, do not tune it
away. Why this copy: it echoes the launcher's own vocabulary ("Corporate Serf
Dashboard", the existing "Starting ... " lines). Never "the dashboard" for
the thing being started; a prior ruling found it reads as the browser.

The cadence is a floor, not a schedule. Loop granularity is an in-flight
health probe's two-second timeout plus the half-second sleep, so a heartbeat
can land up to ~2.5 s after its nominal time and the timeout outcome can
overshoot the ceiling by about as much. On a machine where a closed loopback
port is slow to refuse, every pre-listen probe burns its full timeout, which
is why the PR's transcripts show 7/12 s rather than 5/10 s. The probe itself
is unchanged. Its address stays governed by the
[2026-08-14 configurable-listen-address entry](#2026-08-14-the-listen-address-is-configurable-loopback-by-default):
`Get-ProbeAddress` sends a wildcard bind to its own family's loopback and
every other configured host to that host's literal URL form. The gate on
the full SHA and launch token, and process exit detected at the next loop
check rather than at the ceiling, are likewise unchanged.

Why `$HealthTimeoutSec` stays at 120: the ceiling's job is failure
declaration, and timeout is destructive. On the normal start the child is
killed and the launcher exits with a fatal "check config / reinstall"
message; on the update path the pending version is killed and the previous
one is started instead. A false timeout on a genuinely slow cold start turns
"slow" into "broken" on exactly the first-run path the heartbeat exists to
protect, and the warm-biased measurements above say nothing about the
cold-start tail. Revisit only with clean-machine cold-start evidence, and
then size the ceiling at two to three times the worst observed start.

Alternatives rejected: reassurance copy such as "the first start can take
longer" (words without information; the counter already says it), and
retuning the ceiling alongside the heartbeat (no evidence to size it, and
the failure mode of guessing low is the one described above).
