# Congestion Pricing Project Summary

## Project Question

New York City's Central Business District congestion-pricing program began on January 5, 2025. This project studies whether the taxi and high-volume for-hire vehicle trip data show two related patterns after the policy began:

1. Which TLC zones face the largest congestion-fee burden relative to trip cost?
2. Are higher-burden or higher-exposure zones associated with weaker trip-volume growth after the fee?

The project is an inference-focused descriptive analysis, not a future-demand prediction task. The final interpretation separates the burden result, which is stable and directly measurable, from the volume result, which is suggestive but not cleanly causal.

## Data And Scope

The analysis uses NYC TLC trip records for Yellow Taxi and HVFHV trips. The primary comparison window is February-June 2024 versus February-June 2025. January 2025 is excluded because the fee began on January 5, 2025, making January a transition month rather than a steady-state post-policy month.

The unit of analysis for burden and volume work is zone x direction. Pickup and dropoff sides are kept separate because the same TLC zone can have different burden and volume patterns depending on whether trips start there or end there.

The two services are analyzed separately for most results because their cost fields and market structures differ:

- Yellow Taxi uses `passenger_cost_pretip = total_amount - tip_amount`.
- HVFHV uses a reconstructed pre-tip passenger cost from TLC-recorded components: base fare, tolls, BCF, sales tax, congestion surcharge, airport fee, and CBD fee.
- Yellow has a major Flex Fare regime shift between the pre- and post-policy windows, so Yellow volume analysis excludes Flex when estimating the fee-relevant metered population.
- HVFHV has provider-mix and shared-ride composition issues, so Uber/Lyft and shared-ride patterns are treated as important context and diagnostics.

Detailed source and cleaning documentation:

- [`../README.md`](../README.md)
- [`../docs/data_structure_and_schema.md`](../docs/data_structure_and_schema.md)
- [`../docs/yellow_data_audit.md`](../docs/yellow_data_audit.md)
- [`../docs/hvfhv_data_audit.md`](../docs/hvfhv_data_audit.md)
- [`../docs/cleaning_notes.md`](../docs/cleaning_notes.md)

## Primary KPI

The central burden metric is the Zone Disruption Score, `DS_z`:

```text
DS_z = mean(cbd_congestion_fee / round(passenger_cost_pretip - cbd_congestion_fee, 2))
```

`DS_z` is computed among qualifying 2025 charged trips by zone and direction, with a $1 base-cost floor. It measures how large the CBD fee is relative to the trip's pre-fee passenger cost.

`DS_z` is a burden-ranking metric, not a causal estimate. Because the fee is mostly flat within each service, `DS_z` is mechanically higher for shorter, lower-cost trips. That is exactly why it is useful for the burden question, but it also means the burden-volume relationship is confounded by geography, trip length, and base cost.

Supporting KPIs include:

- trip-volume change from February-June 2024 to February-June 2025;
- geography-based CRZ exposure / charged-share measures;
- passenger pre-tip cost movement;
- rank-stability and floor-sensitivity metrics;
- placebo and robustness diagnostics.

See [`../kpis.md`](../kpis.md) and [`../docs/evaluation_plan.md`](../docs/evaluation_plan.md).

## Method Summary

The analysis has four connected pieces.

### EDA And Feature Decisions

The EDA establishes the data-quality rules and service-specific caveats. Yellow Taxi and HVFHV cannot be pooled into one undifferentiated trip table because they differ in cost construction, payment regimes, provider mix, and route composition.

Key EDA conclusions:

- Yellow raw volume growth is heavily affected by Flex Fare adoption, so all-Yellow volume is not a clean policy signal.
- Yellow card/cash trips are the cleanest population for burden and cost analysis.
- HVFHV passenger cost is reconstructed from TLC components and may not equal final app-wallet cost after discounts or credits.
- HVFHV provider mix shifts modestly toward Lyft in 2025.
- HVFHV shared rides are small, but they are cheaper within distance buckets and should be noted as a limitation for burden and vehicle-volume interpretation.
- Charged and uncharged trips differ in route composition, so a simple charged-versus-uncharged comparison is not enough to isolate a fee effect.
- Fee burden is highest on shorter, lower-cost trips in both services.

