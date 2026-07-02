# Yellow Taxi — Data Audit

*Data-quality audit and analysis-inclusion decisions for the Yellow Taxi portion of the
NYC CBD congestion-pricing study (Feb–Jun 2024 vs. Feb–Jun 2025).*

*Companion to the feature-selection deliverable
[`yellow_dropped_features.md`](yellow_dropped_features.md). Findings here are distilled from
[`notebooks/yellow_taxi_sample_EDA.ipynb`](../notebooks/yellow_taxi_sample_EDA.ipynb) (20K
representative sample) and validated on full data in
[`notebooks/yellow_taxi_full_EDA.ipynb`](../notebooks/yellow_taxi_full_EDA.ipynb).*

---

## 1. Data source and study design

- **Source:** NYC TLC Yellow Taxi trip records, standardized by
  [`scripts/standardize_trips.py`](../scripts/standardize_trips.py) into monthly parquet
  files (`data/processed/00_standardized_trips/yellow/<year>/<month>.parquet`). Full data
  is too large for GitHub; shared via external link.
- **Study window:** February–June **2024** (pre-policy) vs. February–June **2025**
  (post-policy). **January 2025 is excluded** as a policy-transition month (fee began
  Jan 5, 2025); the early period is not representative of the steady state.
- **Reporting rule:** outcomes are reported **by month**, never as a pooled 2024+2025
  average, so pre- and post-policy periods are never silently mixed.
- **Core cost measure:** `passenger_cost_pretip = total_amount − tip_amount`. This is the
  working passenger-facing cost throughout; itemized component sums are **not** used to
  reconstruct cost (see §4.5).

## 2. Cleaning already applied upstream (row drops)

`standardize_trips.py` drops rows that fail conservative validity filters, so the analysis
never sees them:

- invalid timestamps / dropoff not after pickup;
- pickup year–month mismatch with the source file;
- missing zone IDs;
- negative distance, non-positive duration;
- missing or negative CBD fee (2025+);
- non-positive `passenger_cost_pretip`.

Outlier-but-plausible trips (zero distance, very long distance/duration) are **retained
and flagged**, not dropped (see §4.2). Because these anomaly types are removed upstream,
their QC flags on the sample are always-false and must **not** be read as evidence the
anomalies never occur in raw data.

## 3. Missingness — structural, not random

Missingness is **not** a random data-quality problem: it is **structural / by-design**
(fully explained by the observed `payment_type`) and itself signals trip type. These
itemized components do not exist for upfront-priced Flex trips — they are "not applicable,"
not merely unrecorded. The pattern is systematic and predictable, so it's handled by
**flagging the regime**, not by naive imputation.

- All columns with missing values are missing **together**, and those rows are **exactly
  the Flex Fare rows** (`payment_type == 0`); every Flex Fare row has the same fields
  missing.
- Missing fields: `RatecodeID`, `congestion_surcharge`, `airport_fee`, `passenger_count`.
- **Why:** Flex Fare trips are upfront-quoted e-hail bookings (Curb/Arro, and via Uber),
  not metered fares assembled from itemized components. Taximeter metadata and itemized
  surcharges either are never produced or are bundled into the single quoted total.
- **Consequence:** these rows are a **distinct payment regime**, to be flagged and handled
  separately — not imputed and not mixed into component-level analysis. Core fields
  (pickup/dropoff time, zone IDs, `cbd_congestion_fee`, `payment_type`,
  `passenger_cost_pretip`) remain complete for all rows after cleaning.

## 4. Data-quality issues found in EDA

### 4.1 Payment regimes differ in reliability
| Regime | `payment_type` | Reliability | Handling |
|---|---|---|---|
| Credit card / Cash | 1, 2 | Cleanest; full components | **Primary population** for burden/cost/distance |
| Flex Fare | 0 | Upfront-quoted; components missing/bundled; **distance unreliable** | Separate regime; `total_amount` OK for broad volume/cost only |
| No-charge / Dispute / Unknown / Voided | 3, 4, 5, 6 | **Real trips**, payment anomalous (comped/disputed; **0 voided** in the data) | Excluded from **all financial** analysis (burden, cost — payment unreliable); **counted in trip volume** (real metered trips, ~1.5%, rate stable across years) |

**Why Flex is separated whenever cost is involved** (burden, DS_z, cost trends) — an
empirical, not a mechanistic, argument: (1) Flex's cost *components* are unreliable — **≈13% of
Flex trips carry a negative or mixed-sign fee component, vs 0% for card/cash** (sample EDA §5,
component-reliability cell) — and (2) Flex total cost is priced differently and **not
comparable** to card/cash (see §4.4). So any cost-based metric must
look at Flex **separately** rather than pooling it with card/cash. That's the extent of the
claim. (Distance reliability, §4.3, is a separate, secondary point.)

### 4.2 Zero-distance trips

