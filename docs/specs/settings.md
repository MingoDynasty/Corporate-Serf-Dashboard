# Settings And Configuration

The app is told a few things by hand in a configuration file, such as the
port, that an update never asks anyone to edit, and works the rest out for
itself. A number outside the range it can work with is refused as that file
is read, with one line naming the file. Where the KovaaK's runs live and who
the player is on the leaderboards live in a small file the app owns, shown and
changed on a Settings page that also offers what the machine already knows and
holds one preference the browser remembers instead, whether a personal best
celebrates. A setting the running app cannot pick up live is frozen at startup,
and the page says when a restart is needed.

Statements below describe what the app does today and link the
[decision log](../decision_log.md) entries that set them — rationale lives
in those entries, not here. A statement with no link is an implementation
fact that no decision-log entry governs. Runtime structure, including the two
filesystem roots and the in-memory stores, is mapped in
[architecture.md](../architecture.md#state); the user-facing rationale is in
[product.md](../product.md#getting-data-in); the user's view of both files is
the README's [Configuration](../../README.md#configuration) section; the
endpoint that identity detection calls is documented in
[kovaaks_api_notes.md](../kovaaks_api_notes.md#userprofileby-username). How
the installer and launcher set the state root and write the first-run
configuration is owned by [release_and_install.md](release_and_install.md).

## The configuration file

- `config.toml` in the state root is created once, by the installer at first
  install or by hand from `example.toml` in a checkout, and is human-owned and
  app-read-only from then on: the app never writes it, and an update never
  touches it
  ([2026-08-02](../decision_log.md#2026-08-02-user-settings-live-in-an-app-owned-store-with-a-settings-page)).
  `ConfigData` holds `port` (required, no default, `1` to `65535`), `host`
  (`"127.0.0.1"`), `polling_interval` (`1000` ms, `1` to `2147483647`),
  `sens_round_decimal_places` (`1`), `debug` (`False`),
  `scenario_metadata_cache_ttl_hours` (`24`),
  `scenario_rank_cache_ttl_hours` (`168`),
  `leaderboard_total_cache_ttl_hours` (`168`), `percentile_warmup_enabled`
  (`True`), `kovaaks_api_timeout_seconds` (`30`, must be above `0`), and
  `show_version_in_title` (`False`). The port and poll-interval bounds are set
  by
  [2026-09-01](../decision_log.md#2026-09-01-configured-ports-and-poll-intervals-are-bounded-at-load);
  a configured `0` port is refused even though `bind_server_socket(0)` still
  asks the OS for a free port, and the poll interval's upper bound is the
  largest delay `window.setInterval` can hold rather than a product cap on how
  slow a poll may be. `example.toml` states both ranges beside the settings.
- The app owns no default port. `example.toml` ships `port = 8050`, and an
  existing install keeps whatever its file says
  ([2026-07-19](../decision_log.md#2026-07-19-default-port-is-8050-not-8080)).
  The installer's generated file carries `port` only
  ([2026-07-19](../decision_log.md#2026-07-19-the-installer-brings-its-own-toolchain-app-locally),
  its 2026-08-02 addendum).
- The two `168` TTLs are set by
  [2026-04-29](../decision_log.md#2026-04-29-cache-leaderboard-totals-for-one-week)
  and the `30` s timeout by
  [2026-07-13](../decision_log.md#2026-07-13-kovaaks-timeout-is-30s-configurable-read-timeouts-are-not-retried);
  what they govern is specified in
  [scenario_rank.md](scenario_rank.md#caching). `percentile_warmup_enabled`
  disables only the warmup worker
  ([2026-07-16](../decision_log.md#2026-07-16-warm-playlist-percentiles-with-one-polite-background-worker)).
  `show_version_in_title` is read per request and prefixes every page title
  with the release label; the surfaces are listed in
  [release_and_install.md](release_and_install.md#build-identity).
- The file is loaded lazily and cached through `get_config()`; `main()` owns
  the first load and turns a missing, undecodable, unparseable, or invalid
  file into one stderr line, "Configuration error: could not load
  `<path>` -- copy example.toml to config.toml.", and exit code 1, before
  playlists load or any service starts
  ([2026-07-09](../decision_log.md#2026-07-09-load-configuration-lazily-at-application-startup)).
  An out-of-range `port` or `polling_interval` takes that same exit rather than
  reaching the bind; `host` is not part of that check and fails later, at the
  bind, with its own message
  ([2026-09-01](../decision_log.md#2026-09-01-configured-ports-and-poll-intervals-are-bounded-at-load)).
  The same line is written to the log files.
- Unknown keys are named once in a warning, "Ignoring unknown key(s) in
  `<path>`: `<keys>`. Remove them when convenient.", and ignored; a file
  carrying keys a release has retired or does not have yet loads on both
  sides of an update
  ([2026-08-02](../decision_log.md#2026-08-02-user-settings-live-in-an-app-owned-store-with-a-settings-page)).
- `host` must be an IP literal. A name, `localhost` and the empty string
  included, exits before any bind with a message naming the setting; the
  address family comes from the literal, so `::` binds as IPv6. On the
  default host both loopback faces, `127.0.0.1` and `::1`, are bound; any
  other host is bound alone, and under `0.0.0.0` nothing answers on `::1`.
  The app has no authentication, so every device that can reach the chosen
  address can read the run data and change the settings
  ([2026-08-14](../decision_log.md#2026-08-14-the-listen-address-is-configurable-loopback-by-default)).
- Every socket is bound by the app itself with `SO_EXCLUSIVEADDRUSE` and
  handed to waitress bound but not listening. A port taken on either face
  exits 1 with "Startup error: port `<port>` is already in use -- most likely
  another copy of the dashboard is already running, or another program has
  taken the port (Steam uses 8080). The port must be free on both loopback
  addresses, 127.0.0.1 and [::1]. Close that program, or set a different port
  in `<path>`." (the "on `<host>`" form under a non-default host). IPv6
  genuinely absent serves IPv4 alone after one info line
  ([2026-07-19](../decision_log.md#2026-07-19-the-app-binds-its-port-exclusively-and-exits-if-it-is-taken)).
  A well-formed literal no local interface holds fails as a host error, not a
  port error
  ([2026-08-14](../decision_log.md#2026-08-14-the-listen-address-is-configurable-loopback-by-default)).
- `debug = true` serves through Flask's development server on the same host
  and port, validates `host` the same way, and warns at startup, when `host`
  is not the default, that the debugger is reachable from that network; the
  combination is not refused
  ([2026-08-14](../decision_log.md#2026-08-14-the-listen-address-is-configurable-loopback-by-default)).

## The settings store

- `data/settings.json` under the state root is app-owned and written only
  through `settings_service`: module `RLock`, an in-process cache that reads
  the disk at most once per cache life, and a temp-file-plus-atomic-replace
  write. A hand edit made while the app runs is not picked up; one made while
  it is stopped is
  ([2026-08-02](../decision_log.md#2026-08-02-user-settings-live-in-an-app-owned-store-with-a-settings-page)).
- The schema is flat: `stats_dir`, `kovaaks_username`, and `steam_id`, each a
  string, under a top-level `schema_version` stamp written first with the rest
  sorted. A missing key, an empty value, and any unusable file all read as
  *not configured*. Reads return the three keys only; the stamp never reaches
  domain code
  ([2026-08-02](../decision_log.md#2026-08-02-user-settings-live-in-an-app-owned-store-with-a-settings-page)
  as amended by
  [2026-08-11](../decision_log.md#2026-08-11-durable-json-stores-carry-a-schema_version-stamp)).
  The file is read `utf-8-sig` and written plain UTF-8.
- Key absence and key emptiness are distinct facts to the startup bootstrap,
  which writes `stats_dir` only when the key is absent
  ([2026-08-02](../decision_log.md#2026-08-02-restart-scoped-settings-are-pinned-at-boot-and-the-stats-folder-finds-itself)),
  and to the setup card, the landing page's hint, and `decline_identity`,
  which key on whether a key exists
  ([2026-08-11](../decision_log.md#2026-08-11-a-fresh-install-is-asked-once-on-a-card-keyed-to-key-absence)).
  Every other consumer collapses both to unset.
- `save_settings` replaces the file whole with exactly the mapping it is
  given; the Settings page always passes all three keys, empty strings
  included
  ([2026-08-02](../decision_log.md#2026-08-02-user-settings-live-in-an-app-owned-store-with-a-settings-page)).
  `decline_identity` re-reads the store under the lock, writes it back with
  `kovaaks_username` set to `""` and every other key untouched, and does
  nothing when the username key already exists
  ([2026-08-11](../decision_log.md#2026-08-11-a-fresh-install-is-asked-once-on-a-card-keyed-to-key-absence)).
  Both take the write guard in the schema contract below.

## Restart scope and pinning

- `stats_dir` is pinned once by server startup (`resolve_stats_dir`), after
  the bootstrap and before any consumer, and whether it is an existing
  directory is decided as part of that pin; every consumer reads the pin
  (`get_usable_stats_dir`), so a directory appearing or vanishing mid-run
  changes nothing until a restart. A pin never resolved reads as unset
  ([2026-08-02](../decision_log.md#2026-08-02-restart-scoped-settings-are-pinned-at-boot-and-the-stats-folder-finds-itself)).
- Identity is a pair. Reads stay live until the first `get_identity` (or
  single-getter) call that observes a non-empty username, which freezes both
  values for the life of the process; a Steam ID without a username freezes
  nothing. A first-time identity set therefore applies without a restart, and
  any later change is restart-scoped
  ([2026-08-02](../decision_log.md#2026-08-02-restart-scoped-settings-are-pinned-at-boot-and-the-stats-folder-finds-itself)).
- `is_restart_pending()` is derived, never stored: true when the stored
  `stats_dir` differs from the pinned one (an empty and an absent value
  compare equal), or when an identity pin exists and the stored pair differs
  from it. An unfrozen identity pin is never a difference
  ([2026-08-02](../decision_log.md#2026-08-02-restart-scoped-settings-are-pinned-at-boot-and-the-stats-folder-finds-itself)).
  `is_stats_dir_change_pending()` answers the directory half alone.
- The app starts and serves with no usable stats directory. Unset and
  set-but-missing behave the same: the initial scan and the file watchdog are
  skipped, one warning names what was configured, and only `port` is needed to
  serve. The app never restarts itself and re-initializes nothing live
  ([2026-08-02](../decision_log.md#2026-08-02-restart-scoped-settings-are-pinned-at-boot-and-the-stats-folder-finds-itself)).
  What the landing page shows in that state is split between the hint and the
  setup card, below.

## Detection

- On startup with the `stats_dir` key absent (a missing file counts), the app
  collects Steam roots from `HKCU` `SteamPath` and both `HKLM` `InstallPath`
  views, adds every `"path"` in each root's `steamapps/libraryfolders.vdf`
  (flat regex, `\\` unescaped), probes
  `steamapps/common/FPSAimTrainer/FPSAimTrainer/stats` once per normalized
  library in that order, and saves the first existing directory merged with
  whatever is stored. A miss writes nothing and retries next start; a present
  value, `""` included, is never overridden; an unreadable vdf is skipped with
  a warning
  ([2026-08-02](../decision_log.md#2026-08-02-restart-scoped-settings-are-pinned-at-boot-and-the-stats-folder-finds-itself)).
  The bootstrap is the app's only silent writer and declines with a warning
  when the store is in the error or future state
  ([2026-08-11](../decision_log.md#2026-08-11-durable-json-stores-carry-a-schema_version-stamp)).
- The same walk, returning every hit in the same order, feeds the Settings
  page's stats-directory suggestions, recomputed on every render of the page
  ([2026-08-03](../decision_log.md#2026-08-03-settings-detection-suggests-and-identity-is-offered-only-once-verified)).
- Identity detection runs only behind the Detect button. It reads
  `config/loginusers.vdf` from every Steam root, merges accounts by SteamID64
  keeping the newest `Timestamp`, probes each distinct persona against
  `/user/profile/by-username`, and keeps a profile only when its `steamId`
  equals that account's ID; the candidate's username is the profile's
  `webapp.username`, never the persona. The result carries the candidates
  newest `lastAccess` first, an unchecked count (transport failure, unexpected
  status, or an unusable payload), and whether account discovery was complete.
  Personas never reach the log; nothing is written
  ([2026-08-03](../decision_log.md#2026-08-03-settings-detection-suggests-and-identity-is-offered-only-once-verified)).

## The Settings page

- `/settings` renders from the stored view, never the pins, so it shows what
  is on disk. Three fields: "Stats directory" (an Autocomplete over the
  suggestions with filtering off), "KovaaK's username", and "Steam ID", all
  free text. Opening the page never calls KovaaK's
  ([2026-08-02](../decision_log.md#2026-08-02-user-settings-live-in-an-app-owned-store-with-a-settings-page),
  [2026-08-03](../decision_log.md#2026-08-03-settings-detection-suggests-and-identity-is-offered-only-once-verified)).
  The stats-directory field shows a chevron and the sentence "Click the field
  to pick from the folders found on this machine." only when there are
  suggestions.
- Save is all-or-nothing and offline: `stats_dir` must be empty or an existing
  directory ("No such directory."), `steam_id` must be empty or 17 ASCII
  digits at or above `76561197960265728` ("Enter a 17-digit SteamID64 — it
  starts with 7656119."), the username has no rule. Any field error writes
  nothing; values are stripped; a successful save writes every key, says
  "Settings saved.", and, when a username is present and
  `percentile_warmup_enabled` is on, starts the warmup worker if none is
  running
  ([2026-08-02](../decision_log.md#2026-08-02-user-settings-live-in-an-app-owned-store-with-a-settings-page)).
- Save outcomes are in-place statuses, never toasts: an I/O failure says
  "Could not save settings — nothing was written. See data/logs/debug.log."
  and a refused write over a newer file says "Nothing was saved. The settings
  file was written by a newer version of this app. Update the app to change
  settings."
  ([2026-08-11](../decision_log.md#2026-08-11-durable-json-stores-carry-a-schema_version-stamp));
  the routing rule lives in
  [notifications.md](notifications.md#routing-policy).
- While `is_restart_pending()` holds, the page shows "Restart the app to
  apply. This app is still running on the settings it started with.", on
  every visit and immediately after the save that caused it
  ([2026-08-02](../decision_log.md#2026-08-02-restart-scoped-settings-are-pinned-at-boot-and-the-stats-folder-finds-itself)).
- "Detect my accounts" fills inputs only. Exactly one candidate with nothing
  unchecked and discovery complete fills both fields ("Found `<username>`.
  Save to apply it."); any other result with at least one candidate goes to
  the "Detected KovaaK's accounts" picker, led by "Found `<n>` KovaaK's
  accounts. Choose the one to use, then Save." ("account" for one), whose
  pick fills both fields from the rendered result without a second
  detection; an empty result leaves the picker hidden. The conclusive "No
  Steam account on this machine has a KovaaK's profile. Type your username
  in yourself — KovaaK's cannot look one up from a Steam ID." appears only
  when nothing was unresolved; otherwise "No KovaaK's profile matched the
  Steam accounts that could be checked.", followed by the discovery and
  unchecked caveats
  ([2026-08-03](../decision_log.md#2026-08-03-settings-detection-suggests-and-identity-is-offered-only-once-verified)).
  Before any detection the button sits beside the hint "Checks the Steam
  accounts on this machine against KovaaK's.", which a detection's report
  replaces.
- A yellow alert with a warning icon ([2026-08-30](../decision_log.md#2026-08-30-one-severity-color-language-for-inline-notices))
  titled "Your saved settings are not being used" carries the
  store's message in the error and future states and is re-derived after a
  save that repairs the file
  ([2026-08-11](../decision_log.md#2026-08-11-durable-json-stores-carry-a-schema_version-stamp)).
- The version section is static text from `BuildInfo`: "Version `<release
  label>`" then "Commit `<short sha>` (`<commit date>`)", the Commit prefix
  attributing a date that can lag the tag's by a day
  ([2026-08-02](../decision_log.md#2026-08-02-the-settings-page-owns-version-display)).
  Beneath it, "Report a bug" opens the GitHub bug form with `version`
  pre-filled from the same label, and "Logs `<log directory>`" names where
  `debug.log` is
  ([2026-08-10](../decision_log.md#2026-08-10-bug-reports-land-on-github-issues-with-the-log-attached-unredacted-and-disclosed)).
- Every callback that writes `data/settings.json` or spends a KovaaK's call
  guards on its trigger: Save and Detect on `n_clicks` and the triggering id,
  the picker on a chosen value and the triggering id
  ([2026-08-02](../decision_log.md#2026-08-02-user-settings-live-in-an-app-owned-store-with-a-settings-page)).
  The Celebrations switch below is the one state-writing callback that does
  neither, and deliberately: its write is browser-local, and the spurious call
  it has to survive arrives *with* the switch as the triggering id, so it gates
  on the initialization tick instead
  ([2026-09-02](../decision_log.md#2026-09-02-the-celebration-setting-is-browser-local-on-the-settings-page)).

## Celebrations

- A "Celebrations" section sits between the Save form and the version section,
  outside the form: the switch "Personal best celebration", described as
  "Plays a short animation and shows a toast when a run beats your personal
  best in any scenario. Works on every page, and does not depend on Run
  Notifications. Takes effect right away.", with a "Preview" button beside it.
  Nothing here goes through Save, and nothing here touches the restart notice
  or the store alert, which speak for the form's three keys
  ([2026-09-02](../decision_log.md#2026-09-02-the-celebration-setting-is-browser-local-on-the-settings-page)).
- The setting is the shell-hosted `dcc.Store(id="pb-celebration-style",
  storage_type="local")`, not the control: one browser-local string, `"off"`
  or a style name, defaulting to `"confetti"`. The switch initializes from it
  and writes back to it, mapping on to `"confetti"` and off to `"off"`, and
  carries no Dash persistence of its own. What the setting governs is in
  [notifications.md](notifications.md#run-notifications)
  ([2026-09-02](../decision_log.md#2026-09-02-the-celebration-setting-is-browser-local-on-the-settings-page)).
- The value is per browser, is cleared with site data, and is never written to
  `data/settings.json`; a browser that has never visited the page celebrates.
  Anything but the exact `"off"` reads as on, so a value this build does not
  know still celebrates rather than silently disabling the family
  ([2026-09-02](../decision_log.md#2026-09-02-the-celebration-setting-is-browser-local-on-the-settings-page)).
- A one-shot `dcc.Interval` initializes the switch from the store, which reads
  as `State` there; the store-as-`Input` pair would be a dependency cycle. The
  same tick gates the write direction, because mounting the page fires that
  callback with the switch's layout default despite `prevent_initial_call` and
  with the switch as the triggering id, which would otherwise write the on
  value over a stored off on every visit
  ([2026-09-02](../decision_log.md#2026-09-02-the-celebration-setting-is-browser-local-on-the-settings-page)).
- Preview plays the currently selected style through the same clientside path
  a real celebration takes, so it obeys the reduced-motion guard, and it shows
  no toast. With the setting off it plays nothing
  ([2026-09-02](../decision_log.md#2026-09-02-the-celebration-setting-is-browser-local-on-the-settings-page)).

## The setup card

- A store the app cannot read gets its own card first. In the `ERROR` and
  `FUTURE` states the card shows "Your settings can't be read" with no Skip,
  and the key-absence states below never run: both states read as no keys, so
  they would report a fresh install for a store that is configured on disk.
  One card covers both, because the Settings page's store alert is where they
  are told apart and where the remedy lives
  ([2026-08-11](../decision_log.md#2026-08-11-durable-json-stores-carry-a-schema_version-stamp)).
  Copy and treatment belong to the Scenario Performance spec.
- The landing page's card is keyed to key absence in the stored view: an
  absent `stats_dir` shows "Finish setting up" with no Skip and wins when both
  keys are absent; a present `stats_dir` with an absent `kovaaks_username`
  shows "Add your KovaaK's account" with "Open Settings" and "Skip". A key
  that exists with any value retires its item for good, so a configured
  install never sees the card. Nothing renders while
  `is_stats_dir_change_pending()` holds
  ([2026-08-11](../decision_log.md#2026-08-11-a-fresh-install-is-asked-once-on-a-card-keyed-to-key-absence)).
  Placement and copy belong to the Scenario Performance spec.
- Skip calls `decline_identity`: the username becomes `""`, nothing else
  changes, no worker starts, nothing pins, and the card never returns
  ([2026-08-11](../decision_log.md#2026-08-11-a-fresh-install-is-asked-once-on-a-card-keyed-to-key-absence)).
  Two things stop the write and neither takes the card away, because nothing
  was recorded: a future-state store refuses it
  ([2026-08-11](../decision_log.md#2026-08-11-durable-json-stores-carry-a-schema_version-stamp)),
  and an unwritable `data/` fails it. Both report on the red toast "Skip was
  not saved", the refusal with "The settings file was written by a newer
  version of this app. Update the app to change settings." and the failure
  with "Nothing was written. Try again, or see data/logs/debug.log for
  details."; the failure is logged. They share one channel, so a second Skip
  click re-pops the current answer instead of clicking into silence, and a
  retry that fails differently replaces the first explanation rather than
  sitting beside it
  ([2026-08-31](../decision_log.md#2026-08-31-repeatable-toasts-replace-in-place-with-a-visible-re-entry)).
- The landing page's in-place hint "No stats directory configured — set it in
  Settings" speaks only for a `stats_dir` key that exists and is unusable;
  while a set directory awaits a restart it reads "Restart the app to apply
  your saved settings." instead
  ([2026-08-02](../decision_log.md#2026-08-02-restart-scoped-settings-are-pinned-at-boot-and-the-stats-folder-finds-itself)
  as amended by
  [2026-08-11](../decision_log.md#2026-08-11-a-fresh-install-is-asked-once-on-a-card-keyed-to-key-absence)).
- An empty username keeps the app fully offline; the short-circuit is
  specified in [scenario_rank.md](scenario_rank.md#data-sources-and-identity)
  ([2026-08-01](../decision_log.md#2026-08-01-no-username-stays-fully-offline--user-independent-totals-rejected)),
  and how the position surfaces state it is in
  [notifications.md](notifications.md#routing-policy)
  ([2026-08-09](../decision_log.md#2026-08-09-an-unset-username-is-stated-in-place-never-reported-as-a-failure)).

## Durable-store schema contract

This section governs every JSON store the app writes under `data/`:
`settings.json`, `playlist_visibility.json`, and each user playlist under
`data/playlists/`. Cache files under `data/cache/` and the bundled corpus are
exempt
([2026-08-11](../decision_log.md#2026-08-11-durable-json-stores-carry-a-schema_version-stamp)).

- Every store carries a top-level `"schema_version"` whose value must be
  exactly an `int` (a JSON `true` is rejected) in the supported set `{1}`.
  There is no grandfather rule: a well-formed file without the stamp is an
  error
  ([2026-08-11](../decision_log.md#2026-08-11-durable-json-stores-carry-a-schema_version-stamp)).
- `store_schema.read_store_document` classifies each file into one of four
  states and never mutates it: *missing* (no file) reads as the first-run
  default; *error* (unreadable, not JSON, not an object, unstamped, a
  non-integer or non-positive stamp, a retired stamp, or a supported stamp
  whose payload fails its validator) preserves the bytes, reads as the
  first-run default, and logs an actionable message; *supported* reads the
  validated payload; *future* (a stamp above `1`) reads nothing and refuses
  every write with `UnsupportedSchemaError`
  ([2026-08-11](../decision_log.md#2026-08-11-durable-json-stores-carry-a-schema_version-stamp)).
- Automatic writers never touch an error- or future-state store. A
  user-initiated write owns an error-state file: the incumbent is copied, never
  moved, to `<name>.corrupt-<n>.bak` with exclusive create before the
  replace, and the write is refused if the copy fails. The owning surface
  states the error and future states in its own register: the Settings page
  alert and statuses, the Playlists page for visibility, the startup warning
  queue for playlist files
  ([2026-08-11](../decision_log.md#2026-08-11-durable-json-stores-carry-a-schema_version-stamp)).
- Settings v1 is a subset of the three keys with string values, unknown keys
  invalid; visibility v1 is exactly `shown_playlists` as a list of strings;
  playlist v1 is `PlaylistData`, extras ignored. The same validators serve the
  runtime readers and the conversion script
  ([2026-08-11](../decision_log.md#2026-08-11-durable-json-stores-carry-a-schema_version-stamp)).
- The app has no migration code. `scripts/stamp_schema_version.py` stamps an
  unstamped valid-v1 file, leaves stamp 1 alone, and preserves and reports
  everything else; how it ships and resolves its root is in
  [release_and_install.md](release_and_install.md#schema-migration-shipping)
  ([2026-08-11](../decision_log.md#2026-08-11-durable-json-stores-carry-a-schema_version-stamp)).

## State root

- `CSD_STATE_DIR` names the directory holding every mutable file:
  `config.toml` and everything under `data/` (`settings.json`,
  `playlist_visibility.json`, `playlists/`, `cache/`, `logs/`). Unset means
  the current working directory; bundled read-only assets under
  `resources/benchmarks/` resolve from the package root instead. The app only
  reads the variable
  ([2026-07-19](../decision_log.md#2026-07-19-all-mutable-state-lives-under-an-explicit-state-root)).
  An empty value reads as unset. Who sets it is specified in
  [release_and_install.md](release_and_install.md#state-root).
- Runtime data groups under `data/`, logs under `data/logs/`
  ([2026-06-22](../decision_log.md#2026-06-22-keep-user-runtime-data-under-data)),
  and the API cache under `data/cache/`
  ([2026-07-11](../decision_log.md#2026-07-11-move-the-api-cache-under-datacache)).
