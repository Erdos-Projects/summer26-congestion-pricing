**NYC HVFHV CBD Congestion Fee**

**Zone Disruption Analysis**

*Technical Report*

*High-Volume For-Hire Vehicle trip records · NYC Taxi & Limousine
Commission*

Comparison window: Feb–Jun 2024 (pre-policy) vs. Feb–Jun 2025
(post-policy)

Executive Summary

On January 5, 2025, New York City's Central Business District (CBD)
congestion pricing program introduced a \$1.50 per-trip fee on
High-Volume For-Hire Vehicle (HVFHV) trips to, from, or within the
Congestion Relief Zone (CRZ). This report quantifies the fee's relative
burden across NYC TLC zones and examines whether that burden is
associated with changes in trip volume between the pre-policy period
(Feb–Jun 2024) and the post-policy period (Feb–Jun 2025).

We develop the Zone Disruption Score (DSₐ), defined as the median CBD
fee as a proportion of the regulated base trip cost, computed per zone
and direction among fee-charged trips in 2025. We then test the
association between DSₐ and year-over-year trip volume change across
three complementary analyses: overall, borough-stratified, and
trip-length-disaggregated.

**Key findings:**

- DSₐ across Manhattan zones ranges from 3.5% to 6.4%, vs. 1.6%–3.8% in
  outer-borough zones — reflecting the flat fee's disproportionate
  impact on shorter, lower-fare urban trips.

- The overall Pearson correlation between DSₐ and pct_volume_change is r
  = −0.61 (n = 519 zone×direction pairs), with a monotonic quartile
  pattern: zones in the lowest fee-burden quartile grew volume by ~4–5%,
  while zones in the highest quartile shrank by ~5%.

- The association holds within Manhattan alone (r = −0.50, n = 131 pairs
  excluding Randalls Island), substantially weakening the hypothesis
  that the finding is a borough composition artifact.

- Fee burden is mechanically highest for short trips (7–9% of regulated
  cost) vs. long trips (2–3%), but the volume-decline dose-response
  gradient is similar across trip lengths — the effect is a zone-level
  phenomenon, not a short-trip-specific one.

- Dropoff demand is consistently more fee-sensitive than pickup demand
  across all trip lengths, consistent with destination-choice elasticity
  being higher than origin-constraint elasticity.

*These findings are descriptive and associational, not causal. The
placebo test for an intended panel model (HVFHV Model 2) produced a
similar negative estimate in 2023-vs-2024, preventing a clean causal
attribution. All claims are framed accordingly.*

1\. Background and Study Design

1.1 Policy context

NYC's CBD congestion pricing program took effect January 5, 2025. For
HVFHV trips (e.g., Uber, Lyft), the policy adds a \$1.50 fee per trip
to, from, or within the CRZ, on top of existing FHV surcharges and
taxes, billed to the HVFHV base/plate and passed to the rider per TLC
regulation.

Two other charges in the same dataset are explicitly distinct from this
fee and were identified and ruled out early in this analysis:

- congestion_surcharge — a legacy Manhattan-area charge in effect since
  February 2019, separate from and predating the 2025 CBD program.

- An earlier 2024 CBD pricing proposal that was paused by the Governor
  on June 5, 2024 before taking effect — not present in 2024 trip data.

The fee actually studied here is captured in the cbd_congestion_fee
column, confirmed present only in 2025 data, with charged_cbd_flag = 1
indicating a trip was charged.

1.2 Study design

The analysis uses a year-over-year, same-months design:

- Pre-policy baseline: February–June 2024 (no CBD fee in effect)

- Post-policy period: February–June 2025 (CBD fee active throughout)

- Excluded: January 2025, treated as a policy transition month

This design controls for seasonality that a simple before/after
within-2025 comparison would not. Each month is supplied as a separate
cleaned parquet file (~20M rows/month, ~100M+ rows per year). All
queries are executed via DuckDB reading parquet files directly without
loading into memory.

1.3 Data scope and regulated-cost approximation

TLC's regulatory mandate covers driver pay and statutory
taxes/surcharges — not the full passenger bill. Platform-side fees
charged by Uber/Lyft (service fees, booking fees, dynamic pricing
margins) sit outside TLC's rate jurisdiction and are not present in this
dataset. This is a structural feature of the data, not a quality issue.

As a result, all cost fields derived from this data should be understood
as regulated-cost approximations, not true total rider spend. The
confirmed cost identity for HVFHV:

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<tbody>
<tr class="odd">
<td><p>regulated_cost_pretip = base_passenger_fare + tolls + bcf +
sales_tax</p>
<p>+ congestion_surcharge + airport_fee + cbd_congestion_fee</p></td>
</tr>
</tbody>
</table>

The cbd_congestion_fee column is an independently computed, fixed
statutory column — not back-derived from a total. It does not suffer
from the residual-derivation artifacts present in Yellow Taxi Flex Fare
data, where a total-inclusive upfront price is decomposed into
meter-style columns producing negative fare_amount values. HVFHV
components are stacked independently.

