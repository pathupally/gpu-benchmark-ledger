# Benchmark Ledger

Benchmark Ledger is a standalone, vintage-preserving comparison of Ornn and Silicon Data GPU price benchmarks. It turns the first research idea in the parent `compute_futures` repository into a reproducible data contract, analysis pipeline, methodology ledger, decision dashboard, and short research note.

The current release does one thing carefully: it reproduces the 2026-08-29 matched cross-section without inventing a shared time series that the archive does not contain.

## Result

| GPU | Silicon Data | Ornn | Ornn vs. SD | Match | Decision use |
| --- | ---: | ---: | ---: | --- | --- |
| H100 | $2.65 | $2.93 | +10.6% | Mapped / C | Eligible with caveats |
| A100 | $1.61 | $1.21 | −24.8% | Approximate / D | Diagnostic only |
| B200 | $5.58 | $6.01 | +7.7% | Mapped / C | Eligible with caveats |
| H200 | $3.25 | $4.49 | +38.2% | Approximate / D | Diagnostic only |

The A100 sign reversal rules out a single constant vendor markup as a complete explanation. It does not establish arbitrage or hedge effectiveness: form factor, memory, tier, rental mix, and settlement terms are not fully aligned.

## Run it

Requirements: Python 3.11 or later. Runtime and tests use only the standard library.

```sh
make all
make serve
```

Then open `http://127.0.0.1:8000/web/`. `make all` validates the input contract, rebuilds every derived artifact, and runs the test suite.

Individual commands:

```sh
make validate
make build
make test
PYTHONPATH=src python3 -m benchmark_ledger serve --port 8080
```

An editable install also exposes the `benchmark-ledger` command:

```sh
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/benchmark-ledger build
```

## What is versioned

- `schemas/benchmark-observation.schema.json` — portable observation contract.
- `data/source/observations.jsonl` — immutable matched-date records.
- `data/source/benchmark-pairs.json` — declared mappings and coverage assessments.
- `data/source/methodology-ledger.json` — methodology vintages and break events for both vendors.
- `data/source/source-registry.json` — retrieval dates, upstream locations, archive paths, and SHA-256 digests.
- `data/generated/` — deterministic validation, basis, and dashboard artifacts.
- `web/` — accessible static dashboard with no frontend build dependency.
- `docs/paper/one-gpu-two-settlement-prices.md` — research note.
- `docs/plans/` — immutable v1 plan and post-implementation v2 revision.

The frozen inputs are self-contained research records. Their hashes identify the evidence archived in the parent repository; this subrepo never reaches into the parent at runtime and never fetches a live endpoint.

## Calculation

For a declared GPU/date pair:

```text
raw log basis = log(Ornn) - log(Silicon Data)
raw percentage basis = (Ornn / Silicon Data - 1) × 100
```

For a published, non-restated Silicon Data break impact `p`, the counterfactual log basis is:

```text
adjusted log basis = raw log basis + log(1 + p)
```

Low and high endpoints are propagated independently. The pipeline never substitutes an unreported midpoint. Restated events stay in the ledger but are excluded from the non-restated sensitivity adjustment. Unquantified jumps remain visible as unbounded risk.

## Honest unavailable states

Correlation and rolling hedge ratios require at least 20 shared daily returns, or 21 matched levels. The archive has one shared cross-section. The dashboard therefore exposes the data gate and returns no numeric estimate. Hedge effectiveness remains unavailable until a participant cash-price panel exists.

## Repository boundary

This directory has its own `.git` history and can be moved or published separately from the parent research repository. It contains no credentials, subscription-gated payloads, or network collection code.

This is measurement infrastructure, not investment, trading, or hedging advice.

