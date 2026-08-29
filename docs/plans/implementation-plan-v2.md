# Benchmark Ledger — implementation plan v2

Status: implemented and verified  
Created: 2026-08-29  
Supersedes: no files; this is a revision record for `implementation-plan-v1.md`

## What implementation clarified

The v1 scope remains intact. Three details required more explicit treatment during implementation:

1. **An unquantified break cannot become a numerical band.** The 2025-03-01 Silicon Data provider-coverage jump is preserved as an unbounded flag. H100 therefore has a quantified 2026 sensitivity range and an earlier unquantified risk at the same time.
2. **Breaks must respect series inception.** The global 2025 jump predates the B200 and H200 series. The pipeline derives inception from new-index ledger events and does not attach pre-inception breaks to a benchmark that did not yet exist.
3. **A restated event remains auditable without entering the non-restated band.** The 2025-12-04 A100/H100 methodology change is visible in the event ledger and observation methodology version, but its published impact is excluded from the current non-restated sensitivity path.

## Implemented architecture

```text
versioned JSON/JSONL inputs
          ↓
schema + semantic validation
          ↓
declared pair join (no name inference)
          ↓
log basis + published break endpoints
          ↓
deterministic JSON / CSV / browser payload
          ↓
static decision dashboard + research note
```

The nested repository has no runtime dependencies. `PYTHONPATH=src python3 -m benchmark_ledger` exposes `validate`, `build`, `serve`, and narrowly scoped `clean` commands.

## Acceptance status

- [x] Eight observations conform to the versioned schema.
- [x] Six source records carry retrieval dates and SHA-256 digests.
- [x] Four declared benchmark pairs reproduce the documented cross-section to one decimal place.
- [x] H100 and B200 non-restated break endpoints are propagated without midpoints.
- [x] Restated and unquantified events retain distinct machine-readable states.
- [x] Approximate A100 and H200 cells are excluded from decision use.
- [x] Correlation, rolling hedge ratio, and hedge effectiveness have explicit unavailable gates and no numeric placeholder.
- [x] The dashboard supports keyboard GPU tabs, visible focus, responsive coverage records, and reduced motion.
- [x] Generated artifacts are deterministic across repeated builds.
- [x] The standard-library test suite passes.

## Next revision triggers

Create `implementation-plan-v3.md`—do not edit v1 or v2—when one of these conditions is met:

- a second Silicon Data historical observation becomes independently reproducible;
- either vendor publishes a new methodology or break event;
- exact memory, form-factor, tier, region, or contract fields change a pair's confidence grade;
- 21 shared daily levels unlock the first rolling correlation and hedge-ratio estimate;
- a participant cash-price panel makes an out-of-sample hedge test possible.

Until then, collection and provenance maintenance are more valuable than adding model complexity.

