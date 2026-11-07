# 2026-11-07: Every Definition Under Source Carries Type Annotations

Status: Accepted

Every function and method in the application code now declares the types of
its parameters and its return value, and the type check fails on one that
does not. Most of the definitions the sweep annotated are Dash callbacks and
page layouts, typed as the values Dash actually passes them. Nothing the app
does has changed. A contributor notices only that a new function without
annotations fails the type check.

**What changed.** `[tool.mypy]` in `pyproject.toml` sets
`disallow_untyped_defs = true` beside `check_untyped_defs = true`, so the
merge bar's mypy check, locally and in CI, fails on a definition under
`source/` with an unannotated parameter or return. At `0fdde2af` the flag
reported 79 diagnostics across 75 definitions in 20 files: the 17 ordinary
functions the 2026-09-08 count named, 45 Dash callbacks, 7 layouts (the
shell's and six pages'), and 6 helpers that take the values a callback was
given. All 75 are annotated, and the flag reports none. `tests/` and
`scripts/` are outside mypy's `files`, so the requirement does not reach
them.

**How a Dash value is typed.** As Dash delivers it for that prop as the
layout draws it, not as the widest thing the prop could hold:

- A store's data is its JSON shape, with the writer's TypedDict where one
  exists (`RunEventBatch`, `RunEventsPayload`, `RunListModel`), and
  `| None` when the layout draws the store empty.
- An interval's `n_intervals` is `int`, because every interval is drawn
  with 0. A click count is `int | None`, `None` before the first click. A
  switch drawn with a value is `bool`.
- A Select's value is `str | None`, and a NumberInput's is
  `float | str | None`, as `run_list_from_store` already took it: a cleared
  NumberInput sends an empty string.
- A layout's `**kwargs` is `str | list[str]`, what Dash Pages passes for a
  query parameter, a list when the parameter repeats.
- A return type names `NoUpdate` wherever the callback can return
  `no_update`.

`Any` appears where a value is untyped: an AG Grid `cellClicked` event, whose
`value` is any cell's value, the keyword arguments passed through to
`requests`, and the positional values one closure forwards from Dash to a
typed function. It also appears where an annotation repeats a type the code
already declares with it, such as the toast payload `toast` returns. Where
the code guarantees a value mypy cannot see, a `cast` says so: a store that
called holds its value, and an observer scheduled on a `str` path reports
`str` paths. A `cast` returns its argument unchanged. One
`type: ignore[arg-type]`, with a TODO, marks the aim-training page's
checkpoint field, whose NumberInput value goes on unconverted to a parameter
typed `int`.

**Why annotations are inert at runtime here.** Nothing reads them. The app's
`DashProxy` has no transforms, so dash-extensions' serialization transforms,
which load a callback's arguments by their annotations, never run, and Dash's
MCP server, which also reads them, is off. Adding such a transform would make
every callback's annotations load-bearing, and would evaluate the names a
module imports only for type checking.

**Why a gate and not prose.** The
[2026-09-04 conventions entry](2026-09-04-comment-and-docstring-conventions.md)
deferred an annotation requirement with three options: nothing, annotating the
ordinary functions, or a sweep plus this flag. A prose rule no gate checks was
rejected there because it would drift. This is the third option, so the rule
lives in the mypy config and AGENTS.md states nothing about annotations.
