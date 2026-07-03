# Tooling Consolidation Proposal (ruff-only)

**Status:** Final — decisions frozen, ready to implement.
**Date:** 2026-07-02 (audit run at commit `d3ddfaa`, main).
**Revised:** 2026-07-02, external review round 1 — all 5 findings accepted
(lint scope decided, uv.lock gate corrected, pre-commit pinning fixed,
preview-rule losses documented, AGENTS.md/decision-log tasks added).
**Revised:** 2026-07-03, external review round 2 — all 4 findings accepted
(`force-exclude` added, migration command order fixed, inline `# pylint:`
directive cleanup added, accepted-loss inventory corrected and completed).
**Revised:** 2026-07-03, external review round 3 — both findings accepted
(`too-many-nested-blocks` reclassified as preview-only `PLR1702`; stale
tooling reference in `codebase_improvement_proposals.md` added to PR-2).
**Amended:** 2026-07-03, owner review — PR-1 dependency hygiene expanded
(stubs + codegen tool to `dev`; dead `tomli-w` and redundant `tzdata`
removed).
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
- Runtime `dependencies` contains dev-only and dead entries: `black`,
  `mypy`, the type-stub packages (`pandas-stubs`, `scipy-stubs`), and
  codegen-only `datamodel-code-generator` belong in the `dev` group;
  `tomli-w` is referenced nowhere; `tzdata` duplicates pandas's own
  Windows dependency. Note `datamodel-code-generator` **depends on black
  and isort**, so both remain in `uv.lock` as transitive dependencies
  regardless of the cleanup.
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

Every rule below was verified against ruff 0.15.19. Do not enable preview.

**No ruff equivalent** (the rule does not exist in ruff at all):

- **`duplicate-code`** — the 2 current findings are Mantine layout
  boilerplate shared between pages, low value.
- **`too-many-instance-attributes`** — `PLR0902` is not a ruff rule
  (verified: `ruff rule PLR0902` errors), not merely preview.
- **`too-many-lines`** (module length) — no equivalent (`PLC0302` is not a
  ruff rule); the existing inline disable in `api_service.py` is simply
  deleted in PR-2.

**Preview-only in ruff** (exists, but requires `--preview`, so not enforced):

- **`unspecified-encoding`** (`PLW1514`) — the 2 current sites get
  `encoding="utf-8"` added in PR-2 as one-time cleanup, not enforced policy.
- **`too-many-locals`** (`PLR0914`), **`too-many-positional-arguments`**
  (`PLR0917`), **`too-many-boolean-expressions`** (`PLR0916`),
  **`too-many-nested-blocks`** (`PLR1702`).

