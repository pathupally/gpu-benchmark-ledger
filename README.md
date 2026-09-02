# Compute Benchmark Ledger

[![ci](https://github.com/pathupally/gpu-benchmark-ledger/actions/workflows/ci.yml/badge.svg)](https://github.com/pathupally/gpu-benchmark-ledger/actions/workflows/ci.yml)

A vintage-aware measurement system for deciding whether two compute-price
benchmarks are economically comparable before they are used in settlement or
tracking analysis.

**Read the note:**
[One GPU, Two Settlement Prices](docs/paper/one-gpu-two-settlement-prices.md).
**Browse the data:** an interactive dashboard ships in `web/`; `make serve`
opens it locally.

The current release reproduces one cross-section, dated 2026-08-29. It does not
invent a time series, label benchmark disagreement as arbitrage, or report an
underpowered hedge statistic.

## Current evidence

| GPU | Silicon Data | Ornn | Ornn vs. SD | Match | Permitted use |
| --- | ---: | ---: | ---: | --- | --- |
| H100 | $2.65 | $2.87 | +8.3% | Mapped / C | Eligible with caveats |
| A100 | $1.61 | $1.03 | -36.0% | Approximate / D | Diagnostic only |
| B200 | $5.58 | $6.06 | +8.6% | Mapped / C | Eligible with caveats |
| H200 | $3.25 | $4.44 | +36.6% | Approximate / D | Diagnostic only |

H100 and B200 align on model, date, unit, and broad rental market, but still
carry specification uncertainty. A100 and H200 omit material dimensions and
cannot become decision-eligible. These are benchmark differences on one date,
not persistent signals.

## What the package enforces

- Every observation names its methodology vintage, source, locator, dimensions,
  precision, and restatement status.
- Approximate mappings cannot become decision-eligible.
- Published break ranges retain both endpoints; unquantified breaks remain
  unbounded and restated events are not silently reapplied.
- The strict basis monitor requires the same date, unit, statistic, GPU, tier,
  and rental type, with no unknown matching values.
- Persistence and mean-reversion claims are withheld until 120 strictly matched
  daily observations exist.
- Cross-benchmark tracking effectiveness is withheld until 61 matched levels
  exist. Its 20-return coefficient is lagged before out-of-sample application.

The tracking estimand is variance reduction when using Ornn returns to track
Silicon Data returns. It is not a futures hedge and not hedge effectiveness for
a compute buyer or provider.

## Reproduce

Python 3.11 or later is required. Runtime and tests use only the standard
library and make no network requests.

```sh
make all

PYTHONPATH=src python3 -m benchmark_ledger validate
PYTHONPATH=src python3 -m benchmark_ledger build
PYTHONPATH=src python3 -m benchmark_ledger basis
PYTHONPATH=src python3 -m benchmark_ledger hedge
```

The equivalent installed commands are `benchmark-ledger validate`, `build`,
`basis`, and `hedge`. Unavailable analyses return structured `status`, `reason`,
`observed_count`, and `required_count` fields without placeholder estimates.

### Dashboard

```sh
make serve
```

Builds the artifacts and serves the dashboard at
`http://127.0.0.1:8000/web/`.

`web/` presents the same generated records the CLI emits: the basis
cross-section, matched-observation coverage against each withholding gate, and
the methodology break ledger. There is no build step, no framework, and no
network call at any point -- `make build` writes `web/data.generated.js`, and
the page reads that single global. `tests/test_web.py` holds the page to a
contract: every asset it references resolves locally, the generated data loads
before the application script, DOM ids are unique, and the keyboard, focus,
reduced-motion, and responsive behaviours are present.

## Versioned research contract

- `schemas/benchmark-observation.schema.json` defines normalized observations.
- `data/source/observations.jsonl` contains the minimal derived records.
- `data/source/benchmark-pairs.json` declares mappings and decision eligibility.
- `data/source/methodology-ledger.json` preserves methodologies and break events.
- `data/source/source-registry.json` records upstream locations and provenance
  fingerprints without redistributing raw captures.
- `data/generated/` contains deterministic basis, gate, and tracking artifacts.
- `docs/paper/one-gpu-two-settlement-prices.md` is the short research note.

Provenance fingerprints identify private source captures. Because those raw
artifacts are not redistributed, the fingerprints are provenance evidence, not
independently verifiable integrity checks. See `DATA_NOTICE.md`.

## Scope

This repository contains normalized derived records, source metadata, analysis
code, tests, and generated results. It contains no credentials, copied vendor
articles, raw API payloads, or subscription-gated captures.

Author: Adrian Mathew, Purdue University.

Software is MIT licensed. Upstream data and trademarks remain the property of
their respective publishers. This is research infrastructure, not investment,
trading, or hedging advice.
