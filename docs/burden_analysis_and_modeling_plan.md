# Burden Analysis and Modeling Plan

This project has two linked parts. First, a **descriptive burden analysis** ranks zone-sides by how
large the congestion fee is relative to trip cost. Second, the **modeling plan** asks whether fee
exposure is associated with changes in trip volume. The burden analysis produces the `DS_z` ranking
and heterogeneity summaries; the modeling plan uses comparisons over time, exposure, and vehicle
type to evaluate volume-change patterns.

This file defines the burden analysis and volume-modeling design. It is written for both vehicle
tracks; service-specific choices are marked where they matter. The EDA summary, data audits, and
feature-engineering notes provide the data-quality support for these choices:
[`eda_summary.md`](eda_summary.md), [`yellow_data_audit.md`](yellow_data_audit.md),
[`hvfhv_data_audit.md`](hvfhv_data_audit.md),
[`yellow_dropped_and_engineered_features.md`](yellow_dropped_and_engineered_features.md), and
[`hvfhv_dropped_and_engineered_features.md`](hvfhv_dropped_and_engineered_features.md).

**Project goals:**
1. **Who bears the burden?** Rank each zone by how heavy the fee is relative to the fare — the
   Zone Disruption Score, `DS_z`.
2. **Did the fee reduce trips?** Test whether zones/trips charged more lost more volume.

---

## Part I — Burden Analysis Design

Goal 1 is a **burden-ranking analysis**. The goal is to identify which zone-sides face the largest
fee relative to the underlying trip cost, and to check whether that ranking is stable enough to
report.

**Unit.** The unit is **zone × direction**. Pickup and dropoff sides are kept separate because the
same physical zone can have different burden profiles depending on whether trips start there or end
there. Keeping the two sides separate also avoids hiding directional patterns in one pooled zone
score.

**Population.**
- The burden metric is a **financial burden** measure: it needs a comparable rider-cost denominator,
  not just a trip count. The EDA and audit files are used to decide which fare records can support
  that denominator.
- For Yellow, the burden metric uses **card/cash trips only**, because Flex is upfront-priced and is
  not directly comparable to the metered fare base used for `DS_z`
  (see [`yellow_data_audit.md`](yellow_data_audit.md);
  [`yellow_dropped_and_engineered_features.md`](yellow_dropped_and_engineered_features.md)).
- For HVFHV, the burden metric uses the standardized passenger-cost measure built for the HVFHV
  track (see [`hvfhv_data_audit.md`](hvfhv_data_audit.md);
  [`hvfhv_dropped_and_engineered_features.md`](hvfhv_dropped_and_engineered_features.md)). Shared
  and provider-specific fields are kept as descriptive context unless the analysis is explicitly
  asking a shared-trip or provider-specific question.
- Trips used for the burden metric must have a valid fee and a valid base cost after removing the
  fee. Rows with implausibly small denominators are handled with a base-cost floor.

**Metric.** For each charged trip, compute:

`relative fee burden = congestion fee / cost excluding the congestion fee`

Then aggregate this trip-level ratio to zone × direction as `DS_z`, reported with both mean and
median. The mean captures the average fee burden among charged trips; the median is reported because
the Yellow audit found a long right tail when denominators are small, and the EDA summary therefore
uses medians and a base-cost floor rather than raw tail values
([`yellow_data_audit.md`](yellow_data_audit.md); [`eda_summary.md`](eda_summary.md)).

`DS_z` rankings are built **within each service**. Yellow and HVFHV face different fee amounts and
different underlying cost bases, so a raw cross-service comparison of `DS_z` would mix fee size,
fare structure, and trip composition rather than giving a clean burden ranking.

**Base-cost floor.** A small denominator can mechanically create very large ratios. The primary
ranking uses a `$1` base-cost floor after rounding the denominator to cents. This choice is supported
by the data-audit and feature-engineering checks: Yellow shows that the floor removes almost no
card/cash charged trips (5 of about 11.2M charged card/cash trips have base cost below `$1`, and
about 0.02% are below `$5`), while HVFHV documents denominator-floor sensitivity and stable rankings
under `$0.50`, `$1`, `$2`, and `$5` floors. The ranking is considered more credible when the top
zones and rank correlations are stable across those floor choices.

**Geography and heterogeneity.** The ranking is summarized by pickup/dropoff side, Manhattan versus
outer-borough zones, airport-related zones, and trip-length groups. Choropleth maps are used as a
geographic readout of the same ranking, not as a separate model. These cuts are descriptive: they
explain where the burden is concentrated and whether the ranking is mainly a short-trip / core-zone
pattern.

**How to read Goal 1.** A stable `DS_z` ranking answers who faces a higher fee relative to trip
cost. 

---

## Part II — Modeling Plan

The modeling part asks whether fee exposure is associated with trip-volume change. These models use
comparisons over zones, time, and vehicle type to make the volume-change interpretation more
credible.

### The three models

