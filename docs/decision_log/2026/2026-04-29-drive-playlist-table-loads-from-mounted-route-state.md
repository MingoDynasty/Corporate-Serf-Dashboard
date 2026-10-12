# 2026-04-29: Drive Playlist Table Loads From Mounted Route State

Status: Accepted

Decision: Playlist scenario table loads should be driven by state created in the mounted `/playlists/<playlist_code>` layout, not directly by selector changes or URL-change callbacks.

Why: When the playlist selector changes the route, Dash Pages can briefly have the old page instance responding to the URL update before the new route layout finishes mounting. If the expensive table load listens directly to that navigation event, one user selection can trigger duplicate cache/API loads.

Consequences: Keep the selector callback navigation-only. The route layout should publish the resolved playlist code through a lightweight mounted component, currently `dcc.Store(id="playlist-scenarios-code")`, and the table-loading callback should use that mounted state as its trigger.