Zero distance is **concentrated in non-card/cash regimes**: among zero-distance PU≠DO trips
**82% are Flex Fare** (whose distance is unreliable), while card/cash zero-distance is rare
(~1% of card/cash trips). So the card/cash restriction already removes most zero-distance
junk; the rest is handled below. (Source: sample EDA §3, zero-distance-by-zone-match cell.)

The real discriminator is whether the trip **moved** — distance *and* duration (not PU/DO
alone). (`duration == 0` cannot occur: `standardize_trips.py` drops non-positive duration;
min observed = 1 s.)

- **Non-movement → dropped** from the primary burden/DS_z analysis:
  `zero_distance AND (PU == DO OR duration < 60 s)`.
  - *PU == DO:* median duration **10 s** yet a non-trivial charge (median **$25.50**, max
    $301) — a 10-second, 0-mile "trip" charging $25 is a cancellation / void / meter error,
    not a metered ride.
  - *PU ≠ DO but duration < 60 s:* a handful (≈4 in the card/cash sample) at 3–30 s with
    0 miles across two zones — the same artifact.
  - Magnitude ≈ **0.6% of card/cash**, **0.32%** of the 2025-charged DS_z population →
    negligible volume impact, clearly-invalid records removed. The 60 s threshold is robust
    (no card/cash rows fall between ~30 s and ~200 s).
- **Genuine trip, distance mis-recorded → kept, flagged:** `zero_distance AND PU ≠ DO AND
  duration ≥ 60 s` — median duration **919 s (15 min)**, cost $18.50; excluded only from
  distance/speed/per-mile views.

### 4.3 Flex Fare distance is a weakly-anchored, less-reliable measurement

Flex is upfront-priced, so its `trip_distance_miles` is **not taximeter-metered** — a reason
to distrust it by construction. Full-data picture (37.2M trips):

- **Central distribution is plausible:** Flex distance median 2.39 mi, p99 **15.52 mi** —
  *below* the card/cash p99 of 19.93 mi. So the field is not broadly corrupt.
- **Extreme distance errors exist in BOTH regimes:** > 100 mi occurs in
  **1,236 Flex** trips (0.018%) *and* **608 card/cash** trips (0.002%, max 154,097 mi) —
  Flex at ~9× the rate. So an extreme-distance cap is a
  **regime-agnostic** data-quality step, not a Flex-specific one. 
- **Weak anchoring (reliable-distance frame):** Flex
  distance decouples specifically from **price** — Spearman(distance, **cost**) = **0.60 vs
  0.92** (much weaker for Flex), while Spearman(distance, **duration**) = **0.77 vs 0.85**
  (only modestly weaker). So Flex distance still tracks the physical trip roughly, but not the
  fare — consistent with cost being an upfront quote, not distance-metered.
- **Decision:** distance-based analysis uses card/cash (Flex is separated for cost anyway,
  §4.1); Flex distance's weak anchoring is supporting justification. Extreme distances are
  handled by a regime-agnostic cap, applied where warranted (deferred pending HVFHV review).
  (Source: full EDA — Flex-distance reliability, validated on full data.)

### 4.4 Flex Fare total cost — a reliable *number*, but not comparable to card/cash

Unlike its components — ≈13% of Flex trips have a negative or mixed-sign fee component vs 0% for
card/cash (sample EDA §5) — Flex's `total_amount` is a **reliable number**: the upfront price the
rider agreed to pay. The issue is **comparability, not reliability** — Flex total cost
cannot be pooled with card/cash. Figures below are on the **cleaned frame** (non-movement and
over-100-mile rows removed per §4.2–§4.3):

- **Different level:** Flex median cost is higher per trip (**$20.84 vs $18.25**).
- **Different trend:** Flex median cost **fell** 2024→2025 (**$21.55 → $20.55**) while card/cash
  **rose** ($18.20 → $18.55). Pooling would contaminate the policy cost signal with a Flex
  pricing/composition shift. *(We deliberately do **not** compare cost per mile across regimes —
  Flex distance is unreliable, §4.3.)*
- **Different mechanism:** upfront/dynamic quote (incl. surge) vs. the regulated meter.

**Consequence:** burden (`fee/cost`) and cost-trend analyses use **card/cash only**; Flex is
reported **separately**, never pooled. Its total is fine as a *number* for broad
volume/demand context. (Source: full EDA §12 cost-comparability, cleaned frame.)

### 4.5 Itemized fee sum double-counts
A naive `total_amount == Σ(components)` reconciliation shows fixed gaps of **$2.50** and
**$3.25**, matching the legacy NYS congestion surcharge and that surcharge + the new $0.75
CBD fee. So `extra` / other accounting fields sometimes already bundle these charges →
summing every displayed fee field **double-counts**. **Decision:** trust `total_amount`
and use `passenger_cost_pretip = total_amount − tip_amount`; do not rebuild cost from
components. (`extra`, `mta_tax`, `improvement_surcharge` are consequently not used and are
not part of the standardized schema.)

