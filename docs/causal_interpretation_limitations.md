# Causal Interpretation And Limitations

This note explains how far the project can go in interpreting the burden and volume results. 

The short version is:

- The burden finding is strong: the congestion fee creates a measurable and stable relative burden
  ranking across zone-sides.
- The volume finding is suggestive: several models estimate weaker 2025 trip-volume performance in
  higher-burden or higher-exposure comparisons.
- The volume finding should not be reported as a clear causal effect of the fee, because the observed
  trip counts combine policy response, geography, service composition, provider dynamics, and
  pre-existing demand trends.

## 1. What The Current Analysis Can Support

### Burden

The project can support a clear descriptive burden claim.

The fee is mostly flat within each service, while trip cost varies widely. This makes the relative fee
burden higher for shorter, lower-cost trips and lower for longer, higher-cost trips. The EDA shows this
pattern directly for both Yellow Taxi and HVFHV. The burden notebooks also show that the zone-side
rankings are stable to reasonable base-cost floor choices.

This supports the following burden interpretation:

> The fee burden is highest in short-trip, dense Manhattan zone-sides and lower in longer-trip or
> airport-related contexts.

This is a descriptive distributional result.

### Volume

The project can support a more cautious volume claim.

Across Models 1, 2, and 3, several specifications estimate weaker 2025 trip-volume performance in
higher-burden, higher-exposure, or higher-fee comparisons. This pattern is important and worth
reporting.

However, the evidence does not isolate the congestion fee as the only explanation. The rest of this
note separates the limitation into two layers:

- data and policy-setting limitations, which affect what the measured outcome and regression
  coefficient actually represents;
- model-design limitations, which affect whether the comparison can be interpreted causally.

This supports the following volume interpretation:

> The volume models show negative associations in several places, but the evidence does not isolate a
> clear fee-caused trip-volume reduction.

## 2. Data And Policy-Setting Limitations

These limitations come from what the TLC trip data can and cannot observe, and from how the policy
operates in the real transportation system. 

### The Policy Target Is Broader Than Taxi And HVFHV Volume

The congestion-pricing policy primarily targets vehicle entry into the Manhattan core. Under the
initial 2025 toll schedule, a private passenger vehicle entering the CRZ pays a vehicle-entry toll for
the day (USD 9 in the daytime E-ZPass schedule, with a lower overnight rate), while Yellow Taxi and
HVFHV passengers pay smaller per-trip surcharges (USD 0.75 for Yellow Taxi and USD 1.50 for HVFHV).

This means the project's volume outcome is only one part of the policy setting. Yellow and HVFHV trip
counts are useful service-level outcomes, but they are not the full congestion outcome.

What this means for the regression estimate:

- A negative coefficient means completed Yellow/HVFHV trips fell more in the comparison being
  estimated. It does not by itself show whether those trips disappeared, shifted to another service,
  or moved to another mode.
- A near-zero coefficient does not mean the policy had no transportation effect, because private-car
  trips, traffic speeds, transit use, and walking/biking are outside the TLC trip data.
- If some private-car travelers switch into taxi/FHV, that can offset taxi/FHV declines and make the
  taxi/FHV estimate look less negative than the broader transportation response.

### The Data Observes Completed Trips, Not The Full Choice Set

The TLC records observe completed Yellow and HVFHV trips. They do not observe app searches, abandoned
requests, canceled plans, walking, subway use, private-car substitution, or trips that never happened.

What this means for the regression estimate:

- The coefficient measures changes in completed taxi/FHV trip volume, not total travel demand.
- The regression cannot tell whether a completed-trip decline reflects movement into an uncharged or
  lower-fee option, movement into a higher-fee private-car option, substitution across taxi/FHV
  services, or trips that no longer happen.
- If platform matching, wait time, or driver supply changes completed-trip counts, the estimate can
  move even when rider demand does not change by the same amount.

### Exposure Is Strongly Geographic

The fee applies to trips touching the Congestion Relief Zone. High-exposure zone-sides are therefore
concentrated in and around the Manhattan core, not randomly assigned across the city.

The EDA shows that this geography is not neutral:

- dense Manhattan zones have shorter trips;
- shorter trips have higher relative fee burden;
- airport and outer-borough trips have different route and cost structure;
- charged and uncharged trips differ in distance, cost, and airport exposure;
- Yellow and HVFHV have different footprints and trip composition.

What this means for the regression estimate:

- If core Manhattan demand was already declining relative to outer areas, an exposure-based estimate
  can look too negative because it partly captures that pre-existing spatial trend.
- If core Manhattan demand was recovering relative to outer areas, the estimate can look less negative
  or even positive.
