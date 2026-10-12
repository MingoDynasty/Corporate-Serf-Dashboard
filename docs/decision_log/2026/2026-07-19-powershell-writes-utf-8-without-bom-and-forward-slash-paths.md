# 2026-07-19: PowerShell Writes UTF-8 Without BOM And Forward-Slash Paths

Status: Accepted

Decision: every machine-readable file written by the install/launch scripts
(`config.toml`, `install.json`, the `launch.ps1` bootstrap) is written UTF-8
**without** a byte-order mark, via `System.Text.UTF8Encoding($false)`, and every
path inside them uses forward slashes. The scripts target Windows PowerShell
5.1 — the shell the one-liner actually lands in on a stock Windows 11 machine.

Why: 5.1's `-Encoding UTF8` emits a BOM, and this repo's Python 3.14 `tomllib`
rejects both a BOM and raw `\` in TOML basic strings. Either alone yields a
config the app can never parse, which the never-touch-an-existing-config rule
would then make permanent. Both halves were verified empirically against this
repo's interpreter rather than taken from documentation.

This is a contract, not a style preference: do not "modernize" these writes to
`Set-Content -Encoding UTF8`, and do not let Windows-native backslashes reach a
generated TOML file.
