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
| **What it asks** | Do higher-burden zones lose more trips? | Did higher CRZ exposure reduce trips? | Does a *bigger* fee reduce trips more? |
| **Main comparison** | high-burden vs low-burden zones | more- vs less-exposed zone-sides (monthly, 2024→2025) | yellow vs Uber/Lyft, *same zone* (2024→2025) |
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
≈ **Spearman −0.88 / Pearson −0.81** cross-year, not −1. That is collinear enough that a
single-period regression **cannot pin down** the `DS_z` coefficient — it is **unstable** (it swings
with the control set, +0.72 to −3.83 across specs) rather than cleanly attenuated, and cannot isolate
whether volume dropped because of the *fee* or because of something else about *dense core zones*.
Models 2 and 3 sidestep this with a **comparison group** (that differs in the fee) instead of
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
    with `DS_z` (zone-level Spearman ≈ **−0.88**, Pearson ≈ **−0.81**), **not** the −1.00 same-year
    identity. But it is collinear enough that the `DS_z` coefficient is **not identified** — adding
    controls makes it swing (+0.72 to −3.83 across specs), so the regression *documents* the
    confounding problem rather than resolving it.
  - **borough** — either add borough dummies (Manhattan = baseline; one `DS_z` slope, now a
    *within-borough* comparison) **or** restrict to Manhattan only (a *diagnostic*, not clean
    robustness — holding borough fixed also removes most of the treatment variation, since the fee is
    almost entirely a Manhattan phenomenon, so a null there is ambiguous). We do **not** fit a
    separate `DS_z` slope per borough.
- **Outcome** — each zone × direction's % change in trip count 2024→2025 (**non-Flex** for yellow;
  see *Shared choices*).

**Good for:** the headline zone ranking + the first burden-vs-volume look.
**Caveat:** correlational only, and for the volume question **not identified** — the cross-zone
correlation is **weak for yellow** (≈ −0.16, vs HVFHV ≈ −0.61) and the coefficient is unstable under
controls, so Model 1 gives the ranking (Goal 1), not a causal effect (see the Model-1/2 notebook).

---

## Model 2 — geographic exposure-gradient DiD

**Asks:** did zone-sides more exposed to the fee lose more trips?

**How:** measure each zone × direction's **exposure** to the CRZ (pre-policy), then in a monthly
panel test whether more-exposed zone-sides changed *more* 2024→2025 than less-exposed ones.

**Why a control group helps:** weather, the economy, post-COVID recovery all move trip counts and we
can't measure them all — but low-exposure zone-sides are hit by the same forces, so netting them out
ideally **cancels those at once**. We don't model demand; the exposure gradient does.

**What we build:**
- **`charged_share`** — the treatment, a **continuous exposure**: for each zone × direction, the
  **2024 (pre-policy)** share of trips whose pickup **or** dropoff is in the **38 CRZ LocationIDs**
  (Manhattan south of 60th St). Direction-specific (matches the unit). Defined from **geography**
  (not the 2025 fee column) so the *same* rule applies to 2024; validated against the 2025
  `charged_cbd_flag` (**96% agreement**, in [`scripts/yellow_ds_pipeline.py`](../scripts/yellow_ds_pipeline.py)).
  A **binary** CRZ/non-CRZ split is kept only as a *contamination diagnostic* — even non-CRZ
  zone-sides are materially exposed (median share ≈ 0.21), so a binary control is partially treated.
  - *Known limitation:* geography misses **through-trips** (~3.7% of charged trips); flagged, not modeled.
- **Monthly panel** — unit = **zone × direction × month × year** (Feb–Jun × 2024/2025), so
  parallel-trends is inspectable (it can only be *inspected*, not fully tested — the window is all
  pre in 2024 / all post in 2025).
- **Model:** `log_n ~ C(zone_dir) + C(month) + post + post:charged_share`, **cluster-by-zone SE**.
  `C(zone_dir)` = each zone-side its own baseline; `C(month)` = seasonality; `post` = the common
  2024→2025 shift (zero-exposure reference); **`post:charged_share`** = the exposure gradient, the
  number we want. Log so it reads as a **% change**.

**Estimand & reporting:** `post:charged_share` is the **exposure gradient** (how much *more* exposed
zone-sides changed), **not** an individual charged-trip effect; a uniform city-wide effect is
absorbed by `post`. Report **equal-weighted and volume-weighted** — the weighting *is* the estimand
(per zone-side vs per trip).

**Could go wrong:** assumes exposure groups **would have moved together** absent the fee (**parallel
trends**, only inspectable here); riders shifting out of exposed zones push controls up
(**spillover**); the treatment varies with geography, so any differential core-vs-periphery trend
still confounds — only Model 3 breaks that tie.

---

## Model 3 — Yellow vs Uber/Lyft in the same zone

**Asks:** does a *bigger* fee cause a *bigger* drop? (Yellow pays $0.75/charged trip; HVFHV $1.50.)

**How:** within the same zone, compare how yellow changed 2024→2025 vs how Uber/Lyft changed.
Same zone holds fixed many zone-level confounders (density, geography, local demand shocks); what's
left is closer to the different-fee effect. This is the cleanest design: the thing we vary (fee
size) is unrelated to trip length, so it sidesteps the collinearity problem entirely.

**What we build:**
- **`service`** — yellow vs Uber/Lyft (stands in for fee size, $0.75 vs $1.50).
- **`post`** and **`post × HVFHV`** — the latter is how much *more* HVFHV changed than yellow.
- **Zone fixed effects** — same as Model 2.
- **Most of the work is data prep** — aligning yellow and HVFHV into one table with matching
  zones, comparable counts, matched populations.
- **Outcome:** `log(trip count)` per **zone × direction × vehicle × year**.

**Could go wrong:** yellow and Uber/Lyft serve different riders → "would have moved together" is a
weaker assumption (yellow's Flex product complicates it), and service-specific rider mix can still
differ even within the same zone; it measures only the *difference* between the two fees, not the
full effect of either.

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
  effects as a coefficient with a **confidence interval**. For the DiD, report **equal-weighted and
  volume-weighted** estimates — the weighting *defines the estimand* (per zone-side vs per trip), so
  a gradient that holds equal-weighted but vanishes volume-weighted is a per-zone-side pattern, not a
  trip-weighted volume effect.

## Robustness / evaluation
See [`evaluation_plan.md`](evaluation_plan.md) — identification checks, robustness/sensitivity,
placebo, standard errors, triangulation, and the reporting decision rules. **Low-N zones are flagged,
not dropped** — thin zones (`N_z` < 100) are flagged and ranked below sufficient-data ones (a
near-empty pre-policy zone that later grows is a real "activation" signal, not junk).
