# One GPU, Two Settlement Prices

## A matched-date audit of compute benchmark basis

### Abstract

Cash-settled compute contracts can name the same GPU family while settling to materially different benchmark values. On 2026-08-29, Ornn was 8.3% above Silicon Data for H100, 8.6% above for B200, and 36.6% above for H200, but 36.0% below for A100. The sign reversal rejects a single constant vendor markup as a complete explanation. It does not prove that the benchmarks measure distinct tradable markets: the public record leaves important deliverable characteristics unknown. This note introduces a vintage ledger that keeps each value attached to its source hash, methodology version, specification coverage, match class, restatement status, and published break range.

## 1. The object being measured

For GPU/specification cell `g` and date `t`, the observed vendor basis is defined only after declaring the mapping:

```text
B[g,t] = log(I_Ornn[g,t]) - log(I_SD[g,t])
```

The percentage figures below use `I_Ornn / I_SD - 1`, which is easier to read but preserves the same sign. Positive values mean Ornn is above Silicon Data.

| GPU | Silicon Data | Ornn | Log basis | Percentage basis | Classification |
| --- | ---: | ---: | ---: | ---: | --- |
| H100 | 2.65 | 2.87 | 0.0798 | +8.3% | Mapped, grade C |
| A100 | 1.61 | 1.03 | −0.4467 | −36.0% | Approximate, grade D |
| B200 | 5.58 | 6.06 | 0.0825 | +8.6% | Mapped, grade C |
| H200 | 3.25 | 4.44 | 0.3120 | +36.6% | Approximate, grade D |

These are benchmark disagreements, not executable spreads. The instruments are cash-settled and do not share a deliverable that forces convergence.

## 2. Why the match grades matter

All four cells align on date, GPU family, and USD per GPU-hour. They do not align on every contract characteristic.

- Ornn identifies H100 SXM and A100 SXM4; the captured Silicon Data values do not disclose form factor.
- A100 memory capacity is not disclosed in either archived observation. A 40GB/80GB mix can matter.
- Silicon Data identifies H100, A100, and B200 as neocloud series; the Ornn observations do not publish a comparable tier field.
- Ornn's archived methodology describes on-demand transactions. The Silicon Data records represent a blended rental definition.
- Region and contributor coverage are not disclosed at the observation level.
- The captured Silicon Data H200 record omits both tier and ticker.

H100 and B200 are retained as mapped, grade-C cells because their named model, date, unit, and broad rental market align. A100 and H200 remain visible because their differences are diagnostically important, but their missing characteristics make them unsuitable for decision use.

## 3. Methodology breaks are part of the price

Silicon Data's archived break register contains quantified and unquantified discontinuities. For a published, non-restated impact `p`, the ledger reverses the break from the Silicon Data side:

```text
adjusted log basis = raw log basis + log(1 + p)
```

The two endpoints of each published range are carried separately.

| GPU | Raw basis | Break-adjusted range | Applied event | Bound status |
| --- | ---: | ---: | --- | --- |
| H100 | +8.3% | +0.7% to +5.1% | 2026-04-06 provider change, −7% to −3% | Partial; a 2025 coverage jump is unquantified |
| B200 | +8.6% | +2.1% to +8.6% | 2026-07-15 provider change, −6% to 0% | Bounded by published quantified events |
| A100 | −36.0% | No numerical range | 2025 coverage jump unquantified | Unbounded |
| H200 | +36.6% | No applicable quantified break | Index history begins after the 2025 jump | No adjustment |

The 2025-12-04 methodology change is preserved in the ledger but excluded from this non-restated sensitivity calculation because Silicon Data marked it restated to the series start. Its opposite impacts—A100 up 35% to 40%, H100 down 6% to 4%—still demonstrate why a vintage must be stored at the ticker level.

## 4. What cannot yet be estimated

The archive has one shared Ornn/Silicon Data cross-section, not a common daily panel. The release requires 61 matched levels before applying a 20-return rolling coefficient out of sample, so it reports no tracking statistic. A participant cash-price panel is also absent. It would be incorrect to label cross-benchmark tracking as hedge effectiveness against a user's realized rental exposure.

The next valid empirical step is append-only collection of both vendors under frozen mapping rules. Once 21 matched levels exist, rolling statistics can begin as descriptive diagnostics. An out-of-sample hedge test remains gated on participant cash prices.

## 5. Falsification and stop rules

The distinct-markets interpretation should be rejected if exact specification matching reduces the cross-vendor gaps to a stable constant. A cross-index basis product should not be promoted if basis remains unstable and cannot be explained or bounded with observable characteristics. Without participant-level cash exposure, claims must stop at benchmark disagreement.

## 6. Reproduction

From the subrepo root:

```sh
make all
```

The command validates all source references and semantic invariants, writes the matched basis to JSON and CSV, generates the browser payload, and runs the test suite. The calculation uses only the standard library. Inputs, source digests, methodology versions, and pair declarations are stored under `data/source/`; derived artifacts are stored under `data/generated/`.

The evidence was normalized from source captures dated 2026-08-29. Provenance fingerprints identify those non-redistributed captures; they document the research vintage but cannot independently verify unavailable source bytes or the completeness of upstream vendor data.