- The exposure measure uses pickup and dropoff zones, not the full route. Trips that pass through the
  CRZ with neither endpoint inside it can be charged but missed by the geography rule.
- The 2023-to-2024 no-fee placebo checks are important because they test whether this geography-based
  pattern existed before the fee.

### The Burden Ratio Is Mechanically Related To Cost And Trip Length

`DS_z` is defined as:

```text
congestion fee / cost excluding the congestion fee
```

With a nearly flat fee, a higher `DS_z` usually means a lower denominator. In practice, higher-burden
zone-sides are usually shorter, lower-cost, and more concentrated in the Manhattan core. Lower-burden
zone-sides include more long-distance or airport-related trips, where the fixed fee is a smaller share
of total trip cost.

This is why `DS_z` is useful for Goal 1: it identifies where the fixed fee is a larger share of trip
cost. It is also why Model 1 cannot treat high-`DS_z` and low-`DS_z` zone-sides as otherwise
comparable groups.

What this means for the Model 1 coefficient:

- A negative burden-volume coefficient can partly reflect short-trip Manhattan market changes, not
  only fee burden.
- Very small cost denominators can make burden ratios large, which is why the burden analysis uses
  denominator-floor sensitivity checks.
- `DS_z` is computed from observed charged trips. If the fee changed which trips still occurred in
  2025, the observed burden distribution may differ from the burden distribution that would have
  existed without the fee.
- Adding controls such as distance or baseline fare changes the comparison, but it does not create a
  randomized burden contrast because those controls are themselves closely related to `DS_z`.

### Yellow Has A Separate Flex Fare Regime Shift

Yellow Taxi has a population issue that is separate from congestion pricing. Flex Fare moved from
pilot to permanent status between the 2024 and 2025 windows, and Flex volume grew sharply.

The project excludes Flex from the main Yellow volume outcome and treats it as a separate regime. That
is the right design choice for the main analysis, but it does not make Yellow a clean counterfactual
service. Flex growth can still affect the market around card/cash Yellow trips by changing rider
options, driver behavior, and the measured Yellow service mix.

Flex is also relevant because it moves Yellow closer to the HVFHV booking channel. Flex trips can be
requested through app/e-hail channels, including Uber-linked access to Yellow Taxi, so they may draw
from riders with similar habits to HVFHV users. The TLC data show completed trips, not the rider's
choice set or app search process, so we cannot directly measure how much Flex competes with Uber or
Lyft.

What this means for the Yellow regression estimate:

- The non-Flex Yellow outcome may reflect both congestion-pricing response and the remaining
  card/cash market after Flex growth.
- If Flex absorbs trips that would otherwise have been card/cash Yellow, the non-Flex Yellow estimate
  can look more negative.
- If Flex brings riders into the Yellow system who would otherwise have used HVFHV, the Yellow/HVFHV
  comparison can shift for reasons beyond fee size.

### HVFHV Cost Is Reconstructed, Not Final App Wallet Cost

HVFHV does not have a Yellow-style total amount field. The project reconstructs pre-tip passenger cost
from TLC-recorded components. This is the best available cost measure in the TLC data, but it may not
equal what the rider ultimately sees in the app after platform fees, discounts, credits,
subscriptions, refunds, or user-specific pricing.

Effect on burden and volume interpretation:

- If app-level service fees are missing from the reconstructed cost, the denominator is understated
  and measured HVFHV `DS_z` can be too high.
- If discounts or credits lower the final rider price, the direction can differ for some trips.
- Yellow and HVFHV burden rankings should therefore be read primarily within service.
- In Model 3, the Yellow-versus-HVFHV volume gap may reflect app-side price changes as well as the
  congestion fee, which limits whether it can be read as a fee-size response.

### HVFHV Shared Rides Are A Small But Different Trip Type

HVFHV shared rides are a small part of the data, but they are not identical to standard solo HVFHV
trips. They can have lower rider cost within similar distance ranges, and their availability or take-up
can change the relationship between rider-level burden and vehicle-level trip volume.

What this means for interpretation:

- For the main HVFHV analysis, shared rides are not large enough to define the overall result.
- For rider-level burden, shared rides can make the measured burden look different because the
  passenger cost denominator differs.
- For volume models, shared-ride changes are another service-composition channel rather than a direct
  fee response.

### Provider Dynamics Are Large In HVFHV

The EDA shows that HVFHV provider mix shifts modestly toward Lyft in 2025. Model 3 provider diagnostics
are even more important: Yellow-versus-Uber and Yellow-versus-Lyft move in opposite directions even
though Uber and Lyft face the same HVFHV fee.

