# 2026-09-14: App Copy Follows One Set Of Rules, And The Em Dash Is Gated Out

Status: Superseded in part by the
[2026-10-04 skill-judgment entry](#2026-10-04-skill-is-judged-by-the-typical-run-with-honest-uncertainty-in-verdicts-not-advice):
D4 keeping "Ready to move on." on a passed run that did not place no longer
holds, and that toast now ends at the fact. D4 dropping "Keep grinding..."
from the below-threshold toast stands. Everything else here stands.

The app's text was written one feature at a time, so the same condition read
differently from page to page and some messages sounded like log lines. Every
string the app shows now follows nine short copy rules, and every string the
rules changed was swept in one pass. What a user notices is that the same
thing now reads the same way on every page. A test keeps the em dash out of
the app's source for good.

**Scope of "copy" (rule 8).** Every string this app's code puts in front of a
user: page text, service messages a page shows verbatim (import refusals,
startup playlist warnings, store messages, warmup stop reasons), chart
annotations and legend entries, and accessible names, which a screen reader
announces. Text a bundled library draws itself is not copy: plotly.js's
toolbar and its `Share chart...` dialog, kept by the
[2026-09-12 entry](#2026-09-12-charts-keep-plotlyjs-4s-share-chart-button),
AG Grid's overlays, and Mantine's built-in text. The app passes no override for
any of it (no plotly `config`, no grid `localeText`); should it ever supply
such text, that text becomes copy. Console, launcher, and installer output,
`logging` lines, docstrings, comments, and documentation prose are outside the
rules.

**The rules.** AGENTS.md's styling conventions carry the operative form; the
numbering is the proposal's.

1. *A sentence ends with a period; a status readout does not.* `Settings
   saved.` is a sentence; `Update interrupted · 8 of 40 refreshed`, the
   Position hint, and a closing `File: {path}` are readouts. A semicolon never
   joins two sentences. A sentence that ends on an inline link puts its period
   in a separate child after the anchor, or the period renders underlined as
   part of the link. Basis: Microsoft's periods and semicolons entries and the
   Windows writing guidance; Apple punctuates message bodies; Google and
   Polaris also avoid semicolons. Material, Polaris, and Atlassian drop the
   period on a lone-sentence tooltip, and lose on the Windows-first weighting.
2. *No em dashes.* Prose splits into sentences; a readout chains fragments
   with ` · ` (space, middle dot, space). The one exception is the `—` empty
   value under Last played when no scenario is selected
   ([2026-06-30](#2026-06-30-model-home-last-played-empty-states-explicitly)).
   The run-toast scenario/score separator became a colon, the separator the
   celebration toast already used. Why: the no-em-dash ruling of the
   [2026-08-11 setup-card entry](#2026-08-11-a-fresh-install-is-asked-once-on-a-card-keyed-to-key-absence),
   which deferred this sweep; Material calls em dashes best avoided in UX
   writing and Atlassian prefers two sentences. No guide prescribes a fragment
   separator; the middle dot is the web's metadata separator and the grid
   status lines already used it.
3. *Casing (D2).* Sentence case for controls (labels, switches, buttons,
   placeholders), toast, alert, and modal titles, status lines, tooltips,
   chart annotations, and legend entries. Page titles, section headings, and
   grid column headers keep Title Case, as do proper names (KovaaK's, Steam
   ID, PB, SteamID64) and the named chart modes "Score vs Sensitivity" and
   "Score vs Time". Prose that quotes a control repeats its on-screen casing.
4. *One ellipsis form.* The single `…` character, and only for work still in
   progress (the fill's live readout). Placeholders are bare noun phrases, a
   path is never elided, and no line trails off for tone. The app authors no
   command that opens a further dialog, so the desktop ellipsis-on-command
   convention has no site. Basis: Microsoft, Apple, Atlassian, and Polaris use
   the character; Polaris rejects it on placeholders; Windows and Material
   endorse it for in-progress text.
5. *Contractions, consistently (D6).* The common ones: can't, couldn't,
   doesn't, isn't, wasn't, aren't, you're. A contraction and its full form
   never both appear on screen (Microsoft's consistency clause); "do not" is
   reserved for a warning the user must not skip (Material's carve-out), and
   no string uses it today.
6. *Control names are bold (D8), user-typed text is quoted.* A control named
   in prose is bold, in its on-screen casing, and takes its type word when the
   label reads as prose: "Turn on the **Show hidden** switch", "Press the
   **Detect my accounts** button again". Where bold cannot render (a toast
   title, already bold; an accessible name) the name stays plain and the type
   word carries it. A page name ("Settings") and a paraphrased value ("the
   oldest date", "a checkpoint hour") are not control names. User-entered free
   text keeps double straight quotes (`"{name}"`, `KovaaK's username "X"`),
   because playlist names and usernames can contain anything; tokens (Steam
   IDs, playlist codes, counts, full paths) stay bare; a literal file key is
   quoted (`a "code" field`). The app now has a three-way marker: bold for a
   control, double quotes for what the user typed, nothing for a token.
7. *Vocabulary.* The software is *this app* or *the app*, never *the
   dashboard* (the
   [2026-08-21 launcher entry](#2026-08-21-the-launcher-narrates-a-slow-start-and-keeps-its-120-second-ceiling)).
   The run source is the *stats folder*. A cached position is *from cache*.
   *Position*, *Rank*, and *PB* keep the
   [2026-07-06 meanings](#2026-07-06-one-word-per-concept-in-leaderboard-verbiage),
   so a leaderboard lookup is a *position lookup*. A playlist's identifier is
   its *playlist code*; the import help introduces KovaaK's own name, *share
   code*, once. Instructions say *turn on* and *turn off*, states say *on* and
   *off*, the control is a *switch*, and *toggle* is never a verb. An
   open-ended list uses *such as*, never *etc.* Data the app can't use is *not
   valid*, never *invalid*, and a message names the specific problem where it
   can. The log pointer is always `See data/logs/debug.log.`
8. *A message that reaches the screen is copy wherever the app builds it*
   (scope above). The diagnostic detail stays in the log line beside it.
9. *Error copy says what happened, then what to do when there is something to
   do (D7).* A failure with no useful recovery says only what happened. An
   object name or a path never opens a sentence: a noun names it first, and a
   count or a score may lead. A path goes inline only as the last words of a
   message's only sentence (`Couldn't read the playlist file {file}.`);
   otherwise the message names the file by kind, finishes its sentences, and
   closes with the labeled readout `File: {path}`. The toast title carries the
   verdict, unchanged from the
   [2026-08-03 policy](#2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy);
   the "… failed" titles stay, since Atlassian endorses the form and only the
   legacy Windows guide bans "failed to".

**The decisions**, all ruled or ratified by the maintainer on PR #247.

- *D1, the Position hint* (ratified 2026-09-14): middle-dot fragments with
  the instruction halves dropped (`N/A · set your KovaaK's username in
  Settings`, `… · lookup failed`, `… · from cache`). The Refresh button beside
  the value is the affordance, and a hint that keeps "Refresh to update"
  wraps a 300 px stats box to two lines and pushes Refresh to a third
  (measured 2026-08-21). The unset variant keeps its Settings link because no
  adjacent control repairs it. A screen reader may skip the glyph, so each
  hint reads correctly without it. Rejected: keeping the instruction halves
  (a two-line field on every stale render); full sentences beside a
  parenthesised value.
- *D2, casing* (ratified 2026-09-14): as rule 3. The Microsoft and Windows
  guides, Material, Atlassian, Polaris, GitHub's Primer, Obsidian's plugin
  guidelines, and the Mantine docs all use sentence case for controls, modal
  titles, and notification titles; macOS alone title-cases controls, and this
  is a Windows app. The same guides also lowercase page titles, section
  headings, and column headers, so the Title Case exception for those is
  house style, not convention; extending sentence case to them would rename
  surfaces the README, specs, and launch material already name, and is a
  separate scope question. Rejected: Title Case for every control; leaving
  casing unruled.
- *D3, the two unset-username status lines* (ratified 2026-09-14): keep the
  split, "Percentiles unavailable." on the overview and "Positions
  unavailable." on the scenario table, because each names the columns its own
  page empties. Rejected: one noun for both, which names a column the overview
  does not have.
- *D4, the coaching flourishes* (ruled 2026-09-12): keep "Ready to move on."
  on a passed run that did not place; drop "Keep grinding..." from the
  below-threshold toast, which already states the score, the shortfall, and
  any placement, and which repeats on every miss in a session, where
  Atlassian and the Nielsen Norman Group say a flourish wears out. No guide
  covers a flourish on a miss, so this applies general guidance; a short
  repeated-run comparison with a few users is how to measure it if reopened.
  Rejected: "Keep grinding." with a period (taste with no comprehension
  argument, and a period does not answer repetition); dropping both lines.
- *D5, sequencing* (ratified 2026-09-14): the sweep lands before the release
  the launch announcement promotes, because the post's lead visual is a run
  toast beside the Position field, both of which this sweep rewrote. Rejected:
  shipping the post against the old copy.
- *D6, contractions* (ratified 2026-09-14): as rule 5, reversing the first
  draft's full-form rule. Microsoft, the Windows guidance ("too formal or even
  stilted" without them), Google, Material, Apple, Atlassian, and Polaris all
  say to use common contractions. One 2026 corpus study found AI-generated
  academic abstracts lacked the informality features it measured,
  contractions among them; that is a frequency difference in one genre, not a
  detector, so it corroborates the guides rather than carrying the case.
  Rejected: full forms as house voice, legitimate as taste but not the
  convention.
- *D7, values in sentences* (ratified 2026-09-14): as rule 9, with the
  supplemental path written as the readout `File: {path}`. Windows says to
  avoid starting sentences with object names (a value can open with a
  lowercase letter, a digit, or a backslash) and keeps a full path out of the
  main sentence. Rejected: the first draft's ban on every sentence-initial
  value, which would have rewritten clear count-led toasts; exempting the
  store messages as a named exception; writing the path as a sentence (`The
  file is {path}.`); and the "verdict: value" colon tail, which is the log
  idiom. A true second line for the path in alerts and toasts would be closer
  to the Windows layout; it is a component change, and the readout degrades
  into it without a word changing.
- *D8, control names in prose* (ruled 2026-09-14, the alternative): as rule
  6. Apple's rule is that sentence-style element names need marking; Atlassian
  bolds element names in app copy; Microsoft's in-UI guidance prefers wording
  that sets the name off, adding the element type. Bold gives a lowercased
  verb-phrase label a visible edge, and the type word stays because a screen
  reader does not announce bold. The precedent for bold in app copy is
  narrower than for the type word, so this is a product judgment for this
  app's sentence-case labels rather than a convention. Rejected: the type word
  alone (the 2026-09-04 lean); bolding only the four type-word sentences,
  which would put a bold and a plain control name on one detection line;
  quotation marks, reserved for user text; dropping the name beside its
  button.

**Mechanics that hold the rules.**

- One helper, `control_name()` in `source/components/control_name.py`, builds
  the bold span as `html.B`. Not a bold `dmc.Text`: an unsized `dmc.Text`
  renders at Mantine's md size, larger than the 14 px tooltip, description,
  or toast body around it. A chart annotation cannot hold a component and
  writes `<b>…</b>` into its string, which plotly draws. Sentences that carry
  a bold name are children lists; the ones returned from callbacks are built
  fresh per call, and `toast()` accepts a list message.
- `read_store_document` and `decode_store_document` take the file's `kind`
  ("settings file", "playlist visibility file", "playlist file") from their
  four call sites. A malformed stamp is quoted with `json.dumps`, so the
  message shows `"1"`, `true`, or `null` as the file holds them, not Python's
  `repr`.
- Log lines are unchanged where the new user message dropped a fact or added a
  user-only pointer: every import and delete refusal logs its previous text
  beside the new message, and the file-collision refusal is logged where the
  file name is known, in `_guard_playlist_destination`. The playlist-save
  refusal points the user at the log and nothing on the write path records its
  `OSError`, so its warning gained `exc_info` and carries the traceback. Not
  every log-directed message has an exception behind it: a run file with a
  missing field, or a Steam account list the app does not recognize, logs a
  plain warning. The startup playlist
  warnings and the store messages are logged by helpers that log what they
  show, so those log lines follow the new copy. A user-root playlist file the
  loader skipped was logged twice with identical text (store layer and
  loader) until the
  [2026-09-26 logging conventions](#2026-09-26-log-lines-delimit-their-values-by-kind)
  shipped; the loader now only queues the message for the UI. That entry is
  also the audit of how log lines delimit their values.
- `tests/test_em_dash_guard.py` walks every module under `source/`, visits
  every string constant including f-string parts, skips docstrings, and fails
  on an em dash outside an allowlist holding only the Last played glyph, keyed
  by module, enclosing function, and value. It does not see `assets/`, and it
  does not gate the three-period ellipsis, which clientside JavaScript spreads
  and a log line use legitimately. `tests/rendered_text.py` flattens children
  and renders a bold span back as `**name**`, so tests assert the ratified
  text verbatim and a name that loses its bold fails.

**Deliberately not changed.** Softening the red refresh-failure toast, whose
title question this sweep answered and whose color question stays open in
[tech_debt.md](./tech_debt.md) *(resolved 2026-09-27: it stays red, see
[The Manual-Refresh Hard Failure Stays Red](#2026-09-27-the-manual-refresh-hard-failure-stays-red))*;
the configured-but-wrong username; the Steam ID
mismatch toast's structure; the two `plot_service.py` empty-state messages the
page callbacks never reach; the Aim Training Journey page beyond its banner
and one label; the personal best celebration surfaces, already in the target
style.

**Supersedes in part, for copy only.** Each entry keeps its decision and gains
a note where its quoted strings changed:
[2026-08-03 notification layer](#2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy),
[2026-08-09 unset username](#2026-08-09-an-unset-username-is-stated-in-place-never-reported-as-a-failure),
[2026-08-09 Scenario Performance naming](#2026-08-09-the-graph-page-is-scenario-performance-its-panel-is-chart-options),
[2026-08-11 setup card](#2026-08-11-a-fresh-install-is-asked-once-on-a-card-keyed-to-key-absence),
[2026-08-20 run points](#2026-08-20-run-points-get-a-size-preset-and-a-color-and-the-chart-stops-there),
[2026-08-21 empty point color](#2026-08-21-the-empty-point-color-is-called-default-and-the-points-follow-the-theme),
[2026-08-21 master switch](#2026-08-21-run-notifications-have-a-master-switch-and-the-threshold-switch-is-renamed),
[2026-08-22 playlist fill](#2026-08-22-the-playlist-fill-reports-degradation-in-place-only),
and
[2026-09-02 celebration](#2026-09-02-a-new-personal-best-celebrates-on-every-page).

**Sources**, read 2026-09-04 unless noted:
[Microsoft capitalization](https://learn.microsoft.com/en-us/style-guide/capitalization),
[contractions](https://learn.microsoft.com/en-us/style-guide/word-choice/use-contractions),
[periods](https://learn.microsoft.com/en-us/style-guide/punctuation/periods),
[semicolons](https://learn.microsoft.com/en-us/style-guide/punctuation/semicolons),
[ellipses](https://learn.microsoft.com/en-us/style-guide/punctuation/ellipses),
[etc.](https://learn.microsoft.com/en-us/style-guide/a-z-word-list-term-collections/e/etc),
[toggle](https://learn.microsoft.com/en-us/style-guide/a-z-word-list-term-collections/t/toggle),
[turn on, turn off](https://learn.microsoft.com/en-us/style-guide/a-z-word-list-term-collections/t/turn-on-turn-off),
and [formatting text in instructions](https://learn.microsoft.com/en-us/style-guide/procedures-instructions/formatting-text-in-instructions);
the [Windows app writing style](https://learn.microsoft.com/en-us/windows/apps/design/style/writing-style);
the legacy Windows UX guide on
[error messages](https://learn.microsoft.com/en-us/windows/win32/uxguide/mess-error)
and [UI text](https://learn.microsoft.com/en-us/windows/win32/uxguide/text-ui);
Google developer style on
[contractions](https://developers.google.com/style/contractions),
[capitalization](https://developers.google.com/style/capitalization),
[ellipses](https://developers.google.com/style/ellipses), and its
[word list](https://developers.google.com/style/word-list);
Material 3 [UX writing best practices](https://m3.material.io/foundations/content-design/style-guide/ux-writing-best-practices)
and [grammar and punctuation](https://m3.material.io/foundations/content-design/style-guide/grammar-and-punctuation);
the Apple Style Guide on
[quotation marks](https://support.apple.com/guide/applestyleguide/q-apsg38496e66/web)
and [contractions](https://support.apple.com/guide/applestyleguide/c-apsgb744e4a3/web);
Atlassian [language and grammar](https://atlassian.design/content/language-and-grammar)
and [writing style](https://atlassian.design/content/writing-style);
Polaris [grammar and mechanics](https://github.com/Shopify/polaris/blob/main/polaris.shopify.com/content/content/grammar-and-mechanics.mdx);
Primer [content](https://primer.style/product/getting-started/foundations/content/);
Obsidian [plugin guidelines](https://docs.obsidian.md/Plugins/Releasing/Plugin+guidelines);
the Nielsen Norman Group on
[error messages](https://www.nngroup.com/articles/error-message-guidelines/);
and the corpus study
[Informality features in AI-generated academic writing](https://www.sciencedirect.com/science/article/pii/S1475158526000019).
Rule 7's *not valid* line follows the Microsoft Writing Style Guide's word-list
entry on the pair and the Windows error-message guide, read 2026-09-13. Each
guide's position, question by question, is in the research note behind the
proposal (`ignore/design-notes/copy-conventions-research.md`, main checkout
only, untracked).

Provenance: proposal
[#247](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/247)
(opened 2026-08-21; D4 ruled 2026-09-12, D8 ruled 2026-09-14, D1 to D3 and D5
to D7 ratified 2026-09-14), shipped in
[#291](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/291).
Distilled from `docs/proposals/app_messaging_consistency_proposal.md`, deleted
in the shipping PR; git history holds its Copy block, which lists every string
the sweep changed.
