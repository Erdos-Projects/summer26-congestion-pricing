# EDA Summary

This file summarizes what we learned from the exploratory analysis and how those findings shaped the data audit, feature selection, and feature engineering choices. It is a guide to the EDA evidence, not a replacement for the full notebooks.

Sources:

- `notebooks/yellow_taxi_sample_EDA.ipynb`
- `notebooks/yellow_taxi_full_EDA.ipynb`
- `notebooks/hvfhv_sample_EDA.ipynb`
- `notebooks/hvfhv_full_EDA.ipynb`
- `docs/yellow_data_audit.md`
- `docs/hvfhv_data_audit.md`
- `docs/yellow_dropped_and_engineered_features.md`
- `docs/hvfhv_dropped_and_engineered_features.md`

## 1. What The Sample EDA Was For

The sample EDA was used as a first-pass diagnostic, not as the final source for aggregate claims. The full standardized data is large: Yellow Taxi has roughly 37 million trips in the Feb-Jun 2024 and Feb-Jun 2025 windows, and HVFHV has roughly 202 million trips across the same windows. Running every exploratory chart on the full data first would be slow and hard to iterate on.

The samples made the early EDA fast enough to inspect distributions, test definitions, and discover where the two services differ before running full-data checks. They were especially useful for finding missingness patterns, payment-regime issues, potential outliers, and candidate engineered features.

The sample findings were later treated in two ways:

- Findings that held up on full data were carried into the audit and feature documentation.
- Findings that looked sample-specific were revised or dropped.

## 2. What The Full-Data EDA Was For

The full-data EDA was used to validate the findings that matter for reporting and documentation. After the sample EDA identified the main questions, the full-data notebooks checked whether those patterns held at scale. Final descriptive statements should come from full-data aggregates whenever possible.

The full-data notebooks are especially important for:

- monthly volume and cost patterns;
- payment-regime differences;
- charged versus uncharged trip composition;
- distance and burden patterns;
- zone and OD rankings;
- validating data-quality rules before building `DS_z`.

## 3. Yellow Taxi: Key EDA Findings

### Payment Regimes Matter

Yellow Taxi has several payment regimes, and they should not be pooled for every question.

Card/cash trips are the cleanest population for cost and burden analysis because they have reliable fare components and a metered fare structure. Flex Fare trips are different: they are upfront-priced, have missing or bundled components, and grew sharply between the 2024 and 2025 windows.

This means:

- burden and cost analysis use card/cash trips only;
- volume analysis excludes Flex but keeps all real non-Flex trips — card/cash plus a small irregular-payment group;
- Flex is reported separately as a regime shift, not treated as ordinary noise.

The irregular-payment group is the no-charge and dispute payment types — about 1.9% of non-Flex trips (the data contains no voided trips). These are real completed trips: the ride happened, only the payment was comped or disputed, so their distance and duration look like ordinary trips. They are therefore counted in volume, but excluded from cost and burden analysis where their fare is unreliable.

### Flex Growth Explains The Raw Yellow Volume Increase

Raw Yellow volume rises from 2024 to 2025, but this is mostly a Flex adoption story. Over the Feb-Jun window, all-yellow volume rises, while the fee-relevant non-Flex population is roughly flat and Flex grows sharply.

This timing is important. Flex Fare was not just gradually present in the market; the TLC upfront-pricing Flex Fare program moved from pilot to permanent status between our two windows. The rule package was adopted on August 14, 2024 and became effective on September 21, 2024. That means the pre-window, Feb-Jun 2024, is before the permanent program, while the post-window, Feb-Jun 2025, is after it.

This finding is central to the Yellow design. It is why the Yellow volume outcome uses non-Flex trips rather than all Yellow trips. Without this split, the analysis would mix congestion-pricing exposure with a separate product-adoption shift.

### Cost Components Should Not Be Rebuilt Naively

Yellow `passenger_cost_pretip` is defined as `total_amount - tip_amount`. The EDA found that rebuilding cost by summing itemized components can double-count some charges. The project therefore uses the standardized pre-tip passenger cost instead of reconstructing cost from every fee component.

## 4. HVFHV: Key EDA Findings

### HVFHV Volume Is Roughly Flat Overall

HVFHV full-data volume is roughly flat to slightly down between the Feb-Jun 2024 and Feb-Jun 2025 windows. This differs from the raw Yellow pattern because Yellow has the separate Flex adoption issue.