Provider dynamics could include:

- app pricing and discounts;
- supply allocation and driver incentives;
- matching rules;
- rider composition;
- changes in shared-ride availability or take-up;
- platform-specific marketing or service quality changes.

This is plausible in the HVFHV setting because Uber and Lyft are competing platforms. Around this
period, Lyft had been trying to compete more directly with Uber through rider-facing price and product
changes, driver-side incentives, and commuter-oriented features. That external market context does not
explain the project results by itself, but it makes the provider split easier to interpret: a shift
toward Lyft can reflect platform competition as well as any response to the congestion fee.

What this means for the Model 3 coefficient:

- The pooled Yellow-versus-HVFHV estimate can be pulled by Uber-specific or Lyft-specific movement.
- Opposite Uber and Lyft diagnostics mean the pooled HVFHV estimate should not be read as a single
  platform-neutral response to the fee.
- Without app-side pricing, search, matching, and demand data, the public TLC records cannot fully
  separate fee response from provider-specific market movement.

## 3. Model-Design Limitations

These limitations are about the comparison each model uses. For a model to support a causal reading,
its comparison group has to represent what would have happened without the congestion fee. The issue
is not only whether the coefficient is negative. The issue is whether the required comparison
assumption is believable.

### Model 1

Model 1 asks whether higher-burden zone-sides lost more trips. It is useful as a first descriptive
check after the burden ranking is defined.

For Model 1 to have a causal interpretation, high- and low-burden zone-sides would need to be
otherwise comparable, or the controls would need to remove the relevant differences between them.
That is a very strong assumption.

The assumption can break because higher-burden zone-sides are usually shorter, lower-cost, and more
concentrated in the Manhattan core. Lower-burden zone-sides include more long-distance or
airport-related trips. These are different trip markets, not just different levels of fee burden.

Controls can show whether the association is stable, but they cannot turn the cross-zone comparison
into a causal estimate. Model 1 should therefore be read as a descriptive burden-volume association.

### Model 2

Model 2 asks whether more-exposed zone-sides changed more than less-exposed zone-sides from 2024 to
2025.

For Model 2 to have a causal interpretation, higher- and lower-exposure zone-sides would need to have
moved similarly without the fee. This is the parallel-trends assumption in this setting. The monthly
panel and pre-policy exposure definition make this design stronger than Model 1, because the
treatment measure is not built from 2025 outcomes and the model can compare monthly changes.

The assumption can break if high-exposure Manhattan-core zones were already moving differently from
lower-exposure zones before congestion pricing. The 2023-to-2024 no-fee placebo checks directly test
this concern. Both services show negative exposure-related estimates in a period before the policy,
which suggests Model 2 is partly capturing pre-existing spatial demand trends.

Model 2 should therefore be reported as an exposure-volume association, not a clear causal estimate.

### Model 3

Model 3 is included as exploratory, diagnostic, and triangulation evidence. It compares Yellow
card/cash and HVFHV monthly trip-count changes inside the same exposed zones. This holds geography
more fixed than the within-service comparisons, but it remains a cross-service DiD-style comparison
under strong service-comparability assumptions. Service identity stands in for the fee difference;
it also captures differences in riders, booking channels, pricing, providers, and secular trends.

The primary CRZ estimate shows that HVFHV changed about 5.9% more negatively than Yellow from 2024
to 2025. The more demanding triple-difference estimates attenuate: the binary estimate is about
-2.2%, while the continuous-exposure estimate is about -1.9% and its confidence interval includes
zero.

The diagnostics do not support a clean causal fee-size interpretation:

- The 2024 Yellow-HVFHV pre-policy gap is not flat.
- The 2023-2024 no-fee placebo produces large nonzero, opposite-signed cross-service contrasts.
- Yellow-versus-Uber and Yellow-versus-Lyft estimates have opposite signs even though Uber and Lyft
  face the same HVFHV fee.
- Yellow Flex growth can affect the remaining card/cash market and cross-service substitution.
- HVFHV provider, platform-pricing, and shared-ride dynamics can change completed trip counts for
  reasons other than the congestion fee.

Model 3 therefore documents a 2025 cross-service volume gap that is consistent with several possible
mechanisms, including a fee response. It does not identify a clean causal effect of the fee
difference, and it should not be described as a per-dollar fee elasticity or as causal proof.

## 4. What Additional Information Could Help

Additional information could improve the interpretation, but it would also expand the scope of the
project. The following points are future directions rather than missing pieces of the current
analysis.

### More Pre-Policy Time

A longer pre-policy panel would help test whether high-exposure zones, low-exposure zones, Yellow,
HVFHV, Uber, and Lyft were already moving differently before the fee.

