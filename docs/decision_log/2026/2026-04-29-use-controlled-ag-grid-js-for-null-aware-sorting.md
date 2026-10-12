# 2026-04-29: Use Controlled AG Grid JS For Null-Aware Sorting

Status: Accepted

Decision: Playlist scenario AG Grid tables may use repo-owned JavaScript comparators from `assets/dashAgGridFunctions.js` with `dangerously_allow_code=True` when AG Grid requires client-side sort behavior that Python cannot provide directly.

Why: AG Grid sorting runs in the browser. The playlist table needs `NULLS LAST` behavior for rank, total, and percentile columns so unknown values do not sort ahead of real numeric values.

Consequences: Only reference controlled functions committed under `assets/`. Do not generate JavaScript strings from user input. If additional custom grid behavior is needed, prefer adding named functions to `assets/dashAgGridFunctions.js` rather than embedding ad hoc code in page callbacks.