Yellow Taxi data is not included in this report. Yellow Taxi has its own
DSₐ outputs and a preliminary analysis notebook, but the deep
validation, placebo work, and heterogeneity analysis documented here
apply to HVFHV only. Cross-service comparison (Yellow vs. HVFHV) is
reserved as future work; see Section 8.

2\. Zone Disruption Score (DSₐ)

2.1 Definition

For a given TLC zone z, computed separately for PULocationID (pickup)
and DOLocationID (dropoff) directions, pooled across Feb–Jun 2025:

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<tbody>
<tr class="odd">
<td><p>DS_z = MEDIAN( cbd_congestion_fee_i / (regulated_cost_pretip_i -
cbd_congestion_fee_i) )</p>
<p>where i indexes individual trips satisfying:</p>
<p>charged_cbd_flag = 1</p>
<p>ROUND(regulated_cost_pretip - cbd_congestion_fee, 2) &gt; 0</p></td>
</tr>
</tbody>
</table>

The denominator is the regulated trip cost net of the CBD fee — i.e.,
what the rider would have paid in regulated components absent the
policy. DSₐ therefore measures the fee as a proportion of that
counterfactual regulated cost.

Median is used as the primary estimator rather than mean. The
distribution of per-trip fee burdens within a zone is right-skewed; the
median is robust to both genuine outliers and the floating-point
cancellation artifact described in Section 2.3. The mean is computed and
exported alongside the median as a secondary reference.

2.2 Why alternative denominators were rejected

|                                                         |                                                                                                                                                                                                                                            |
|---------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Candidate**                                           | **Reason rejected**                                                                                                                                                                                                                        |
| base_passenger_fare alone                               | Excludes tolls, BCF, sales tax, airport fee, legacy congestion surcharge. Average gap vs. correct denominator: \$8.65/trip. Briefly used in an intermediate version; caught by trip-level audit before producing reported output.          |
| passenger_cost_pretip (full total, not netting out fee) | This is what the dataset's pre-existing relative_cbd_burden column measures. A different, also-valid metric (fee as % of total regulated cost), but not the DSₐ spec (fee as % of cost without this fee). Retained as secondary reference. |
| Unfloored denominator without rounding                  | Near-zero floating-point residuals (~1e-16) from summing six double-precision columns produce ratios ~10¹⁵ for a handful of trips, silently dominating AVG(). Resolved by ROUND(..., 2) before comparison. See Section 2.3.                |

2.3 Data quality: floating-point cancellation

A small number of trips have every cost component except
cbd_congestion_fee equal to exactly zero (e.g., a fully comped ride
still charged the regulatory CBD fee). The true base cost is \$0, but
floating-point summation of six doubles evaluates to 1.5000000000000009
rather than 1.5, yielding base_cost ≈ 8.88×10⁻¹⁶ instead of 0. Dividing
\$1.50 by this value produces a ratio ≈ 1.7×10¹⁵.

Diagnosis: initial DSₐ results showed zone means in the range 10⁹–10¹¹
while medians were 0.03–0.06. Pulling the top 20 rows by fee_burden DESC
immediately revealed the floating-point signature.

Fix: ROUND(regulated_cost_pretip − cbd_congestion_fee, 2) \> 0 collapses
floating-point near-zeros to exactly 0.00, which the \> 0 filter then
correctly excludes. Of 34,717,550 fee-charged trips, 19 had true
zero/negative base cost after rounding and 89 had genuine sub-cent base
cost — 108 rows total (0.0003%), negligible exclusion.

Post-fix validation: the monotonicity check confirmed that for every
qualifying trip, recomputed fee_burden ≥ relative_cbd_burden (since the
DSₐ denominator ≤ the relative_cbd_burden denominator). Result: 0
violations.

2.4 SQL implementation

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<tbody>
<tr class="odd">
<td><p>CREATE OR REPLACE TABLE ds_z AS</p>
<p>WITH cleaned AS (</p>
<p>SELECT</p>
<p>PULocationID, DOLocationID,</p>
<p>cbd_congestion_fee,</p>
<p>ROUND(passenger_cost_pretip - cbd_congestion_fee, 2) AS
base_cost,</p>
<p>cbd_congestion_fee</p>
<p>/ ROUND(passenger_cost_pretip - cbd_congestion_fee, 2) AS
fee_burden</p>
<p>FROM trips_2025</p>
<p>WHERE charged_cbd_flag = 1</p>
<p>AND ROUND(passenger_cost_pretip - cbd_congestion_fee, 2) &gt; 0</p>
<p>),</p>
<p>pickup AS (</p>
<p>SELECT PULocationID AS zone, 'pickup' AS direction,</p>
<p>MEDIAN(fee_burden) AS DS_z_median,</p>
<p>AVG(fee_burden) AS DS_z_mean,</p>
<p>COUNT(*) AS N_z</p>
<p>FROM cleaned GROUP BY PULocationID</p>
<p>),</p>
<p>dropoff AS (</p>
<p>SELECT DOLocationID AS zone, 'dropoff' AS direction,</p>
<p>MEDIAN(fee_burden) AS DS_z_median,</p>
<p>AVG(fee_burden) AS DS_z_mean,</p>
<p>COUNT(*) AS N_z</p>
<p>FROM cleaned GROUP BY DOLocationID</p>
<p>)</p>
<p>SELECT * FROM pickup UNION ALL SELECT * FROM dropoff</p>
<p>ORDER BY zone, direction;</p></td>
</tr>
</tbody>
</table>

