# 2026-07-06: Adopt The Cross-Repo Python V2 Tooling Spec

Status: Superseded in part, for the spec version, the action pins, and the
cancelling of superseded runs, by the
[2026-10-05 python-v3 decision](#2026-10-05-adopt-the-cross-repo-python-v3-tooling-spec)

Supersedes: The workflow shape, command set, tool and runtime pin placement,
and concurrency behavior in the 2026-07-03 CI decision. Windows execution,
locked dependency sync, SHA-pinned actions, read-only contents permission, and
the broader local pre-handoff validation remain in force.

Decision: Use the canonical `tooling-spec: python-v2` workflow at
`.github/workflows/ci.yml`. Its matrix-backed `test (windows-latest)` job runs
`uv sync --locked`, ruff format, ruff lint, bare mypy, and bare pytest.
`pyproject.toml` owns the required uv version (`==0.11.26`), pytest discovery
and options, and mypy's `source/` scope. The workflow no longer overrides Git
line endings, cancels superseded runs, caches uv, pins Python or uv through
`setup-uv`, or runs `compileall`.

Why: The cross-repo spec keeps local and CI invocations aligned through project
configuration and gives repositories one recognizable CI shape. Moving the uv,
pytest, and mypy defaults into `pyproject.toml` makes the bare commands
authoritative in every environment instead of relying on workflow-only flags.

Consequences: Local pre-handoff validation still includes `compileall`, while
CI has four named checks inside the single Windows matrix job. CI resolves a
compatible interpreter from `requires-python = ">=3.14"`; this migration does
not add a `.python-version` pin. The required branch-protection check changes
from `gates` to `test (windows-latest)` and must be updated by the repository
owner at merge time. Add a minimal `.gitattributes` only if a runner actually
reports line-ending format drift; the migration's first CI run did not.
