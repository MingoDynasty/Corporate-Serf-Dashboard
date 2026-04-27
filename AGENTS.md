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
uv run ruff check source tests
uv run python -m compileall source tests
```

- Local commits authored by Codex should use:

```text
Codex <codex@local>
```

- PRs opened through the GitHub connector may still show as opened by `MingoDynasty` because the connector uses the user's GitHub authorization.

## Cache Conventions

- Runtime cache files live under `cache/` and should not be committed.
- Cache reads should tolerate missing, stale, malformed, or partially-written files.
- Cache writes should be atomic where practical.
- Derived display fields should not be persisted unless there is a clear reason.

## Scenario Rank Feature

The source of truth for detailed design is `docs/scenario_rank_proposal.md`.

Current agreed behavior:

- Current rank comes from `/leaderboard/scores/global`.
- `/user/scenario/total-play` is metadata/upsert only.
- `/scenario/popular` is an exact-name fallback for resolving `scenarioName -> leaderboardId`.
- `ScenarioRankStatus` uses `StrEnum` with stable JSON values.
- `scenario_rank_cache_ttl_hours` defaults to `168`.
- `leaderboard_total_cache_ttl_hours` defaults to `24`.
- New high scores trigger background rank refresh through `ThreadPoolExecutor(max_workers=2)`.
- Background refresh failures should notify the UI through `dash_logger.error(...)`.
- Leaderboard total enrichment is best-effort. If total lookup fails, preserve the valid rank/unranked result.
- Percentile is derived from rank plus leaderboard total when rank info is returned; do not store it in rank cache.

## UI Boundaries

- UI code should consume `ScenarioRankInfo` and avoid endpoint-specific logic.
- Service-layer expected KovaaK's API/domain failures should become `ScenarioRankInfo(status=UNKNOWN, error_message=...)`.
- Unexpected application bugs may still raise and can be handled by UI/background safety nets.