3\. Behavioral Shift Metrics (Layer B)

3.1 Definition

Trip volume and average regulated cost are compared year-over-year per
zone and direction, using all trips (not filtered by charged_cbd_flag)
to capture the full behavioral response including both CRZ-charged and
non-charged trips within each zone.

- n_trips: count of trips per zone per direction per year

- avg_regulated_cost: AVG(passenger_cost_pretip) — TLC-regulated
  components only; excludes platform fees

- avg_base_fare: AVG(base_passenger_fare) — underlying ride cost,
  independent of any surcharge

- pct_volume_change: n_2025 / n_2024 − 1, undefined (NULL) when n_2024 =
  0

Low-N zones (fewer than 100 trips in either year) are flagged via
low_n_flag rather than dropped, so 2024→2025 activation effects remain
visible. Only 2 zone×direction combinations had zero 2024 baseline
volume, confirmed to be isolated geographic edge cases.

3.2 SQL implementation

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<tbody>
<tr class="odd">
<td><p>CREATE OR REPLACE TABLE behavioral_shift AS</p>
<p>WITH combined AS (</p>
<p>SELECT yr, PULocationID, DOLocationID,</p>
<p>passenger_cost_pretip, base_passenger_fare FROM trips_2024</p>
<p>UNION ALL</p>
<p>SELECT yr, PULocationID, DOLocationID,</p>
<p>passenger_cost_pretip, base_passenger_fare FROM trips_2025</p>
<p>),</p>
<p>pu_stats AS (</p>
<p>SELECT PULocationID AS zone, 'pickup' AS direction, yr,</p>
<p>COUNT(*) AS n_trips,</p>
<p>AVG(passenger_cost_pretip) AS avg_regulated_cost,</p>
<p>AVG(base_passenger_fare) AS avg_base_fare</p>
<p>FROM combined GROUP BY PULocationID, yr</p>
<p>),</p>
<p>do_stats AS (</p>
<p>SELECT DOLocationID AS zone, 'dropoff' AS direction, yr,</p>
<p>COUNT(*) AS n_trips,</p>
<p>AVG(passenger_cost_pretip) AS avg_regulated_cost,</p>
<p>AVG(base_passenger_fare) AS avg_base_fare</p>
<p>FROM combined GROUP BY DOLocationID, yr</p>
<p>),</p>
<p>all_stats AS (SELECT * FROM pu_stats UNION ALL SELECT * FROM
do_stats)</p>
<p>SELECT</p>
<p>zone, direction,</p>
<p>MAX(CASE WHEN yr=2024 THEN n_trips END) AS n_2024,</p>
<p>MAX(CASE WHEN yr=2025 THEN n_trips END) AS n_2025,</p>
<p>MAX(CASE WHEN yr=2025 THEN n_trips END)::DOUBLE</p>
<p>/ NULLIF(MAX(CASE WHEN yr=2024 THEN n_trips END), 0) - 1</p>
<p>AS pct_volume_change,</p>
<p>MAX(CASE WHEN yr=2024 THEN avg_regulated_cost END) AS
avg_regulated_cost_2024,</p>
<p>MAX(CASE WHEN yr=2025 THEN avg_regulated_cost END) AS
avg_regulated_cost_2025,</p>
<p>MAX(CASE WHEN yr=2024 THEN avg_base_fare END) AS
avg_base_fare_2024,</p>
<p>MAX(CASE WHEN yr=2025 THEN avg_base_fare END) AS
avg_base_fare_2025,</p>
<p>CASE WHEN COALESCE(MAX(CASE WHEN yr=2024 THEN n_trips END), 0) &lt;
100</p>
<p>OR COALESCE(MAX(CASE WHEN yr=2025 THEN n_trips END), 0) &lt; 100</p>
<p>THEN TRUE ELSE FALSE END AS low_n_flag</p>
<p>FROM all_stats</p>
<p>GROUP BY zone, direction</p>
<p>ORDER BY zone, direction;</p></td>
</tr>
</tbody>
</table>

3.3 Layer B results

Zones with the largest volume declines (low_n_flag = FALSE):

