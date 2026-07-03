# CI Gates Proposal

Status: Proposed
Date: 2026-07-03

## Goal

Run the merge bar automatically on every pull request: `ruff format --check`,
`ruff check`, `mypy source`, `pytest`, plus the cheap `compileall` syntax
check. Today the gates are honor-system — four commands every human and agent
must remember to run. The 2026-07-03 ruff consolidation decision explicitly
deferred "add CI or a single-command task runner separately"; this is that
work, scoped to CI.

## Why Now

- The merge bar only works if it runs. An honor-system bar degrades exactly
  when it matters most: large PRs, agent handoffs, and doc-only changes where
  "surely nothing broke."
- The docs hygiene test (PR #50) enforces proposal lifecycle rules through
  pytest — it only has teeth if pytest runs on every PR.
- Cost is one workflow file. No application changes.

## Scope

### In

- One GitHub Actions workflow, `.github/workflows/gates.yml`, running the five
  checks on `pull_request` and on `push` to `main`.
- uv-based environment setup honoring `uv.lock` (`uv sync --frozen`), with the
  uv cache enabled so warm runs are fast.
- `windows-latest` runner.
- A concurrency group so superseded runs on the same ref are cancelled.

### Out

- A local single-command task runner (`make check` equivalent). The workflow
  file itself becomes the canonical, executable list of gates; a task runner
  remains an optional follow-up if typing four commands ever hurts.
- Branch protection / marking the check required. That is a repo-settings
  action for the owner once the workflow has a few green runs.
- Coverage reporting, artifact upload, release automation, matrix builds,
  scheduled runs.

## Design

### Runner OS: `windows-latest`

The suite is only known-green on Windows (the development environment), and
the app itself targets Windows (KovaaK's, watchdog on a local stats
directory, atomic `os.replace` cache writes). CI should exercise the OS users
actually run. Trade-offs: Windows runners are slower than Ubuntu, but the
repository is public so Actions minutes are free, and a ~2-4 minute wall time
is acceptable. Add an Ubuntu job later only if cross-platform support becomes
a real goal — not speculatively.

### Workflow sketch

Action versions below are indicative; pin the current majors at
implementation time.

```yaml
name: gates

on:
  pull_request:
  push:
    branches: [main]

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  gates:
    runs-on: windows-latest
    steps:
      - run: git config --global core.autocrlf false
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true
      - run: uv sync --frozen
      - run: uv run ruff format --check .
      - run: uv run ruff check
      - run: uv run mypy source
      - run: uv run python -m compileall source tests
      - run: uv run pytest tests
```

### Windows considerations

- **Line endings.** Set `core.autocrlf false` *before* checkout so the
  working copy matches the committed LF blobs. This heads off the historical
  "formatter flaps on a CRLF checkout" failure mode; without it, a
  runner-image git config could hand `ruff format --check` CRLF files.
- **Known local flakes.** Two tests have been observed to fail locally with
  `PermissionError` on `os.replace` under sandboxed runs, passing on rerun.
  Start CI with **no** retry plugin. If the same flake reproduces on hosted
  runners, fix it narrowly (bounded retry around the replace in the affected
  tests, or `pytest-rerunfailures` scoped to those tests) rather than blanket
  reruns that could mask real regressions.

### Environment

- `uv sync --frozen` installs the locked environment including the dev group
  (pytest, mypy, ruff), and resolves the Python version (3.14) per the
  project metadata — no separate `setup-python` step.
- `setup-uv`'s cache is keyed on `uv.lock`, so dependency installs are
  near-instant after the first run per lockfile revision.

## Test Plan

- The implementing PR itself must run the workflow and pass — that is the
  primary test.
- Nice-to-have red-path check on the PR branch before merge: push one commit
  with a deliberate formatting violation, confirm the run fails on the
  `ruff format --check` step, then revert it.

## Documentation Updates If Implemented

- Add a decision-log entry ("CI Runs The Merge Bar On Every PR") noting it
  fulfills the deferred consequence of the 2026-07-03 ruff decision.
- `CLAUDE.md`: replace "There is no CI workflow" with a pointer that CI now
  enforces the same commands; running them locally first remains the fast
  path.
- `AGENTS.md`: note that CI exists; the pre-handoff validation commands are
  unchanged.
- Delete this proposal per the shipping checklist.

## Open Questions

- None blocking. After a few green runs, the owner should mark the `gates`
  check required on `main` in repo settings.
