# Who Bears The Congestion Price?

Executive summary for the NYC Yellow Taxi and HVFHV congestion-pricing analysis.

## Project Question

New York City's Central Business District congestion-pricing program began on January 5, 2025. This project uses public TLC Yellow Taxi and high-volume for-hire vehicle records to answer two linked questions:

1. Which TLC zones face the largest congestion-fee burden relative to trip cost?
2. Are higher-burden or higher-exposure zone-sides associated with weaker trip-volume growth after the fee?

The project is an inference-focused descriptive analysis, not a future-demand prediction task. The final interpretation separates a strong burden result from a more cautious volume result.

The short conclusion is:

> The congestion fee creates a clear and stable relative-burden pattern across taxi and HVFHV zones. Higher-burden or higher-exposure areas often show weaker volume performance, especially for HVFHV, but the available TLC trip data do not cleanly establish that the fee caused a robust Yellow Taxi or HVFHV trip-volume decline.

## Data And Scope

The analysis uses NYC TLC trip records for Yellow Taxi and HVFHV trips. The primary comparison window is February-June 2024 versus February-June 2025. January 2025 is excluded because the fee began on January 5, 2025, making January a transition month rather than a steady-state post-policy month.

The unit of analysis for burden and volume work is zone x direction. Pickup and dropoff sides are kept separate because the same TLC zone can have different burden and volume patterns depending on whether trips start there or end there.

The full-data EDA covers roughly 37 million Yellow Taxi trips and 202 million HVFHV trips across the study windows. Samples are used for early diagnostics, but final burden, volume, and modeling claims come from full-data aggregates and durable model outputs.

Yellow and HVFHV are analyzed separately for most results because their cost fields and market structures differ:

- Yellow Taxi uses `passenger_cost_pretip = total_amount - tip_amount`.
- HVFHV uses a reconstructed pre-tip passenger cost from TLC-recorded components: base fare, tolls, BCF, sales tax, congestion surcharge, airport fee, and CBD fee.
- Yellow has a major Flex Fare regime shift between the pre- and post-policy windows, so Yellow volume analysis excludes Flex when estimating the fee-relevant metered population.
- HVFHV has provider-mix and shared-ride composition issues, so Uber/Lyft and shared-ride patterns are treated as important context and diagnostics.

Primary documentation:

- [`../README.md`](../README.md)
- [`../docs/data_structure_and_schema.md`](../docs/data_structure_and_schema.md)
- [`../docs/eda_summary.md`](../docs/eda_summary.md)
- [`../docs/yellow_data_audit.md`](../docs/yellow_data_audit.md)
- [`../docs/hvfhv_data_audit.md`](../docs/hvfhv_data_audit.md)

## Primary KPI

The central burden metric is the Zone Disruption Score, `DS_z`:

```text
DS_z = mean(cbd_congestion_fee / round(passenger_cost_pretip - cbd_congestion_fee, 2))
```

`DS_z` is computed among qualifying 2025 charged trips by zone and direction, with a $1 base-cost floor. It measures how large the CBD fee is relative to the trip's pre-fee passenger cost.

`DS_z` is a burden-ranking metric, not a causal estimate. Because the fee is mostly flat within each service, `DS_z` is mechanically higher for shorter, lower-cost trips. That is exactly why it is useful for the burden question, but it also means a cross-zone burden-volume relationship is confounded by geography, trip length, and base cost.

Supporting KPIs include:

- trip-volume change from February-June 2024 to February-June 2025;
- geography-based CRZ exposure / charged-share measures;
- passenger pre-tip cost movement;
- rank-stability and floor-sensitivity metrics;
- placebo and robustness diagnostics.

See [`../kpis.md`](../kpis.md), [`../docs/evaluation_plan.md`](../docs/evaluation_plan.md), and [`../docs/feature_leakage_and_post_policy_controls.md`](../docs/feature_leakage_and_post_policy_controls.md).

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

Model 3 compares Yellow card/cash and HVFHV inside the same exposed zones. It is included as an exploratory cross-service DiD-style comparison that holds geography more fixed, but it relies on strong service-comparability assumptions and remains sensitive to Yellow Flex spillovers, cross-service substitution, and provider/platform dynamics.

Design details are in [`../docs/burden_analysis_and_modeling_plan.md`](../docs/burden_analysis_and_modeling_plan.md). Results are in [`../docs/burden_analysis_and_modeling_results.md`](../docs/burden_analysis_and_modeling_results.md). The causal interpretation is separated in [`../docs/causal_interpretation_limitations.md`](../docs/causal_interpretation_limitations.md).

## Modeling Choice For Final Reporting

Because the project is inference-focused, there is no single predictive model selected as a final forecasting model. Instead, the final reporting uses a triangulation strategy:

- the burden ranking is the primary descriptive output;
- Model 1 checks whether the burden ranking lines up with volume change;
- Model 2 adds a within-service exposure comparison over time;
- Model 3 adds exploratory diagnostic and triangulation evidence from a cross-service comparison inside exposed zones.