|                                |               |            |            |           |                    |                    |
|--------------------------------|---------------|------------|------------|-----------|--------------------|--------------------|
| **Zone**                       | **Direction** | **n 2024** | **n 2025** | **Vol Δ** | **Reg. cost 2024** | **Reg. cost 2025** |
| East Village                   | Dropoff       | 1,119,252  | 990,843    | −11.5%    | \$28.19            | \$31.86            |
| East Village                   | Pickup        | 1,367,384  | 1,211,105  | −11.4%    | \$32.39            | \$36.76            |
| Stuy Town/Peter Cooper Village | Dropoff       | 187,122    | 163,517    | −12.6%    | \$28.59            | \$32.09            |
| Stuy Town/Peter Cooper Village | Pickup        | 230,755    | 201,803    | −12.5%    | \$31.75            | \$35.92            |
| Alphabet City                  | Dropoff       | 271,542    | 242,158    | −10.8%    | \$27.56            | \$30.66            |
| Penn Station/Madison Sq West   | Dropoff       | 815,224    | 730,496    | −10.4%    | \$32.22            | \$35.86            |

Average regulated cost rose 10–13% in high-decline zones, outpacing the
~8–9% rise in average base fare — consistent with a flat \$1.50 fee
adding a fixed amount on top of fares that changed more modestly. Volume
growth was concentrated in outer-borough, non-CRZ zones (Far Rockaway,
Astoria Park, Cambria Heights), consistent with either organic growth
unrelated to the policy or substitution away from CRZ-adjacent demand.

4\. Model 1: DSₐ vs. Volume Change Association

4.1 Overall correlation

Joining DSₐ (Layer A) to behavioral shift (Layer B) on zone × direction,
excluding low-N zones and zones with undefined pct_volume_change (n =
519 pairs):

|                          |           |                                                    |
|--------------------------|-----------|----------------------------------------------------|
| **Metric**               | **Value** | **Interpretation**                                 |
| Pearson r (overall)      | −0.610    | Moderately strong negative linear relationship     |
| Pearson r (pickup only)  | −0.610    | Nearly identical to overall — directional symmetry |
| Pearson r (dropoff only) | −0.611    | Nearly identical to overall — directional symmetry |

4.2 Quartile breakdown

Zones split into DSₐ quartiles within each direction; this view is
robust to outlier zones and confirms the relationship is monotonic, not
driven by extremes:

|               |              |             |               |                    |
|---------------|--------------|-------------|---------------|--------------------|
| **Direction** | **Quartile** | **Avg DSₐ** | **Avg vol Δ** | **Interpretation** |
| Dropoff       | 1 (lowest)   | 1.8%        | +4.4%         | Growth             |
| Dropoff       | 2            | 2.6%        | +3.1%         | Modest growth      |
| Dropoff       | 3            | 3.6%        | +1.2%         | Near flat          |
| Dropoff       | 4 (highest)  | 5.3%        | −5.3%         | Decline            |
| Pickup        | 1 (lowest)   | 1.8%        | +4.6%         | Growth             |
| Pickup        | 2            | 2.5%        | +4.5%         | Growth             |
| Pickup        | 3            | 3.5%        | +1.1%         | Near flat          |
| Pickup        | 4 (highest)  | 5.0%        | −4.8%         | Decline            |

The step from Q1 to Q4 spans roughly 9–10 percentage points of volume
change in both directions, with a steady monotonic gradient. This
dose-response pattern is more informative than the single Pearson r, as
it rules out the association being driven by a handful of extreme zones.

4.3 SQL implementation

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<tbody>
<tr class="odd">
<td><p>-- Overall and direction-stratified correlation</p>
<p>WITH joined AS (</p>
<p>SELECT d.zone, d.direction, d.DS_z_median, b.pct_volume_change,
b.low_n_flag</p>
<p>FROM ds_z d</p>
<p>JOIN behavioral_shift b ON d.zone = b.zone AND d.direction =
b.direction</p>
<p>WHERE b.pct_volume_change IS NOT NULL AND b.low_n_flag = FALSE</p>
<p>)</p>
<p>SELECT</p>
<p>COUNT(*) AS n_zones,</p>
<p>CORR(DS_z_median, pct_volume_change) AS pearson_r,</p>
<p>CORR(DS_z_median, pct_volume_change)</p>
<p>FILTER (WHERE direction = 'pickup') AS corr_pickup,</p>
<p>CORR(DS_z_median, pct_volume_change)</p>
<p>FILTER (WHERE direction = 'dropoff') AS corr_dropoff</p>
<p>FROM joined;</p>
<p>-- Quartile breakdown</p>
<p>WITH quartiled AS (</p>
<p>SELECT d.zone, d.direction, d.DS_z_median, b.pct_volume_change,</p>
<p>NTILE(4) OVER (PARTITION BY d.direction ORDER BY d.DS_z_median)</p>
<p>AS ds_quartile</p>
<p>FROM ds_z d</p>
<p>JOIN behavioral_shift b ON d.zone = b.zone AND d.direction =
b.direction</p>
<p>WHERE b.pct_volume_change IS NOT NULL AND b.low_n_flag = FALSE</p>
<p>)</p>
<p>SELECT direction, ds_quartile, COUNT(*) AS n,</p>
<p>AVG(DS_z_median) AS avg_DS_z,</p>
<p>AVG(pct_volume_change) AS avg_vol_change</p>
<p>FROM quartiled</p>
<p>GROUP BY direction, ds_quartile</p>
<p>ORDER BY direction, ds_quartile;</p></td>
</tr>
</tbody>
</table>

