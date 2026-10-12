# 2026-08-10: Bug Reports Land On GitHub Issues, With The Log Attached Unredacted And Disclosed

Status: Accepted

The app now has one place for feedback and bug reports: GitHub Issues, with a
bug form and a feature form and no blank-issue option. The bug form asks for
the app version and requires a log file, because a failure on a machine no one
else can see is otherwise undiagnosable. The log is attached exactly as the
app wrote it — including the reporter's KovaaK's username and Steam ID — and
the form says so plainly before the upload box, because the issue and its
attachments are public. The Settings page pre-fills the version into the form
and shows where the log lives, so filing a report is a click rather than a
scavenger hunt.

Decision: three parts, all settled on the
[feedback intake proposal](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/226)
and shipped in PRs #228 and #229.

**Disclose, do not redact (D1).** `debug.log` is attached as written. A
KovaaK's player's username and SteamID64 are already stamped on every
leaderboard score they set unless they opt out of leaderboards entirely, and
both values are what diagnoses the likeliest bug class — rank lookups and
benchmark row matching that fail on *which account* they resolved. An audit of
real logs on 2026-08-09 (the maintainer's production installs, Aug 5–9, plus a
4.3 MB dev corpus back to June 24) established the boundary this rests on:
Steam personas never reach the log at all (the identity probe's by-username
calls log as `<redacted>` via the `sensitive` flag in
`api_service._get_with_retry`, and `config/identity_detection.py` logs counts
and positions only); the startup config dump is benign under the current
schema; and no credentials exist anywhere in the app to leak. What *is* in the
log and is accepted here: the KovaaK's username in per-attempt request params
and in failure lines that embed the full URL, the SteamID64 that
`get_benchmark_json` passes unredacted (latent — not witnessed in any log
yet, and knowingly left that way by this decision), Windows usernames inside
absolute paths under `%LOCALAPPDATA%`, and the scores, sensitivities, and
timestamps the app exists to record. Nothing about what the app logs changes;
the escape hatch is that the log is plain text the reporter can read first.

Disclosure must name the audience, not only the contents. The form's copy
states that the issue and its attachments are public to anyone on the
internet, GitHub account or not, and invites reading the log before uploading.
Those two are required content, not style. The alternative — redaction
machinery across several unredacted failure-logging sites plus the benchmark
request params — buys privacy the leaderboard already gave away and costs the
values that identify the root cause.

**Issues and forms only (D2).** Blank issues are disabled in favor of
`bug_report.yml` and `feature_request.yml`; there is no Discord server and no
GitHub Discussions. Labels: `bug`, `enhancement`, `question`, `needs-info`,
and `upstream` for KovaaK's-side breakage the app can only work around.
Feedback arriving anywhere else is transcribed into an issue by the maintainer
as the canonical record (`gh issue create` is unaffected by the blank-issue
setting). This knowingly accepts an exclusion: users without a GitHub account
— likely a real share of a gamer audience — have no direct submission path.
**Revisit trigger:** launch feedback showing reports dying for want of an
account. Rejected for now: a second moderated inbox (Discord) or a second
triage surface (Discussions) for a single maintainer, ahead of any
demonstrated volume; and email, for its spam surface and lack of public dedupe
or history. Crash telemetry (Sentry or similar) is rejected outright as
privacy-hostile for a local tool.

**The Settings-page affordance (D3).** Under the version block,
`pages/settings.py` renders a "Report a bug" anchor whose href is
`bug_report_url(release_label)` — `…/issues/new?template=bug_report.yml&version=<label>`,
built with `urlencode`. Two contracts with
`.github/ISSUE_TEMPLATE/bug_report.yml` live in that URL: the template
*filename*, and the `version` field *id* that GitHub pre-fills by name. The
label is encoded rather than pasted because a release tag arrives from JSON
the app did not write. Every label the resolver produces is pre-filled —
`dev` and `unknown` included — since the field is required and editable, so a
placeholder beats an empty box. Beside it the resolved log directory is shown,
so "attach `debug.log`" names a place to look. `data/logs` moved into
`utilities/paths.log_dir()` for this, consumed by both `app.py` and the page:
pages cannot import `app`, and the literal should exist once.
