# Log Lines Delimit Their Values By Kind

Status: Proposed
Date: 2026-09-19

## TL;DR

Log lines have no written convention, so the same kind of value is written
bare, in parentheses, in single quotes, or as a Python repr depending on who
wrote the line. The debug log ships with bug reports, and nearly every
scenario and playlist name contains a space, so a name or a path dropped
into the middle of a sentence has no visible start or end. This proposal
wraps names and paths in double quotes, leaves tokens and numbers bare, keeps
Python's repr for a value nothing has checked yet, and fixes the ways a
caught exception may reach the log. It also sweeps the existing lines once,
so the code teaches the rule the agent instructions state.

## Decisions needed

Nothing is ratified, and the maintainer has no lean on record for any row.
Each row keeps its recommendation beside the strongest alternative and what
choosing it would change. Everything else in this proposal is author-owned
and sits in Design; a reviewer may still challenge it.

### D1 — Free text takes double quotes

Status: Open.

Free text is a string whose content someone outside the code chose: a
scenario, playlist, or user name, or a value read from a run file. 61
placeholders carry one today: 56 are bare, 4 sit in parentheses, and 1 is a
`%r`. Eight more carry a code or key the user typed that nothing has
validated yet: 7 are bare and 1 is single-quoted.

**Recommendation: `"%s"` for free text, wherever the value sits in the line,
and `%r` for a code or key the user typed, until validation accepts it.**
Of the 3177
scenario names and 257 playlist names in the bundled corpus, none contains a
double quote, 62 contain an apostrophe, and 35 contain a parenthesis, so the
double quote is the only one of the three candidate delimiters that never
collides. It is also what the app does on screen for the same values:
shipped copy writes `"{label}"` for a playlist and `"{username}"` for a user
name, and several of these log lines sit directly above such a message. It
never escapes, so the name reads in the log exactly as it does in the UI and
in KovaaK's, and a search of the log for a reported scenario name always
hits.

A code or key the user typed is the one kind of value that can hold
whatever a clipboard holds: a double quote, which would collide with the
delimiter, or an invisible character. The import field is stripped before
it is logged, and a zero-width space survives `strip()`. A playlist code
pasted with one is a realistic cause of a "code not found" report; `"%s"`
shows it as nothing and `%r` shows `'KovaaKsXyz\u200b'`. So this kind takes
`%r`, which is the job the design already gives `%r` (see Kinds, and the
test for each). Once validation accepts the code it is a token and stays
bare. The KovaaK's username is typed too, and validated against KovaaK's,
but it is a name, not a code: it takes `"%s"` before and after validation,
as copy quotes it. Its one pre-validation log line fires when the lookup
could not run at all, where its characters are not the diagnosis, and its
rejection reaches the log only inside the user message that names it,
which no delimiting rule edits.

Choosing differently: `%r` for all free text is the Python idiom and shows
more. It escapes invisible characters and tells `None` from `"None"`. No
bundled name has an invisible character, and a scenario or playlist name is
read from a run file's own field or an upstream response, not from a
clipboard. Its costs:
the quote character flips to `"` for the 62 names with an apostrophe, so one
kind of value carries two delimiters, an escaped name no longer matches a
search for it, and it cannot serve paths (D2), so paths would need a second
rule. `%r` for the username as well, until KovaaK's confirms it, treats
every typed value alike and would show a pasted invisible character on the
username's own lines. It moves five placeholders, adds a third divergence
from copy rule 6 (which quotes the username), and renders one value two
ways inside a single event, because the rejection message that names the
username is copy and keeps its double quotes; and the line it would help,
the one that logs the username when validation could not run, fires on a
network failure, where the characters are not the diagnosis. `"%s"` for
typed codes too is one rule fewer, and leaves the one value that can hold a
double quote or an invisible character as the one the delimiter cannot
bound. Bare `%s` with no rule is the status quo: an empty
value renders as nothing, and `for %s (leaderboard %s)` renders a name such
as `Tracking Benchmarks (Easy)` as two parenthesized groups.

### D2 — Paths take the same double quotes

Status: Open.

34 placeholders carry a path or a file name. 16 already sit last after a
colon, where the end of the line delimits them. 11 have prose running on
after the path, 4 have the sentence's period glued to the path's last
character, 2 end a line with no colon before them, and 1 is already
double-quoted inside its argument.

