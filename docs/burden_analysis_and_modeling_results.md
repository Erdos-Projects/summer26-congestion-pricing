# Burden Analysis and Modeling Results

This document summarizes the results of the burden analysis and the inference models. The analysis
design is documented separately in [`burden_analysis_and_modeling_plan.md`](burden_analysis_and_modeling_plan.md).

The results are drawn from the following notebooks:

- [`yellow_burden_ranking_and_heterogeneity.ipynb`](../notebooks/yellow_burden_ranking_and_heterogeneity.ipynb)
- [`hvfhv_burden_ranking_and_heterogeneity.ipynb`](../notebooks/hvfhv_burden_ranking_and_heterogeneity.ipynb)
- [`yellow_model1_model2.ipynb`](../notebooks/yellow_model1_model2.ipynb)
- [`hvfhv_model1_model2.ipynb`](../notebooks/hvfhv_model1_model2.ipynb)
- [`model3_cross_vehicle.ipynb`](../notebooks/model3_cross_vehicle.ipynb)

## 1. Burden Analysis Results

### Across Services

Both Yellow Taxi and HVFHV produce stable `DS_z` rankings at the zone × direction level. The highest
burden is concentrated in dense Manhattan core zones. Outer-borough and airport-related zone-sides
generally have lower measured burden.

The ranking is stable to the base-cost floor in both services:

- Yellow: Spearman rank correlation versus the $1 primary definition is at least 0.996 across
  $0.50 to $5, with 100% top-10/top-20 overlap.
- HVFHV: Spearman rank correlation versus the $1 primary definition is 1.00 across $0.50 to
  $5, with 100% top-10/top-20 overlap.

Trip length explains much of the burden pattern. Within Manhattan, Yellow `DS_z` is roughly 6% for
short trips, 4% for medium trips, and 2% for long trips. HVFHV shows the same ordering: short trips
have the highest burden, medium trips are lower, and long trips are lowest.

Airport trips have lower measured burden in both services. Among charged trips, Yellow airport-trip
median burden is about 0.99% versus 4.19% for non-airport trips; HVFHV airport-trip median burden is
about 1.69% versus 4.67% for non-airport trips.

Yellow and HVFHV results are reported within service rather than as a raw cross-service `DS_z`
ranking, because the total-cost fields are constructed differently.

### Yellow Taxi

Yellow's highest-burden zone-sides include Kips Bay, Flatiron, Union Sq, West Village, and Gramercy,
with `DS_z` around 4.6-4.8%. The directional rankings point to the Manhattan core on both pickup and
dropoff sides.

### HVFHV

HVFHV's highest-burden zone-sides include Alphabet City, Stuy Town/Peter Cooper Village, East
Village, West Village, Greenwich Village, and Kips Bay, with `DS_z` around 6%.

## 2. Inference Results

This section reports the volume-model results. The causal reading of these results is discussed
separately in Section 3.

### Across Models and Services

The models answer different comparison questions. Model 1 shows a stronger descriptive
burden-volume association for HVFHV than for Yellow. Model 2 produces negative main estimates for
both services, but its diagnostics are more sensitive for Yellow and the no-fee placebo matters for
both. Model 3 adds a same-zone cross-service comparison, whose interpretation depends on Yellow and
HVFHV having comparable underlying trends. The estimates and diagnostics are reported once below.

### Model 1: Burden-Volume Association

**Yellow Model 1.** The Yellow burden-volume association is weak. Pearson and Spearman correlations
are about -0.17. The highest-burden quartile is the only quartile with an average volume decline
(roughly Q1 +3.8% to Q4 -1.4%), but the relationship is not stable under controls. The `DS_z`
coefficient changes materially when borough and distance controls are added, and within-Manhattan
diagnostics are close to zero.

**HVFHV Model 1.** HVFHV shows a much stronger descriptive association. Among 519 usable
zone × direction pairs, Pearson is about -0.61 and Spearman about -0.64. The quartile pattern is
clear: the lowest-burden quartile grows by about +4.5% on average, while the highest-burden quartile
declines by about -5.1%. Control variants remain negative. This is a strong descriptive pattern,
but it is still not a causal estimate.


### Model 2: CRZ Exposure DiD

**Yellow Model 2.** Yellow has a negative equal-weighted estimate of about -11.1%, but it is not
stable across the most important diagnostics. Volume weighting moves the estimate to about +1.4%,
within-Manhattan is close to zero, and the 2023→2024 no-fee placebo is strongly negative at about
-26%. Yellow Model 2 is therefore sensitive to weighting and comparison choices.

**HVFHV Model 2.** HVFHV Model 2 is more stable within the 2024→2025 window. The FE-style exposure
estimate is about -10.7% for a zero-to-full exposure contrast; the
baseline-volume-weighted sensitivity is about -9.2%, and low-volume trims keep the estimate near the
same range. However, the 2023→2024 placebo is also negative and similar in magnitude.


### Model 3: Cross-Vehicle DiD

Model 3 is a cross-service DiD-style comparison under strong service-comparability assumptions. The
primary within-CRZ estimate is about -5.9%: HVFHV changed about 5.9% more negatively than Yellow from
2024 to 2025. This primary gap is stable to weighting, a zone-shock control, vehicle-specific
seasonality, and CRZ bottom-volume trimming. It is a relative cross-service change, not a direct
estimate of trips caused to disappear by the fee difference.

The more demanding triple-diff specification reduces the estimate to about -2% in the binary version.
The continuous-exposure triple difference is about -1.9%, and its confidence interval includes zero.
Dropping June gives a negative estimate as well, roughly -4% to -6% depending on the specification.

The diagnostics limit the interpretation:

- The 2023→2024 no-fee placebo gives a large positive CRZ-specific contrast, about +7.5% in the
  binary triple-diff.
- The placebo magnitude is large relative to the 2024→2025 estimates.
- The provider split is inconsistent: Yellow versus Uber is about -11.4%, while Yellow versus Lyft is about
  +10.3%, even though Uber and Lyft face the same $1.50 HVFHV fee.
- Yellow Flex growth can affect the card/cash comparison population, while HVFHV provider and
  platform dynamics can change the cross-service gap independently of the fee.

Model 3 therefore shows a 2025 cross-service volume gap and adds useful diagnostic and triangulation
evidence. It does not identify a clean causal effect of the fee difference.

## 3. Causal Interpretation

The volume models estimate differences across burden, exposure, time, and vehicle groups. Their
causal interpretation depends on comparisons that the public TLC data cannot fully verify: similar
underlying trends across exposure groups in Model 2, and comparable service trends in Model 3. Model
1 remains descriptive because burden is closely tied to trip length, cost, and geography.

The TLC data also observe completed Yellow and HVFHV trips rather than the full transportation
response. They do not show whether riders switched to transit, walking, biking, private vehicles, or
another service. The estimates therefore describe completed-trip volume patterns and are not
per-dollar fee elasticities.

The detailed reasoning is documented in
[`causal_interpretation_limitations.md`](causal_interpretation_limitations.md).

## 4. Overall Conclusion

For both Yellow and HVFHV, the burden ranking is stable and concentrated in short, lower-cost
Manhattan core trips. The volume models show suggestive negative patterns, while the placebo,
weighting, geographic, and provider diagnostics limit a direct fee-caused interpretation.
