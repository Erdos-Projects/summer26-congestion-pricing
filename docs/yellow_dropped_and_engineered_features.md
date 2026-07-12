# Yellow Taxi — Feature Selection (Dropped / Kept / Engineered)

*The concrete per-feature decisions for the Yellow Taxi track: what is dropped, kept, or
engineered, and why.*

*This is the written feature list (dropped / kept / engineered); the analysis and
engineered-feature construction live in
[`yellow_feature_selection_and_engineering.ipynb`](../notebooks/yellow_feature_selection_and_engineering.ipynb).
The leakage / manufactured-correlation framework is general to the whole project and
written in [`feature_leakage_and_post_policy_controls.md`](feature_leakage_and_post_policy_controls.md);
the 2024-safe / 2025-forbidden rule referenced below is defined there. Data-quality basis
for the reliability decisions is in [`yellow_data_audit.md`](yellow_data_audit.md).*

---

## 1. Selection criteria

A feature is dropped/kept/engineered on four grounds:

1. **Leakage** — post-policy (2025) variables cannot serve as controls; see the general
   leakage doc. (Marked ❌ below.)
2. **Redundancy / collinearity** — definitionally or mechanically duplicates another
   variable, adding no independent information. (⚠️)
3. **Reliability** — data-quality problems from the audit (e.g. Flex distance unreliable,
   component double-count). (🧹)
4. **Scope** — outside the burden/volume question (e.g. speed/duration). (○)

## 2. DS_z is (definitionally) ≈ 1/base_cost — so cost/fare/distance can't be *same-year* controls

**This is a general property of the DS_z *metric*, not yellow-specific** — it holds for HVFHV
too (same formula, $1.50 fee); the numbers below are just yellow's confirmation. The disruption
score `DS_z = mean[ cbd_fee / (passenger_cost_pretip − cbd_fee) ]` has a near-constant fee
numerator ($0.75 for yellow), so **DS_z ≈ fee / base_cost** — an algebraic identity, not an
empirical relationship. Measured on 2025 charged card/cash trips (feature-selection
notebook §4): **Spearman(DS_z, base_cost) = −1.00**, **Pearson(DS_z, 1/base_cost) = 1.00**;
`fare_amount` is collinear for the same reason (Spearman −0.99), and **distance is only the
weaker proxy** (Spearman −0.89). Two consequences for feature selection:

- **`trip_duration_seconds` is dropped** — highly collinear with distance (and endogenous
  to traffic), so it adds no independent control value and is off-scope (a speed variable).
- **Same-year (2025) cost/fare/distance cannot be controls** — collinear with DS_z *by
  construction* (base cost near-deterministically), so they'd control the treatment away; and
  they are post-policy (leakage) regardless.
- **The pre-policy 2024 baseline distance/fare CAN be controls** (this is what Model 1 uses) —
  a *distinct* quantity, only *empirically* correlated with DS_z (zone-level Spearman ≈ **−0.88**).
  It captures the "dense short-trip zone" confound, but is collinear enough that the DS_z
  coefficient can't be cleanly separated from it; the **DiD** designs (M2/M3) complement it with
  a control group rather than a statistical control.

## 3. Trip-level fields

Status legend: ✅ 2024-safe · ❌ 2025-forbidden as control · ⚠️ redundant/collinear ·
🧹 reliability/cleaning · ○ out of scope.