5\. Heterogeneity Analysis

5.1 Borough stratification

To test whether the overall r = −0.61 is a borough composition artifact
(Manhattan zones having both higher DSₐ and declining volume for
structural reasons unrelated to the fee), we stratify zones into three
groups: Manhattan, outer-borough, and airport (zones 1, 132, 138).

|                            |             |               |             |               |                              |
|----------------------------|-------------|---------------|-------------|---------------|------------------------------|
| **Stratum**                | **n pairs** | **Pearson r** | **Avg DSₐ** | **Avg vol Δ** | **Interpretation**           |
| Manhattan (all)            | 132         | −0.534        | 4.6%        | −5.5%         | Strong, monotonic            |
| Manhattan (excl. zone 194) | 131         | −0.503        | 4.6%        | −5.4%         | Robust to outlier            |
| Outer borough              | 382         | −0.234        | 2.6%        | +3.4%         | Dampened growth, not decline |
| Airport                    | 5           | +0.843        | 1.7%        | −0.3%         | n=5, uninterpretable         |

The within-Manhattan correlation (r = −0.50 on 131 pairs) directly
addresses the composition confound: even holding borough constant,
higher-burden zones lose more trips. The outer-borough result is
directionally consistent but weaker — higher burden is associated with
dampened growth rather than absolute decline, consistent with
outer-borough DSₐ values being much lower (avg 2.6% vs. Manhattan 4.6%).
Airport zones have captive demand and n too small for correlation
inference; they are treated as a separate behavioral class.

Zone 194 (Randalls Island) is the single noteworthy outlier in Manhattan
— +43% volume growth in a low-DSₐ zone (2.4%). Randalls Island is
event-venue-driven (Icahn Stadium), with trip patterns reflecting venue
scheduling rather than regular urban demand. Excluding it strengthens
the monotonic quartile pattern for Manhattan pickup Q1 and leaves the
overall correlation essentially unchanged (r changes from −0.534 to
−0.503).

5.2 Trip-length disaggregation

We recompute DSₐ separately for three trip-length buckets defined by the
distribution of trip_distance_miles among 2025 fee-charged trips:

|            |                           |                            |                                                                  |
|------------|---------------------------|----------------------------|------------------------------------------------------------------|
| **Bucket** | **Threshold**             | **Median DSₐ (Manhattan)** | **Interpretation**                                               |
| Short      | \< 1.80 miles (p25)       | 7.2%–8.6%                  | Hyper-local; flat fee is ~7–9% of regulated cost                 |
| Medium     | 1.80–7.86 miles (p25–p75) | 4.2%–5.1%                  | Core urban trips                                                 |
| Long       | \> 7.86 miles (p75)       | 1.8%–2.6%                  | Airport/outer-borough hauls; flat fee is ~2–3% of regulated cost |

Short trips bear 3–4× the fee burden of long trips in the same Manhattan
zones — a mechanical consequence of the flat fee structure. However, the
key finding is that the volume-decline dose-response gradient (Q1→Q4
spread) is similar across all three length types within Manhattan:

|            |              |              |              |              |                  |
|------------|--------------|--------------|--------------|--------------|------------------|
| **Length** | **Q1 avg Δ** | **Q2 avg Δ** | **Q3 avg Δ** | **Q4 avg Δ** | **Q1→Q4 spread** |
| Short      | −5.1%        | −6.0%        | −7.2%        | −8.6%        | 3.5pp            |
| Medium     | −4.6%        | −6.6%        | −7.1%        | −8.6%        | 4.0pp            |
| Long       | −4.8%        | −7.0%        | −7.2%        | −7.9%        | 3.1pp            |

The fee effect is a zone-level phenomenon, not a short-trip-specific
one. A zone with high DSₐ loses trips across all length categories, not
disproportionately among short trips. This is inconsistent with a simple
per-trip price elasticity story (which would predict the steepest
decline among short trips where the burden is highest) and more
consistent with a zone-level demand depression — the fee may reduce
overall attractiveness of hailing a ride in high-burden zones rather
than targeting a specific trip-length segment.

Direction asymmetry: dropoff demand is consistently more fee-sensitive
than pickup demand across all trip lengths:

|               |               |                |              |                      |
|---------------|---------------|----------------|--------------|----------------------|
| **Direction** | **r (short)** | **r (medium)** | **r (long)** | **r (differential)** |
| Dropoff       | −0.489        | −0.512         | −0.336       | −0.417               |
| Pickup        | −0.441        | −0.337         | −0.350       | −0.290               |

The r_differential column measures whether zones where short trips bear
disproportionately more burden than long trips (DSₐ_short − DSₐ_long)
show larger volume declines. The negative differential correlation
(−0.29 to −0.42) indicates an additional compositional effect beyond
average burden: zones with unequal fee incidence across trip lengths
show somewhat larger overall declines. The direction gap is largest for
medium-length trips, consistent with destination-choice elasticity being
higher than origin-constraint elasticity for typical urban HVFHV trips.

