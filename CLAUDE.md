# Corporate Serf Dashboard

Dash (Plotly) web app that watches the local Kovaak's stats directory and
plots scenario scores. Python 3.14, dependencies managed with uv.

## Commands
- Run: `uv run python source/app.py` (settings in `config.toml`, copied from
  `example.toml`; the default port 8080 may already be taken by Steam)
- Tests: `uv run pytest`
- Lint: `uv run pylint source` (config in `pyproject.toml`, fail-under 10)
- Types: `uv run mypy source`
- Format: ruff (`uv run ruff format .`), line length 88

There is no CI workflow — these local gates are the merge bar. Run all three
before calling a change done or approving a PR.

## Layout
- `source/` — application code. See `docs/architecture.md` for the module map
  and runtime data flow (the "where does X live" index).
- `tests/` — pytest suite
- `resources/playlists/` — benchmark playlist JSON (files under `generated/`
  are machine-generated; don't hand-edit)
- `docs/` — living docs (architecture, `decision_log.md`) plus proposals for
  in-flight work. One file per proposal (git is the version history — no
  `_v2`/`_v3` filename suffixes); when a proposal ships, distill it into a
  `decision_log.md` entry and delete the file. Review handoff docs are
  ephemeral and never land on main (see the `/pr-review` skill).
