# Tooling Consolidation Proposal (ruff-only)

**Status:** Final — decisions frozen, ready to implement.
**Date:** 2026-07-02 (audit run at commit `d3ddfaa`, main).
**Revised:** 2026-07-02, external review round 1 — all 5 findings accepted
(lint scope decided, uv.lock gate corrected, pre-commit pinning fixed,
preview-rule losses documented, AGENTS.md/decision-log tasks added).
**Decided by:** MingoDynasty. Do not reopen the frozen decisions below; implement them.

Consolidate formatting and linting on ruff, replacing black + isort + pylint.
The toolchain becomes **ruff + mypy + pytest**. Two PRs, each leaving all
gates green.

---

## Current state (audit snapshot, 2026-07-02)

| Tool | Configured where | State at HEAD |
|---|---|---|
| black | `[tool.black]` (no `line-length` → default 88) | 2 of 39 files in `source/`+`tests/` would reformat |
| isort | `[tool.isort]` `profile = "black"` | 10 files unsorted (8 in `source/`+`tests/`, 2 in `scripts/`) |
| pylint | ~560 lines of `[tool.pylint.*]`, `fail-under = 10` | **9.34/10 — red** (gate covers `source/` only) |
| mypy | `[tool.mypy]` | green |
| ruff | dev dep `ruff>=0.14.5` (locked: **0.15.19**); no config; invoked by AGENTS.md validation (`ruff check source tests`) on default rules | defaults pass |
| pytest | — | green (the reliable gate) |

Known defects in the current setup:

- **The pylint gate can never pass.** The `fixme` check counts the 8
  deliberate `TODO` comments against the score, so 10.0 is unreachable while
  any TODO exists.
- **The stated line length (120) is not what the formatter enforces.** Black
  runs at its default 88; pylint's 120 is just a lenient ceiling. The
  codebase already conforms to 88.
- **Two workflow docs describe the gates** — `CLAUDE.md` (commands + merge
  bar) and `AGENTS.md` (standard validation: pytest, `ruff check source
  tests`, `compileall`). Both must be updated by these PRs, and the
  2026-06-20 "Interim Merge Bar" entry in `docs/decision_log.md` must be
  marked `Superseded` when the new bar lands (per AGENTS.md rules).
- `black` and `mypy` sit in runtime `dependencies`; they belong in the `dev`
  group with pylint/pytest/ruff. Note `datamodel-code-generator` (runtime
  dep, used only for offline model generation) **depends on black and isort**,
  so both remain in `uv.lock` as transitive dependencies regardless.
- `[tool.pylint.main]` `source-roots = "Corporate-Serf-Dashboard/source"`
  points at a nonexistent path (dies with the pylint config removal).
- The `except A, B:` (PEP 758) style in `source/kovaaks/api_service.py` was
  deliberately kept "pending formatter standardization" — this proposal is
  that standardization.

Pylint violation breakdown (`uv run pylint source`, ~100 findings): 65
missing docstrings (35 function / 25 class / 5 module), 8 `fixme`, 5
`unused-argument`, 4 `line-too-long` (>120), 4 `too-many-locals`, 3
`logging-fstring-interpolation`, 2 each of `too-many-arguments`,
`duplicate-code`, `unspecified-encoding`, `too-many-return-statements`,
`too-many-branches`, `too-many-positional-arguments`, and 1 each of
`broad-exception-caught`, `too-many-instance-attributes`,
`too-many-boolean-expressions`, `no-else-return`, `too-many-nested-blocks`,
`useless-return`.

**Verified ruff baseline:** with the frozen PR-2 config below, `uv run ruff
check` at `d3ddfaa` reports **111 findings**: 76 missing docstrings (D1,
all under `source/` — more than pylint's 65 because D1 also counts
`__init__.py` package docstrings and `__init__` methods that the pylint
config exempted), 8 unsorted-import files (auto-fixed in PR-1), and 27
other findings (itemized in PR-2 step 3). Do not re-estimate; these counts
are measured, not extrapolated from the pylint numbers.

---

## Frozen decisions

1. **Ruff-only.** `ruff format` replaces black; ruff's `I` rules replace
   isort; ruff's lint rules replace pylint. Pylint, black, and isort are
   removed as direct dependencies and configured tools. The lint gate
   becomes "`uv run ruff check` is clean" — no score, no fail-under.
2. **Formatter line length is 88** (ruff's default, set explicitly), with a
   **hard ceiling of 120** for lines the formatter can't split (long
   strings, URLs) via `E501` + `pycodestyle.max-line-length = 120`. This
   matches what the codebase already follows; 120-as-formatter-width was
   rejected because it would unwrap large amounts of settled code.
3. **Lint scope: `source/` + `tests/`; `scripts/` is formatted but not
   linted** (`lint.exclude`). The old pylint gate never covered `scripts/`,
   `scripts/Playlist Generator/` is slated for replacement by
   `benchmark_importer` (see `docs/playlist_generator_refactor_proposal.md`),
   and `scripts/Leaderboard Sensitivities/` is a one-off analysis script —
   docstring/lint investment there is waste. Tests are linted but exempt
   from docstring (`D1`), design-metric (`PLR09`), and unused-argument
   (`ARG`) rules: fixtures and fakes legitimately have unused parameters
   and long signatures.
