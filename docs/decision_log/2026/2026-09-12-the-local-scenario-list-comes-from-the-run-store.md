# 2026-09-12: The Local Scenario List Comes From The Run Store

Status: Accepted

With no playlist selected, the Scenario Performance dropdown listed scenarios
by reading the stats file names, and it cut each name at its first hyphen. A
scenario like "Anti-Centering Easy" showed up as "Anti", and choosing it said
there were no local runs. The list now comes from the runs the app has
already loaded, named the way each stats file names its own scenario. A
scenario none of whose files could be read no longer appears.

**The defect.** `get_unique_scenarios` listed the stats directory and took
`file.split("-")[0].strip()` as the name, splitting at the first hyphen
rather than at the ` - Challenge - ` separator. The run store
(`kovaaks_database`) is keyed by `RunData.scenario`, which
`extract_data_from_file` reads from the file's `Scenario:` line
(`Anti-Centering Easy - Challenge - ... Stats.csv` carries
`Scenario:,Anti-Centering Easy`; `Reflex Flick - Easy - ... Stats.csv`
carries `Scenario:,Reflex Flick - Easy`). The two sources disagreed for every
hyphenated name, and `is_scenario_in_database` is a plain membership test, so
a truncated entry fell to the "No local runs found" empty state. Measured on
the maintainer's corpus (8,066 files, 2026-09-12, names as the parser strips
them): 866 scenarios in the store against 838 dropdown entries, 13 entries
naming no scenario (`Anti`, `Reflex Flick`, `Reflex Flick Wide`, `cA x`,
`TSK`, and others), and 41 scenarios with no entry at all, among them the 23
`TSK - ...` scenarios collapsed into the single dead `TSK` entry.

**The store is the single authority for which scenarios exist locally.**
`get_scenario_names()` returns `sorted(kovaaks_database)`; it takes no
directory. `_local_scenario_options()` in the home page keeps its
`get_usable_stats_dir()` guard. The pin that guard reads is restart-scoped,
and the store is only ever filled behind a usable pin, so today the guard
never trims a populated list; it keeps the spec's promise (no usable
directory, no local list) a property of this function rather than of the
startup order. The store is populated at startup before the server serves,
and the watchdog adds newly played scenarios to it, so the list is complete
on first render. Rejected: fixing the split to cut at ` - Challenge - `. It
works for today's names, re-breaks on the next naming quirk, and still would
not be guaranteed to agree with the store's keys; the file's own field is the
only authority and the store already holds it.

**Accepted consequence: a scenario with no parseable run leaves the list.**
Before, such a scenario contributed a filename-derived entry that already
showed "No local runs found" when selected, so dropping it removes a dead
entry rather than hiding data. Its failed files are still reported the way
they were: the startup load's counted log line, and the watchdog's toast for
live imports.

**Incidental.** The per-render `os.listdir` of the stats directory is gone.
That was not the motivation, and no caching was restructured for it.
