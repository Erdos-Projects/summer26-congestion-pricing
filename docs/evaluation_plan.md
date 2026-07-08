# Evaluation Plan

This file evaluates the project's two linked parts. The burden-ranking part is descriptive: it is
evaluated by whether the fee-burden metric is clearly defined and stable enough to rank zones. The
volume-modeling part is inference-oriented: it asks whether the congestion fee changed rider
behavior, and whether the estimates are credible enough to interpret.

Evaluation for the inference part therefore means checking five things:

1. Is the burden metric defined consistently?
2. Is the comparison meaningful?
3. Is the estimate stable across reasonable modeling choices?
4. Does the same design behave sensibly in a no-fee comparison?
5. Do the different models tell a consistent story?

The per-model results live in the notebooks. This file only defines how we evaluate the designs.

Companion files (both services):

- Shared design: [`burden_analysis_and_modeling_plan.md`](burden_analysis_and_modeling_plan.md).
- Data audits: [`yellow_data_audit.md`](yellow_data_audit.md), [`hvfhv_data_audit.md`](hvfhv_data_audit.md).
- Build pipelines: [`../scripts/yellow_ds_pipeline.py`](../scripts/yellow_ds_pipeline.py); [`../scripts/01_pipeline.py`](../scripts/01_pipeline.py) with [`../scripts/hvfhv_model2_monthly_panel.py`](../scripts/hvfhv_model2_monthly_panel.py) and [`../scripts/hvfhv_pretrend_placebo.py`](../scripts/hvfhv_pretrend_placebo.py).
- Goal-1 burden notebooks: [`../notebooks/yellow_burden_ranking_and_heterogeneity.ipynb`](../notebooks/yellow_burden_ranking_and_heterogeneity.ipynb), [`../notebooks/hvfhv_burden_ranking_and_heterogeneity.ipynb`](../notebooks/hvfhv_burden_ranking_and_heterogeneity.ipynb).
- Goal-2 model notebooks: [`../notebooks/yellow_model1_model2.ipynb`](../notebooks/yellow_model1_model2.ipynb), [`../notebooks/hvfhv_model1_model2.ipynb`](../notebooks/hvfhv_model1_model2.ipynb).
- Cross-vehicle Model 3: [`../notebooks/model3_cross_vehicle.ipynb`](../notebooks/model3_cross_vehicle.ipynb).

---

## Goal 1: Burden Ranking

Goal 1 is evaluated as a descriptive burden analysis. It asks whether the relative fee burden can be
ranked clearly and consistently across zone-sides.

For the burden ranking, we check:

- **Metric definition.** `DS_z` must use a clear numerator and denominator: congestion fee divided
  by trip cost excluding the fee, then aggregated to zone × direction.
- **Population consistency.** The trips entering the burden metric should match the fare fields used
  to define the denominator. For Yellow, this means card/cash trips for the main fare-based burden
  metric. For HVFHV, this means the standardized HVFHV passenger-cost measure.
- **Directional consistency.** Pickup and dropoff sides should be reported separately, with any
  combined zone view treated as an overview.
- **Base-cost floor sensitivity.** The top ranking should not be an artifact of near-zero base
  costs. Recompute the ranking under nearby floor choices and compare rank correlations and top-zone
  overlap.
- **Mean and median.** Report both. A stable story across mean and median is stronger than a ranking
  carried by a few unusually high ratios.
- **Geographic interpretation.** Summarize the ranking by borough/core geography, airport-related
  zones, and trip-length groups so the reader can see whether high burden is mainly a short-trip or
  core-zone pattern.

A successful Goal 1 result is a stable and interpretable burden ranking. Trip-volume interpretation
comes from the modeling sections below.

---

## 1. Identification

For each model, we state the comparison and the assumption that makes the comparison interpretable.

- **Model 1: `DS_z` vs volume change.** This is a cross-zone comparison using the burden metric from
  Goal 1. It is useful for a first descriptive look, but it is not a clean causal design because high
  `DS_z`, short trips, dense Manhattan zones, and being charged are closely related.

- **Model 2: CRZ exposure DiD.** This compares higher-exposure zone-sides with lower-exposure
  zone-sides over time. The key assumption is that, without the fee, higher- and lower-exposure
  places would have moved similarly. We check this with the 2024 pre-period view, the 2023→2024
  placebo, the within-Manhattan comparison, and the binary-vs-continuous exposure comparison.

