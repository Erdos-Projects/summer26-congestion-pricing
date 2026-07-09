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

Both Yellow Taxi and HVFHV produce stable `DS_z` rankings at the zone x direction level. The highest
burden is concentrated in dense Manhattan core zones. Outer-borough and airport-related zone-sides
generally have lower measured burden.

The ranking is stable to the base-cost floor in both services:

- Yellow: Spearman rank correlation versus the USD 1 primary definition is at least 0.996 across
  USD 0.50 to USD 5, with 100% top-10/top-20 overlap.
- HVFHV: Spearman rank correlation versus the USD 1 primary definition is 1.00 across USD 0.50 to
  USD 5, with 100% top-10/top-20 overlap.

Trip length explains much of the burden pattern. Within Manhattan, Yellow `DS_z` is roughly 6% for
short trips, 4% for medium trips, and 2% for long trips. HVFHV shows the same ordering: short trips
have the highest burden, medium trips are lower, and long trips are lowest.

Airport trips have lower measured burden in both services. Among charged trips, Yellow airport-trip
median burden is about 0.99% versus 4.19% for non-airport trips; HVFHV airport-trip median burden is
about 1.69% versus 4.67% for non-airport trips.

Yellow and HVFHV results are reported within service rather than as a raw cross-service `DS_z` ranking, because the total-cost fields are not constructed the same way.

### Yellow Taxi

Yellow's highest-burden zone-sides include Kips Bay, Flatiron, Union Sq, West Village, and Gramercy,
with `DS_z` around 4.6-4.8%. The directional rankings point to the Manhattan core on both pickup and
dropoff sides.

### HVFHV

HVFHV's highest-burden zone-sides include Alphabet City, Stuy Town/Peter Cooper Village, East
Village, West Village, Greenwich Village, and Kips Bay, with `DS_z` around 6%.

## 2. Inference Results

Several volume specifications estimate larger 2025 declines in higher-burden or higher-exposure areas. However, the placebo and sensitivity checks make the evidence insufficient to attribute those declines clearly to the congestion fee.

### Across Models and Services

Model 1 shows the clearest service difference: HVFHV has a much stronger descriptive
burden-volume association, while Yellow's association is weak and sensitive to controls.

Model 2 estimates lower 2025 volume in higher-exposure areas for both services in the main
equal-weighted comparison. HVFHV gives the more stable negative higher-exposure versus lower-exposure
association, while Yellow is unstable across weighting and within-Manhattan checks. In the
2023-to-2024 no-fee placebo window, both services also show negative exposure-related estimates, so
Model 2 is interpreted as an exposure-gradient association rather than strong causal evidence.

Model 3 estimates a negative cross-vehicle gap inside the CRZ, but the no-fee placebo and provider
split show substantial cross-vehicle and provider-specific movement.

### Model 1: Burden-Volume Association

**Yellow Model 1.** The Yellow burden-volume association is weak. Pearson and Spearman correlations
are about -0.17. The highest-burden quartile is the only quartile with an average volume decline
(roughly Q1 +3.8% to Q4 -1.4%), but the relationship is not stable under controls. The `DS_z`
coefficient changes materially when borough and distance controls are added, and within-Manhattan
diagnostics are close to zero.

**HVFHV Model 1.** HVFHV shows a much stronger descriptive association. Among 519 usable
zone-direction pairs, Pearson is about -0.61 and Spearman about -0.64. The quartile pattern is
clear: the lowest-burden quartile grows by about +4.5% on average, while the highest-burden quartile
declines by about -5.1%. Control variants remain negative. This is a strong descriptive pattern,
but it is still not a causal estimate.


### Model 2: CRZ Exposure DiD

**Yellow Model 2.** Yellow has a negative equal-weighted estimate of about -11.1%, but it is not
stable across the most important diagnostics. Volume weighting moves the estimate to about +1.4%,
within-Manhattan is close to zero, and the 2023->2024 no-fee placebo is strongly negative at about
-26%. Yellow Model 2 is therefore a fragile geographic association.

**HVFHV Model 2.** HVFHV Model 2 is more stable within the 2024->2025 window. The FE-style
exposure estimate is about -10.7% for a zero-to-full exposure contrast; volume weighting remains
negative at about -9.7%, and low-volume trims keep the estimate near the same range. However, the
2023->2024 placebo is also negative and similar in magnitude.


### Model 3: Cross-Vehicle DiD

