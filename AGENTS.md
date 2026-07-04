# AGENTS.md

Shared context for future agent work in this repository.

## Workflow

- This project is developed on Windows with PowerShell.
- Prefer `rg` for text/file search when available.
- Use `uv` for Python commands. In this environment, set the local cache before running `uv`:

```powershell
$env:UV_CACHE_DIR='.uv-cache'
```

- Standard validation before handoff:

```powershell
uv run pytest tests
uv run ruff format --check .
uv run ruff check
uv run mypy source
uv run python -m compileall source tests
```

- Local commits authored by Codex should use:

```text
Codex <codex@local>
```

- PRs opened through the GitHub connector may still show as opened by `MingoDynasty` because the connector uses the user's GitHub authorization.

## Documentation Habits

- Use `AGENTS.md` for repo-local workflow rules, conventions, and recurring gotchas.
- Use proposal docs under `docs/` for feature design that is in flight or
  planned. Every proposal starts with a `Status:` line near the top
  (`Proposed`, `In progress`, `Future`, ...) so a reader can tell live work
  from stale files at a glance.
- Use `docs/decision_log.md` for durable decisions that are cross-cutting, costly to reverse, based on external constraints, or likely to be questioned later.
- Use `docs/kovaaks_api_notes.md` for KovaaK's endpoint behavior, quirks, relied-upon fields, and failure semantics.
- Gitignored scratch (review handoffs, kickoff prompts, one-off scripts, data
  samples) goes under `ignore/` in a categorized subdirectory, never loose at
  the top level — routing table in [ignore/README.md](ignore/README.md).
- Do not log every small implementation choice as a decision.
- When a durable decision changes, keep the old decision and mark it superseded instead of erasing history.
- If a user direction changes an existing proposal or decision, call it out. After agreement, update the relevant docs as part of the implementation.
- When fixing a bug, add or update a regression test unless there is a clear reason not to; explain the exception in the handoff.

### Shipping a proposal (docs definition of done)

The PR that ships (or finishes shipping) a proposal must also tidy the docs,
in the same PR — do not leave it for later:

1. Distill the proposal's durable decisions into `docs/decision_log.md`.
2. Delete the proposal file (git history preserves the full text).
3. Update `docs/roadmap.md`: move the milestone to Shipped with PR numbers;
   promote what's next.
4. Add the feature's user-facing rationale — the problem it solves — to the
   inventory in `docs/product.md` (the product counterpart to step 1's
   technical distillation).
5. Remove any `docs/tech_debt.md` entries the change fixed.
6. Fix references to the deleted file (`rg` for the filename). The docs test
   in `tests/test_docs.py` fails on dangling relative links, so a stale
   reference breaks the pytest gate.

## Testing Philosophy

- Prefer simple production APIs that reflect the app's real behavior. Do not add parameters, classes, or abstractions only for tests. Tests should usually adapt with fixtures, monkeypatching, or small fakes. Add explicit test seams only when they also improve the production design, or when testing would otherwise require brittle, slow, or unreliable workarounds.

## Styling Conventions

- Prefer semantic CSS classes in `assets/stylesheet.css` for static presentation rules, especially styles that callbacks conditionally enable or disable.
- Keep inline style dictionaries for values that are genuinely computed at runtime or for small, highly local layout adjustments where a named class would add more indirection than clarity.

## Cache Conventions

- Runtime cache files live under `cache/` and should not be committed.
- Cache reads should tolerate missing, stale, malformed, or partially-written files.
- Cache writes should be atomic where practical.
- Derived display fields should not be persisted unless there is a clear reason.

## Scenario Rank Feature

The design rationale lives in `docs/decision_log.md` (the 2026-04-27 through
2026-07-01 scenario-rank entries); runtime structure in `docs/architecture.md`.
Endpoint behavior and quirks are tracked in `docs/kovaaks_api_notes.md`.

Current agreed behavior:

- Current rank comes from `/leaderboard/scores/global`.
- `/user/scenario/total-play` is metadata/upsert only.
- `/scenario/popular` is an exact-name fallback for resolving `scenarioName -> leaderboardId`.
- `ScenarioRankStatus` uses `StrEnum` with stable JSON values.
- `scenario_rank_cache_ttl_hours` defaults to `168`.
- `leaderboard_total_cache_ttl_hours` defaults to `168`.
- New high scores trigger a bounded score-aware background refresh through a
  daemon `threading.Timer` chain.
- Background refresh failures should notify the UI through `dash_logger.error(...)`.
- Leaderboard total enrichment is best-effort. If total lookup fails, preserve the valid rank/unranked result.
- Percentile is derived from rank plus leaderboard total when rank info is returned; do not store it in rank cache.

## UI Boundaries

- UI code should consume `ScenarioRankInfo` and avoid endpoint-specific logic.
- Service-layer expected KovaaK's API/domain failures should become `ScenarioRankInfo(status=UNKNOWN, error_message=...)`.
- Unexpected application bugs may still raise and can be handled by UI/background safety nets.
