# Corporate Serf Dashboard

Dash (Plotly) web app that watches the local Kovaak's stats directory and
plots scenario scores. Python 3.14, dependencies managed with uv.

## Commands
- Run: `uv run python source/app.py` (settings in `config.toml`, copied from
  `example.toml`; the default port 8080 may already be taken by Steam)
- Tests: `uv run pytest`
- Lint: `uv run ruff check`
- Types: `uv run mypy source`
- Format: ruff (`uv run ruff format .`), line length 88

CI runs ruff format/check, mypy, compileall, and pytest on every pull request
and push to `main`; `.github/workflows/gates.yml` is the executable merge bar.
Run the same five checks locally first for the fastest feedback before calling
a change done or approving a PR.

## Layout
- `source/` — application code. See `docs/architecture.md` for the module map
  and runtime data flow (the "where does X live" index).
- `tests/` — pytest suite
- `resources/playlists/` — benchmark playlist JSON (files under `generated/`
  are machine-generated; don't hand-edit)
- `docs/` — living docs (architecture, `decision_log.md`, `product.md`) plus
  proposals for in-flight work. One file per proposal (git is the version history — no
  `_v2`/`_v3` filename suffixes); when a proposal ships, distill it into a
  `decision_log.md` entry and delete the file **in the shipping PR** — full
  checklist in AGENTS.md "Shipping a proposal". `tests/test_docs.py` enforces
  proposal `Status:` lines and fails on dangling doc links. Review handoff
  docs are ephemeral and never land on main (see the `/pr-review` skill).
