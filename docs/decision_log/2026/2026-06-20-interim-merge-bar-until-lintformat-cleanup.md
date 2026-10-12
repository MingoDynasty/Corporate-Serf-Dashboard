# 2026-06-20: Interim Merge Bar Until Lint/Format Cleanup

Status: Superseded by the 2026-07-03 ruff-only tooling decision

Decision: Until the lint/format cleanup lands, the merge bar is: `uv run pytest` and `uv run mypy source` must be **green**, and `uv run pylint source` plus `black --check`/`isort --check` must **not regress versus `main`** (no new findings in the files a change touches). The absolute CLAUDE.md bar (pylint `fail-under = 10`, black/isort clean) is the target, not yet current reality.

Why: As of 2026-06-20 `main` is green on pytest and mypy (the latter since PR #18 deleted a dead `mypy.ini` that was shadowing `[tool.mypy]`), but not on pylint (9.22/10 — missing docstrings, TODOs, broad-except, too-many-*), `black --check` (3 files), or `isort --check` (2 files). Those are pre-existing and reproduce on the committed LF blobs (not a CRLF flap). There is no CI, so the gates are an honour-system check; blocking feature PRs on an absolute bar `main` itself cannot meet is incoherent, while a baseline-comparison bar keeps shipping unblocked without growing the debt.

Consequences: Reviewers compare pylint/black/isort output for the changed files against the `main` baseline rather than requiring a green absolute run; pytest and mypy are hard green gates. The remaining pylint cleanup is deferred tech debt (~115 findings on `main`, dominated by missing docstrings, plus fix-or-disable calls on `too-many-*`, `broad-except`, `fixme`, and similar); the `black`/`isort` deltas are a few files. Remove this interim framing once pylint and the formatters are green on `main`.
