# 2026-06-30: Model Home Last-Played Empty States Explicitly

Status: Superseded in part, for the exact absolute-string format (`%Y-%m-%d %I:%M:%S %p`), by the 2026-07-11 humanized absolute-format decision

Supersedes: The home sentinel and hover-only tooltip interaction in the 2026-06-21 relative timestamp decision. The playlist-grid behavior and shared timestamp formatting rules remain unchanged.

Decision: Home Scenario Stats distinguishes three "Last played" states: no scenario selected renders `—`; a selected scenario with no local play data renders `Never`; and a selected scenario with play data renders the relative timestamp. Only a real timestamp receives the dotted underline and `cursor: help` affordance. Its exact local timestamp (`%Y-%m-%d %I:%M:%S %p`) is available by hover, keyboard focus, or touch. Empty states are not focusable and disable the tooltip entirely.

Why: `—` communicates an unselected field without implying missing or failed data, while `Never` communicates a known selected scenario with no recorded plays. Showing the affordance only when more information exists keeps the interaction honest and avoids a tooltip that merely repeats an empty-state value.

Consequences: The home callback owns the empty-state value and tooltip affordance alongside the raw timestamp. The clientside relative-time callback continues to own the live-updating visible timestamp. A selected scenario missing from the local database is treated as having no local play data; temporary loading or error states must not be mapped to `Never`.
