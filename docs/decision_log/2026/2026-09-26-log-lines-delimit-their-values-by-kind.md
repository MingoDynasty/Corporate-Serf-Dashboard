# 2026-09-26: Log Lines Delimit Their Values By Kind

Status: Accepted

Log lines had no written convention, so the same scenario name, playlist
name, or file path appeared bare, in parentheses, in single quotes, or as a
Python repr depending on who wrote the line. Nearly every name contains a
space, and the debug log travels with bug reports to a reader who can't
re-run what happened, so a name with no visible start or end is a misread
waiting to happen. Names and paths now sit in double quotes, codes and counts
stay bare, and a value the app hasn't checked yet is shown exactly as
received. Every existing line was changed to match in one pass, and a caught
exception reaches the log by one of three written routes.

**The rule.** AGENTS.md's Logging Conventions section carries the operative
form. It governs how a value is delimited, never whether it may be logged:
the identity probe's persona names and a `sensitive` request's parameters
stay out of the log where they are handled, and nothing here changes that.

**What was measured.** Commit-scoped: an AST walk over a `git archive`
export of `origin/main`, first at `8aa47fd` on 2026-09-19, then at `88060d9`
on 2026-09-25, and again by the shipping PR at `47cd578` on 2026-09-26 with
identical counts. 163 logging calls in 19 files under `source/`, all on a
module-level `logger`, none an f-string (ruff's `G` rules are on); 273
placeholders: `%s` 200, `%d` 47, `%f` 19, `%g` 4, `%r` 3. Each of the 203
string placeholders was read and its argument recorded in a table of 87
distinct expressions; an expression the table did not know was reported,
never guessed.

| Kind | Placeholders | How it was delimited |
| --- | --- | --- |
| Names and other outside text | 61 | 56 bare, 4 in parentheses, 1 `%r` |
| Codes and keys the user typed | 8 | 7 bare, 1 single-quoted |
| Paths and file names | 34 | 33 bare, 1 double-quoted inside its argument |
| Tokens rendered as strings | 71 | 56 bare, 11 in parentheses, 2 single-quoted, 2 `%r` |
| Request summaries | 11 | all last, after a colon |
| Exceptions interpolated | 8 | 7 last after a colon, 1 in parentheses |
| Pre-built messages | 5 | all last, after a colon |
| Collections | 5 | Python's container repr |

The 103 free-text and path placeholders sat in 100 calls: 53 with prose
after the value, 5 in parentheses, 44 ending the message, and 1 already
quoted. A playlist code was single-quoted in one module and parenthesized,
after a colon, or bare in another. The bundled corpus at the same commit
holds 3177 scenario names and 257 playlist names: 96.5% and 96.9% contain a
space, 62 an apostrophe, 35 a parenthesis, 7 a bracket, and none a double
quote. The sweep changed 104 placeholders in 101 calls across 17 files and
broke 24 test assertions in 10 test files, every one an assertion on rendered
log text, each updated to assert the quoted rendering.

**The decisions**, all ratified by the maintainer on 2026-09-26.

- *D1, free text takes `"%s"` wherever it sits.* Of the three candidate
  delimiters the double quote is the only one no bundled name contains. It
  is what copy already does for the same values (`"{label}"` for a playlist,
  `"{username}"` for a user name), and it never escapes, so a search of the
  log for a reported name always hits. A code or key the user typed takes
  `%r` until validation accepts it: a clipboard can carry a double quote or
  an invisible character, and a zero-width space survives `strip()`, so a
  pasted code renders as `'KovaaKsXyz\u200b'` under `%r` and as nothing
  under `"%s"`. The eight such lines are the six that log a pasted playlist
  code, the import line, and the unknown config keys, which now log the list
  itself. Once validation accepts a code it is a token and stays bare.
  Rejected: `%r` for all free text, which flips to a double-quoted repr for
  the 62 names with an apostrophe, stops matching a log search once it
  escapes, and cannot serve paths; `"%s"` for typed codes too, which leaves
  the values that can hold a double quote or an invisible character as the
  ones the delimiter cannot bound; and no rule, where an empty value renders
  as nothing and `for %s (leaderboard %s)` turns `Tracking Benchmarks (Easy)`
  into two parenthesized groups.
- *The KovaaK's username, the one D1 point a reviewer contested.* The
  username is typed and then validated against KovaaK's, but it is a name,
  not a code, so it takes `"%s"` before and after validation, as copy quotes
  it. The counter was `%r` until KovaaK's confirms it, treating every typed
  value alike. What settled it is that the name's exact characters already
  reach the log: every attempt of the total-play request that validates it
  logs its parameters at DEBUG, and a dict renders its values with `repr`, so
  a pasted zero-width space shows as `'Pasu\u200b'` on the request line of
  the lookup that got KovaaK's answer. That line need not sit near the
  rejection: a rejection served from the cached unknown-user marker sends no
  request, so the escaped name is on the line of the earlier lookup whose
  answer the marker records. `%r` for the username would have added
  locality, not information, and cost two moved placeholders (the lines that
  log the username when the total-play lookup failed with no cached answer,
  both network failures) plus a third divergence from copy rule 6.
- *D2, paths take the same `"%s"`.* A Windows path cannot contain a double
  quote, so the delimiter cannot collide, and the quoted form is what
  Windows produces for Copy as path. `%r` cannot serve: it doubles every
  backslash in a `str`, renders a `Path` as `WindowsPath('C:/...')`, and
  switches to double quotes, the delimiter D1 reserves, when the path holds
  an apostrophe. Rejected: bare paths, always last after a colon, which keeps
  a path pasteable with nothing to trim but cannot hold two paths in one line
  (the unusable-store backup line names the file and its copy), would have
  needed 18 sentences rebuilt around the path, and leaves an empty or
  whitespace-tailed path invisible.
- *D3, a caught exception reaches the log one of three ways, keyed on what
  can reach the handler.* Before the rule, 55 calls logged an exception: 36
  with a traceback, 11 through `request_exception_summary`, and 8 by bare
  `%s`. In five of the eight, everything that could reach the handler carried
  a message. The identity probe's `except ValueError` is one of them, and is
  safe only because its callee raises four handwritten `ValueError`s and
  nothing else in the `try` can raise one, which is why the test cannot be
  read off the `except` clause. The other three caught broadly, and what
  reached them included `requests` exceptions that bypassed the summary
  helper and types that can carry no message. Bare `%s` is the hazard: `TimeoutError()` renders as nothing,
  `KeyError("steamId")` as `'steamId'`, and `str()` of a bare `OSError()`
  or `ValueError()` is empty too, so every route keeps the floor that the
  words before the colon name the failure. The `requests` route exists for
  privacy: a `requests` failure's `str`, `repr`, and logged traceback all
  carry the query string (measured on Python 3.14.6), so no handler a
  `sensitive` request's failure can reach may interpolate it or take a
  traceback. Rejected: `%r` on every exception logged without a traceback,
  which renders the app's own messages, full of contractions and double
  quotes, with backslash escapes, drops the filename from an `OSError`, and
  changes all eight lines instead of three; a class-name fallback helper for
  every interpolated exception, which the floor makes unnecessary.
- *D4, one full sweep, in the PR that lands the rule.* The comment and
  docstring conventions
  ([2026-09-04](#2026-09-04-comment-and-docstring-conventions)) took no
  backfill because they transcribed a style the tree already followed nine
  times in ten; here 1 of 103 placeholders did. Agents in this repository
  learn house style from neighboring code at least as much as from the
  instructions, so an unswept tree would teach bare `%s` on every edit. The
  sweep is also what makes `%r` legible: a single-quoted placeholder value
  now means "shown as received, not vouched for", which three hand-quoted
  formats would otherwise have contradicted until someone edited them. It was
  cheapest before the public launch, after which bug-report logs in two
  formats would coexist for as long as old installs do. Rejected: no
  backfill, a mixed log for as long as the lines go unedited; a targeted
  sweep of only the values with prose after them or parentheses around them
  (60 placeholders, 58 calls, 11 failing tests), which leaves 44 bare values
  at line ends and a two-branch rule.

**Two deliberate divergences from copy rule 6.** Rule 6 keeps playlist
codes and paths bare as tokens, and shipped copy follows it, down to a code
that hasn't passed validation (`Couldn't look up {input_playlist_code} on
KovaaK's.`). The log quotes every path, and renders a playlist code with `%r`
until validation accepts it, because the log's reader needs an unambiguous
boundary more than a sentence needs to read naturally, and a code that has
not passed validation may not be a code at all. The two sides agree on names
and user names, which both quote, and on a validated playlist code, which
both leave bare.

**`OSError` text keeps Python's rendering.** Python puts the filename into
an `OSError`'s text as a repr: backslashes doubled, in single quotes, or in
double quotes when the path holds an apostrophe. A conforming line that also
carries a traceback therefore shows one path two ways, once as
`"C:\...\loginusers.vdf"` in the message and once as
`'C:\\...\\loginusers.vdf'` in the traceback's last line. The second is
neither corruption nor a distrusted value; it is Python's text, a fix would
be per line, and it stays.

**What is deliberately not enforced.** Review only, the posture of the
comment conventions. A guard in the style of the em dash test would have to
know a placeholder's value kind, which the AST does not carry: the census
needed 87 hand-read expressions, and a name heuristic misfiles the pair that
matters most (`playlist_code` is a token, `input_playlist_code` is typed and
takes `%r`). The one check with no false positives, no `'%s'` in a logger
format, guards three lines' worth of deviation. After the sweep the tree is
the second teacher. Ruff's `G` rules stay on and logging calls keep lazy `%`
arguments; a quoting helper in the argument list was rejected because it
formats eagerly and hides the delimiter from the format string.

**Out of scope.** `scripts/` (developer tools that print to a terminal and
never reach a bug report); lines from bundled libraries; numeric formats; the
log format, levels, handlers, and rotation; structured or JSON logging. A
line that logs a user-facing message verbatim is copy and keeps its text,
including the bad-stamp message that shows a non-ASCII stamp with `\u`
escapes, and the unknown-username rejection, which carries the name as
typed. Also rejected as delimiters: single quotes (62 bundled names hold an
apostrophe), brackets (7 names hold one) and curly quotes (not typeable in a
log search), parentheses (10.1% of playlist names hold one, and the
dominant playlist pattern is already name then code in parentheses), and
placement alone (44 calls carry a free-text or path value followed by
another value, and a line has one last position).

Provenance: proposal
[#301](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/301)
(opened 2026-09-19; all four rows ratified 2026-09-26 in the
[ratification record](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/301#issuecomment-5851883535)),
shipped in
[#315](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/315).
Distilled from `docs/proposals/log_line_delimiting_proposal.md`, deleted in
the shipping PR.
