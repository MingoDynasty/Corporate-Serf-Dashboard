# 2026-04-27: Use The Midpoint Percentile Formula

Status: Accepted

Decision: Derive percentile with:

```python
percentile = ((total_players - rank + 0.5) / total_players) * 100
```

Why: This matches the KovaaK's-style percentile behavior we agreed to use.

Consequences: Percentile is display-only metadata derived when rank info is returned. It is not stored in rank cache. No tiny-leaderboard special casing is planned, so `rank 1 of 1` displays `50.00%`.