See [`../docs/eda_summary.md`](../docs/eda_summary.md), [`../docs/yellow_dropped_and_engineered_features.md`](../docs/yellow_dropped_and_engineered_features.md), and [`../docs/hvfhv_dropped_and_engineered_features.md`](../docs/hvfhv_dropped_and_engineered_features.md).

### Burden Analysis

The burden analysis ranks zone-sides by `DS_z` and checks whether the ranking is stable across denominator-floor and aggregation choices. The result is descriptive: it answers who bears more relative fee burden among observed charged trips.

### Model 1: Burden-Volume Association

Model 1 asks whether higher-`DS_z` zone-sides had weaker trip-volume growth from 2024 to 2025. This is a descriptive cross-zone association, not a causal design, because high burden is closely tied to dense Manhattan geography and short-trip structure.

### Model 2: CRZ Exposure Difference-In-Differences

Model 2 asks whether zone-sides with higher pre-policy geography-based CRZ exposure changed more than lower-exposure zone-sides. This adds a comparison group, but the interpretation depends on whether higher- and lower-exposure areas would have followed similar trends without the fee.

### Model 3: Cross-Vehicle Difference-In-Differences

Model 3 compares Yellow and HVFHV inside the same exposed zones. This holds geography more fixed and uses the fact that HVFHV faces a higher per-trip fee than Yellow. It is the strongest design geographically, but it depends on a cross-vehicle trend assumption and is sensitive to Uber/Lyft provider dynamics.

Design details are in [`../docs/burden_analysis_and_modeling_plan.md`](../docs/burden_analysis_and_modeling_plan.md). Results are in [`../docs/burden_analysis_and_modeling_results.md`](../docs/burden_analysis_and_modeling_results.md).

## Modeling Choice For Final Reporting

Because the project is inference-focused, there is no single predictive model selected as a final forecasting model. Instead, the final reporting uses a triangulation strategy:

- the burden ranking is the primary descriptive output;
- Model 1 checks whether the burden ranking lines up with volume change;
- Model 2 adds a within-service exposure comparison over time;
- Model 3 adds a cross-vehicle comparison inside exposed zones.

Model 3 is the strongest design for holding geography fixed, but it is not selected as a definitive causal model because the placebo and provider-split diagnostics do not clear the evaluation bar. The final conclusion therefore relies on the stable burden result and treats the volume models as supporting evidence with explicit limitations.

## Main Results

### Burden Results

The clearest result is the burden ranking.

For both Yellow and HVFHV, `DS_z` rankings are stable across denominator-floor checks. High-burden zone-sides are concentrated in dense Manhattan areas, and shorter trips carry the highest relative fee burden.

Yellow examples include Kips Bay, Flatiron, Union Square, West Village, and Gramercy, with top `DS_z` values around 4.6-4.8%.

HVFHV examples include Alphabet City, Stuy Town/Peter Cooper Village, East Village, West Village, Greenwich Village South, and Kips Bay, with top `DS_z` values around 6%.

Airport trips have lower measured burden in both services. Among charged trips, Yellow airport-trip median burden is about 0.99% versus 4.19% for non-airport trips; HVFHV airport-trip median burden is about 1.69% versus 4.67% for non-airport trips.

### Volume And Modeling Results

The volume findings are more cautious.

Model 1 shows a weak Yellow burden-volume relationship: Yellow correlations are about -0.17, and the relationship is unstable under controls. HVFHV shows a much stronger descriptive relationship: among 519 usable zone-direction pairs, Pearson is about -0.61 and Spearman about -0.64. The lowest-burden HVFHV quartile grows by about 4.5% on average, while the highest-burden quartile declines by about 5.1%.

