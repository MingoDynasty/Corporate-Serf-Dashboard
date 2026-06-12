# Corporate Serf Dashboard — System Diagrams

A living visual reference of how the system fits together. Companion to `research.md` (the comprehensive write-up) and `analysis.md` (the topic-by-topic walkthrough).

All diagrams use [Mermaid](https://mermaid-js.github.io/), which Obsidian renders natively. Edit any diagram by changing the code inside the ```` ```mermaid ```` blocks.

## Contents

1. **High-level system overview** — every major piece in one picture.
2. **Tech stack layers** — what's running where.
3. **CSV ingestion pipeline** — how data gets into the in-memory database.
4. **In-memory database shape** — the four sorted views.
5. **Rank lookup pipeline** — the three-tier fallback and caches.
6. **Concurrency / thread model** — who's running on which thread.
7. **Cache layout on disk** — what lives under `cache/`.

How to read the diagrams:
- **Cyan boxes** = Python code (modules, functions).
- **Yellow boxes** = on-disk state (files, caches).
- **Green boxes** = in-memory state (the database, queues).
- **Pink boxes** = external systems (browser, KovaaK's API, KovaaK's game).
- **Gray boxes** = threading primitives (locks, executors).
- **Dashed arrows** = "fires/triggers" (async).
- **Solid arrows** = "calls/reads/writes" (sync).

---

## 1. High-Level System Overview

Every major component on one page. This is the diagram to come back to whenever you want to remember *what talks to what*.

```mermaid
flowchart TB
    subgraph EXT [External Systems]
        direction LR
        BROWSER([User's Browser])
        KOVAAKS_GAME([KovaaK's Game])
        KOVAAKS_API([KovaaK's Webapp API<br/>kovaaks.com/webapp-backend])
    end

    subgraph DISK [On Disk]
        direction LR
        CONFIG[(config.toml)]
        STATS_DIR[(stats_dir/<br/>thousands of CSVs)]
        PLAYLISTS[(resources/playlists/<br/>*.json)]
        CACHE[(cache/<br/>rank, totals, mappings)]
    end

    subgraph APP [Corporate Serf Dashboard Process]
        direction TB

        subgraph BOOT [Boot Phase]
            APP_PY[app.py<br/>main]
            CONFIG_SVC[config_service<br/>loads ConfigData]
            INIT_DATA[initialize_kovaaks_data<br/>bulk CSV ingest]
            INIT_PLAYLISTS[load_playlists<br/>JSON ingest]
        end

        subgraph CORE [Runtime]
            direction TB
            WAITRESS[Waitress WSGI Server<br/>127.0.0.1:8080]
            DASH[Dash App + Mantine UI]
            WATCHDOG[Watchdog Observer<br/>+ NewFileHandler]
            API_SVC[api_service<br/>rank lookup pipeline]
            DATA_SVC[data_service<br/>ingestion + queries]
            PLOT_SVC[plot_service<br/>Plotly figures]
        end

        subgraph MEM [In-Memory State]
            DB[(kovaaks_database<br/>+ run_database<br/>+ playlist_database)]
            QUEUE[(message_queue<br/>deque)]
        end
    end

    %% Boot wiring
    CONFIG -.read at startup.-> CONFIG_SVC
    STATS_DIR -.bulk scan.-> INIT_DATA
    PLAYLISTS -.read at import.-> INIT_PLAYLISTS
    INIT_DATA --> DB
    INIT_PLAYLISTS --> DB
    APP_PY --> WAITRESS
    APP_PY --> WATCHDOG

    %% Runtime flows
    BROWSER <-->|HTTP| WAITRESS
    WAITRESS --> DASH
    DASH --> DATA_SVC
    DASH --> API_SVC
    DASH --> PLOT_SVC

    KOVAAKS_GAME -.writes CSV.-> STATS_DIR
    STATS_DIR -.OS event.-> WATCHDOG
    WATCHDOG --> DATA_SVC
    WATCHDOG -.appends.-> QUEUE
    WATCHDOG -.triggers refresh.-> API_SVC

    DATA_SVC <--> DB
    API_SVC <-->|HTTP| KOVAAKS_API
    API_SVC <--> CACHE

    QUEUE -.polled by dcc.Interval.-> DASH
    DB -.read by callbacks.-> PLOT_SVC

    classDef python fill:#bde0fe,stroke:#0077b6,color:#000
    classDef disk fill:#ffe5b4,stroke:#cc8400,color:#000
    classDef mem fill:#b8e7c8,stroke:#1b9e3e,color:#000
    classDef external fill:#fbb4d5,stroke:#a4133c,color:#000
    class APP_PY,CONFIG_SVC,INIT_DATA,INIT_PLAYLISTS,WAITRESS,DASH,WATCHDOG,API_SVC,DATA_SVC,PLOT_SVC python
    class CONFIG,STATS_DIR,PLAYLISTS,CACHE disk
    class DB,QUEUE mem
    class BROWSER,KOVAAKS_GAME,KOVAAKS_API external
```

---

## 2. Tech Stack Layers

What runs where. The Python side runs in your terminal; the JavaScript side runs in the browser. Dash bridges them.

```mermaid
flowchart TB
    subgraph SERVER [Python Process - Server Side]
        direction TB
        APPCODE[Your Application Code<br/>app.py, pages/, callbacks, services]
        DMC[Dash Mantine Components<br/>Python wrappers]
        DASH_LAYER[Dash<br/>layout + callback engine]
        FLASK[Flask<br/>WSGI app object app.server]
        WAITRESS_LAYER[Waitress<br/>multi-threaded WSGI server]
        STDLIB_DEPS[Pydantic, Watchdog, Requests,<br/>sortedcontainers, NumPy, Pandas, Plotly Python]
    end

    NETWORK[/HTTP over localhost/]

    subgraph BROWSER_SIDE [Browser - Client Side]
        direction TB
        HTML[Generated HTML page]
        REACT[React<br/>component tree + virtual DOM]
        MANTINE[Mantine<br/>CSS + React components]
        PLOTLY_JS[Plotly.js<br/>chart renderer]
        DASH_RENDERER[Dash Renderer<br/>callback round-trip glue]
    end

    APPCODE --> DMC
    DMC --> DASH_LAYER
    DASH_LAYER --> FLASK
    FLASK --> WAITRESS_LAYER
    APPCODE -.uses.-> STDLIB_DEPS
    WAITRESS_LAYER --> NETWORK
    NETWORK --> HTML
    HTML --> REACT
    REACT --> MANTINE
    REACT --> PLOTLY_JS
    REACT --> DASH_RENDERER
    DASH_RENDERER -.callback POST.-> NETWORK

    classDef python fill:#bde0fe,stroke:#0077b6,color:#000
    classDef js fill:#fde68a,stroke:#b45309,color:#000
    classDef net fill:#e9d5ff,stroke:#6b21a8,color:#000
    class APPCODE,DMC,DASH_LAYER,FLASK,WAITRESS_LAYER,STDLIB_DEPS python
    class HTML,REACT,MANTINE,PLOTLY_JS,DASH_RENDERER js
    class NETWORK net
```

---

## 3. CSV Ingestion Pipeline

How a `.csv` file becomes a row in the in-memory database. Two entry points (bulk at startup, live via watchdog), one converging code path.

```mermaid
flowchart TB
    subgraph SOURCES [Entry Points]
        STARTUP[app.py main<br/>app boot]
        KOVAAKS_WRITE([KovaaK's writes CSV])
    end

    BULK[initialize_kovaaks_data<br/>os.scandir stats_dir]
    OS_EVENT[OS filesystem event]
    WATCHDOG_HANDLER[NewFileHandler<br/>.on_created]

    SLEEP[time.sleep 1s<br/>wait for KovaaK's<br/>to finish writing]

    EXTRACT[extract_data_from_file<br/>parse filename + lines]
    LOADER[load_csv_file_into_database]

    subgraph PARSER_DETAIL [extract_data_from_file]
        direction TB
        P1[Parse datetime from filename]
        P2[Walk lines looking for:<br/>Score:, Sens Scale:,<br/>Horiz Sens:, Scenario:]
        P3[Find sub-CSV header,<br/>read next line for shots/hits]
        P4[Round horiz_sens to<br/>config decimal places]
        P5{All fields<br/>present?}
        RUNDATA[Return RunData]
        SKIP[Return None<br/>log warning]
        P1 --> P2 --> P3 --> P4 --> P5
        P5 -->|yes| RUNDATA
        P5 -->|no| SKIP
    end

    EXTRACT -.calls.-> PARSER_DETAIL

    subgraph DB_UPDATE [load_csv_file_into_database]
        direction TB
        D1{Scenario in db?}
        D2[Create scenario entry:<br/>scenario_stats +<br/>SortedList time_vs_runs +<br/>SortedDict sensitivities_vs_runs]
        D3[Update scenario_stats:<br/>number_of_runs, date_last_played, high_score]
        D4[Add to sensitivities_vs_runs<br/>at sensitivity_key]
        D5[Add to time_vs_runs]
        D6[Add to global run_database]
        D1 -->|no| D2
        D1 -->|yes| D3
        D3 --> D4
        D4 --> D5
        D2 --> D6
        D5 --> D6
    end

    LOADER -.calls.-> DB_UPDATE

    DB[(In-Memory Database<br/>kovaaks_database + run_database)]
    QUEUE_W[(message_queue)]
    RANK_REFRESH[rank_refresh_executor<br/>ThreadPoolExecutor max_workers=2]

    STARTUP --> BULK --> EXTRACT
    KOVAAKS_WRITE -.OS notifies.-> OS_EVENT
    OS_EVENT --> WATCHDOG_HANDLER
    WATCHDOG_HANDLER --> SLEEP --> EXTRACT
    EXTRACT --> LOADER
    LOADER --> DB
    WATCHDOG_HANDLER -.case 1/2/3.-> QUEUE_W
    WATCHDOG_HANDLER -.if new high score.-> RANK_REFRESH

    classDef python fill:#bde0fe,stroke:#0077b6,color:#000
    classDef mem fill:#b8e7c8,stroke:#1b9e3e,color:#000
    classDef external fill:#fbb4d5,stroke:#a4133c,color:#000
    classDef thread fill:#d1d5db,stroke:#374151,color:#000
    class BULK,WATCHDOG_HANDLER,EXTRACT,LOADER,STARTUP,SLEEP,OS_EVENT,P1,P2,P3,P4,P5,D1,D2,D3,D4,D5,D6 python
    class DB,QUEUE_W mem
    class KOVAAKS_WRITE,RUNDATA,SKIP external
    class RANK_REFRESH thread
```

---

## 4. In-Memory Database Shape

The four parallel sorted views of the same `RunData` objects. Each view is sorted by the dimension some UI question cares about.

```mermaid
flowchart TB
    subgraph GLOBAL [Global view]
        RUN_DB[(run_database<br/>SortedList sorted by datetime)]
        RUN_DB_USE[Aim Training Journey:<br/>walk chronologically]
        RUN_DB -.feeds.-> RUN_DB_USE
    end

    subgraph PER_SCEN [Per-scenario views inside kovaaks_database]
        direction TB
        STATS[scenario_stats<br/>ScenarioStats:<br/>date_last_played<br/>number_of_runs<br/>high_score]
        TIME_VR[time_vs_runs<br/>SortedList sorted by datetime]
        SENS_VR[sensitivities_vs_runs<br/>SortedDict sorted by numeric sens]
        SENS_INNER[Per sens: SortedList sorted by score]

        SENS_VR --> SENS_INNER

        STATS_USE[Scenario Stats panel:<br/>Last played, Runs, High score]
        TIME_USE[Score-vs-Time chart:<br/>filter by date, take top N]
        SENS_USE[Score-vs-Sensitivity chart:<br/>walk reverse for top N per sens]

        STATS -.feeds.-> STATS_USE
        TIME_VR -.feeds.-> TIME_USE
        SENS_INNER -.feeds.-> SENS_USE
    end

    subgraph PLAYLISTS_VIEW [Playlists]
        PLAYLIST_DB[(playlist_database<br/>dict name to PlaylistData)]
        PLAYLIST_USE[Playlist dropdowns,<br/>Rank overlays,<br/>Playlist Scenarios page]
        PLAYLIST_DB -.feeds.-> PLAYLIST_USE
    end

    RUN[Single RunData object<br/>datetime, score, scenario,<br/>horiz_sens, sens_scale, accuracy]

    RUN -.indexed by.-> RUN_DB
    RUN -.indexed by.-> TIME_VR
    RUN -.indexed by.-> SENS_INNER
    RUN -.aggregated into.-> STATS

    classDef mem fill:#b8e7c8,stroke:#1b9e3e,color:#000
    classDef python fill:#bde0fe,stroke:#0077b6,color:#000
    class RUN_DB,TIME_VR,SENS_VR,SENS_INNER,STATS,PLAYLIST_DB,RUN mem
    class RUN_DB_USE,STATS_USE,TIME_USE,SENS_USE,PLAYLIST_USE python
```

---

## 5. Rank Lookup Pipeline

`get_scenario_rank_info` end-to-end. Each step is best-effort and produces a stable `ScenarioRankInfo` for the UI, regardless of which paths succeed.

```mermaid
flowchart TB
    ENTRY[get_scenario_rank_info<br/>scenario_name, username, steam_id]

    NO_USER{username<br/>configured?}
    UNKNOWN_NO_USER[Return UNKNOWN<br/>error: not configured]

    RESOLVE[resolve_leaderboard_id]

    subgraph TIER [Three-tier leaderboard ID fallback]
        direction TB
        TIER_A{Permanent local<br/>mapping cache?}
        HYDRATE[hydrate from<br/>/user/scenario/total-play<br/>bulk metadata fill]
        TIER_B{In cache<br/>after hydrate?}
        SEARCH[search_scenario_exact<br/>/scenario/popular<br/>require exactly 1 exact match]
        FOUND[leaderboard_id]
        NOT_FOUND[None]

        TIER_A -->|hit| FOUND
        TIER_A -->|miss| HYDRATE
        HYDRATE --> TIER_B
        TIER_B -->|hit| FOUND
        TIER_B -->|miss| SEARCH
        SEARCH -->|exactly 1| FOUND
        SEARCH -->|0 or many| NOT_FOUND
    end

    RANK_CACHE{Rank cache fresh?<br/>TTL 168h}
    FETCH_RANK[fetch_scenario_rank<br/>/leaderboard/scores/global<br/>+ _find_matching_player]
    SAVE_RANK[save_scenario_rank<br/>strips total_players + percentile]

    WITH_TOTAL[_with_leaderboard_total<br/>best-effort enrichment]
    TOTAL_CACHE{Total cache fresh?<br/>TTL 168h}
    FETCH_TOTAL[fetch_leaderboard_total<br/>same endpoint, max=1]
    WITH_PCT[_with_percentile<br/>midpoint formula]
    WITH_WARN[_with_derived_rank_warning<br/>Steam ID mismatch check]

    RESULT[ScenarioRankInfo<br/>status, rank, total_players,<br/>percentile, warning_message]

    ENTRY --> NO_USER
    NO_USER -->|no| UNKNOWN_NO_USER
    NO_USER -->|yes| RESOLVE
    RESOLVE --> TIER_A
    NOT_FOUND -.UNKNOWN result.-> RESULT
    FOUND --> RANK_CACHE
    RANK_CACHE -->|hit| WITH_TOTAL
    RANK_CACHE -->|miss| FETCH_RANK
    FETCH_RANK --> SAVE_RANK --> WITH_TOTAL
    WITH_TOTAL --> TOTAL_CACHE
    TOTAL_CACHE -->|hit| WITH_PCT
    TOTAL_CACHE -->|miss| FETCH_TOTAL --> WITH_PCT
    WITH_PCT --> WITH_WARN --> RESULT

    UNKNOWN_NO_USER -.via.-> RESULT

    classDef python fill:#bde0fe,stroke:#0077b6,color:#000
    classDef decision fill:#fef3c7,stroke:#b45309,color:#000
    classDef result fill:#b8e7c8,stroke:#1b9e3e,color:#000
    class ENTRY,RESOLVE,HYDRATE,SEARCH,FETCH_RANK,SAVE_RANK,WITH_TOTAL,FETCH_TOTAL,WITH_PCT,WITH_WARN python
    class NO_USER,TIER_A,TIER_B,RANK_CACHE,TOTAL_CACHE decision
    class FOUND,NOT_FOUND,RESULT,UNKNOWN_NO_USER result
```

### The supporting HTTP layer

Every KovaaK's request flows through one wrapper that handles timeouts and 429 retries.

```mermaid
flowchart LR
    CALLER[Any rank pipeline function]
    WRAPPER[_get_with_retry<br/>10s timeout default]
    GET1[requests.get attempt 1]
    CHECK{HTTP 429?}
    SLEEP_R[time.sleep Retry-After<br/>or 0.5s, capped 5s]
    GET2[requests.get attempt 2]
    OK[Response object]
    RAISE[raise_for_status<br/>propagates error]

    CALLER --> WRAPPER --> GET1 --> CHECK
    CHECK -->|no| OK
    CHECK -->|yes| SLEEP_R --> GET2
    GET2 -->|2xx| OK
    GET2 -->|error| RAISE

    classDef python fill:#bde0fe,stroke:#0077b6,color:#000
    classDef decision fill:#fef3c7,stroke:#b45309,color:#000
    class CALLER,WRAPPER,GET1,SLEEP_R,GET2,RAISE python
    class CHECK,OK decision
```

---

## 6. Concurrency / Thread Model

The app is multi-threaded. This diagram shows every thread that exists at runtime and what shared state they touch.

```mermaid
flowchart TB
    subgraph MAIN [Main Thread]
        BOOT[Boot:<br/>load config,<br/>ingest CSVs,<br/>load playlists,<br/>start observer,<br/>start Waitress]
    end

    subgraph WAITRESS_THREADS [Waitress Worker Threads default 4]
        DASH_REQ1[Dash callback thread A]
        DASH_REQ2[Dash callback thread B]
        DASH_REQ_N[...]
    end

    subgraph WD_THREAD [Watchdog Observer Thread]
        WD_LOOP[on_created:<br/>parse CSV,<br/>update DB,<br/>append queue]
    end

    subgraph RANK_POOL [rank_refresh_executor<br/>ThreadPoolExecutor max=2]
        RR1[refresh_scenario_rank A]
        RR2[refresh_scenario_rank B]
    end

    subgraph PL_POOL [Playlist scenarios pool<br/>ThreadPoolExecutor max=4]
        PR1[get_scenario_rank_info A]
        PR2[get_scenario_rank_info B]
        PR3[get_scenario_rank_info C]
        PR4[get_scenario_rank_info D]
    end

    subgraph SHARED [Shared State protected]
        DB_SHARED[(In-memory DB<br/>SortedList/SortedDict<br/>append-safe enough)]
        QUEUE_SHARED[(message_queue<br/>collections.deque<br/>thread-safe enough)]
        CACHE_SHARED[(cache/ JSON files)]
        LOCK[_CACHE_IO_LOCK<br/>threading.RLock]
        CACHE_SHARED -.guards.-> LOCK
    end

    BOOT -.starts.-> WD_LOOP
    BOOT -.starts.-> DASH_REQ1
    WD_LOOP -->|writes| DB_SHARED
    WD_LOOP -->|appends| QUEUE_SHARED
    WD_LOOP -.submits.-> RR1
    WD_LOOP -.submits.-> RR2

    DASH_REQ1 -->|reads| DB_SHARED
    DASH_REQ1 -->|drains| QUEUE_SHARED
    DASH_REQ1 -.submits playlist load.-> PR1
    DASH_REQ1 -.submits playlist load.-> PR2
    DASH_REQ1 -.submits playlist load.-> PR3
    DASH_REQ1 -.submits playlist load.-> PR4

    RR1 -->|R/W| CACHE_SHARED
    RR2 -->|R/W| CACHE_SHARED
    PR1 -->|R/W| CACHE_SHARED
    PR2 -->|R/W| CACHE_SHARED
    PR3 -->|R/W| CACHE_SHARED
    PR4 -->|R/W| CACHE_SHARED
    DASH_REQ1 -->|R/W| CACHE_SHARED
    DASH_REQ2 -->|R/W| CACHE_SHARED

    classDef thread fill:#d1d5db,stroke:#374151,color:#000
    classDef python fill:#bde0fe,stroke:#0077b6,color:#000
    classDef mem fill:#b8e7c8,stroke:#1b9e3e,color:#000
    classDef disk fill:#ffe5b4,stroke:#cc8400,color:#000
    classDef lock fill:#fde68a,stroke:#92400e,color:#000
    class BOOT,WD_LOOP,DASH_REQ1,DASH_REQ2,DASH_REQ_N,RR1,RR2,PR1,PR2,PR3,PR4 python
    class DB_SHARED,QUEUE_SHARED mem
    class CACHE_SHARED disk
    class LOCK lock
```

---

## 7. Cache Layout on Disk

What lives under `cache/`. All caches are JSON; all writes are atomic (temp file + `os.replace`); all reads tolerate missing/malformed files.

```mermaid
flowchart TB
    ROOT[(cache/)]

    subgraph SCEN [Permanent leaderboard mapping]
        SCEN_DIR[(scenario_leaderboards/)]
        SCEN_FILE[(scenario_name_to_leaderboard_id.json<br/>name to id, source, fetched_at)]
        SCEN_DIR --> SCEN_FILE
    end

    subgraph BENCH [Benchmarks]
        BENCH_DIR[(benchmarks/)]
        BENCH_FILE[(<benchmark_id>.json<br/>raw benchmark progress responses)]
        BENCH_DIR --> BENCH_FILE
    end

    subgraph TP [Total play metadata]
        TP_DIR[(user_scenario_total_play/)]
        TP_MERGED[(<safe_username>.json<br/>merged paginated view)]
        TP_PAGE_DIR[(<safe_username>/)]
        TP_PAGE[(page_N.json<br/>raw API pages for completeness proof)]
        TP_DIR --> TP_MERGED
        TP_DIR --> TP_PAGE_DIR
        TP_PAGE_DIR --> TP_PAGE
    end

    subgraph LB [Leaderboard data]
        LB_DIR[(leaderboard/)]
        UR_DIR[(user_rank/<safe_username>/)]
        UR_FILE[(<leaderboard_id>.json<br/>per-user rank<br/>TTL: 168h<br/>invalidated on new high score)]
        TOTALS_DIR[(totals/)]
        TOTALS_FILE[(<leaderboard_id>.json<br/>ranked-player count<br/>TTL: 168h)]
        LB_DIR --> UR_DIR
        UR_DIR --> UR_FILE
        LB_DIR --> TOTALS_DIR
        TOTALS_DIR --> TOTALS_FILE
    end

    ROOT --> SCEN_DIR
    ROOT --> BENCH_DIR
    ROOT --> TP_DIR
    ROOT --> LB_DIR

    classDef disk fill:#ffe5b4,stroke:#cc8400,color:#000
    class ROOT,SCEN_DIR,SCEN_FILE,BENCH_DIR,BENCH_FILE,TP_DIR,TP_MERGED,TP_PAGE_DIR,TP_PAGE,LB_DIR,UR_DIR,UR_FILE,TOTALS_DIR,TOTALS_FILE disk
```

### Cache invalidation summary

| Cache                                                        | TTL                                        | Invalidated by                    |
| ------------------------------------------------------------ | ------------------------------------------ | --------------------------------- |
| `scenario_leaderboards/scenario_name_to_leaderboard_id.json` | None (permanent)                           | Never — only upserted             |
| `benchmarks/<id>.json`                                       | None (explicit `use_cache=True`)           | Manual deletion                   |
| `user_scenario_total_play/<user>.json`                       | 24h (`scenario_metadata_cache_ttl_hours`)  | TTL expiry                        |
| `leaderboard/user_rank/<user>/<id>.json`                     | 168h (`scenario_rank_cache_ttl_hours`)     | New high score (watchdog refresh) |
| `leaderboard/totals/<id>.json`                               | 168h (`leaderboard_total_cache_ttl_hours`) | TTL expiry                        |

---

## Things not yet shown (deliberately blank for now)

These will be filled in as we cover them in the analysis. Treat them as placeholders so we know what's intentionally absent.

- **Dash callback graph for the Home page** — how the ~10 callbacks chain together and which `dcc.Store` / `dcc.Interval` triggers each one. Sequence-style diagram.
- **Playlist Scenarios page architecture** — how the AG Grid table, the URL routing, the route-bound `dcc.Store`, and the parallel rank lookups coordinate.
- **Notification flow** — how `dash_logger` and the `NotificationContainer` produce toast messages, both from log records and from explicit callback returns.
- **Light/dark theme propagation** — the clientside callback, the cached-plot store, and the Plotly template swap.
- **Aim Training Journey computation** — the per-playlist running averages, checkpoints, and the journey plot generation.

---

## How to iterate this document

When a new topic is covered in `analysis.md` and changes how we should picture the system:

1. **Add or extend the relevant diagram.** Each section above is a Mermaid block — edit it directly.
2. **Keep the color/style conventions** so cross-diagram references stay consistent.
3. **Move items out of "Things not yet shown"** as their diagrams get added.
4. **When in doubt, prefer adding a small new diagram** over making one diagram do too much. The high-level overview at the top is the integration point; everything else can be focused.