| Feature | Decision | Status | Reason |
|---|---|---|---|
| `pickup_datetime` / `dropoff_datetime` | **engineer (index + EDA)** | ✅ | source for the year/month pre-vs-post **index** (used) and for `pickup_hour`/`day_of_week` (**EDA-only**); raw datetime is not itself a model feature |
| `pickup_hour`, `day_of_week` | **EDA-only (not a model feature)** | ○ | used in the descriptive temporal EDA (hourly CBD exposure, day-of-week seasonality); **not used by any of the 3 models** — they are zone×direction, which collapses trip-level time. (Available for an optional time-stratified robustness run.) |
| `PULocationID` / `DOLocationID` | **engineer** | ✅ | basis for `charged_geo` and the zone × direction unit (unit justified in `burden_analysis_and_modeling_plan.md`); categorical, never numeric |
| `trip_distance_miles` | **keep (card/cash)** | ✅/🧹 | baseline trip-economics control; for Flex it is **less reliable / weakly-anchored** (§4.3), not unusable — only rare extreme values (>100 mi, in **both** regimes) are capped; distance analysis uses card/cash anyway (burden population) |
| `trip_duration_seconds` | **drop** | ⚠️/○ | rank-collinear with distance/DS_z (Spearman ~0.94; its low VIF is a Pearson artifact); endogenous to traffic; off-scope (speed) |
| `passenger_cost_pretip` | **keep** | ✅ | `total_amount − tip_amount`; cost outcome + burden denominator basis |
| `cbd_congestion_fee` | **keep** | 🧹 | the fee (DS_z numerator); ~$0.75; defines treatment (2025) |
| `charged_cbd_flag` | **replace → `charged_geo`** | ❌ | 2025-only (no 2024 charged group) → cannot support cross-year comparison |
| `fare_amount` | **drop** | ⚠️ | mechanically part of the cost total; no info beyond `passenger_cost_pretip` |
| `tip_amount` | **drop** | ⚠️ | subtracted out to define pretip cost; not a covariate |
| `total_amount` | **drop** | ⚠️ | = pretip + tip; definitionally redundant |
| `passenger_cost_excl_cbd` | **engineer → `base_cost_ex_cbd`** | 🧹 | DS_z denominator = `round(pretip − cbd, 2)`, $1 floor; not a standalone control (**built in Part B / DS_z pipeline**) |
| `relative_cbd_burden` | **keep as reference only** | ⚠️ | near-duplicate of DS_z (fee/total vs fee/base); secondary cross-check, not the metric |
| `payment_type` | **engineer → regime flags** | ✅ | defines card/cash vs Flex vs irregular; drives the population split |
| `congestion_surcharge` (legacy) | **keep in denominator** | 🧹 | pre-existing surcharge; part of base cost, not a study feature; NA on Flex (upfront-priced) |
| `tolls` | **context only** | 🧹 | part of base cost; not a standalone feature |
| `airport_fee` | **engineer → `airport_trip_flag` (EDA-only)** | ✅/○ | `airport_fee>0` & PU/DO ∈ {132,138}; airport trips are characterized in EDA and are not model features in the current design; NA on Flex |
| `extra`, `mta_tax`, `improvement_surcharge` | **drop** | 🧹 | bundling → double-count (audit §4.5); not in standardized schema |
| `passenger_count` | **drop** | ⚠️/🧹 | low analytic value; NA on Flex (upfront-priced) |
| `RatecodeID` | **drop (optional)** | ⚠️/🧹 | NA on Flex (upfront-priced); marginal use only |

## 4. Engineered zone×direction features

| Feature | Decision | Status | Reason |
|---|---|---|---|
| `DS_z` (mean) + `DS_z_median` | **primary metric** | — | burden per zone×direction; 2025 charged card/cash, $1 floor; report mean **and** median |
| `charged_geo` | **engineer** | ✅ | (PU or DO in CRZ); constant across years → enables charged-vs-control DiD. **Defined + CRZ-validated (~96.5%) in the notebook's Part B / DS_z pipeline** (needs the committed CRZ 38-zone lookup) |
| `base_cost_ex_cbd` (zone avg) | **keep (descriptive)** | ⚠️ | ≈ 1/DS_z (collinear); context, not a control |
| `n_2024` (baseline volume) | **keep (control)** | ✅ | pre-policy zone size; exogenous baseline |
| `avg_distance_2024`, `borough` | **keep (control)** | ✅ | pre-policy zone character |
| `pct_volume_change` | **outcome** | 🎯 | non-Flex n₍2025₎/n₍2024₎ − 1 (card/cash + irregular real trips); behavioral response — never a predictor |
| `avg_cost_2025`, `n_2025`, any 2025 aggregate | **drop as control** | ❌ | post-policy; consequence of the same shock → circular |

## 5. Summary lists (dropped / engineered / kept)

**Dropped** — `trip_duration_seconds`, `fare_amount`, `tip_amount`, `total_amount`,
`extra`, `mta_tax`, `improvement_surcharge`, `passenger_count`, `RatecodeID`;
`charged_cbd_flag` (replaced); all **2025 zone aggregates** as controls;
`relative_cbd_burden` demoted to reference.

**Engineered** — `charged_geo`, `base_cost_ex_cbd`,
payment-regime flags (`flex_fare_flag`, `yellow_card_or_cash_flag`, `irregular_payment_flag`),
and the zone×direction aggregates `DS_z` (mean+median),
`pct_volume_change`, `n_2024`, `avg_distance_2024`.

**Kept as-is (baseline controls / core)** — `trip_distance_miles` (card/cash),
`passenger_cost_pretip`, `cbd_congestion_fee`, `borough`, `n_2024`.

**Used in EDA only (not model features)** — `pickup_hour`, `day_of_week` (descriptive temporal
patterns), and `airport_trip_flag` (airport-trip characterization). The three models are zone-level
and do not use these.
