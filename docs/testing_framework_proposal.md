# Testing Framework Proposal

This proposal establishes a practical testing baseline before larger refactors.

## Recommended framework stack

1. **pytest** as the core test runner.
2. **pytest-cov** for coverage tracking.
3. **pytest-mock** for mocking APIs and watcher events.
4. **Hypothesis** (later phase) for property-based tests on CSV parsing and ranking boundaries.

## Test layers (in order)

### 1) Fast unit tests (run on every PR)
- `source/utilities/utilities.py`
  - `ordinal` suffix behavior, including 11/12/13 edge cases.
  - `format_decimal` integer vs decimal normalization.
- `source/plot/plot_service.py`
  - Plot trace counts/names and overlay presence.
  - Rank overlay boundary conditions (lowest/highest rank logic).
- `source/kovaaks/data_service.py`
  - `extract_data_from_file` parsing success/failure paths.
  - Date filtering/top-N filtering on deterministic in-memory data.

### 2) Service/integration tests (run on PR + nightly)
- Watchdog event → queue message → database update flow.
- Playlist import paths:
  - API success,
  - duplicate playlist name,
  - no-response / multi-result failures.
- Notification generation decisions in `source/pages/home.py` callback logic.

### 3) UI/smoke tests (run nightly)
- Minimal Dash smoke test: app boots with seeded fixture data.
- Page routing smoke test for `/` and `/aim-training-journey`.

## CI gates

- Required on every PR:
  - `python -m pytest`
  - `python -m pytest --cov=source --cov-report=term-missing`
- Initial quality gate target: **70% coverage**.
- Raise gradually to 80%+ after callback/service refactors.

## Immediate next tests to add

1. `tests/test_file_watchdog.py`
   - Ensure `NewFileMessage` fields are always populated.
   - Ensure event path handling uses the correct path semantics.
2. `tests/test_home_notifications.py`
   - Validate top-N notification and threshold notification decisions.
3. `tests/test_playlist_import.py`
   - Mock `get_playlist_data` to cover API edge-cases.

## Why this sequence

- Unit tests provide quick confidence while refactoring internals.
- Integration tests protect thread/queue/data interactions.
- Smoke tests ensure Dash wiring continues to load and route.
