# 2026-07-16: Keep Pre-Hydration States Honest

Status: Accepted

Decision: Empty-state copy renders only after the owning data callback resolves.
AG Grid layouts omit initial `rowData` so the built-in loading overlay owns the
hydration gap. Plot layouts use a transparent, annotation-free placeholder;
`generate_empty_plot` is reserved for resolved-empty results.

Consequences: Initial page hydration stays visually neutral and never makes a
false no-data claim. Callbacks that resolve to empty grid rows or empty figures
continue to show their explicit empty-state guidance.