The primary within-CRZ estimate is about -5.9%: HVFHV lost about 5.9% more volume than Yellow from
2024 to 2025. This primary gap is stable to weighting, a zone-shock control, vehicle-specific
seasonality, and CRZ bottom-volume trimming.

The more demanding triple-diff specification reduces the estimate to about -2% in the binary version.
Dropping June gives a negative estimate as well, roughly -4% to -6% depending on the specification.

The diagnostics limit the interpretation:

- The 2023->2024 no-fee placebo gives a large positive CRZ-specific contrast, about +7.5% in the
  binary triple-diff.
- The placebo magnitude is large relative to the 2024->2025 estimates.
- The provider split is inconsistent: Yellow-vs-Uber is about -11.4%, while Yellow-vs-Lyft is about
  +10.3%, even though Uber and Lyft face the same USD 1.50 HVFHV fee.

## 3. Causal Interpretation

The results support a clear burden finding and several negative volume associations, especially for
HVFHV. However, the inference models do not isolate a clean causal effect of the congestion fee on
trip volume. The credibility checks show that the same designs also capture spatial,
service-specific, and provider-specific changes that are not uniquely attributable to the fee.

The main identification limits are:

- **Model 1 is descriptive by construction.** High `DS_z` zones are dense, short-trip, Manhattan-core
  zones. Those zones differ from lower-burden zones in ways that are not caused by the fee, so the
  burden-volume association cannot by itself isolate a fee effect.
- **Model 2 is weakened by placebo checks.** The exposure-gradient estimates are negative in the
  2024->2025 policy window, but both Yellow and HVFHV also show negative exposure-related estimates
  in the 2023->2024 no-fee placebo window. That suggests the model is partly capturing pre-existing
  spatial demand trends.
- **Model 3 is limited by cross-vehicle dynamics.** Comparing Yellow and HVFHV within the same zones
  helps with geography, but it relies on Yellow and HVFHV having comparable trends absent the fee.
  The no-fee placebo and the opposite-signed Uber/Lyft split show that vehicle and provider trends
  are large enough to complicate the pooled estimate.
- **The estimates are not per-dollar fee elasticities.** Model 3 compares services with different
  fares, rider populations, providers, and secular trends. The coefficient is a cross-vehicle volume
  gap, not a clean price-response parameter.

The results therefore support two distinct conclusions:

- **Burden result:** clear and stable. The fixed fee creates higher relative burden for shorter,
  lower-cost trips, especially in dense Manhattan zone-sides.
- **Volume result:** suggestive but not causal. Higher-burden or higher-exposure areas often have
  weaker volume performance, but the evidence does not cleanly establish that the fee caused the
  volume changes.

## 4. Limitations

The following limitations affect interpretation of the results:

- **Observed-trip burden.** `DS_z` is computed on observed 2025 charged trips. If the fee changed
  which trips still occurred, the observed burden distribution may not equal the counterfactual
  burden for trips that would have happened without the fee.
- **Geographic confounding.** High-burden and high-exposure zones are not random. They are strongly
  tied to Manhattan core geography, short trips, and local demand patterns.
- **Placebo evidence.** The 2023->2024 no-fee checks show sizable effects in periods without the CBD
  fee, so the DiD-style estimates cannot be read as clean fee effects.
- **Service composition.** Yellow is affected by the Flex Fare regime shift, while HVFHV is affected
  by provider mix and Uber/Lyft dynamics.
- **Shared rides.** HVFHV shared rides are a small share of rows, but they are cheaper within
  distance buckets and can affect interpretation of rider-level burden versus vehicle-level volume.
- **Exposure measurement.** Geography-based CRZ exposure is reproducible and pre-policy, but it can
  miss through-trips and leaves some nominal control zones partly exposed.

## 5. Overall Conclusion

For both Yellow and HVFHV, the fee burden is measurable,
stable, and concentrated in short, lower-cost Manhattan core trips. 

For the inference models: Model 1 is mainly a descriptive burden-volume result, Model 2
is weakened by no-fee placebo comparisons, and Model 3 is limited by the no-fee placebo and provider
split. The evidence therefore does not support a clean causal interpretation of the volume changes.

**Overall result:** the analysis supports a clear burden finding and a suggestive negative volume
signal, but it cannot cleanly establish a robust fee-attributable trip-volume reduction for Yellow Taxi or HVFHV.