**Recommendation: the same `"%s"` as D1, so one delimiter covers every
value that can hold a space.** A Windows path cannot contain a double quote,
so the delimiter cannot collide, and the quoted form is the one Windows
itself produces for Copy as path. `%r` is not an option for paths: it
doubles every backslash in a `str`, renders a `Path` as
`WindowsPath('C:/...')`, and switches to double quotes, the delimiter D1
reserves, whenever the path holds an apostrophe (a Windows user name can).
Not verified here: that Explorer's address bar
accepts the quoted form on paste, as a terminal and the Run dialog do. The
manual check in Testing settles it. A negative result costs a user two
characters at a keyboard with the path in view, not the row: an unbounded
path costs a maintainer a misread in a report they cannot re-run.

Choosing differently: bare `%s`, always last after a colon, keeps a path
pasteable with no quote characters to trim and matches the 16 lines that
already do it. It cannot hold two paths in one line (the backup line names
the file and its copy), and the other 18 lines would need their sentences
rebuilt around the path rather than two characters added. It also leaves an
empty or whitespace-tailed path invisible.

### D3 — A caught exception reaches the log one of three ways

Status: Open.

55 calls log an exception: 36 carry a traceback and name the failure in
words, 11 route a `requests` failure through `request_exception_summary`,
and 8 interpolate the exception itself with a bare `%s`. In five of those
eight, everything that can reach the handler carries a message: an exception
this app constructed with one, or an `OSError` from the operating system.
One of the five shows why the test cannot be read off the `except` clause:
the identity probe catches a bare `ValueError`, and is safe only because its
callee raises four handwritten ones and nothing else in the `try` can raise
another. The other three catch broadly, and what reaches them includes
`requests` exceptions that bypass the summary helper and types that can
carry no message at all.

**Recommendation: write down the three routes the code already mostly
follows, keyed on what can reach the handler.** A `requests` failure always
goes through the summary helper. Any other exception is interpolated with
`%s` only when everything that can reach the handler is an exception this
app constructs with a message, or an `OSError` raised by the operating
system;
otherwise the line names the failure in words and, when the failure is
unexpected, carries the traceback. Bare `%s` on a broad catch is the hazard
this closes: `TimeoutError()` renders as nothing and `KeyError("steamId")`
renders as `'steamId'`, so the line ends at its colon or names a key with no
hint of what failed. A type is no guarantee either, since `str()` of a bare
`OSError()` or `ValueError()` is empty, so every route keeps one floor: the
words before the colon name the failure, and the line still says what
happened when the exception renders as nothing. The summary helper already
has the equivalent floor for `requests`: it falls back to the class name.
The rule is written so that following it literally cannot weaken the privacy
invariants: no handler that a `sensitive` request's failure can reach takes
direct interpolation or a traceback, however broad its `except`, because the
`str`, the `repr`, and the logged traceback of a `requests` failure all
carry the query string (measured; see How the candidates render).

Choosing differently: `%r` on every exception logged without a traceback is
one short rule, is never empty, and always shows the type. It renders this
app's own messages, which copy rule 5 fills with contractions and copy rule
6 with double quotes, as `PlaylistFileCollisionError('... \'...\' ...')`
with backslash escapes. It drops the filename from an `OSError`, and it
changes all 8 lines instead of 3.

### D4 — The existing lines are swept once, in the PR that lands the rule

Status: Open.

**Recommendation: a full sweep, in the implementation PR, so the rule and a
tree that follows it land together.** Measured by applying the sweep to a
checkout of `88060d9` and running the suite (baseline 1380 passed): 104
placeholders in 101 calls across 17 files change, and 24 tests in 10 files
fail, every one a plain assertion on rendered log text. The comment and
docstring conventions took the opposite posture, no backfill, and that was
right there because the rule transcribed a style the tree already followed
better than nine times in ten. One of the 103 placeholders this rule governs
already follows it. Agents in this repository learn house style from the
neighboring code at least as much as from the agent instructions, so an
unswept tree teaches bare `%s` on every edit while the instructions say
otherwise, and each conforming new line makes the log less consistent than
it is today rather than more. The sweep is also what makes `%r` legible.
`%r` renders a string in single quotes, and the design gives it one job, so
a single-quoted placeholder value should mean "shown as received, not
vouched for". Python's own quoting inside a collection's repr or an
exception's text is not that signal, and a reader has to know it; but three
formats single-quote an ordinary placeholder by hand today, and under no
backfill they survive until someone edits them, so even the narrow signal
never becomes reliable. The change is mechanical, has no behavior in it, and
is cheapest before the public launch, after which bug-report logs in two
formats would coexist for as long as old installs do. The measurement
applies D1 as amended: `"%s"` for names and paths, `%r` for the eight
typed codes and keys, on the same lines.

