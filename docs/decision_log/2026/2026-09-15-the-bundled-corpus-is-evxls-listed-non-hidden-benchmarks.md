# 2026-09-15: The Bundled Corpus Is Evxl's Listed, Non-Hidden Benchmarks

Status: Accepted

The app ships a benchmark only while Evxl lists it and does not mark it
hidden. When Evxl delists a benchmark, its file leaves the app at the next
refresh, even if KovaaK's still serves it. A benchmark Evxl marks hidden
stays out until Evxl unhides it. Refreshes apply both rules without asking
the maintainer again.

**The rule.** `resources/benchmarks/` holds the importable sharecodes that
the committed Evxl snapshot (`resources/evxl/benchmarks.json`) lists under a
benchmark without `hidden: true`. The maintainer made both calls for the
2026-09-14 refresh and ruled them standing rules on 2026-09-15
([PR #289 thread](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/289#discussion_r4013683306)):

- **Delisting removes.** A bundled file whose sharecode the refreshed
  snapshot no longer lists is deleted in the refresh PR, even when KovaaK's
  still serves that benchmark ID unchanged. First applied to
  `Trial of Lords S2.json` (Black Dawn / Trials V2, benchmark 2285), which
  still matched KovaaK's exactly when Evxl dropped Black Dawn.
- **Hidden waits.** A sharecode under a hidden benchmark is not imported
  until Evxl unhides it. First applied to AIMCORE Benchmarks S1 and The Good
  Benchmark. Voltaic S5.5 Advanced had been kept out on the same grounds
  since the 2026-07-11 curation, and was imported once Evxl unhid it. A
  bundled benchmark that Evxl later hides is not covered by this ruling.

**The importer enforces neither rule.** `load_evxl_data` does not filter
`hidden`, and a sweep leaves the file for a removed sharecode in place,
logging that the manifest contains a removed sharecode. The refresh author
applies both: generate with `--only` over the listed, non-hidden codes, and
delete delisted files in the same PR.

**Consequences.** Corpus membership can be checked against the committed
snapshot alone, so a reviewer can verify a refresh PR mechanically. A user
who had a delisted benchmark shown stops seeing it after the update, with no
migration.
