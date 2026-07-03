# Modeling Plan — CBD Congestion Pricing (yellow taxi + HVFHV)

**This project is inference only** — we estimate an *effect* (how the CBD congestion fee changed
rider behavior), not a prediction. Written for both vehicle tracks; yellow-specific choices are
marked. This file **explains the design**; the data audit
([`yellow_data_audit.md`](yellow_data_audit.md)) and the feature list
([`yellow_dropped_and_engineered_features.md`](yellow_dropped_and_engineered_features.md))
confirm the features serve it; the yellow DS_z pipeline
([`scripts/yellow_ds_pipeline.py`](../scripts/yellow_ds_pipeline.py)) applies it to full data.

**Two goals:**
1. **Who bears the burden?** Rank each zone by how heavy the fee is relative to the fare — the
   Zone Disruption Score, `DS_z`.
2. **Did the fee reduce trips?** Test whether zones/trips charged more lost more volume.

---

## The three models

| | **Model 1** | **Model 2** | **Model 3** |
|---|---|---|---|
| **What it asks** | Do higher-burden zones lose more trips? | Did being charged reduce trips? | Does a *bigger* fee reduce trips more? |
| **Main comparison** | high-burden vs low-burden zones | charged vs un-charged trips (2024→2025) | yellow vs Uber/Lyft, *same zone* (2024→2025) |
| **Trustworthiness** | weakest (correlational) | medium | strongest |
| **Data needed** | within a service | within a service | both services combined |

These are a **ladder** — we report all three and check whether they agree (**triangulation**: if
three methods with different weaknesses point the same way, the answer is far more believable).

**Why one model isn't enough (the collinearity problem).** `DS_z` is `flat fee ÷ base cost`, so
with a near-constant fee it is mechanically **DS_z ≈ 1 / base_cost** — a *trip-level, same-year*
algebraic identity (Spearman(DS_z, base_cost) = **−1.00**, true for both vehicles). This is the
*mechanism*: a cheap short trip has a small base fare, so the same fee is a big slice → high
`DS_z`. And cheap short trips are exactly what dense Manhattan-core zones have. So at the **zone
level** `DS_z` is **strongly** correlated with the "dense core zone" characteristic — but *not
perfectly*: `DS_z` (2025) vs the **2024** trip-economics proxy (the actual Model-1 control) is
≈ **−0.76** cross-year (preview), not −1. A single-period regression that controls for that 2024
proxy therefore (a) heavily **attenuates** the `DS_z` coefficient, and (b) still can't capture every
unmeasured dense-core trait, so residual confounding remains — it can't *cleanly* isolate whether
volume dropped because of the *fee* or because of something else about *dense core zones*. Models 2
and 3 sidestep this with a **comparison group** (trips that differ in the fee) instead of
statistical control.

*(The −1.00 identity is a separate point — it is why **2025** cost/distance can't be used as
controls: they would define `DS_z` away, and they are post-policy leakage. The 2024 baseline above
is a distinct quantity; see Model 1.)*

---

## Unit of analysis — zone × direction

The observation unit is **zone × direction**: each TLC zone is scored separately on its **pickup
side** and its **dropoff side**. Rejected alternatives:

- **OD-pair (zone × zone)** — ~67k possible pairs, most tiny or empty → per-pair estimates are
  noisy and unstable, and the deliverable would be 67k corridors instead of a rankable set of
  zones. (Optional finer "which corridor" analysis only.)
- **PU/DO pooled** — pooling a trip's two zones double-counts it and hides directional asymmetry
  (in HVFHV, dropoffs dominate the high-burden ranking). Keeping the sides separate avoids
  double-counting and reveals the asymmetry. It also matches how `DS_z` and volume are computed.

~520 zone × direction units are stable enough to rank (with a low-N flag for thin ones).

---

## Model 1 — Compare zones by their burden score

**Asks:** do higher-burden zones lose more trips? (And rank the zones — Goal 1.)

**How:** for each zone × direction compute two numbers — its `DS_z` and its % change in trip
count 2024→2025 — and check whether higher burden goes with bigger drops.