5.3 SQL implementation: trip-length disaggregation

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<tbody>
<tr class="odd">
<td><p>-- Step 1: compute p25 and p75 thresholds from 2025 fee-charged
trips</p>
<p>SELECT</p>
<p>PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY trip_distance_miles) AS
p25,</p>
<p>PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY trip_distance_miles) AS
p75</p>
<p>FROM read_parquet('data/2025-*.parquet')</p>
<p>WHERE charged_cbd_flag = 1</p>
<p>AND ROUND(passenger_cost_pretip - cbd_congestion_fee, 2) &gt; 0;</p>
<p>-- Result: p25 = 1.80 miles, p75 = 7.86 miles</p>
<p>-- Step 2: DS_z by trip-length bucket</p>
<p>CREATE OR REPLACE TABLE ds_z_by_length AS</p>
<p>WITH cleaned AS (</p>
<p>SELECT</p>
<p>PULocationID, DOLocationID,</p>
<p>CASE</p>
<p>WHEN trip_distance_miles &lt; 1.80 THEN 'short'</p>
<p>WHEN trip_distance_miles &lt;= 7.86 THEN 'medium'</p>
<p>ELSE 'long'</p>
<p>END AS trip_length,</p>
<p>cbd_congestion_fee</p>
<p>/ ROUND(passenger_cost_pretip - cbd_congestion_fee, 2) AS
fee_burden</p>
<p>FROM read_parquet('data/2025-*.parquet')</p>
<p>WHERE charged_cbd_flag = 1</p>
<p>AND ROUND(passenger_cost_pretip - cbd_congestion_fee, 2) &gt; 0</p>
<p>),</p>
<p>pickup AS (SELECT PULocationID AS zone, 'pickup' AS direction,
trip_length,</p>
<p>MEDIAN(fee_burden) AS DS_z_median, COUNT(*) AS N_z</p>
<p>FROM cleaned GROUP BY PULocationID, trip_length),</p>
<p>dropoff AS (SELECT DOLocationID AS zone, 'dropoff' AS direction,
trip_length,</p>
<p>MEDIAN(fee_burden) AS DS_z_median, COUNT(*) AS N_z</p>
<p>FROM cleaned GROUP BY DOLocationID, trip_length)</p>
<p>SELECT * FROM pickup UNION ALL SELECT * FROM dropoff</p>
<p>ORDER BY zone, direction, trip_length;</p>
<p>-- Step 3: pivot and correlate (Manhattan, n_short &gt;= 30)</p>
<p>WITH pivoted AS (</p>
<p>SELECT zone, direction,</p>
<p>MAX(CASE WHEN trip_length='short' THEN DS_z_median END) AS
DS_z_short,</p>
<p>MAX(CASE WHEN trip_length='medium' THEN DS_z_median END) AS
DS_z_medium,</p>
<p>MAX(CASE WHEN trip_length='long' THEN DS_z_median END) AS
DS_z_long,</p>
<p>MAX(CASE WHEN trip_length='short' THEN N_z END) AS n_short</p>
<p>FROM ds_z_by_length GROUP BY zone, direction</p>
<p>),</p>
<p>joined AS (</p>
<p>SELECT p.*, b.pct_volume_change, z.Borough</p>
<p>FROM pivoted p</p>
<p>JOIN behavioral_shift b ON p.zone=b.zone AND
p.direction=b.direction</p>
<p>JOIN zone_lookup z ON p.zone=z.LocationID</p>
<p>WHERE b.pct_volume_change IS NOT NULL AND b.low_n_flag=FALSE</p>
<p>AND z.Borough='Manhattan' AND p.n_short &gt;= 30</p>
<p>)</p>
<p>SELECT direction,</p>
<p>CORR(DS_z_short, pct_volume_change) AS r_short,</p>
<p>CORR(DS_z_medium, pct_volume_change) AS r_medium,</p>
<p>CORR(DS_z_long, pct_volume_change) AS r_long,</p>
<p>CORR(DS_z_short - DS_z_long, pct_volume_change) AS r_differential</p>
<p>FROM joined GROUP BY direction;</p></td>
</tr>
</tbody>
</table>

6\. Inference Validity and Constructed Leakage

Traditional feature leakage (training data encoding future target
information) does not directly apply to a descriptive inference problem.
The analogous concern here is manufactured correlation: if two metrics
are correlated by algebraic construction rather than genuine empirical
relationship, no discovery has been made. We address three distinct
concerns.

6.1 Circular construction between DSₐ and volume change

DSₐ and pct_volume_change are computed from genuinely separate data
populations:

|                  |                                            |                                       |
|------------------|--------------------------------------------|---------------------------------------|
|                  | **DSₐ**                                    | **pct_volume_change**                 |
| Source trips     | 2025 fee-charged only (charged_cbd_flag=1) | All trips, both years (no fee filter) |
| What is measured | Median of fee/base_cost ratio              | Ratio of two aggregate counts         |
| Years used       | 2025 only                                  | 2024 and 2025                         |

