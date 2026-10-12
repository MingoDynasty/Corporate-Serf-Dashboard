# 2026-07-09: Load Configuration Lazily At Application Startup

Status: Accepted

Decision: Configuration is loaded and cached through `get_config()` instead of
at module import. `main()` owns the initial load and translates expected file,
decode, TOML, and validation failures into the existing concise startup error
before loading playlists or initializing runtime services. Other modules resolve
the cached configuration only inside function bodies.

Why: Import-time loading forced pytest to overwrite the real repo-root
`config.toml`, keeping its backup only in process memory. Abnormal termination
could permanently replace a user's configuration, and concurrent test sessions
could corrupt each other's backup/restore chain. A lazy production accessor makes
modules import-safe and gives tests an in-process seam without adding a test-only
environment-variable override.

Consequences: Tests monkeypatch the config loader and clear the accessor cache;
they never modify the real `config.toml`. `get_config()` propagates load errors,
while the executable startup boundary alone prints the user-facing message and
exits. Playlist loading happens in `main()` after configuration validation so a
bad config still produces exactly one clean error with no prior warning output.