Useful additions:

- more months from 2023 and 2022;
- the same Feb-Jun window across multiple pre-policy years;
- monthly or weekly panels by zone, direction, service, and provider;
- pre-specified placebo windows and event-study style plots.

This would not solve all problems, but it would make the parallel-trends assumption more inspectable.
For this project, however, fully rebuilding additional years of Yellow and HVFHV panels at the same
level of cleaning, feature construction, and diagnostics is outside the current scope.

### Better Cross-Mode Data

Cross-mode data could help explain where riders may have gone when completed taxi/FHV trips changed.
But this is not a simple missing-column problem. Much of the relevant behavior is hard to observe at
the same trip, rider, time, and geography level as the TLC data.

Examples of useful context data include:

- subway station entries near high-burden zones;
- bus ridership;
- Citi Bike trips;
- pedestrian counts if available;
- traffic counts or vehicle entries into the CRZ;
- parking or curb activity data;
- aggregated private-vehicle volume and speed data.

Even if these data were available, they would introduce a broader research design. Subway entries,
bike trips, pedestrian counts, and vehicle speeds have their own seasonality, geography, user base,
and policy shocks. They would help place the taxi/FHV results in the transportation context, but they
would not automatically identify the causal effect of the fee on Yellow or HVFHV trips.

In other words, cross-mode data would be most useful for a larger question: how the policy changed
the transportation system as a whole. The current project is narrower: it measures burden and observed
trip-volume changes inside TLC taxi/FHV data.

### Better App-Side HVFHV Information

For HVFHV, stronger interpretation would require information not present in public TLC trip records.

Most useful would be:

- final rider wallet price;
- app-level service fees;
- discounts, credits, subscriptions, and refunds;
- fare quotes before booking;
- canceled or abandoned requests;
- provider-specific pricing and matching changes;
- driver supply and incentive information.

Without this information, the project can describe completed HVFHV trips and reconstructed cost, but
it cannot fully separate fee response from app-side market dynamics.

### Provider-Specific Baselines

One possible improvement is to model Uber and Lyft separately before pooling HVFHV. This can help
measure provider-specific baseline movement and reduce the risk that the pooled HVFHV estimate is
driven by one platform.

Potential approaches:

- estimate Model 2 separately for Uber and Lyft;
- include provider-specific pre-trend plots;
- compare low-exposure Uber/Lyft movement to high-exposure Uber/Lyft movement;
- use provider fixed effects and provider-specific month patterns in a richer panel;
- report pooled HVFHV only after showing that provider-specific estimates point in similar
  directions.

This can improve credibility, but it cannot fully solve the problem if provider changes differ
precisely in the same places and months as the fee exposure.

## 5. What Would Be Needed For Stronger Causal Claims

The answer depends on the target claim.

### Narrower Claim

A more plausible causal claim would be narrow:

> In the observed Yellow/HVFHV trip data, higher CRZ exposure is associated with additional volume
> changes after accounting for pre-policy trends and selected comparison groups.

With more pre-policy years, stronger placebo checks, provider-specific modeling, and external
transportation controls, this claim could become more credible. It would still need careful wording.

### Service-Level Causal Claim

A harder claim would be:

> The congestion fee caused an X% reduction in Yellow or HVFHV trip volume.

This is difficult because taxi/FHV volume is affected by geography, provider dynamics, product
changes, app pricing, rider substitution, and broader city travel demand.

The public TLC data alone is probably not enough for this claim unless the effect is very large,
stable across many designs, absent in all placebo checks, and consistent across providers and
services.

### System-Wide Congestion Claim

The hardest claim would be:

> The congestion fee reduced overall travel or congestion by X% through changes in taxi/FHV demand.

This project is not designed for that claim. The policy's largest direct toll is on vehicles entering
the Manhattan core, especially private passenger vehicles, while Yellow Taxi and HVFHV are charged
through smaller per-trip passenger surcharges. Taxi/FHV trip counts are therefore an important
service-specific outcome, but they are not the full policy outcome. A full congestion evaluation would
need vehicle counts, speeds, transit ridership, private-vehicle behavior, and possibly emissions or
travel-time data.

## 6. Bottom Line

The causal uncertainty is part of the result. In this policy setting, completed taxi/FHV trip counts
combine fee response, geography, service substitution, provider behavior, and broader transportation
demand.

The strongest contribution is therefore two-part:

1. a stable burden ranking showing who faces the highest relative fee burden; and
2. an evidence ladder showing that observed taxi/FHV volume changes are suggestive but not directly
   attributable to the fee with the available data.