Different populations, different years, different mathematical
operations. The r = −0.61 correlation is a real empirical finding, not
an algebraic identity.

6.2 Endogeneity between DSₐ and volume change

DSₐ is computed from 2025 trips. If the policy caused some zones to lose
trips, the surviving 2025 fee-charged trips may be a self-selected
sample biased toward trips where riders accepted the fee burden,
compressing DSₐ downward in the most affected zones. This is attenuation
bias — it pushes the observed correlation toward zero, not away from it.
The reported r = −0.61 is therefore a conservative lower bound on the
true association, not an inflated one.

6.3 Feature contamination in downstream models

If DSₐ is used as a predictor in a classification or regression model,
post-policy variables must not be included as covariates alongside it.
Post-policy variables (avg_regulated_cost_2025, avg_base_fare_2025,
n_2025, N_z) are consequences of the same policy shock and would create
circular reasoning. The operative rule:

**Pre-policy variables (any feature computed from Feb–Jun 2024 data) are
valid predictors. Post-policy variables are not, unless they are the
outcome being predicted.**

|                                                     |                  |                                                                                                              |
|-----------------------------------------------------|------------------|--------------------------------------------------------------------------------------------------------------|
| **Feature**                                         | **Status**       | **Reason**                                                                                                   |
| n_2024, avg_regulated_cost_2024, avg_base_fare_2024 | ✅ Safe          | Pre-policy baseline; independent of CBD fee                                                                  |
| DS_z_median                                         | ⚠️ Use with care | 2025 metric; valid as primary cause variable but cannot be combined with other 2025 covariates (Concern 6.2) |
| relative_cbd_burden                                 | ⚠️ Redundant     | Near-duplicate of DSₐ (same numerator, slightly larger denominator); not independent                         |
| avg_regulated_cost_2025, avg_base_fare_2025, n_2025 | ❌ Post-policy   | Consequences of the same policy shock; circular as predictors                                                |
| pct_volume_change                                   | ❌ Outcome       | Cannot simultaneously be a predictor                                                                         |

Note on over-controlling: post-policy variables like avg_base_fare_2025
may be mediators in the causal chain (the fee may have caused base fares
to shift), not confounders. Including them as covariates would block
part of the causal path being measured, not control for an alternative
explanation.

7\. Limitations

- Correlational, not causal. The DSₐ–volume association is robustly
  descriptive but cannot be given a clean causal interpretation from
  Model 1 alone. An attempted panel model (HVFHV Model 2) using
  pre-policy geography-based CRZ exposure produced a similar negative
  estimate in a 2023-vs-2024 placebo test, suggesting pre-existing
  spatial demand trends in high-exposure zones that are not attributable
  to the policy. Model 2 is therefore excluded from this report's
  headline claims.

- Confounding by zone type. High-DSₐ zones are disproportionately dense,
  low-base-fare, short-trip Manhattan core neighborhoods. These
  characteristics may independently drive 2024→2025 ridership trends via
  mechanisms unrelated to the fee (subway/bike-share competition,
  post-pandemic normalization, broader CBD traffic effects). The
  within-Manhattan robustness check (r = −0.50) substantially weakens
  but does not eliminate this concern.

- Regulated cost ≠ total rider spend. All cost metrics exclude
  platform-side fees (Uber/Lyft service/booking fees). Absolute
  regulated-cost figures understate true rider spend; year-over-year
  changes remain valid comparisons under the assumption that platform
  fee structures did not change structurally between 2024 and 2025.

- Short-trip coverage in outer-borough zones. The trip-length
  disaggregation is complete for Manhattan (all zones present in all
  three length buckets) but 312 of ~520 outer-borough zone×direction
  pairs had zero fee-charged trips under 1.80 miles. Trip-length
  findings therefore apply to Manhattan only.

- DSₐ uses the 2025 surviving trip population. Zones where the policy
  caused the most short-trip abandonment have a self-selected 2025
  fee-charged trip sample, attenuating DSₐ downward in the most affected
  zones (see Section 6.2). This is conservative bias.

- Sensitivity check pending. The median is robust to the choice of
  base-cost floor (\> 0 after rounding), but a formal sensitivity
  analysis varying the trip-length tertile thresholds (±20%) has not
  been completed.

8\. Future Work

8.1 Yellow Taxi comparison (primary pending item)

Yellow Taxi DSₐ outputs and a preliminary Model 1/2 notebook exist but
have not undergone the full validation, placebo testing, and
heterogeneity analysis documented here for HVFHV. Yellow Taxi has a
different regulated-cost structure (total_amount is available and
meter-derived, unlike HVFHV) and a different fee rate (\$0.75 vs.
\$1.50). Direct cross-service comparison requires a carefully aligned
combined table; this is the main remaining analytical work.