**What we build:**
- **`DS_z`.** For each zone × direction, over every 2025 trip charged the fee, compute
  `fee ÷ (cost without the fee)` and take the mean **and** median. Drop trips whose base cost is
  under the **$1 floor** (a few near-zero fares would blow the ratio up; for yellow this barely
  bites — see audit §4.6). Yellow uses **card/cash** trips only and drops **non-movement** rows
  (audit §4.2).
- **Controls — pre-policy (2024) values only.** Any 2025 value is already a *result* of the fee
  and would cancel the effect. Specifically:
  - *one* trip-economics measure — 2024 average **distance** (distance/fare/duration all measure
    roughly the same thing; keep one). **Note:** 2024 distance is only *empirically* correlated
    with `DS_z` (zone-level Spearman ≈ **−0.76**, preview — reproducible number to come from the
    Model-1 analysis), **not** the −1.00 same-year identity. So it is a valid control: it nets out
    the "dense short-trip zone" confound at the cost of *attenuating* the `DS_z` coefficient (a
    conservative estimate), rather than controlling `DS_z` away entirely.
  - **borough** — either add borough dummies (Manhattan = baseline; one `DS_z` slope, now a
    *within-borough* comparison) **or** restrict to Manhattan only (cleaner, smaller sample; also
    kept as a robustness check). We do **not** fit a separate `DS_z` slope per borough.
- **Outcome** — each zone × direction's % change in trip count 2024→2025 (**non-Flex** for yellow;
  see *Shared choices*).

**Good for:** the headline zone ranking + the first burden-vs-volume look.
**Caveat:** correlational only — cannot prove the fee *caused* the drop. (Preliminary full-data
cross-zone correlation is **weak for yellow**, ≈ −0.16 vs HVFHV −0.61 — plausibly the smaller
$0.75 fee + a flatter card/cash volume signal; to be refined in the Model-1 analysis.)

---

## Model 2 — Charged vs un-charged trips (a control group)

**Asks:** did being charged the fee reduce trips?

**How:** split trips into **charged** (touched the CRZ) and **control** (did not), and compare how
each group's count changed 2024→2025. If charged fell *more*, the extra drop is the fee's effect.

**Why a control group helps:** weather, the economy, post-COVID recovery, subway competition all
move trip counts and we can't measure them all — but the control group is hit by the same forces,
so subtracting it ideally **cancels them at once**. We don't model demand; the control group does.