| | **Model 1** | **Model 2** | **Model 3** |
|---|---|---|---|
| **What it asks** | Do higher-burden zones lose more trips? | Did higher CRZ exposure reduce trips? | Does a *bigger* fee reduce trips more? |
| **Main comparison** | high-burden vs low-burden zones | more- vs less-exposed zone-sides (monthly, 2024→2025) | yellow vs HVFHV, *same exposed zone* (monthly, 2024→2025) |
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
with the control set) rather than cleanly attenuated, and cannot isolate whether volume dropped
because of the *fee* or because of something else about *dense core zones*.
Models 2 and 3 sidestep this with a **comparison group** (that differs in the fee) instead of
statistical control.

*(The −1.00 identity is a separate point — it is why 2025 cost/distance can't be used as
controls: they would define `DS_z` away, and they are post-policy leakage. The 2024 baseline above
is a distinct quantity; see Model 1.)*

---

### Unit of analysis — zone × direction

The observation unit is **zone × direction**: each TLC zone is scored separately on its **pickup
side** and its **dropoff side**. Rejected alternatives:

- **OD-pair (zone × zone)** — ~67k possible pairs, most tiny or empty → per-pair estimates are
  noisy and unstable, and the deliverable would be 67k corridors instead of a rankable set of
  zones. 
- **PU/DO pooled** — pooling a trip's two zones double-counts it and hides directional asymmetry
  (in HVFHV, dropoffs dominate the high-burden ranking). Keeping the sides separate avoids
  double-counting and reveals the asymmetry. It also matches how `DS_z` and volume are computed.

~520 zone × direction units are stable enough to rank (with a low-N flag for thin ones).

---

### Model 1 — Compare zones by their burden score

**Asks:** do higher-burden zones lose more trips?

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
  - trip-economics measures from **2024 only** — average distance is the main readable proxy, with
    baseline fare/cost shown as a sensitivity because distance, fare, cost, and duration all measure
    the same short-trip / dense-core structure. **Note:** 2024 distance is only *empirically*
    correlated with `DS_z` (zone-level Spearman ≈ **−0.88**, Pearson ≈ **−0.81**), **not** the
    −1.00 same-year identity. But it is collinear enough that the `DS_z` coefficient is **not
    identified** — adding controls makes it swing rather than settle, so the regression *documents*
    the confounding problem rather than resolving it.
  - **borough** — either add borough dummies (Manhattan = baseline; one `DS_z` slope, now a
    *within-borough* comparison) **or** restrict to Manhattan only (a *diagnostic*, not clean
    robustness — holding borough fixed also removes most of the treatment variation, since the fee is
    almost entirely a Manhattan phenomenon, so a null there is ambiguous). We do **not** fit a
    separate `DS_z` slope per borough.
- **Outcome** — each zone × direction's % change in trip count 2024→2025 (**non-Flex** for yellow;
  see *Shared choices*).

**Good for:** a first burden-vs-volume look after the Goal 1 ranking has been defined.
**Caveat:** descriptive by design. `DS_z` is mechanically tied to base cost and closely tied to
short-trip, dense-core geography before any regression is run, so high- and low-`DS_z` zones are not
clean comparison groups for identifying a fee effect. Model 1 should be read as a descriptive
association between the Goal 1 burden ranking and volume change.

---

### Model 2 — CRZ exposure DiD

**Asks:** did zone-sides more exposed to the fee lose more trips?

**How:** measure each zone × direction's **exposure** to the CRZ (pre-policy), then in a monthly
panel test whether more-exposed zone-sides changed *more* 2024→2025 than less-exposed ones.

**Why a control group helps:** weather, the economy, post-COVID recovery all move trip counts and we
can't measure them all — but low-exposure zone-sides are hit by the same forces, so netting them out
ideally **cancels those at once**. We do not model demand directly; we compare higher-exposure
zone-sides to lower-exposure zone-sides.

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
  2024→2025 shift (zero-exposure reference); **`post:charged_share`** = whether higher-exposure
  zone-sides changed more than lower-exposure zone-sides. Log so it reads as a **% change**.

**What the coefficient means:** `post:charged_share` compares higher-exposure zone-sides with
lower-exposure zone-sides; it is **not** an individual charged-trip effect. A uniform city-wide
change is absorbed by `post`. Report **equal-weighted and volume-weighted** because those answer
different questions (per zone-side vs per trip).

**Could go wrong:** assumes exposure groups **would have moved together** absent the fee (**parallel
trends**, only inspectable here); riders shifting out of exposed zones push controls up; the treatment varies with geography, so any differential core-vs-periphery trend
still confounds — only Model 3 breaks that tie.

---

### Model 3 — cross-vehicle DiD (same zone, different fee size)

**Asks:** does a *bigger* fee cause a *bigger* drop? (Yellow pays $0.75/charged trip; HVFHV $1.50.)

**How:** within the same zones, compare how yellow changed 2024→2025 vs how HVFHV changed. Same zone
→ density, geography, COVID recovery, local demand shocks hit both vehicles equally and **cancel**;
what's left is the different-fee effect. The treatment we vary (fee size) is a property of the
*vehicle*, not the zone, so geography is held fixed — **this is the design that breaks the confound
Models 1–2 could not** (there, treatment ≈ geography). The trade: it **swaps the geography confound
for a cross-vehicle-trend confound** — yellow and HVFHV are different services with different secular
trajectories, so "they would have moved together" is now the load-bearing (and shaky) assumption.

