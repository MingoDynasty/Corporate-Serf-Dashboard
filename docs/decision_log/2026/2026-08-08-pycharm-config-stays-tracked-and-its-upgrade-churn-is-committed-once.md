# 2026-08-08: PyCharm Config Stays Tracked And Its Upgrade Churn Is Committed Once

Status: Accepted

An IDE upgrade changed the format PyCharm writes its own tracked config files
in, and PyCharm re-emits that format every time it launches. Reverting the diff
therefore only defers it, so the project commits it once instead. The IDE
config directory also no longer counts as a reason to cut an automated release,
which it previously would have. A leftover Black on-save setting turned out to
be orphaned by the same upgrade, and deleting it survived an IDE restart, so it
is gone rather than merely documented.

Decision: `.idea/` stays tracked, IDE-upgrade schema churn is committed rather
than reverted, and `.idea/` joins `_BLOCKED_DIRECTORIES` in
`scripts/release_job.py` so an IDE-config-only push does not release.

Why: the same tool-config diff was committed as `89d54cf` on 2026-08-04 and
reverted by `b44901a`; launching PyCharm on `main` rewrote both XML files
immediately, so the revert bought nothing. Untracking `.idea/` instead would
throw away real configuration work — the interpreter and mypy setup, the source
root, and the indexing exclusions — while the genuinely volatile per-user files
(`workspace.xml`, `tasks.xml`, `shelf/`, datasources) are already covered
between the root `.gitignore` and `.idea/.gitignore`. On the release side,
`is_release_worthy()` is a blocklist, and `.idea/` matched no entry, so
`should_release()` returned `True` for a PyCharm tool map and
`.github/workflows/ci.yml` would have tagged CalVer and published a Latest
release that cannot be deleted. `.gitignore` and `.pre-commit-config.yaml` were
already blocked for exactly this reason.

Consequences and constraints:

- **Committing is not self-enforcing.** `.idea/pyLspTools.xml` records the
  registered tool map, so the loop restarts whenever a tool is toggled in the
  IDE: `89d54cf` registered `black` and `ruff`, while the settled state
  registers `ruff` only. What ended the churn is that tool state is now stable,
  not the act of committing it.
- **Neither remaining on-save formatter switch is live.** `.idea/misc.xml`'s
  `Black` component (`enabledOnSave=true`, against the
  `uv (Corporate-Serf-Dashboard)` SDK where `black.exe` really resolves) was
  deleted, because the upgrade orphaned it rather than leaving it live: tool
  state moved to `pyLspTools.xml`, and dropping `enabledOnReformat` was a
  one-time migration write. Hand-editing a generated file is normally what
  invites churn back, so this was tested — after the deletion a PyCharm restart
  rewrote `pyLspTools.xml` and `workspace.xml` and left `misc.xml` alone.
  `.idea/ruff.xml`'s `RuffConfigService` (`runRuffOnSave=true`) is inert for a
  different reason: it belongs to the third-party `com.koxudaxi.ruff` plugin,
  which is disabled IDE-side, so ruff-on-save runs from the built-in tool state
  instead. Read `ruff.xml` as a dormant plugin's config, not as live state. If
  a future upgrade re-emits either component, repeat the delete-and-restart
  check rather than reverting the config.
- **black is a transitive dependency, not an absent one.** It is not in
  `pyproject.toml` and not a configured project tool, but it stays in the lock
  under `datamodel-code-generator` and is installed in `.venv` — see
  [Consolidate Formatting And Linting On Ruff](#2026-07-03-consolidate-formatting-and-linting-on-ruff).
- **Blocking is about triggering, not shipping.** The two lists are separate:
  `_BLOCKED_DIRECTORIES` decides whether a push cuts a release, while
  `.gitattributes` decides what the release zip carries. `.idea/` is now on
  both — it neither triggers a release nor ships in one, per
  [Release Integrity Rests On GitHub Digests And An Enforced Archive Contract](#2026-08-21-release-integrity-rests-on-github-digests-and-an-enforced-archive-contract).
  `docs/` still shows the split as it was: blocked from triggering, but
  shipped, because the zip's own README links into it.