The HVFHV track therefore does not need the same Flex/non-Flex split, but it does need careful provider and trip-composition checks.

### Passenger Cost Is Reconstructed

HVFHV does not have a Yellow-style `total_amount`. The project reconstructs pre-tip passenger cost from TLC-recorded components such as base fare, tolls, tax, surcharges, airport fee, and CBD fee.

This is the best available TLC-field cost measure, but it may not equal the final app-wallet price after discounts, credits, subscriptions, or platform-specific adjustments. HVFHV cost findings should therefore be described as reconstructed TLC passenger cost.

### Provider Mix Changes Over Time

Provider mix is an important HVFHV context variable. In the Feb-Jun totals, Uber's share falls from about 74.5% in 2024 to 72.2% in 2025, while Lyft's share rises from about 25.5% to 27.8%.

The month-to-month pattern is not perfectly monotonic: February looks similar across years, but from March through June 2025 Lyft's share is consistently higher than in the matching 2024 months. So the useful summary is not random fluctuation; it is a modest shift toward Lyft in the post-policy window.

This is useful descriptive context for HVFHV: the provider mix is a moving background variable, so provider-specific movement should be kept visible. Provider is context here, not a standard control, unless the analysis is explicitly asking a provider-specific question.

### Shared Rides Are A Small HVFHV Context Group

HVFHV includes two shared-ride fields: `shared_request_flag` and `shared_match_flag`. In the Feb-Jun
full-data window, shared rides are small and almost entirely Uber. About 3.7% of 2024 trips and 3.1%
of 2025 trips requested sharing; about 1.4% of 2024 trips and 1.7% of 2025 trips were actually
matched. Lyft has essentially no shared-ride volume in this window.

Shared-request trips have lower median reconstructed passenger cost than non-shared trips, but they
also have longer median distance and duration. So shared status is useful context for HVFHV trip
composition, not a separate main population like Yellow Flex.

The current HVFHV burden and volume summaries pool shared and non-shared trips. That is the main
EDA definition used here because the shared group is small and mostly nested inside the Uber side of
the provider mix. The limitation is that discounted shared rides can carry a higher fee burden
relative to base cost, so the pooled HVFHV burden summary includes a small shared-ride composition
layer. This should be noted as a limitation rather than treated as a separate main population.

## 5. Cross-Service Lessons From EDA

### The Two Services Are Analyzed Separately Because Their Cost Is Not Comparable

The two services are not pooled — not just because their cleaning differs, but because their cost,
and therefore their burden, is not measured on the same footing.

Yellow card/cash cost is a metered `total_amount − tip`; HVFHV cost is reconstructed from TLC fee
components and set by app pricing; and the fees themselves differ ($0.75 Yellow vs $1.50 HVFHV).
Everything the project reports — the descriptive cost and burden work — rests on the fee-burden
quantity `DS_z = fee / pre-fee cost`. Since neither the cost base nor the fee is comparable across
services, `DS_z` is only comparable *within* a service. So the burden ranking is built per service and
never pooled, and any cross-service comparison is done on *volume* movement, not pooled burden.

The services do share the same broad study window and zone-direction logic; the data-quality
decisions diverge only where the raw structure differs — Yellow's Flex payment regime versus HVFHV's
reconstructed cost and provider mix.

### Non-Movement Rows: Handled Differently By Service And Comparison

Zero-distance trips are not all the same. Some are likely real trips with bad distance recording, while others look like cancellations, meter errors, or non-movement rows. Non-movement rows are defined as:

```text
zero distance AND (PU == DO OR duration < 60 seconds)
```

These are treated as invalid for Yellow's trip-count and burden analyses — about 0.6% of card/cash trips, a share large enough to matter for the burden ratio. For HVFHV-only EDA, they are kept because they are roughly 0.014% of trips, too small to move the descriptive summaries. In cross-vehicle comparisons, the common panel drops non-movement rows for both services so Yellow and HVFHV use the same row rule.

### Charged vs Uncharged Composition Differs By Service, In Opposite Directions

In both services, charged (CRZ-touching) trips are not just uncharged trips plus a fee — they differ
in length and route type. But the *direction* of the composition difference is not the same across
services, and it reflects each service's own mechanism rather than the fee.

