"""The rule for which runs belong to one play session.

A play session is what the docs call a session: one stretch of play,
including the breaks between runs. The rules, and the decision that set
them, are in ``docs/specs/sessions.md``.
"""

import datetime

# The longest break between two runs that keeps them in one play session, and
# the time a play session stays in progress after its last run. One number
# with both meanings, so a play session reads as in progress for exactly as
# long as a new run would still join it. It is not a setting: every install
# splits the same runs the same way.
PLAY_SESSION_BREAK_LIMIT = datetime.timedelta(minutes=30)
