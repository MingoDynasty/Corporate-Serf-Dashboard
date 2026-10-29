# 2026-10-29: The Run List's Shots Fired Column Starts Hidden

Status: Accepted

Shots Fired is now off in the run list until a player turns it on in the
Columns menu, as the list's other optional columns are. The default columns then need
less than the list's 480px minimum, so the default list sits at that minimum,
as wide as the latest-run card. Every browser's remembered choice of Shots
Fired resets once, so a player who wants the column turns it back on.

**Maintainer direction, 2026-10-29.** While choosing how the run list should
use its width, the maintainer said: "'Shots Fired' should not be a default
column." The layout built on it was then chosen as "Copy A"
([the marks column's entry](2026-10-29-the-run-lists-marks-column-is-30px-and-three-columns-share-its-spare-room.md)).
It moves Shots Fired from the tier the maintainer called probably useful by
default to the tier of columns possibly useful to some players
([the three new columns](2026-10-22-the-run-lists-columns-menu-offers-reloads-fov-and-avg-fps-off-to-start.md)).
What the list does today is in
[run_history.md](../../specs/run_history.md#the-run-list).

**The rule.**

- The grid's Shots Fired column starts with `hide: True`, and its menu entry,
  `MenuColumn("shots", "Shots Fired", shown_by_default=False)`, starts
  unchecked. The two must agree, or a fresh browser's checkbox and column
  would disagree.
- A run row has six columns by default: `#`, Time, Score, the marks,
  Accuracy and Sensitivity. The menu still lists Shots Fired first, in table
  order.
- The default columns need 407px, under the 480px minimum. With Shots Fired
  on they need 489px.

**The one-time reset.** Dash stores a persisted checkbox's value with the
layout default it was saved against, and drops it once that default changes.
So every browser's stored choice of Shots Fired is dropped on its first load
after this change, and the column shows hidden. A player who had turned it
off loses nothing; one who wants it turns it on once, and that choice is
remembered again. No other column's choice is touched. The ids are
unchanged, so nothing else resets.