Model 2 gives negative equal-weighted exposure-gradient estimates for both services, but placebo checks weaken the causal interpretation. Yellow has a negative equal-weighted estimate around -11.1%, but volume weighting and within-Manhattan checks are much weaker, and the 2023-to-2024 no-fee placebo is strongly negative. HVFHV has a more stable negative 2024-to-2025 estimate around -10.7% in the FE-style specification and about -9% with volume weighting, but the 2023-to-2024 placebo is also negative and similar in magnitude.

Model 3 finds that, within CRZ-exposed zones, HVFHV lost about 5.9% more volume than Yellow from 2024 to 2025. This estimate is stable across several robustness checks. However, the more demanding triple-diff estimate is smaller, the no-fee placebo is large, and the Uber/Lyft provider split moves in opposite directions. That prevents a clean causal reading.

## Final Interpretation

The project supports a clear burden conclusion:

> The CBD fee creates an uneven relative burden. Shorter, lower-cost trips in dense Manhattan zone-sides face the highest fee burden relative to pre-fee cost.

The project does not support a clean causal volume conclusion:

> Higher-burden or higher-exposure areas often show weaker volume performance, especially for HVFHV, but the placebo and robustness checks show that the models also capture pre-existing spatial trends and provider-specific dynamics. The evidence is suggestive, not sufficient to claim that the fee caused Yellow Taxi or HVFHV trip volumes to fall.

This is still a substantive result. The TLC per-trip fees are small relative to the broader passenger-vehicle congestion charge, and the models show that any taxi/HVFHV volume response is difficult to isolate from service-specific and geography-specific trends.

## Limitations

- `DS_z` is computed from observed 2025 charged trips. If the fee changed which trips occurred, the observed burden distribution may differ from the counterfactual burden distribution.
- High-burden zones are not random. They are closely tied to Manhattan core geography, shorter trips, and lower base costs.
- The DiD-style results are weakened by no-fee placebo checks, especially the 2023-to-2024 comparisons.
- Yellow results must account for the Flex Fare regime shift, which strongly affects raw Yellow volume.
- HVFHV cost is reconstructed from TLC fields and may miss app-level discounts, refunds, subscriptions, or credits.
- HVFHV provider dynamics matter: Uber and Lyft move differently even though they face the same HVFHV fee.
- HVFHV shared rides are a small share of rows, but they can affect interpretation because passenger records and vehicle movements are not always one-to-one.
- Geography-based CRZ exposure is reproducible and pre-policy, but it can miss through-trips and leaves some nominal control zones partly exposed.

## Future Directions

The strongest next improvements would focus on identification and communication:

- Build a cleaner final-results notebook that reproduces the exact tables and figures used in the presentation.
- Add final maps and concise zone-ranking visuals for the burden result.
- Explore matched-zone or boundary-style comparisons to reduce the Manhattan-core confound.
- Add external mode-substitution data, such as MTA ridership or Citi Bike, if the project expands beyond TLC records.
- Add equity context by joining TLC zones to neighborhood demographics or income measures.
- Study time-of-day and day-of-week heterogeneity, since commute and discretionary trips may respond differently.
- Treat driver pay as a possible outcome in future work, not as a post-policy control.
- Keep provider-specific HVFHV checks visible, especially Uber versus Lyft.

## Final Reporting Message

The final presentation should foreground the result we can defend most strongly: the fee burden is uneven and regressive in trip length. The modeling results should be presented as careful evidence about associations and robustness, not as proof of a causal trip-volume reduction.

Recommended one-sentence conclusion:

> Congestion pricing created a clear and stable relative-burden pattern across taxi and HVFHV zones, but the available TLC trip data do not cleanly establish that the fee caused a robust decline in Yellow Taxi or HVFHV trip volume.