**Not selected:**

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
   # pre-commit passes filenames explicitly; without this, exclusions
   # (PR-2's lint.exclude for scripts/) are ignored for explicit paths.
   force-exclude = true

   [tool.ruff.lint]
   # Defaults (E4, E7, E9, F) plus import sorting. PR-2 expands this.
   extend-select = ["I"]
   ```

   No `lint.exclude` yet — PR-1 deliberately lints `scripts/` too so its
   imports get sorted once (2 files); PR-2 adds the exclusion.
   `force-exclude` is a no-op in PR-1 but must be present before PR-2:
   verified that without it, the pre-commit hook reports all 29 `scripts/`
   findings despite `lint.exclude`, and with it the exclusion holds.
2. Delete `[tool.black]` and `[tool.isort]` sections. Then clean up
   `dependencies` (all verified 2026-07-03):
   - **Remove `black`** (replaced by ruff).
   - **Move to the `dev` group:** `mypy`, `pandas-stubs`, `scipy-stubs`
     (stub-only packages consumed exclusively by mypy), and
     `datamodel-code-generator` (offline codegen only — never imported).
     Black and isort will remain in `uv.lock` as its transitive deps —
     expected, see audit notes.
   - **Remove `tomli-w`** — dead: referenced in no `.py` file in the repo
     nor in any pending proposal; legacy carryover from the pip→uv
     migration.
   - **Remove `tzdata`** — redundant: nothing in `source/` imports
     `zoneinfo`, and pandas already depends on tzdata on `win32`.

   Keep pylint and its config for now (it is already the known-red gate;
   PR-2 removes it).
3. Run, **in this order** (fix first, then format — import fixes can
   produce lines the formatter then needs to rewrap; same order as the
   pre-commit hooks):

   ```powershell
   uv run ruff check --fix .
   uv run ruff format .
   ```

   Expected churn: the 2 black-dirty files, the 10 isort-dirty
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
   exclude = ["scripts/**"]  # lint-only exclusion (frozen decision 3);
                             # holds for explicit paths via force-exclude (PR-1)

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
   - `BLE001` ×1 — `api_service.py:1048`: already marked deliberate with
     an inline `# pylint: disable=broad-exception-caught` — convert to
     `# noqa: BLE001` (step 4 covers the directive cleanup).
   - `PLR0913` ×4 / `PLR0911` ×3 / `PLR0912` ×3 — 10 design-metric
     findings over 7 functions (`api_service.py:1122` trips three at
     once). Four of these functions (`api_service.py:676`, `:995`,
     `:1077`, `:1122`) already carry `# pylint: disable-next=too-many-*`
     directives — those are prior deliberate suppress decisions; carry
     them over as `# noqa: PLR0911`/`PLR0913`/`PLR0912`, do not
     re-litigate refactors. For the unsuppressed sites (`home.py:59`,
     `home.py:272`, `data_service.py:370`): refactor only where a clean
     split is obvious; otherwise targeted `# noqa` with justification. Do
     not force awkward refactors to satisfy a metric.
   - `PLR1711` ×3 (useless return) — auto-fixable.
   - `PLW0108` ×2 — `tests/test_scenario_rank_freshness.py`: inline the
     lambdas.
   - `PLW0603` ×2 — both on `tests/conftest.py:13` (deliberate module-global
     config backup/restore fixture): one `# noqa: PLW0603`.
   - `PLW2901` ×1 — `data_service.py:392`: rename the loop variable.
   - One-time unenforced cleanups (accepted-loss rules): add
     `encoding="utf-8"` at the 2 `unspecified-encoding` sites; fix the 1
     `no-else-return`.
4. Remove the **11 inline `# pylint:` directives** across `source/` (grep
   `# pylint`), then re-run `uv run ruff check` and add a `# noqa: <rule>`
   only where a finding actually fires after removal. Known mappings:
   - `disable-next=too-many-*` at `api_service.py:675/994/1076/1121` →
     `# noqa: PLR0911`/`PLR0913`/`PLR0912` on the `def` line (see step 3;
     `too-many-positional-arguments` has no stable ruff rule — drop it).
   - `disable=broad-exception-caught` at `api_service.py:1048` →
     `# noqa: BLE001`. The same directive at `api_service.py:1068`,
     `file_watchdog.py:56`, and `home.py:208/248` either already has a
     `# noqa: BLE001` alongside it or does not fire under ruff — delete
     the pylint half only.
   - `disable=line-too-long` at `data_service.py:30` → `# noqa: E501`.
   - `disable=too-many-lines` at `api_service.py:5` → delete outright (no
     ruff equivalent; see accepted losses).
5. Remove pylint: delete the `pylint` dev dep and **all** `[tool.pylint.*]`
   sections (~560 lines).
6. Update **both** workflow docs: `CLAUDE.md` Lint line becomes
   `uv run ruff check` (no fail-under, no pylint) — the gates are ruff
   (format + check), mypy, pytest. `AGENTS.md` standard validation likewise
   drops any pylint mention. Also update
   `docs/codebase_improvement_proposals.md` item 14: the
   `ruff`/`black`/`mypy` tooling choice is resolved by this proposal
   (ruff + mypy, no black) — rewrite the item to keep only its still-open
   part (a single-command entry point / task runner and CI gating).
7. Ship-out per docs process:
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
- Dropping `datamodel-code-generator` entirely or running it via `uvx`
  (which would purge black/isort from `uv.lock`). PR-1 moves it to the
  `dev` group; full removal is an optional follow-up, not required by
  this proposal.
- Ruff preview mode, pydocstyle conventions (`D2`+), pyupgrade (`UP`), or
  any rule families beyond the frozen list. If a rule family seems
  attractive mid-implementation, note it in the PR description instead of
  enabling it.