### 4.6 Extreme relative-burden tail (small denominator)
`relative_cbd_burden = cbd_fee / passenger_cost_pretip` develops a long right tail when the
denominator is tiny. Sample p99 = 0.25 (max 0.95) driven by ~76 rows; **full-data p99 is
~7.6%**, so the sample overstated the tail.
- These extreme rows are **low-cost short-haul riders — the population of greatest policy
  interest** — so they are **retained, not dropped**.
- Summaries use **median / percentiles**; any mean is **winsorized (p99) and disclosed**.
- For the disruption metric, a **$1.00 base-cost floor** is applied (see
  [`methodology_notes.md`](methodology_notes.md)) to stop tiny denominators from swinging
  zone averages.

## 5. Analysis-inclusion rules (by outcome)

Different questions use different row subsets of the cleaned data:

| Question / outcome | Rows used |
|---|---|
| **Relative burden / DS_z** | **2025, charged, card/cash** trips only; base cost ≥ $1.00 floor; **exclude non-movement** (zero-distance with PU==DO or duration<60s); report per zone × direction, medians |
| **Trip volume (clean policy signal)** | **exclude Flex** (its adoption boom confounds raw totals, §6); count card/cash **+ irregular** (no-charge/dispute) — all real metered trips; irregular rate is stable across years (§7) so no YoY bias; report by month |
| **Total demand (context only)** | all yellow incl. Flex — but read as demand, **not** a policy effect |
| **Distance / speed / per-mile** | card/cash, exclude zero-distance rows |
| **Cost trend** | card/cash by month (Flex reported separately, never merged) |

## 6. The Flex-adoption confound (why raw volume is not a policy signal)

Yellow trip volume rose ~11–20% in every post-policy month, but this is **not** the congestion
fee. Two forces push the Flex Fare share up between the two windows — **neither is the fee**:

1. **A structural program change:** the Flex Fare (TLC upfront-pricing) pilot was made
   permanent — **adopted Aug 14, 2024, effective Sept 21, 2024** — which falls **exactly
   between** the pre-window (Feb–Jun 2024, still a pilot) and the post-window (Feb–Jun 2025,
   permanent). So much of the 2024→2025
   Flex-share jump is a *mechanical* consequence of that Aug-2024 launch — not rider response
   to the Jan-2025 fee. This is the point that raw totals hide.
2. **Ongoing adoption** of the app-dispatch booking channel (Flex has been offered in the Uber
   app via opt-out since ~2022).

Flex's share roughly doubled–tripled (weighted ~4.8% → 13.3% in the sample; ~6–12% → 19–29%
in full data). Because Flex is a different, structurally-shifted, growing regime, pre/post
comparisons of *total* yellow volume or *pooled* median cost largely reflect this regime shift
(above all the Aug-2024 program change), not policy. **The volume outcome therefore excludes
Flex**, counting the metered population (card/cash plus the ~1.5% no-charge/dispute real
trips), which is insulated from the Flex channel.
(Whether Flex is pulling riders from Uber/Lyft is a cross-service substitution question that
needs HVFHV data.)

*Source: NYC TLC Flex Fare Rule Package — adopted 2024-08-14, effective 2024-09-21
([rules.cityofnewyork.us](https://rules.cityofnewyork.us/rule/flex-fare-rule-package/)).*

## 7. Composition checks (pre/post comparability)

- 2024 vs. 2025 **card/cash** populations are broadly comparable in pickup-hour and
  day-of-week distribution, and in the no-charge/dispute split (~75/25), stable across
  years.
- The credible year-over-year signal is **cost** (2025 median slightly higher every
  month). Sample-level April-2025 distance/duration wobbles did **not** survive on full
  data (thin per-cell N) — treated as sample noise.
- Charged card/cash trips are more expensive (full-data median **$19.25 vs $16.10**) not
  only because of the $0.75 fee but because they are longer and less airport-heavy — geography
  and route composition, not the fee, explain most of the gap.

## 8. Summary of decisions carried into feature engineering

1. Study window Feb–Jun; exclude Jan 2025; report by month.
2. Cost = `total_amount − tip_amount`; never rebuilt from components.
3. Card/cash is the primary **financial** population; **Flex is a separate regime**; irregular
   (3/4/5/6) are real trips → excluded from all **financial** analysis, but **counted in volume**.
4. Flex distance unusable; distance analysis is card/cash only.
5. **Non-movement dropped** — zero-distance with PU==DO or duration<60s (~0.6% of card/cash);
   genuine zero-distance PU≠DO trips (duration≥60s) kept-flagged, not used for distance analysis.
6. Burden tail retained; medians + winsorized means + $1 floor.
7. Volume outcome = **non-Flex** metered trips (card/cash + irregular real trips); only Flex is
   excluded (confound).

Feature-level keep/drop/engineer decisions are in
[`yellow_dropped_features.md`](yellow_dropped_features.md).