**Where the contrast lives:** the fee difference only exists on **CRZ-touching trips**, so the
comparison must be made where both vehicles are exposed.
- *Primary:* restrict to **high-CRZ-exposure zone-sides** and compare yellow vs HVFHV there.
- *Advanced (triple-diff):* keep all zones and estimate `post × vehicle × charged_share` — does the
  yellow-vs-HVFHV gap widen with exposure? This is designed to net out a common cross-vehicle trend
  using lower-exposure zones as a comparison; run it alongside the primary contrast as a robustness /
  advanced variant.

**What we build:**
- **Monthly panel** — unit = **zone × direction × vehicle × month × year** (Feb–Jun × 2024/2025), so
  the cross-vehicle **pre-trend is inspectable**, and the same design runs on a no-fee year pair as a
  placebo — the two central credibility checks for M3.
- **`vehicle`** — yellow vs HVFHV (stands in for fee size, $0.75 vs $1.50).
- **Comparability diagnostics** — before reading the cross-vehicle coefficient, check that the two
  services are aligned on scale, citywide movement, CRZ footprint, and the shape of vehicle-specific
  seasonality. These checks do not replace the main contrast; they show whether the comparison is
  being driven by an obvious mismatch between the two vehicle series.
- **Model (primary, exposed zones):** `log_n ~ C(zone_dir_vehicle) + C(month) + post + post:hvfhv`,
  **cluster-by-zone SE**. `C(zone_dir_vehicle)` = each zone-side × vehicle series its own baseline (so
  the yellow/HVFHV level gap is absorbed, not treated as an effect); **`post:hvfhv`** = how much
  *more* HVFHV changed than yellow — the coefficient we report.
- **Populations (matched):** yellow = **card/cash only** (so Uber↔yellow-Flex substitution doesn't
  move volume between the two compared services); HVFHV = **all HVFHV** (provider Uber/Lyft and
  shared/solo split kept as robustness). Both aggregated with the **same rules as yellow** (38 CRZ
  zones, non-movement drop, Feb–Jun).

**What the coefficient means:** `post:hvfhv` compares the higher-fee service (HVFHV, $1.50) with the
lower-fee service (yellow, $0.75) in the same exposed zones. It is **not** the effect of the fee vs no
fee, and **not** a per-dollar elasticity (HVFHV's higher base fare means the fee-as-%-of-fare is not
simply double). Report **equal-weighted and volume-weighted** because those answer different
questions (per zone-side vs per trip).

**Could go wrong:**
- **Cross-vehicle parallel trends** — the load-bearing assumption; yellow and HVFHV had different
  pre-fee trajectories, so it is checked with the 2024 pre-trend, a 2023→2024 placebo, and a provider
  split.
- **Flex migration → biases toward zero.** Even on card/cash, the growing Flex product mechanically
  pulls card/cash volume *down* on the yellow side (unrelated to the fee), making yellow look like it
  dropped more → `post:hvfhv` biased *up* (toward 0), understating a true negative. Mitigate with a
  non-Flex-total robustness cut.
- **Cross-service substitution is part of the comparison.** The bigger HVFHV fee pushes some riders
  HVFHV→yellow (HVFHV down, yellow up), *widening* the gap → `post:hvfhv` reflects the change in the
  *relative mix* (substitution included), not pure demand reduction. Read it as such.

---

## How the pieces fit together
- **Goal 1** = *who faces the largest relative fee burden* — the ranking.
- **Model 1** = *whether that burden ranking lines up with volume change* — descriptive only.
- **Model 2** = *do higher-exposure places change more* — cleaner than Model 1 because it adds a
  comparison group.
- **Model 3** = *does a bigger fee do more* — cleanest on geography (only the fee-size difference
  varies within a zone), but trades that for a cross-vehicle-trend assumption; credible only if the
  yellow-vs-HVFHV pre-trend is flat.
- If all three point the same way, we're confident; if they disagree, that tells us which
  assumption needs the most scrutiny.

## Shared choices (all three models)
- **Which trips we count (yellow).**
  - *Financial / burden (Model 1 `DS_z`):* **card/cash only**, following the burden-analysis
    population above; Flex uses a different upfront-pricing regime and is not comparable for a
    fare-denominator burden metric.
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
  volume-weighted** estimates because the weighting changes the comparison (per zone-side vs per
  trip), so an estimate that appears equal-weighted but not volume-weighted is a per-zone-side
  pattern, not a trip-weighted volume effect.

## Robustness / evaluation
See [`evaluation_plan.md`](evaluation_plan.md) — identification checks, robustness/sensitivity,
placebo, standard errors, triangulation, and the reporting decision rules. **Low-N zones are flagged,
not dropped** — thin zones (`N_z` < 100) are flagged and ranked below sufficient-data ones (a
near-empty pre-policy zone that later grows is a real "activation" signal, not junk).