4. **Docstrings are required and will all be written** (76 in `source/`,
   per the verified baseline). Tests and scripts are exempt. Enforcement is
   ruff's `D1` (missing-docstring) rules only — presence, not
   format-pedantry, so no pydocstyle convention churn.
5. **TODO comments do not fail the gate.** Do not enable ruff's `FIX`/`TD`
   rules. TODOs are tracked deliberately (see `docs/tech_debt.md`).
6. **Pre-commit enforces format + lint locally.** There is no CI; local
   gates are the merge bar, so the hook is the consistency backstop. mypy
   and pytest stay manual (too slow for a hook). The ruff-pre-commit `rev`
   is pinned to the same version as `uv.lock`'s ruff (see PR-1 step 4) —
   pre-commit installs its own ruff and does **not** use the project
   environment, so the two pins must be bumped together.
7. **`compileall` stays in the AGENTS.md standard validation.** Ruff uses
   its own parser; `python -m compileall` is an independent CPython syntax
   check and costs nothing to keep.

## Accepted losses (do not try to work around these)

Verified against ruff 0.15.19 without preview mode. Do not enable preview.

- **`duplicate-code` detection** — no ruff equivalent. The 2 current
  findings are Mantine layout boilerplate shared between pages, low value.
- **`unspecified-encoding`** — ruff's `PLW1514` is preview-only (verified:
  requires `--preview`), so it will not be enforced. The 2 current sites
  get `encoding="utf-8"` added in PR-2 as one-time cleanup, not enforced
  policy.
- **Other preview-only design metrics** — `too-many-locals`,
  `too-many-positional-arguments`, and similar will not be enforced.
- **`no-else-return`** — requires `RET505`, which is not in the frozen rule
  set. The 1 current site is fixed in PR-2 as one-time cleanup, not
  enforced policy.

---

## PR-1 — Formatter/imports swap (mechanical, low risk)

Scope: tooling only. No lint-rule expansion, no docstrings.

1. Add to `pyproject.toml`:

   ```toml
   [tool.ruff]
   line-length = 88
   target-version = "py314"

   [tool.ruff.lint]
   # Defaults (E4, E7, E9, F) plus import sorting. PR-2 expands this.
   extend-select = ["I"]
   ```

   No `lint.exclude` yet — PR-1 deliberately lints `scripts/` too so its
   imports get sorted once (2 files); PR-2 adds the exclusion.
2. Delete `[tool.black]` and `[tool.isort]` sections. Remove `black` from
   `dependencies`. Move `mypy` from `dependencies` to the `dev` group.
   (black and isort will remain in `uv.lock` as transitive deps of
   `datamodel-code-generator` — expected, see audit notes.) Keep pylint
   and its config for now (it is already the known-red gate; PR-2 removes
   it).
3. Run `uv run ruff format .` and `uv run ruff check --fix .` (import
   sorting). Expected churn: the 2 black-dirty files, the 10 isort-dirty
   files, plus a handful of files where ruff format deviates slightly from
   black. Commit the reformat as its own commit and add its hash to a new
   `.git-blame-ignore-revs` file.
4. Add pre-commit: `pre-commit` in the `dev` group, plus
   `.pre-commit-config.yaml` using the `astral-sh/ruff-pre-commit` hooks
   (`ruff-check` with `--fix`, then `ruff-format`), pinned to
   **`rev: v0.15.19`** to match `uv.lock`'s ruff. Add a comment in the
   YAML: "keep rev in sync with the ruff version in uv.lock". Note in the
   PR description that the user must run `uv run pre-commit install` once.
5. Update **both** workflow docs:
   - `CLAUDE.md`: Format line becomes "ruff (`uv run ruff format .`), line
     length 88"; drop the black + isort mention and the 120 claim.
   - `AGENTS.md`: standard validation becomes `uv run pytest tests`,
     `uv run ruff format --check .`, `uv run ruff check`,
     `uv run python -m compileall source tests` (compileall stays, frozen
     decision 7).

**Acceptance gates for PR-1:** `uv run ruff format --check .`,
`uv run ruff check`, `uv run pre-commit run --all-files`,
`uv run mypy source`, `uv run pytest` all green. Pylint unchanged (still
9.34 — pre-existing, not made worse).

## PR-2 — Lint consolidation + docstrings (the real work)