**What we build:**
- **`charged_geo`** — charged if pickup **or** dropoff is in one of the **38 CRZ LocationIDs**
  (Manhattan south of 60th St). Defined from **geography** (not the 2025 fee column) so the *same*
  rule applies to 2024, which has no fee column. Validated against the 2025 `charged_cbd_flag`:
  **96.15% agreement** (precision 98.8%, recall 96.1%; reproducible in
  [`scripts/yellow_ds_pipeline.py`](../scripts/yellow_ds_pipeline.py)).
  - *Known limitation:* geography misses **through-trips** (both endpoints outside the CRZ but the
    trip passes through) — **~3.7% of charged trips**. We flag it rather than build toll/route
    logic to recover it.
  - *Optional:* a zone-level **charged-share** exposure (share of a zone's trips touching the CRZ),
    computed from 2024, used as `post × charged_share` in the DiD. Reading the share off the 2025
    flag instead is an endogeneity/leakage risk → robustness cross-check only.
- **`post`** — 2025 (after) vs 2024 (before).
- **`post × charged`** — the number we care about: the *extra* change for charged trips in 2025.
- **Zone fixed effects** — each zone keeps its own baseline, so big and tiny zones aren't compared
  unfairly; only each zone's own before-vs-after change is used.
- **Outcome:** `log(trip count)` per **zone × direction × year** (pickup/dropoff run separately).
  Log so the coefficient reads as a **% change** and sizes stay comparable.

**Could go wrong:** assumes charged and control *would have* moved together absent the fee
(**parallel trends**); riders shifting from charged to control zones push the control up
(**spillover**), inflating the estimate; the ~3.7% through-trips are mislabeled control.

---

## Model 3 — Yellow vs Uber/Lyft in the same zone

**Asks:** does a *bigger* fee cause a *bigger* drop? (Yellow pays $0.75/charged trip; HVFHV $1.50.)

**How:** within the same zone, compare how yellow changed 2024→2025 vs how Uber/Lyft changed.
Same zone → density, trip length, COVID recovery hit both equally and **cancel**; what's left is
the different-fee effect. This is the cleanest design: the thing we vary (fee size) is unrelated to
trip length, so it sidesteps the collinearity problem entirely.

**What we build:**
- **`service`** — yellow vs Uber/Lyft (stands in for fee size, $0.75 vs $1.50).
- **`post`** and **`post × HVFHV`** — the latter is how much *more* HVFHV changed than yellow.
- **Zone fixed effects** — same as Model 2.
- **Most of the work is data prep** — aligning yellow and HVFHV into one table with matching
  zones, comparable counts, matched populations.
- **Outcome:** `log(trip count)` per **zone × direction × vehicle × year**.

**Could go wrong:** yellow and Uber/Lyft serve different riders → "would have moved together" is a
weaker assumption (yellow's Flex product complicates it); it measures only the *difference* between
the two fees, not the full effect of either.

---

## How the three fit together
- **Model 1** = *who / how much* (the ranking) — the headline, least airtight.
- **Model 2** = *is there any effect* — cleaner (control group).
- **Model 3** = *does a bigger fee do more* — cleanest (only the fee-size difference).
- If all three point the same way, we're confident; if they disagree, that tells us which
  assumption is failing.

## Shared choices (all three)
- **Which trips we count (yellow).**
  - *Financial / burden (Model 1 `DS_z`):* **card/cash only** — Flex is upfront-priced with
    unreliable distance and non-comparable cost, so it can't enter a fare-based metric (audit §4).
  - *Trip counts (Model 1 outcome, Models 2–3 yellow side):* **non-Flex** = card/cash **+ irregular
    real trips** (no-charge/dispute are real rides, 0 voided in the data). **Flex is a separate
    regime**, reported alongside but read with caution — its 2024→2025 jump is largely a *program
    change* (the Flex pilot became permanent **effective Sept 21, 2024**, between the two windows)
    plus ongoing app adoption, **not** the fee, which breaks the DiD parallel-trends assumption. For
    **Model 3**, use **card/cash only on the yellow side** (Uber→yellow-Flex substitution would move
    volume between the two services being compared).
  - *Uber/Lyft:* keep provider (Uber vs Lyft) and shared-vs-solo as separate groups.
- **Only pre-fee (2024) values as controls** — any 2025 number is already a *result* of the fee.
- **Reporting.** `DS_z` as mean **and** median; any correlation two ways — **Pearson** (linear)
  and **Spearman** (rank-based, robust to a few extreme zones) — plus a burden-quartile breakdown;
  effects as a coefficient with a **confidence interval**.

## Robustness / evaluation (initial)
- **Placebo:** re-run on 2023-vs-2024 (no fee). If we still "find" an effect, something is wrong.
- **Base-cost floor sensitivity:** re-run `DS_z` at $0.50 / $2 / $5. For yellow the ranking is
  already stable (floor barely bites — pipeline: $0.50 vs $1 rank Spearman = 1.0).
- **Within-Manhattan:** re-run on Manhattan zones alone; if the burden–volume link survives, it
  isn't just "Manhattan vs outer boroughs."
- **Cluster / spatial-robust standard errors** — neighboring zones move together, so independent
  error bars overstate certainty; widen them honestly.
- **Low-N zones flagged, not dropped** — thin zones (N_z < 100; ~181 of 509 for yellow `DS_z`) are
  flagged and ranked below sufficient-data zones (a near-empty 2024 zone that later grows is a real
  "activation" signal, not junk).
- **No train/test split** — the comparison groups in Models 2–3 *are* how we test the claim.
