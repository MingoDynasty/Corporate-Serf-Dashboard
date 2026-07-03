# CI Gates Proposal

Status: Proposed
Date: 2026-07-03

## Goal

Run the merge bar automatically on every pull request: `ruff format --check`,
`ruff check`, `mypy source`, `pytest`, plus the cheap `compileall` syntax
check. Today the gates are honor-system — five commands every human and agent
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
- uv-based environment setup that *validates* `uv.lock` against
  `pyproject.toml` (`uv sync --locked`) and pins the Python minor version,
  with the uv cache enabled so warm runs are fast.
- `windows-latest` runner.
- A concurrency group so superseded runs on the same ref are cancelled.
- Least-privilege workflow token (`permissions: contents: read`) and actions
  pinned to full commit SHAs.

### Out

- A local single-command task runner (`make check` equivalent). The workflow
  file itself becomes the canonical, executable list of gates; a task runner
  remains an optional follow-up if typing five commands ever hurts.
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

`<sha>` placeholders below stand for full commit SHAs resolved at
implementation time — mutable tags like `@v4` are not immutable references,
so actions must be pinned by SHA (with a version comment for readability).

```yaml
name: gates

on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  gates:
    runs-on: windows-latest
    steps:
      - run: git config --global core.autocrlf false
      - uses: actions/checkout@<sha> # vX.Y.Z
      - uses: astral-sh/setup-uv@<sha> # vX.Y.Z
        with:
          enable-cache: true
          python-version: "3.14"
      - run: uv sync --locked
      - run: uv run --no-sync ruff format --check .
      - run: uv run --no-sync ruff check
      - run: uv run --no-sync mypy source
      - run: uv run --no-sync python -m compileall source tests
      - run: uv run --no-sync pytest tests
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

- `uv sync --locked` installs the locked environment including the dev group
  (pytest, mypy, ruff) and **fails if `uv.lock` is stale** relative to
  `pyproject.toml`. (`--frozen` would not: it uses the lockfile as-is without
  validating it, letting a stale committed lockfile pass CI.)
- The gate commands run with `uv run --no-sync` so they use the environment
  exactly as synced — without it, each `uv run` may quietly re-resolve and
  update the environment, undoing the `--locked` guarantee.
- Python is pinned to `3.14` via `setup-uv`'s `python-version` input.
  `requires-python = ">=3.14"` is a floor, not a pin, and the repo has no
  `.python-version` file — without the explicit pin, CI would silently move
  to 3.15+ when uv starts preferring it. (Committing a `.python-version`
  file is the alternative; the workflow-level pin avoids changing local
  behavior in this proposal.)
- `setup-uv`'s cache is keyed on `uv.lock`, so dependency installs are
  near-instant after the first run per lockfile revision.

### Token and supply-chain hygiene

- `permissions: contents: read` at the workflow level: this workflow only
  checks out and tests code, so the `GITHUB_TOKEN` should not inherit
  whatever broader default the repository settings allow.
- Actions pinned to full commit SHAs, the only immutable action reference;
  bump them deliberately (comment carries the human-readable version).

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