Model 3 holds geography more fixed than the within-service comparisons, but it is not a clean or preferred causal model. The cross-service pretrend, placebo, and provider-split diagnostics do not support the service-comparability assumptions required for fee attribution. The final conclusion therefore relies on the stable burden result and treats all volume models as an evidence ladder with explicit limitations.

## Main Results

### Burden Results

The clearest result is the burden ranking.

For both Yellow and HVFHV, `DS_z` rankings are stable across denominator-floor checks. High-burden zone-sides are concentrated in dense Manhattan areas, and shorter trips carry the highest relative fee burden.

Yellow examples include Kips Bay, Flatiron, Union Square, West Village, and Gramercy, with top `DS_z` values around 4.6-4.8%. The Yellow ranking is stable across $0.50, $1, $2, and $5 denominator floors, with Spearman rank correlation at least 0.996 against the $1 primary definition and 100% top-10/top-20 overlap.

HVFHV examples include Alphabet City, Stuy Town/Peter Cooper Village, East Village, West Village, Greenwich Village South, and Kips Bay, with top `DS_z` values around 6%. The HVFHV ranking is even more stable across the same floor checks, with Spearman rank correlation of 1.00 and 100% top-10/top-20 overlap.

Airport trips have lower measured burden in both services. Among charged trips, Yellow airport-trip median burden is about 0.99% versus 4.19% for non-airport trips; HVFHV airport-trip median burden is about 1.69% versus 4.67% for non-airport trips.

The burden result is therefore the project's strongest claim: the fee weighs more heavily on shorter, lower-cost trips, especially in dense Manhattan zone-sides.

### Volume And Modeling Results

The volume findings are more cautious.

Model 1 shows a weak Yellow burden-volume relationship: Yellow correlations are about -0.17, and the relationship is unstable under controls. HVFHV shows a much stronger descriptive relationship: among 519 usable zone-direction pairs, Pearson is about -0.61 and Spearman about -0.64. The lowest-burden HVFHV quartile grows by about 4.5% on average, while the highest-burden quartile declines by about 5.1%.

Model 2 gives negative equal-weighted exposure-gradient estimates for both services, but placebo checks weaken the causal interpretation. Yellow has a negative equal-weighted estimate around -11.1%, but volume weighting moves the estimate close to zero, within-Manhattan checks are weak, and the 2023-to-2024 no-fee placebo is strongly negative. HVFHV has a more stable negative 2024-to-2025 estimate around -10.7% in the FE-style specification and about -9.2% with baseline volume weighting, but the 2023-to-2024 placebo is also negative and similar in magnitude.

Model 3 finds that, within the primary CRZ sample, HVFHV changed about 5.9% more negatively than Yellow from 2024 to 2025. The triple-difference estimates attenuate; the continuous-exposure triple-difference interval includes zero. The 2023-2024 placebo produces large nonzero contrasts, and the Uber/Lyft provider splits move in opposite directions despite the same HVFHV fee. Yellow Flex and provider/platform dynamics further limit attribution. Model 3 therefore shows a 2025 cross-service volume gap, not a clean causal effect of the fee difference.

## Final Interpretation

The project supports a clear burden conclusion:

> The CBD fee creates an uneven relative burden. Shorter, lower-cost trips in dense Manhattan zone-sides face the highest fee burden relative to pre-fee cost.

The project does not support a clean causal volume conclusion:

> Higher-burden or higher-exposure areas often show weaker volume performance, especially for HVFHV, but the placebo and robustness checks show that the models also capture pre-existing spatial trends and provider-specific dynamics. The evidence is suggestive, not sufficient to claim that the fee caused Yellow Taxi or HVFHV trip volumes to fall.

This is still a substantive result. The TLC per-trip fees are small relative to the broader passenger-vehicle congestion charge, and the models show that any taxi/HVFHV volume response is difficult to isolate from service-specific, provider-specific, and geography-specific trends.

## Limitations

The detailed limitations are documented in [`../docs/causal_interpretation_limitations.md`](../docs/causal_interpretation_limitations.md). The main points for presentation are:

- TLC records observe completed Yellow and HVFHV trips, not the full rider choice set. The data do not show app searches, abandoned requests, transit substitution, walking, biking, private-car use, or trips that never happened.
- The policy target is broader than taxi/HVFHV trip volume. Private vehicle entries, traffic speeds, transit ridership, and system-wide congestion outcomes are outside the primary TLC trip records.
- `DS_z` is computed from observed 2025 charged trips. If the fee changed which trips occurred, the observed burden distribution may differ from the counterfactual burden distribution.
- High-burden and high-exposure zones are not random. They are closely tied to Manhattan core geography, shorter trips, lower base costs, and route composition.
- The DiD-style results are weakened by no-fee placebo checks, especially the 2023-to-2024 comparisons.
- Yellow results must account for the Flex Fare regime shift, which strongly affects raw Yellow volume and can shift the remaining metered Yellow population.
- HVFHV cost is reconstructed from TLC fields and may miss app-level discounts, refunds, subscriptions, final wallet prices, or platform-specific pricing changes.
- HVFHV provider dynamics matter: Uber and Lyft move differently even though they face the same HVFHV fee.
- HVFHV shared rides are a small share of rows, but they can affect interpretation because passenger records and vehicle movements are not always one-to-one.
- Geography-based CRZ exposure is reproducible and pre-policy, but it can miss through-trips and leaves some nominal control zones partly exposed.

