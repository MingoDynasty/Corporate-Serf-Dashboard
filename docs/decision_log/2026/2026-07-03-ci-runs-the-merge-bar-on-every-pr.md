# 2026-07-03: CI Runs The Merge Bar On Every PR

Status: Superseded in part by the 2026-07-06 cross-repo Python v2 tooling decision

Decision: A single GitHub Actions `gates` job runs the repository merge bar on
every pull request and push to `main`: ruff format check, ruff lint, mypy,
CPython `compileall`, and pytest. It runs on `windows-latest`, validates the
lockfile with `uv sync --locked`, and executes each gate with
`uv run --no-sync`. Python and uv are pinned, action dependencies use immutable
full commit SHAs, the workflow token has read-only contents access, and
superseded runs on the same ref are cancelled.

Why: This fulfills the deferred CI consequence of the 2026-07-03 ruff
consolidation decision. An executable merge bar catches stale lockfiles,
formatting drift, type errors, syntax errors, and regressions consistently,
including on doc-only changes where the docs hygiene tests still matter.
Windows matches the supported development and runtime environment.

Consequences: `.github/workflows/gates.yml` is the canonical executable list of
gates. Local pre-handoff validation remains unchanged because it is the fastest
feedback path. A local single-command task runner remains optional rather than
part of this decision. After the workflow has established a short green
history, the repository owner should mark the `gates` check required on
`main`; branch protection is intentionally outside the workflow.
