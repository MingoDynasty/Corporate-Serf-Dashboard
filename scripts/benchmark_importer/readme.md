# Playlist Generator

Generates the playlist in `generated`

## General Flow

1. Read Evxl `benchmarks.json` file
2. Each playlist code found,
    1. Query KovaaK's API for playlist data
    2. Query KovaaK's API for benchmarks data
3. Merge all this data and store into `generated`

## Evxl API

https://api.evxl.app/documentation - Fastify documentation
https://evxl.app/data/benchmarks - Evxl benchmarks data