For Yellow (full EDA §9; 2025 card/cash), charged trips are more expensive (median $19.25 vs $16.10)
and a little longer, yet not-charged trips are far more airport-heavy (airport-trip share 17.3% vs
5.1%).
This follows from how Yellow operates: it is largely a Manhattan street-hail service, so its ordinary
trips are short dense-core rides that touch the CRZ, while its main business outside the core is
airport runs (JFK/LaGuardia, outside the CRZ) — so "not charged" skews toward airports.

For HVFHV (full EDA §8) the airport pattern is
reversed: charged trips are *more* airport-exposed (airport-fee share 10.2% vs 7.6%), as well as
longer (median 3.76 vs 2.66 mi) and much more expensive (median pre-tip cost $36.29 vs $18.73). As a citywide app-dispatch
service, HVFHV's charged trips are a selected longer, Manhattan-bound subset, not its typical trip.

The lesson is the same for both: a charged-versus-uncharged contrast is a route/geography selection,
not enough by itself to isolate a fee-specific volume change. The opposite airport direction is also a reminder that the two services have
genuinely different footprints and should not be pooled.

Separately, the geographic CRZ rule — whether a zone touches the CRZ — matches the observed 2025 charge
flag about 96% of the time for Yellow (HVFHV geo-only misses ≈ 5.6% of charged trips), so CRZ
membership is a reliable, fee-independent proxy for exposure that still applies to the no-fee years.

### Both Services Show Strong Weekly and Hourly Structure

Daily volume in both services is strongly weekly-seasonal: the lag-7 autocorrelation clearly exceeds
lag-1 (HVFHV ≈ 0.83 in 2024 and 0.86 in 2025; Yellow shows the same pattern, confirmed by an STL
decomposition), and Yellow volume and cost both peak on Thursday. CBD exposure is also uneven across
the day — for HVFHV the charged share peaks around 9 PM (≈ 40%) and is lowest around 7 AM (≈ 28%),
with median base-cost burden highest in the early evening; Yellow shows the same low-early-morning,
high-late-night shape.

This regular structure has to be accounted for before comparing volume changes across time, so within-window
seasonality is inspected rather than treated as noise. The hourly exposure curve is also a useful
descriptive KPI for the burden story.

### `DS_z` Is A Burden Metric — Regressive In Trip Length And Collinear With Geography

`DS_z` measures how large the CBD fee is relative to the trip's pre-fee cost — the right quantity for
the burden-ranking goal.

Because the fee is mostly flat within each service, the relative burden is higher when the underlying
fare is small: shorter, cheaper trips carry a larger fee share than longer ones, in **both Yellow and
HVFHV**. Burden is therefore clearly regressive in trip length. On full data the tail is thinner than
the sample suggested — the Yellow p99 relative burden is about 7.6%, not the ~25% the sample implied —
which is why the burden work uses medians and a base-cost floor rather than raw tail values.

The same mechanism makes `DS_z` collinear with geography: higher `DS_z` means lower base cost and
shorter trips, and dense-core zones tend to have shorter trips. The EDA measures this directly — for
Yellow, `Pearson(DS_z, 2024 trip distance) ≈ −0.82`. So at the zone level, high burden, short trips,
and dense-core geography are nearly the same signal, and any cross-zone association between burden and
volume is confounded by geography and trip economics.

This is why the burden ranking stands on its own, but a cross-zone burden-volume association cannot be interpreted from EDA alone as a fee-specific volume change.

## 6. Summary

The EDA shows that Yellow Taxi and HVFHV cannot be summarized with one pooled trip table. The two
services have different payment structures, cost fields, product regimes, provider mixes, and trip
composition patterns. Those differences matter before the results are interpreted.

The main EDA takeaways are:

1. The full-data window is large enough that sample EDA should be treated as diagnostic only.
2. Yellow Taxi volume is strongly affected by Flex growth, so all-Yellow volume is not a clean summary of the core Yellow trend.
3. Yellow card/cash trips have the cleanest fare components for burden and cost summaries.
4. HVFHV passenger cost must be read as reconstructed TLC cost, not final app price.
5. HVFHV provider mix shifts modestly toward Lyft in 2025.
6. Shared rides are small and mostly Uber, so pooling them is reasonable but should be noted.
7. Charged and uncharged trips differ in route composition, especially airport exposure.
8. Fee burden is highest on shorter, lower-cost trips, so burden patterns are closely tied to trip length and geography.