Choosing differently: no backfill (new and edited lines only) costs nothing
now and leaves a mixed log for as long as the 100 calls go unedited, which
for log lines is a long time. A targeted sweep of only the values with prose
after them or parentheses around them is 60 placeholders in 58 calls and 11
failing tests; it leaves 44 bare values at line ends, so the tree would then
match a two-branch rule (quote unless last) rather than the one-branch rule
D1 and D2 recommend.

## Problem

### Why now

The app copy rules (the
[2026-09-14 entry](../decision_log.md#2026-09-14-app-copy-follows-one-set-of-rules-and-the-em-dash-is-gated-out))
exempt log lines and close their log-line bullet with "How log lines delimit
their values is a separate audit." This is that audit. Log lines are the one
class of string in `source/` with no written convention, and
`data/logs/debug.log` arrives attached to bug reports (the
[2026-08-10 entry](../decision_log.md#2026-08-10-bug-reports-land-on-github-issues-with-the-log-attached-unredacted-and-disclosed)),
so it is a support surface the maintainer reads cold, not only a developer
aid.

### What was measured

Commit-scoped: an AST walk over a `git archive` export of `origin/main`,
run twice with identical output, first at `8aa47fd` on 2026-09-19 and again
at `88060d9` on 2026-09-25 after `main` moved. Between the two, `main`
added two warnings (five `%s` placeholders) and 22 tests; the corpus, the
exception routes, and every other count are unchanged, and the numbers
below are the later ones. Value kinds were assigned by reading every one of
the 203 string placeholders and recording each of their 87 distinct
argument expressions in an explicit table; an expression the table does
not know is reported, never guessed.

- **Calls.** 163 logging calls in 19 files under `source/`, all on a
  module-level `logger`: warning 86, info 31, debug 29, exception 12, error
  3, critical 2. 142 pass a literal format with arguments, 16 a literal
  with none, and 5 a pre-built message variable; none is an f-string (ruff's
  `G` rules are on). 36 carry a traceback.
- **Conversions.** 273 placeholders: `%s` 200, `%d` 47, `%f` 19, `%g` 4,
  `%r` 3.
- **Value kinds, for the 203 `%s` and `%r` placeholders.**

  | Kind | Count | How it is delimited today |
  | --- | --- | --- |
  | Names and other outside text | 61 | 56 bare, 4 in parentheses, 1 `%r` |
  | Codes and keys the user typed | 8 | 7 bare, 1 single-quoted |
  | Paths and file names | 34 | 33 bare, 1 double-quoted inside its argument |
  | Tokens rendered as strings | 71 | 56 bare, 11 in parentheses, 2 single-quoted, 2 `%r` |
  | Request summaries | 11 | all last, after a colon |
  | Exceptions interpolated | 8 | 7 last after a colon, 1 in parentheses |
  | Pre-built messages | 5 | all last, after a colon |
  | Collections | 5 | Python's container repr |

- **Position, for the 103 free-text and path placeholders (100 calls).** 53
  have prose after the value, so its end is not visible; 5 are wrapped in
  parentheses; 44 end the message; 1 is quoted. Four of the 44 are paths
  with the sentence's period glued on (`Failed to read %s.`). In 44 calls a
  free-text or path value is followed by another value.
- **The same value, four ways.** A playlist code is single-quoted in
  `pages/playlists.py`, and parenthesized, after a colon, or bare in
  `kovaaks/data_service.py`. A scenario name is bare in 39 places, in
  parentheses in 4, and a `%r` in 1.
- **`scripts/`.** 47 calls, 3 f-string messages, 2 `%r`. Excluded from
  lint; output goes to a terminal, never to `debug.log`.
- **Tests.** 261 `caplog` references in 18 files. The count that matters is
  how many assert on text a sweep would change; D4 carries it.

### What the values look like

The bundled corpus at the same commit: 257 files, 3177 distinct scenario
names, 257 playlist names.

| Trait | Scenario names | Playlist names |
| --- | --- | --- |
| Contains a space | 3067 (96.5%) | 249 (96.9%) |
| Contains an apostrophe | 53 | 9 |
| Contains a double quote | 0 | 0 |
| Contains a parenthesis | 9 | 26 (10.1%) |
| Contains a colon or a semicolon | 0 | 0 |
| Leading, trailing, or doubled whitespace | 0 | 3 (doubled) |
| Non-ASCII | 0 | 3 |
| Non-printable | 0 | 0 |

A user's own scenarios and an imported community playlist are not in the
corpus, and the import path strips whitespace from upstream names. Paths
contain spaces and parentheses on a stock install (`Program Files (x86)`).

### How the candidates render

Python 3.14.6, this repository's interpreter.

| Value | `%s` | `%r` | `"%s"` |
| --- | --- | --- | --- |
| `Bob's Voltaic` | `Bob's Voltaic` | `"Bob's Voltaic"` | `"Bob's Voltaic"` |
| a name with both quote kinds | as is | `'Bob\'s "Pasu" Voltaic'` | `"Bob's "Pasu" Voltaic"` |
| empty string | nothing | `''` | `""` |
| `None` | `None` | `None` | `"None"` |
| trailing space | invisible | `'Pasu Track '` | `"Pasu Track "` |
| no-break space inside | invisible | `'Pasu\xa0Track'` | invisible |
| zero-width space inside | invisible | `'Pasu\u200bTrack'` | invisible |
| non-ASCII | as is | as is | as is |
| a Windows path `str` | as is | every backslash doubled | as is |
| a `Path` | as is | `WindowsPath('C:/...')`, in double quotes when the path holds an apostrophe | as is |

Exceptions: `%s` renders `TimeoutError()` as nothing and
`KeyError("steamId")` as `'steamId'`; `%r` renders `TimeoutError()` and
`KeyError('steamId')`, and drops the filename from
`FileNotFoundError(2, "...", path)`. A type guarantees nothing: `str()` of a
bare `OSError()`, `ValueError()`, or `RuntimeError()` is empty too, while an
`OSError` the operating system raises always carries its errno text. For a
`requests` failure the `str`, the
`repr`, and the logged traceback (three occurrences, through the chained
urllib3 errors) all contain the request's query string. What keeps a
`sensitive` request's parameters out of the log is
`request_exception_summary(..., redact_query=True)` and the request helper's
`sensitive` flag, never the conversion type.

## Design

### The rule

The implementation PR adds a section titled "Logging Conventions" to
`AGENTS.md`, after "Comment and Docstring Conventions". Its text, verbatim
apart from a link to the decision-log entry and the scope sentence, which
follows D4:

> These rules govern log lines under `source/`: how a logged value is
> delimited, never whether it may be logged. What stays out of the log (the
> identity probe's persona names, a `sensitive` request's parameters) is
> decided where the value is handled. The existing lines were swept to match
> when the rules landed.
>
> - Free text and paths take double quotes: `"%s"`. Free text is a string
>   whose content someone outside the code chose: a scenario, playlist, or
>   user name, a file name, a value read from a run file. Parentheses and
>   single quotes do not delimit a value, because names contain both.
> - Tokens and numbers stay bare. The test is who chose the content, not
>   whether the value happens to hold a space: counts, scores, IDs, playlist
>   codes after validation, SHAs, URLs, HTTP statuses, timestamps, words the
>   code chose.
> - `%r` is for a value nothing has vouched for: a code or key the user
>   typed, until validation accepts it, and a value read back in the wrong
>   type or shape (a cached ID that is not a number, an unknown schema
>   stamp). There the exact characters or the type are the diagnosis.
> - A `requests` failure always goes through `request_exception_summary`,
>   with `redact_query=True` when the request is `sensitive`. Its `str`, its
>   `repr`, and its traceback all carry the query string, so no handler that
>   a `sensitive` request's failure can reach takes `exc_info`, however
>   broad its `except` (a `requests` exception is an `OSError`, so
>   `except OSError` around a request counts).
> - Any other caught exception is interpolated with `%s` only when
>   everything that can reach the handler is an exception this app
>   constructs with a message, or an `OSError` raised by the operating
>   system. The test is what can reach the handler, not what the `except`
>   names. Otherwise
>   the line names the failure in words and, when the failure is unexpected,
>   carries the traceback (`logger.exception`, or `exc_info=True` below
>   ERROR). Either way the words before the colon name the failure, so the
>   line still says what happened when the exception renders as nothing
>   (`TimeoutError()`, a bare `ValueError()`).
> - Unbounded text goes last, after a colon: an exception's text, a request
>   summary, a pre-built message. It cannot be quoted usefully, so the end
>   of the line is its delimiter.
> - A line that logs a user-facing message verbatim is copy: the message
>   follows the copy rules in Styling Conventions, and these rules do not
>   edit it.

If D4 is ruled no backfill, the scope sentence reads instead: "They govern
new and edited log lines; existing lines are not swept to match."

### Kinds, and the test for each

The line between free text and a token is who chose the content, not whether
this particular value happens to hold a space. A timestamp renders with a
space and stays bare, because its shape is fixed by the code that formatted
it. A KovaaK's username is typed by the user and validated against
KovaaK's, but it is a name, not a code, so it takes `"%s"` before and after
validation, as copy quotes it. A sensitivity label assembled from a run
file's fields is free text, because the scale name comes from the file.

`%r` keeps one job: a value nothing has vouched for. Two of its three uses
today are that job: a cached leaderboard ID that failed the numeric check,
and a build stamp with an unknown schema version. In both, whether the value
is `"12"`, `12`, or `None` is the diagnosis. A code or key the user typed
is the same job before validation (D1): the six lines that log the pasted
playlist code, the import line that single-quotes it by hand today, and the
unknown config keys, which become the list itself. The third use today, a scenario name in
the corpus-disagreement warning, is a trusted name and becomes `"%s"`. One
more line fits the job and is `%s` today: the unsupported radio option in
`pages/home.py`.

This diverges from copy rule 6 twice, deliberately. Rule 6 keeps playlist
codes and paths bare as tokens, and shipped copy follows it, down to a
pre-validation code (`Couldn't look up {input_playlist_code} on KovaaK's.`).
The log quotes a path always, and renders a playlist code with `%r` until
validation accepts it, because the log's reader needs an unambiguous
boundary more than a sentence needs to read naturally, and a code that has
not passed validation may not be a code at all. Where the two sides agree is
names and user names, which both quote. After validation a playlist code is
bare on both sides.

### Placement

Delimiting by kind leaves placement free, so there is no general placement
rule and copy rule 9's ordering is deliberately not imported: a log line's
reader scans for the operation, and the code already leads with it. The one
placement rule covers the text that quoting cannot bound. 23 of the 24
unbounded placeholders already sit last after a colon; the exception is the
IPv6 fallback line in `app.py`, which puts an `OSError` in parentheses
mid-sentence.

### Exceptions

The test is what can reach the handler, and applying it means reading the
`try` body's callees. That is a judgment no rule removes; stating it is what
keeps the identity probe's `except ValueError` honestly conforming rather
than conforming by a reading the text does not support. The floor (the words
before the colon name the failure) holds on every line regardless, so a
line that ends at its colon still says which operation failed. The routes
are ordered by what reached the handler, never by how the `except` is
spelled: a `requests` failure that arrives through a blind `except
Exception` still takes the summary, and only what remains takes the
traceback.

The three broad lines D3 names, and what conforming looks like:

- `kovaaks/data_service.py`, the Evxl fallback, catches
  `(requests.RequestException, ValidationError)` and interpolates either.
  The playlist lookup earlier in the same function catches the same pair
  and already conforms: the summary for a `requests` failure, the class
  name for a `ValidationError`. The fallback takes the same shape.
- `kovaaks/percentile_warmup_service.py`, the expected-failure helper,
  receives five types from four call sites, one of them
  `requests.RequestException`. It takes the summary for a `requests`
  failure and the class name for a `ValidationError`. The rest keep `%s`
  only where the test holds, which the implementer settles by reading the
  four `try` bodies, and take the class name where it does not.
- `kovaaks/playlist_scenarios_service.py`, the best-effort hydration, is a
  blind `except Exception`, and a `requests` failure can reach it: the
  total-play hydration it calls does not consume request exceptions. A
  `requests.RequestException` clause takes the summary first, and the blind
  catch that remains takes the traceback.

None of the three requests is `sensitive`, so none is a privacy defect
today.

### Privacy

No rule here says what may be logged. The identity probe's module logs
counts and positions only and marks its request `sensitive`; the one
exception it interpolates is a `ValueError` whose four possible messages are
all handwritten and carry no value. No traceback route wraps the probe
today. The rule's `requests` bullet exists so that the rule about tracebacks
cannot be followed into a leak: a reader who learns "an unexpected failure
takes `exc_info`" and applies it around a `sensitive` request would log the
persona in the traceback's last line. It is keyed on what can reach the
handler for the same reason the `%s` test is: a blind `except Exception`
around the probe catches a `sensitive` request's failure without naming it.

### Boundaries

- `source/` only. `scripts/` holds developer tools that print to a terminal
  and are excluded from lint; nothing there reaches a bug report.
- Lines from bundled libraries (urllib3, waitress, Dash) are not the app's.
- Five calls pass a pre-built message variable and five pass a pre-built
  message as the last argument. The message is user copy that a helper logs
  as it shows it, so the copy rules own its text and the sweep does not
  touch it.
- Collections keep Python's container repr, which already delimits each
  element. The one hand-joined list, the unknown config keys, becomes the
  list itself.

### Enforcement

Review only, the same posture as the comment conventions. A guard in the
style of `tests/test_em_dash_guard.py` would have to know a placeholder's
value kind, and the AST does not carry it: the table behind this proposal's
numbers needed 87 hand-read expressions, and any name heuristic misfiles the
pair that matters most (`playlist_code` is a token and stays bare,
`input_playlist_code` is user-typed and takes `%r`). The one check with no
false positives, "no `'%s'` in a logger
format", guards three lines' worth of deviation. After a sweep the tree is
the second teacher, which is the enforcement D4 buys. Ruff's `G` rules stay
on and logging calls keep lazy `%` arguments.

### Copy

No user-facing copy. The boundary above exists so that this rule never
edits a string the copy rules own.

### Alternatives rejected

- **Single quotes.** 62 bundled names contain an apostrophe, and the copy
  side already chose the double quote.
- **Brackets or curly quotes.** 3 scenario and 4 playlist names contain a
  bracket, and a path may. No bundled name holds a curly quote, but it is
  not typeable in a log search and a Windows path permits it. The straight
  double quote is the only candidate with no collision in the census.
- **Parentheses as the delimiter**, the tree's second most common form.
  10.1% of playlist names contain one, and the dominant playlist pattern is
  already `%s (%s)`, name then code.
- **Placement only**: every free-text value last after a colon, bare. A line
  has one last position, and 44 calls carry a free-text or path value with
  another value after it.
- **Escaping every quoted value**, so a double quote or a control character
  inside one can never break its boundary. `%r` is that encoding, and the
  design uses it where a value can hold either: a code or key the user
  typed. Applied
  to names it would break the property that a search of the log for a
  reported name always hits, to guard a collision no bundled name has and
  that degrades, when it happens, to today's ambiguity and no further.
- **A class-name fallback for every interpolated exception**, mirroring the
  `requests` summary helper's. It closes the empty render mechanically, for a
  handful of lines and at the price of a second helper. The floor in the
  rule closes it with no new code.
- **A quoting helper** called in the argument list. It formats eagerly,
  which is what the `G` rules exist to prevent, and it hides the delimiter
  from the format string where a reader looks for it.
- **Structured or JSON logging, a log parser, a lint plugin, and any change
  to the log format, levels, or handlers.** Out of scope by the audit's
  brief; none is needed to make a value's edges visible.

### Blast radius

Under D4's recommendation: 101 of 163 calls change only how a value is
delimited, four exception lines change shape, and 24 tests update an
expected string. No log level, logger name, or message wording changes, so a
search for a line's words still finds it. Anyone who searches a log for a bare
`for <name> (` pattern would need the quote. No cache, store, or wire format
is involved.

## Out of scope

- The log format, levels, handlers, rotation, and which loggers are quieted.
- The nine copy rules and every string they govern, including the bad-stamp
  message in `utilities/store_schema.py`, which renders a non-ASCII stamp
  with `\u` escapes through `json.dumps`. It is user copy, real stamps are
  numbers or short words, and it stays as it is unless the maintainer says
  otherwise.
- `scripts/`.
- The text Python itself puts in an `OSError`. It carries the filename as a
  repr: backslashes doubled, in single quotes, or in double quotes when the
  path holds an apostrophe. A conforming line that also carries a traceback
  therefore shows one path twice, once as `"C:\...\loginusers.vdf"` and once
  in the traceback's last line as `'C:\\...\\loginusers.vdf'`, and the second
  is neither corruption nor a distrusted value. It is Python's text and a fix
  would be per line, so it stays; the decision-log entry carries this caveat,
  because a reader meets it in a real bug report after this file is gone.
- An invisible character in a pasted KovaaK's username. The username is a
  name and takes `"%s"`, and its rejection reaches the log only inside the
  user message that quotes it, so a stray character in it stays invisible
  in the log as it does on screen.
- Numeric formats (`%d`, `%f`, `%g`).

## Testing

- This PR is one Markdown file: `git diff --check` and
  `uv run pytest tests/test_docs.py`.
- The implementation PR updates the 24 assertions the sweep breaks,
  tightened and never loosened: each asserts the quoted rendering rather
  than dropping to a substring that avoids the value. By file at `88060d9`:
  `test_api_service.py` 5, `test_app_startup_stats_dir.py` 3,
  `test_percentile_warmup_service.py` 3, `test_scenario_rank_freshness.py`
  3, `test_aim_training_journey.py` 2, `test_crash_logging.py` 2,
  `test_data_service_queries.py` 2, `test_playlist_rekey.py` 2,
  `test_data_service_extract.py` 1, `test_file_watchdog_rank_refresh.py` 1.
- The double-warning fix (see Delivery plan) adds a `caplog` regression test
  asserting exactly one record for a skipped user-root playlist file.
- Gates: `uv run pytest tests`, `uv run ruff format --check .`,
  `uv run ruff check`, `uv run mypy source`,
  `uv run python -m compileall source tests`.
- Manual: start the app against a stats folder whose path contains a space,
  read the startup lines in `data/logs/debug.log`, and paste a logged path,
  quotes included, into Explorer's address bar.

## Delivery plan

1. **This PR: the proposal.** Heavy lane as a wave from one frozen head: the
   connector, a full Codex review (the current flagship), and a full Opus
   review, both in co-design mode, then the maintainer's deep read and the
   direction checkpoint. A second Codex model adds a first-wave advisory
   pass: one signed review body with a stance per row, no inline threads,
   and no LGTM seat. The author is a Fable session, so there is no Fable
   review seat.
2. **One implementation PR** (Opus 5.5 at high, from a kickoff prompt written
   into `ignore/prompts/` after ratification), in five commits:
   1. the `AGENTS.md` section and an `Accepted` decision-log entry, which
      carries this proposal's measurements, the two deliberate divergences
      from copy rule 6, and the `OSError` text caveat from Out of scope,
      because the entry is what remains once this file is deleted;
   2. the delimiting sweep with its test updates (D1, D2, D4): `"%s"` for
      free text and paths, `%r` for typed codes and keys, and the parentheses
      and single quotes that stood in as delimiters dropped;
   3. the four exception lines (D3, and the placement outlier in `app.py`);
   4. the double-warning fix: a skipped user-root playlist file is logged
      by the store layer and then again, with identical text, when the
      loader queues the same message for the UI. The loader appends to the
      startup warning queue directly, with a comment that the store layer
      already logged it, and the same commit rewrites the sentence in the
      2026-09-14 entry that records the double log as known;
   5. the docs definition of done.
3. **Docs definition of done**, in the implementation PR: the decision-log
   entry; the `AGENTS.md` section; the proposal file deleted; the kickoff
   prompt moved to `ignore/prompts/done/`. No capability spec covers
   logging, and the roadmap and product-inventory steps of the Shipping a
   proposal checklist apply when a proposal ships an app feature, which a
   logging convention is not, so there is no spec, `docs/roadmap.md`, or
   `docs/product.md` change; the implementer searches
   `docs/` for any quoted log line the sweep alters.

If D4 is ruled no backfill, the implementation PR is commits 1 and 5, and
the double-warning fix ships as its own small PR.