- **Model 3: cross-vehicle DiD.** This compares yellow and HVFHV within the same exposed zones. The
  key assumption is that, without the fee-size difference, yellow and HVFHV would have moved similarly
  within those zones. We check this with the 2024 pre-trend, the 2023→2024 placebo, the Uber-vs-Lyft
  provider split, matched populations, and zone alignment.

---

## 2. Robustness And Sensitivity

These checks ask whether the estimate depends on a reasonable modeling choice.

- **Weighting.** Equal-weighted and volume-weighted estimates answer different questions. Equal-weighted
  treats each zone-side equally; volume-weighted gives more influence to high-volume places. Both
  should be reported and interpreted separately.

- **Sample cutoff.** Low-volume zone-sides can be noisy. We check whether the estimate changes when
  thin units are removed. Only trims that remove a small share of units are useful for the main
  comparison; very large trims create a different sample.

- **Treatment definition.** A binary CRZ/non-CRZ split is easy to read, but many non-CRZ zone-sides
  still have trips touching the CRZ. The continuous `charged_share` version is the primary exposure
  measure; the binary version is reported as a comparison.

- **Model specification.** For Model 1, show the raw association and the versions with borough and distance controls. We do this to show whether the DS_z coefficient stays similar or changes when the comparison is adjusted.

- **Reporting redundancy.** Report `DS_z` as mean and median; report correlations as Pearson and
  Spearman; report estimates with confidence intervals. This prevents one statistic from carrying the
  whole claim.

- **Base-cost floor.** For the burden ranking, recompute `DS_z` under several base-cost floors and
  check whether the ranking is stable.

---

## 3. Placebo Checks

Placebo checks run the same logic in settings where the fee should not be driving the result.

- **2023→2024 placebo.** Run the same DiD setup on a no-fee year pair. If the estimate is large in a
  no-fee period, the design may also be picking up pre-existing time patterns. June 2023 is excluded
  because Canadian wildfire smoke depressed NYC traffic that month.

- **Provider split for Model 3.** Uber and Lyft both pay the same HVFHV fee. If the pooled HVFHV
  result mainly reflects the fee, the Uber and Lyft comparisons should point in the same direction.
  Opposite signs would suggest Uber/Lyft-specific changes are large enough to complicate the pooled
  yellow-vs-HVFHV comparison.

- **Low-exposure check for Model 3.** In zones with very little CRZ exposure, the yellow-vs-HVFHV gap
  should be close to zero. Because this sample can be small, this check is supportive rather than
  decisive.

---

## 4. Standard Errors

For the panel models, standard errors are clustered by zone because the same zone appears repeatedly
across months and directions. Treating those rows as fully independent would overstate precision.

Neighboring zones may also move together, but spatial standard errors are out of scope here. We note
this limitation rather than treating the current confidence intervals as the final word.

---

## 5. Estimand

Each number should be labeled by what it estimates.

- **Model 2.** `post:charged_share` compares higher-exposure zone-sides with lower-exposure
  zone-sides. It is not a trip-level charged-vs-uncharged comparison.

- **Model 3.** `post:hvfhv` compares the higher-fee service with the lower-fee service inside the
  same exposed zones. It is not the effect of having a fee versus no fee.

- **Weighting.** Equal-weighted and volume-weighted versions have different estimands: average
  zone-side vs average trip/rider.

---

## 6. Triangulation

The three models have different weaknesses, so we compare them rather than relying on one result.

- Goal 1 is best for the burden ranking.
- Model 1 is the first descriptive check of whether that ranking lines up with volume change.
- Model 2 adds a time dimension and a lower-exposure comparison group.
- Model 3 holds geography more fixed by comparing yellow and HVFHV within the same exposed zones, but
  relies on a cross-vehicle trend assumption.

Agreement across the models would strengthen the interpretation. Disagreement helps identify which
assumption needs more caution.

---

## 7. Reporting Decision Rules

To report a clean fee-related volume reduction, the estimate should be:

- negative;
- reported with a confidence interval;
- reasonably stable across weighting and sample choices;
- not present in the no-fee placebo comparison;
- and not dependent on a comparison group that is itself partly exposed.

If an estimate does not clear that bar, report it as not cleanly established rather than turning it
into a positive causal claim. For the burden goal, the standard is different: success means a stable
and interpretable zone ranking, not a causal volume estimate.