1. Expand the ruff config:

   ```toml
   [tool.ruff.lint]
   extend-select = [
       "I",    # import sorting (from PR-1)
       "E",    # pycodestyle errors, incl. E501 line length
       "W",    # pycodestyle warnings
       "D1",   # missing docstrings (presence only)
       "PL",   # pylint-derived rules (design metrics etc.)
       "ARG",  # unused arguments
       "G",    # logging format (G004 = f-string in logging call)
       "BLE",  # blind except
   ]
   ignore = [
       "PLR2004",  # magic-value comparisons — not part of the old bar
   ]
   exclude = ["scripts/**"]  # formatted but not linted (frozen decision 3)

   [tool.ruff.lint.pycodestyle]
   max-line-length = 120  # hard ceiling; formatter wraps at 88

   [tool.ruff.lint.per-file-ignores]
   "tests/**" = ["D1", "PLR09", "ARG"]
   ```

   This exact config was run against `d3ddfaa`: 111 findings, of which the
   8 import findings are fixed by PR-1, leaving 76 docstrings + 27 fixes.

2. Write the **76** missing docstrings in `source/` (30 functions, 25
   classes, 7 methods, 5 modules, 8 `__init__.py` packages, 1 `__init__`
   method). One-line imperative summaries matching the style of existing
   docstrings in the codebase; multi-line only where a one-liner would be
   misleading; package `__init__.py` docstrings are one line describing
   the package. This is the bulk of the PR and the part the reviewer will
   read closely — no filler docstrings that restate the function name.
3. Fix the 27 remaining findings (verified locations):
   - `G004` ×3 — `source/my_watchdog/file_watchdog.py`: convert f-string
     logging calls to lazy `%s` style.
   - `E501` ×5 — `data_service.py:30,32`, `file_watchdog.py:113`,
     `home.py:411,423`: wrap, or `# noqa: E501` for unsplittable URLs
     (pylint previously exempted URL lines; ruff does not).
   - `BLE001` ×1 — `api_service.py:1048`: if this broad except is a
     deliberate handler, keep it with `# noqa: BLE001` and a one-line
     justification comment.
   - `PLR0913` ×4 / `PLR0911` ×3 / `PLR0912` ×3 — 10 design-metric
     findings over 7 functions (`api_service.py:1122` trips three at
     once): refactor only where a clean split is obvious; otherwise
     targeted `# noqa` with justification. Do not force awkward refactors
     to satisfy a metric.
   - `PLR1711` ×3 (useless return) — auto-fixable.
   - `PLW0108` ×2 — `tests/test_scenario_rank_freshness.py`: inline the
     lambdas.
   - `PLW0603` ×2 — both on `tests/conftest.py:13` (deliberate module-global
     config backup/restore fixture): one `# noqa: PLW0603`.
   - `PLW2901` ×1 — `data_service.py:392`: rename the loop variable.
   - One-time unenforced cleanups (accepted-loss rules): add
     `encoding="utf-8"` at the 2 `unspecified-encoding` sites; fix the 1
     `no-else-return`.
4. Remove pylint: delete the `pylint` dev dep and **all** `[tool.pylint.*]`
   sections (~560 lines).
5. Update **both** workflow docs: `CLAUDE.md` Lint line becomes
   `uv run ruff check` (no fail-under, no pylint) — the gates are ruff
   (format + check), mypy, pytest. `AGENTS.md` standard validation likewise
   drops any pylint mention.
6. Ship-out per docs process:
   - Add a `docs/decision_log.md` entry distilling this proposal (what was
     decided and why, including the accepted losses).
   - Mark the **2026-06-20 "Interim Merge Bar Until Lint/Format Cleanup"**
     entry `Superseded` by the new entry (keep the old text — AGENTS.md
     requires preserving superseded decisions).
   - **Delete this file** in the same PR.

**Acceptance gates for PR-2:** `uv run ruff format --check .`,
`uv run ruff check` (full rule set), `uv run pre-commit run --all-files`,
`uv run mypy source`, `uv run pytest` all green. `pylint` absent from
`pyproject.toml` and `uv.lock`; `black`/`isort` absent as **direct**
dependencies and config sections (they remain in `uv.lock` as transitive
deps of `datamodel-code-generator` — that is not a failure).

---

## Sequencing and coordination

- PR #41 (playlist-generator refactor proposal) is docs-only — no conflict
  risk with the reformat.
- **Land PR-1 before the benchmark_importer implementation PRs (PR-A,
  B1–B3) start**, since those touch `source/` and would otherwise need
  rebasing across the reformat commit.
- PR-2 can follow at leisure; it is additive (docstrings + config) and
  conflicts less.
- The project environment's ruff is pinned by `uv.lock` (0.15.19); the
  pre-commit hook's ruff is pinned separately by `rev:` in
  `.pre-commit-config.yaml`. **Bump both together** when upgrading ruff,
  or format output can drift between the hook and the CLI.

## Out of scope

- CI setup — local gates remain the merge bar.
- Items in `docs/tech_debt.md` (datetime consistency, binary search,
  inline styles) — unrelated to tooling.
- Moving `datamodel-code-generator` out of runtime `dependencies` (it is
  codegen-only tooling, and dropping it — or running it via `uvx` — would
  also remove black/isort from `uv.lock` entirely). Optional follow-up,
  not required by this proposal.
- Ruff preview mode, pydocstyle conventions (`D2`+), pyupgrade (`UP`), or
  any rule families beyond the frozen list. If a rule family seems
  attractive mid-implementation, note it in the PR description instead of
  enabling it.
