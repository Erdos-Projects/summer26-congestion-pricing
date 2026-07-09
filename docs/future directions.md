# Future Directions

This document summarizes future work that would extend the analysis beyond the current project
scope. The detailed causal and data limitations are documented separately in
[`causal_interpretation_limitations.md`](causal_interpretation_limitations.md). The emphasis here is on
additional designs, data sources, and reproducibility improvements that would strengthen a later
policy evaluation.

## 1. Stronger Causal Designs

The current analysis supports a stable burden ranking and suggestive volume associations, but it does
not establish a clean causal fee effect. A stronger causal design would require clearer
counterfactual evidence for what taxi and HVFHV volume would have been without the congestion fee.

Promising extensions include:

- **Longer pre-policy panels.** Additional pre-policy months or years, such as 2022 and 2023, would
  allow exposure-group and vehicle-trend assumptions to be inspected over multiple comparable
  windows.
- **Event-study style estimates.** Monthly or weekly panels around January 2025 would show whether
  volume changes appear at policy implementation and whether they persist, fade, or reverse.
- **Matched-zone comparisons.** High-burden or high-exposure zone-sides could be compared with
  lower-exposure zone-sides with similar pre-policy volume, distance, cost, borough, and airport
  composition.
- **Boundary or near-boundary comparisons.** If TLC zone geography supports it, zones near the CRZ
  boundary could provide comparisons where neighborhood context is more similar but exposure differs.
- **Provider-specific HVFHV models.** Key HVFHV models could be estimated separately for Uber and
  Lyft before pooling, because provider movement is large enough to affect interpretation.

These designs would still require placebo checks and sensitivity analysis. More flexible models would
not, by themselves, solve omitted-confounder problems unless they also improve the comparison group
or the credibility of the counterfactual.

## 2. Broader Transportation Context

TLC data observe completed taxi and HVFHV trips. They do not show whether riders switched to another
mode, skipped a trip, drove privately, or changed timing. A broader policy evaluation would need
external data.

Relevant external sources include:

- subway station entries and exits near high-burden zones;
- bus ridership or bus-speed data;
- Citi Bike trip counts;
- pedestrian or curb-activity data where available;
- traffic counts, vehicle entries, and speed data for the CRZ;
- Green Taxi or smaller FHV records as supplemental service tracks.

These sources would help answer whether observed taxi/HVFHV changes reflect mode substitution or a
larger transportation-system change. Each source would require separate cleaning, seasonality checks,
and geographic alignment before it could be combined with TLC trip records.

## 3. Better HVFHV Price And Platform Data

HVFHV passenger cost is reconstructed from public TLC fields. Stronger interpretation would require
platform-side information that is not available in the public trip records.

Useful additions include:

- final rider wallet price;
- platform fees, discounts, subscriptions, credits, refunds, or promotions;
- fare quotes before booking;
- canceled or abandoned requests;
- provider-specific matching, wait-time, and driver-supply information;
- driver incentives and provider-side pricing changes.

These data would help distinguish congestion-fee response from Uber/Lyft platform competition and
app-specific market changes.

## 4. Additional Burden And Equity Questions

The current burden result is stable within the TLC data. A later extension could examine which riders,
neighborhoods, or trip types are most exposed to the fee burden.

Potential analyses include:

- joining TLC zones to ACS or other neighborhood demographic measures to study whether high-burden
  zones are associated with income, commuting patterns, or other equity-relevant measures;
- examining time-of-day and day-of-week burden patterns, especially commute versus evening/weekend
  trips;
- studying airport corridors separately, since airport trips are longer, higher-cost, and lower-burden
  than core Manhattan trips;
- treating driver pay as an outcome, not a post-policy control, to study whether driver-side patterns
  differ in high-burden or high-exposure areas;
- exploring trip-purpose proxies where defensible, while being clear that TLC records do not directly
  observe trip purpose.

## 5. Reproducibility And Communication Improvements

Additional reproducibility work would make the analysis easier to audit and extend.

- A final-results notebook would reproduce the exact tables and figures used in the presentation.
- Final figures can be organized under `results/` by analysis stage: EDA, feature work, burden
  analysis, and modeling.
- A single command or script would improve reproducibility by regenerating the key final tables and
  plots from the processed data.
- Final wording can remain aligned with the main interpretation: stable burden ranking,
  suggestive volume associations, no clean causal volume claim.
- Presentation claims can link to the notebooks, result files, and documentation that reproduce
  them.
