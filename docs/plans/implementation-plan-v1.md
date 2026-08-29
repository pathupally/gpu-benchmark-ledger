# Benchmark Ledger — implementation plan v1

Status: approved for implementation from `ideas/01-benchmark-basis-and-vintages.md`  
Created: 2026-08-29  
Scope: standalone, standard-library Python project with a generated static dashboard

## Product decision

Build an auditable measurement product, not a synthetic history. The repository has one matched Ornn/Silicon Data cross-section and published Silicon Data methodology breaks, but it does not have a shared daily history or participant cash-price panel. The first release will therefore:

- calculate current log and percentage basis for explicitly mapped benchmark cells;
- preserve source hashes, methodology versions, dimension coverage, and restatement status on every observation;
- propagate quantified, non-restated break ranges into a sensitivity band;
- expose insufficient-data states for correlation, rolling hedge ratios, and hedge effectiveness;
- distinguish decision-eligible mapped comparisons from approximate diagnostic comparisons.

## Users and jobs

1. A hedger compares the listed settlement benchmark with a named rental exposure.
2. A risk desk sees which specification gaps remain and how large published break uncertainty is.
3. A researcher can reproduce the exact calculation from versioned inputs and source hashes.

## Deliverables

### 1. Versioned data contract

- `schemas/benchmark-observation.schema.json` defines the portable observation shape.
- `data/source/observations.jsonl` stores the 2026-08-29 matched cross-section as immutable, source-linked records.
- `data/source/benchmark-pairs.json` records mappings, known mismatches, confidence grades, and analysis eligibility.
- `data/source/methodology-ledger.json` records vendor methodology vintages and dated break events.
- `data/source/source-registry.json` identifies the archived parent-repository evidence and its SHA-256 digest.

Validation combines structural checks with semantic invariants that JSON Schema alone does not make convenient: unique IDs, valid dates, positive prices, recognized source hashes, complete pairs, and confidence/eligibility consistency.

### 2. Reproducible analysis pipeline

The `benchmark-ledger build` command will:

1. validate all source records;
2. join the declared benchmark pairs only—never infer a match from a similar GPU name;
3. calculate `log(Ornn) - log(Silicon Data)` and `Ornn / Silicon Data - 1`;
4. apply each quantified, non-restated Silicon Data break as a low/high counterfactual path;
5. generate the coverage matrix and methodology timeline;
6. gate correlation and rolling hedge ratios on at least 20 shared daily returns;
7. write deterministic JSON, CSV, and browser-ready artifacts under `data/generated/` and `web/`.

The sensitivity adjustment reverses a published break impact `p` from the observed Silicon Data level. In log-basis terms the adjusted value is `raw_basis + log(1 + p)`. Published endpoints are carried separately; no midpoint is invented.

### 3. Decision dashboard

Use an editorial market-surveillance aesthetic: warm paper, dense ink, ruled tables, and a restrained signal-orange accent. The interface will include:

- a basis tape comparing all GPU cells and their sensitivity bands;
- keyboard-operable GPU selection and a full specification/mismatch readout;
- a coverage matrix that treats unknown as unknown;
- a methodology and break ledger with restatement and quantified-impact filters;
- clear unavailable states for correlation and hedge ratio, including the observations required to unlock them;
- responsive table-to-record layouts, visible focus states, and reduced-motion support.

No frontend build chain is required. Generated data is loaded from a local JavaScript payload, so the dashboard works from a simple static server and remains inspectable.

### 4. Research note

`docs/paper/one-gpu-two-settlement-prices.md` will state the finding, calculation, specification limits, sensitivity logic, stop rules, and exact conditions required before making a hedge-effectiveness claim.

## Acceptance criteria

- `python -m unittest discover -s tests -v` passes without third-party dependencies.
- `python -m benchmark_ledger build` is deterministic and fails non-zero on invalid inputs.
- Generated basis agrees with the documented cross-section to rounding: H100 +10.6%, A100 -24.8%, B200 +7.7%, H200 +38.2%.
- Quantified non-restated H100 and B200 breaks widen the displayed sensitivity range; restated events do not.
- Approximate cells remain visible but are marked ineligible for decision use.
- The dashboard has no false correlation or hedge-ratio number.
- `README.md` contains one-command build, test, and serve instructions.

## Out of scope for v1

- ingesting live vendor endpoints;
- reconstructing unpublished vendor histories;
- estimating hedge effectiveness without participant-level cash prices;
- fitting the hierarchical factor model before adequate panel depth exists;
- investment, trading, or hedging recommendations.

## Revision policy

This file is immutable planning history. Implementation discoveries and deviations will be recorded in a new `implementation-plan-v2.md`, leaving this plan intact.
