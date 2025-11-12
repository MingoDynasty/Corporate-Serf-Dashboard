# Playlist Cache Generator

Generates the cache in `resources/playlists/cache`

## General Flow

1. Read Evxl `benchmarks.json` file
2. Each playlist code found,
    1. Query KovaaK's API for playlist data
    2. Query KovaaK's API for benchmarks data
3. Merge all this data and store into `resources/playlists/cache`