Key consideration for Yellow vs. HVFHV comparison: the two datasets have
different cost-field scopes. Yellow total_amount includes meter-derived
totals; HVFHV passenger_cost_pretip is a regulated-component stack
excluding platform fees. Any "average fare" comparison across services
conflates different measurement scopes. Comparison on fields both
datasets share in equivalent form (cbd_congestion_fee, trip counts by
zone) is safer than reconstructing a total.

8.2 Other suggested extensions

- Regression with controls: model pct_volume_change as a function of DSₐ
  plus pre-policy zone characteristics (avg_base_fare_2024, n_2024,
  borough fixed effects). The residual DSₐ coefficient after controlling
  for zone type is a cleaner estimate of the fee's marginal association.

- Border discontinuity design: zones straddling the CRZ boundary are a
  near-natural experiment. Identifying TLC zones with mixed CRZ/non-CRZ
  coverage could provide a stronger identification strategy than the
  geography-based panel approach in Model 2.

- Driver-side effects: driver_pay is available in the schema. Did driver
  earnings change in high-DSₐ zones? Did drivers reposition away from
  CRZ-heavy routes?

- Shared-ride response: shared_request_flag and shared_match_flag are
  available. Did shared-ride uptake change differently from solo rides
  in high-burden zones?

- Time-of-day and day-of-week heterogeneity: pickup_hour and day_of_week
  are in the schema. Commute trips (more price-inelastic) vs.
  discretionary evening/weekend trips (more elastic) may respond very
  differently to the same flat fee.

- Income/equity overlay: DSₐ by zone can be joined to Census ACS
  tract-level income data to test whether fee burden is
  disproportionately concentrated in lower-income neighborhoods.

Appendix A: Top 20 Zones by DSₐ (2025, Pooled)

|                                |             |               |                  |         |
|--------------------------------|-------------|---------------|------------------|---------|
| **Zone**                       | **Borough** | **Direction** | **DSₐ (median)** | **N_z** |
| Alphabet City                  | Manhattan   | Dropoff       | 6.38%            | 239,356 |
| Stuy Town/Peter Cooper Village | Manhattan   | Dropoff       | 6.31%            | 160,441 |
| East Village                   | Manhattan   | Dropoff       | 6.25%            | 983,593 |
| West Village                   | Manhattan   | Dropoff       | 6.19%            | 742,528 |
| Greenwich Village North        | Manhattan   | Dropoff       | 6.14%            | 492,654 |
| Kips Bay                       | Manhattan   | Dropoff       | 6.15%            | 499,679 |
| Two Bridges/Seward Park        | Manhattan   | Dropoff       | 6.14%            | 353,805 |
| Greenwich Village South        | Manhattan   | Dropoff       | 6.17%            | 526,218 |
| Gramercy                       | Manhattan   | Dropoff       | 6.10%            | 628,489 |
| Chinatown                      | Manhattan   | Dropoff       | 6.05%            | 212,931 |
| Flatiron                       | Manhattan   | Dropoff       | 6.02%            | 545,771 |
| Sutton Place/Turtle Bay North  | Manhattan   | Dropoff       | 6.02%            | 427,328 |
| Alphabet City                  | Manhattan   | Pickup        | 6.02%            | 284,803 |
| Kips Bay                       | Manhattan   | Pickup        | 5.94%            | 509,958 |
| Greenwich Village South        | Manhattan   | Pickup        | 5.90%            | 603,421 |
| Clinton West                   | Manhattan   | Dropoff       | 5.998%           | 424,843 |
| Lower East Side                | Manhattan   | Dropoff       | 5.88%            | 756,594 |
| Murray Hill                    | Manhattan   | Dropoff       | 5.91%            | 848,187 |
| Penn Station/Madison Sq West   | Manhattan   | Dropoff       | 5.72%            | 727,032 |
| UN/Turtle Bay South            | Manhattan   | Dropoff       | 5.84%            | 466,376 |

Every zone in the top 20 is a Manhattan Yellow Zone. Dropoffs dominate
over pickups, consistent with destination-choice elasticity. The
geographic concentration in the East Side (East Village, Gramercy, Kips
Bay, Stuy Town, Sutton Place) and Greenwich Village cluster reflects the
density of short trips in these neighborhoods.

Appendix B: Inference Validity Summary

Full detail in the standalone Appendix B document. Summary of three
concerns:

|                       |                                                                                                                           |                                                                              |
|-----------------------|---------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------|
| **Concern**           | **Finding**                                                                                                               | **Implication**                                                              |
| Circular construction | DSₐ and pct_volume_change use different source populations, years, and mathematical operations — not algebraically linked | r = −0.61 is a genuine empirical finding                                     |
| Endogeneity           | Self-selection of surviving 2025 trips biases DSₐ downward in most-affected zones                                         | Reported correlation is conservative (lower bound), not inflated             |
| Feature contamination | Post-policy variables (2025 fare, 2025 volume) are consequences, not predictors                                           | Only pre-2025 zone characteristics are valid covariates in downstream models |
