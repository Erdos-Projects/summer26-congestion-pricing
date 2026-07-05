# Evaluation Plan — CBD Congestion Pricing (yellow taxi + HVFHV)

This project estimates an **effect** (did the CBD congestion fee change rider behavior), so
"evaluation" is **not** predictive accuracy — there is no label to predict and no train/test split.
Evaluation here means: **is the causal estimate credible?** That breaks into four questions —
*is it identified*, *is it robust*, *does it survive a placebo*, and *do independent designs agree* —
plus honest statements of *what the estimand is* and *what would count as an effect*. The framework
below applies to **both vehicle tracks**; each track instantiates it on its own estimates (a check
that passes for one vehicle need not pass for the other).

Companion docs: the design is in [`modeling_plan.md`](modeling_plan.md); each track has its own data
audit, DS_z pipeline, and modeling notebook (e.g. [`yellow_data_audit.md`](yellow_data_audit.md),
[`../scripts/yellow_ds_pipeline.py`](../scripts/yellow_ds_pipeline.py),
[`../notebooks/yellow_model1_model2.ipynb`](../notebooks/yellow_model1_model2.ipynb)).

## The predictive checklist, mapped to inference

| Predictive-ML step | Why it does not apply | Inference analog we use instead |
|---|---|---|
| train / test split | we estimate an effect, not a prediction | the **comparison / control group** *is* the test of the claim |
| accuracy / RMSE / AUC | no outcome label | **effect size + confidence interval** |
| cross-validation | — | **sensitivity** across specs, samples, weights |
| overfitting | — | **over-controlling / spec-mining** → declared specs + sensitivity checks |
| baseline model | — | **placebo** (2023, no fee) = the null baseline |
| generalization to new data | — | **agreement across designs** (M1/M2/M3) and vehicles (yellow/HVFHV) |

---

## 1. Identification — is the estimate interpretable as causal?

Each model rests on an assumption; evaluation states it and checks it.

- **Model 1 (cross-zone `DS_z`↔volume).** Assumes `DS_z` varies independently of the confounds.
  Where "charged", "dense/short-trip", and "high `DS_z`" collapse to nearly the same object at the
  zone level, the coefficient is **not identified** — it swings with the control set. Model 1 is then
  evaluated by **documenting the non-identification honestly** (a spec-swing decomposition) and used
  only for the **burden ranking** (Goal 1) and a correlational look, never as a causal effect.
- **Model 2 (geographic exposure-gradient DiD).** Assumes low-exposure zone-sides are a valid
  counterfactual for high-exposure ones (**parallel trends**), that exposure is exogenous (measured
  **pre-policy**), and no differential spillover. Checks: pre-trend inspection, placebo,
  within-core-vs-periphery, spillover discussion.
- **Model 3 (cross-vehicle DiD).** Assumes yellow and HVFHV would move together in the same zone
  absent the fee-size difference. Checks: pre-trend on the two vehicles, matched populations (so
  cross-service substitution does not move volume between the compared services), zone alignment.

## 2. Robustness / sensitivity — does the estimate survive reasonable alternative choices?

An effect that flips or vanishes under a defensible alternative is not a finding. Report the
**range**, not a single number.

- **Weighting (estimand-defining).** Equal-weighted zone-sides vs weighted by baseline volume —
  these answer different questions (*average zone-side* vs *average trip/rider*). Report both and
  label which each answers.
- **Sample cutoff.** Sweep the minimum monthly volume; interpret only **non-distorting trims** as
  robustness checks (e.g. dropping ≤10% of zone-direction units). Extreme cutoffs that remove most of
  the sample change the estimand and should not be read as evidence for or against the original
  design.
- **Treatment definition.** Continuous exposure (`charged_share`, primary) vs a binary charged/control
  split — the gap between them measures the control-group contamination.
- **Base-cost floor (`DS_z`).** Recompute at $0.50 / $1 / $2 / $5 and check rank stability.
- **Reporting redundancy.** `DS_z` as **mean and median**; every correlation as **Pearson and
  Spearman**; effects always with a **confidence interval**.
- **Specification.** Report the control decomposition (raw / each control / all) rather than a single
  "preferred" model, so the reader sees the stability directly.

## 3. Placebo / falsification

- **2023-vs-2024 placebo (primary).** Re-run the DiD on a no-fee year pair. A non-null "effect" there
  means the design is picking up secular trends, not the fee. *Requires downloading and standardizing
  the earlier year — a separate data task; not a blocker for the main estimates.*
- **Standing in for the placebo until then:** pre-window seasonality (no obvious differential movement
  by exposure), a within-core comparison (reduces, but does not eliminate, the geography confound —
  the within-core control is itself partially exposed), and the binary-vs-dose comparison — a
  **limited** credibility statement, explicitly not a full parallel-trends test.

## 4. Standard errors

- **Cluster by zone** for the panel models (repeated periods of a zone are correlated — treating them
  as independent overstates precision).
- **Spatial / Conley SE** for the cross-sectional zone comparison (neighboring zones move together;
  clustering does not apply when each unit appears once). *Deferred to implementation alongside the
  placebo.*

## 5. Triangulation across designs

The three models are a **ladder** with different weaknesses; a claim is credible only when designs
that fail differently point the same way. Report all three and state what each rules out: Model 1
(weakest, confounded) → Model 2 (control group, but a geographic confound can survive) → Model 3
(cleanest, varies only fee size). External check: do the two vehicle tracks cohere (yellow $0.75 vs
HVFHV $1.50)?

## 6. Estimand — stated, not implied

- Model 2 identifies the **exposure-gradient** (how much *more* high-exposure zone-sides changed),
  **not** a trip-level "charged vs not" individual effect.
- Any **uniform, city-wide** component of the fee's effect is absorbed by `post` → the gradient may
  **understate** the total effect.
- The **weighting choice changes the estimand** (average zone-side vs average trip); name which one
  each number answers.

## 7. Reporting decision rules

To avoid reading a story into noise, "the fee reduced volume" requires the effect to be: negative,
with a CI excluding 0, **and** stable across weighting, sample cutoff, and within-core, **and** absent
in the placebo. Anything short of that is reported as a **null / fragile** effect, not a softened
positive claim. For the burden goal (Goal 1), success is a **stable ranking** — robust to the floor
and consistent between mean and median — not a significance test.

Each track is judged against the same bar independently: the yellow volume effect is **not robust**
(it flips under weighting and is not supported within Manhattan, where the comparison is still
geographic and the control is partially treated) → reported as a characterized **null / fragile**
effect, while its burden ranking is stable; the HVFHV track applies the identical rules to its own
estimates.