More complex modeling would not automatically solve these identification problems. The key issue is not model flexibility; it is whether the comparison group represents what would have happened without the fee.

## Suggested Final Figures

The final slides/report should prioritize figures that answer one clear question each:

| Figure | Question it answers |
|---|---|
| Yellow and HVFHV top `DS_z` zone rankings | Who bears the highest relative fee burden? |
| Yellow and HVFHV `DS_z` choropleth maps | Where are the high-burden zones geographically? |
| `DS_z` versus volume-change scatterplots | Are higher-burden zones associated with weaker volume performance? |
| Burden by distance bucket / trip length | Why does the fixed fee weigh more on shorter trips? |
| Model 2 and Model 3 coefficient summary | What do the inference models estimate, and how do robustness checks change the interpretation? |
| Placebo/provider diagnostic table | Why do we avoid a clean causal volume claim? |

Current review-ready outputs are organized under [`../results/`](../results/): burden maps and top-zone figures in [`../results/burden_analysis/`](../results/burden_analysis/), EDA design-support figures in [`../results/eda/`](../results/eda/), and model/diagnostic tables in [`../results/modeling/`](../results/modeling/).

## Future Directions

The main opportunities for future work focus on identification, external transportation context, and
reproducibility:

- A final-results notebook can reproduce the exact tables and figures used in the presentation.
- Longer pre-policy panels would allow parallel-trend assumptions to be inspected more directly.
- Matched-zone, border, or event-study style comparisons would reduce the Manhattan-core confound.
- External mode-substitution data, such as MTA ridership, bus ridership, Citi Bike, pedestrian counts, or traffic-speed data, would broaden the analysis beyond TLC records.
- App-side HVFHV information would clarify rider price, discounts, credits, abandoned requests, driver supply, and provider-specific pricing or matching changes.
- Zone-level demographic or income measures would add equity context to the burden analysis.
- Time-of-day and day-of-week heterogeneity would show whether commute and discretionary trips respond differently.
- Driver pay could be analyzed as a possible outcome rather than a post-policy control.
- Provider-specific HVFHV checks, especially Uber versus Lyft, are important for interpreting pooled HVFHV results.

The full future-work discussion is in [`../docs/future directions.md`](<../docs/future directions.md>).

## Evidence Base

The main claims in this summary trace to:

- EDA notebooks: [`yellow_taxi_full_EDA.ipynb`](../notebooks/yellow_taxi_full_EDA.ipynb), [`hvfhv_full_EDA.ipynb`](../notebooks/hvfhv_full_EDA.ipynb)
- Burden notebooks: [`yellow_burden_ranking_and_heterogeneity.ipynb`](../notebooks/yellow_burden_ranking_and_heterogeneity.ipynb), [`hvfhv_burden_ranking_and_heterogeneity.ipynb`](../notebooks/hvfhv_burden_ranking_and_heterogeneity.ipynb)
- Modeling notebooks: [`yellow_model1_model2.ipynb`](../notebooks/yellow_model1_model2.ipynb), [`hvfhv_model1_model2.ipynb`](../notebooks/hvfhv_model1_model2.ipynb), [`model3_cross_vehicle.ipynb`](../notebooks/model3_cross_vehicle.ipynb)
- Result docs: [`../docs/burden_analysis_and_modeling_results.md`](../docs/burden_analysis_and_modeling_results.md), [`../docs/causal_interpretation_limitations.md`](../docs/causal_interpretation_limitations.md)
- Feature/leakage docs: [`../docs/yellow_dropped_and_engineered_features.md`](../docs/yellow_dropped_and_engineered_features.md), [`../docs/hvfhv_dropped_and_engineered_features.md`](../docs/hvfhv_dropped_and_engineered_features.md), [`../docs/feature_leakage_and_post_policy_controls.md`](../docs/feature_leakage_and_post_policy_controls.md)
- Result outputs: [`../results/README.md`](../results/README.md)

## Final Reporting Message

The final presentation should foreground the result we can defend most strongly: the fee burden is uneven and regressive in trip length. The modeling results should be presented as careful evidence about associations and robustness, not as proof of a causal trip-volume reduction.

Recommended one-sentence conclusion:

> Congestion pricing created a clear and stable relative-burden pattern across taxi and HVFHV zones, but the available TLC trip data do not cleanly establish that the fee caused a robust decline in Yellow Taxi or HVFHV trip volume.
