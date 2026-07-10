# Machine Learning Modeling Scope for NYC CBD Congestion Pricing Taxi/FHV Analysis

## Project Context

On January 5, 2025, New York City's Central Business District (CBD) congestion-pricing fee went into effect. This project studies how the policy is associated with fare burden and trip-volume changes across TLC zones using NYC Taxi and Limousine Commission trip records.

The current analysis scope includes:

- Yellow Taxi trips
- High-volume for-hire vehicle trips, or HVFHV, including large app-based fleets such as Uber and Lyft

The current analysis excludes or defers:

- Green Taxi trips
- Smaller non-high-volume FHV trips
- Private passenger vehicle trips
- Subway, bus, Citi Bike, pedestrian, and other cross-mode outcomes

The project is primarily an inference-focused descriptive analysis. The current regression and exploratory work should be interpreted as association-based unless a specific design and robustness evidence support a stronger interpretation.

For more information on interpreting the burden and volume results, please see [docs/causal_interpretation_limitations.md](docs/causal_interpretation_limitations.md)

The proposed machine learning extension should therefore be framed as:

> A predictive, diagnostic, and heterogeneity-focused extension, not a standalone causal identification strategy.

Machine learning can help identify nonlinear patterns, predict expected post-policy volume, flag unusual zone-side behavior, classify zones into trip-market types, and examine provider-specific heterogeneity. It should not be used to claim that the congestion fee caused a particular volume change unless paired with a credible causal design.

---

## Main Research Questions for the ML Extension

The machine learning extension can address the following questions:

1. Can pre-policy zone, service, fare, and trip characteristics predict expected 2025 trip volume?
2. Which zone-sides show the largest negative deviations from predicted 2025 trip volume?
3. Are high-burden or high-exposure zone-sides more likely to show unusually weak post-policy volume performance?
4. Do Yellow Taxi and HVFHV differ in the features that predict post-policy volume decline?
5. Do Uber and Lyft show different provider-specific post-policy residual patterns?
6. Can unsupervised clustering identify distinct taxi/FHV trip-market types?
7. Do burden-volume associations differ across these market types?
8. Are observed post-policy volume changes spatially clustered around the Congestion Relief Zone?
9. Can ML-assisted controls improve descriptive exposure-volume or burden-volume association models?

---

## Machine Learning Modeling Options for the NYC CBD Congestion Pricing Taxi/FHV Project

### Predicting Disruption Scores for Unobserved Zones Using Partial Future TLC Data

#### Problem Setup

---

Suppose that in a future year, full zone-wise TLC ride-share data are not available for all zones.

Instead, detailed future-year data are available only for a selected subset of zones.

Let:

- $Z$ denote the full set of TLC zones.
- $Z_{obs}$ denote the subset of zones with observed future ride-share data.
- $Z_{miss}$ denote the subset of zones without observed future ride-share data.
- $|Z_{obs}| = X$.
- $Z = Z_{obs} \cup Z_{miss}$.
- $Z_{obs} \cap Z_{miss} = \varnothing$.

For zones in $Z_{obs}$, we observe future-year data such as:

- number of trips,
- trip fares,
- congestion fees,
- other charges,
- trip distance,
- trip duration,
- provider mix,
- pickup/dropoff patterns,
- airport share,
- service type,
- CRZ exposure.

Using these observed future-year data, we can compute a future-year disruption score:

$$
DisruptionScore_{z,t}^{obs}
$$

for each observed zone $z \in Z_{obs}$.

The goal is to predict:

$$
\widehat{DisruptionScore}_{z,t}
$$

for each unobserved zone $z \in Z_{miss}$.

This is a missing-zone prediction problem, spatial imputation problem, or small-area prediction problem.

### Main Modeling Question

---

The main question is:

Can we learn the relationship between observed zone characteristics and observed disruption scores in the subset of zones with data, then use that relationship to predict disruption scores for zones without future ride-share data?

Formally, we want to estimate a function:

$$
DisruptionScore_{z,t}
$$

---
$$
f(X_{z,t})
+
\epsilon_{z,t},
$$

where:

- $DisruptionScore_{z,t}$ is the future-year disruption score for zone $z$,
- $X_{z,t}$ is a feature vector describing zone $z$,
- $f(\cdot)$ is the learned prediction function,
- $\epsilon_{z,t}$ is prediction error.

For observed zones:

$$
z \in Z_{obs},
$$

we observe both:

$$
X_{z,t}
$$

and

$$
DisruptionScore_{z,t}^{obs}.
$$

For missing zones:

$$
z \in Z_{miss},
$$

we observe or construct:

$$
X_{z,t},
$$

but do not observe the disruption score.

The trained model is then used to predict:

$$
\widehat{DisruptionScore}_{z,t}
$$

---
$$
\widehat{f}(X_{z,t})
$$

for all zones $z \in Z_{miss}$.

### What Features Can Be Used?

---

The model can only predict missing-zone disruption scores if we have useful features for both observed and unobserved zones.

The best features are those available for all zones, even when future ride-share data are missing.

Recommended feature groups are:

A. Historical zone features

- 2024 trip count
- 2025 trip count
- historical Yellow volume
- historical HVFHV volume
- historical Uber/Lyft share
- historical fare
- historical distance
- historical duration
- historical airport share
- historical CRZ exposure
- historical burden score

B. Static geographic features

- TLC zone ID
- borough
- Manhattan indicator
- CRZ indicator
- airport indicator
- distance to CRZ boundary
- neighboring zones
- zone cluster label
- pickup/dropoff side
- direction category

C. Policy-related features

- current congestion fee
- future congestion fee
- fee increase percentage
- policy-implied burden score
- exposure share
- high-burden indicator
- high-exposure indicator

D. Partial future-year features, if available for all zones

If some future-year aggregated information is available even for missing zones, it can be used. Examples:

- future total Yellow trips by zone,
- future total taxi trips by borough,
- future exposure bin,
- future service availability indicator,
- future zone-level charge schedule.

E. Neighbor features

For zone $z$, define neighboring zones as $\mathcal{N}(z)$.

Neighbor average disruption among observed neighboring zones:

$$
NeighborDisruption_{z,t}
$$

---

$$
\frac{1}{|\mathcal{N}_{obs}(z)|}
\sum_{j \in \mathcal{N}_{obs}(z)}
DisruptionScore_{j,t}^{obs}.
$$

Neighbor average burden:

$$
NeighborBurden_{z,t}
$$

---

$$
\frac{1}{|\mathcal{N}(z)|}
\sum_{j \in \mathcal{N}(z)}
DS_{j,t}.
$$

Neighbor average exposure:

$$
NeighborExposure_{z,t}
$$

---

$$
\frac{1}{|\mathcal{N}(z)|}
\sum_{j \in \mathcal{N}(z)}
E_{j,t}.
$$

Neighbor features are useful because zones near each other may experience similar trip-market conditions.

### Basic Prediction Model

---

The simplest supervised learning model is:

$$
DisruptionScore_{z,t}^{obs}
$$

---
$$
f(
DS_{z,t},
E_{z,t},
X^{hist}_{z},
X^{geo}_{z},
X^{policy}_{z,t}
)
+
\epsilon_{z,t},
\quad z \in Z_{obs}.
$$

Then, for missing zones:

$$
\widehat{DisruptionScore}_{z,t}
$$

---

$$
\widehat{f}(
DS_{z,t},
E_{z,t},
X^{hist}_{z},
X^{geo}_{z},
X^{policy}_{z,t}
),
\quad z \in Z_{miss}.
$$

Here:

- $DS_{z,t}$ is the burden score or policy-implied burden score.
- $E_{z,t}$ is the exposure score.
- $X^{hist}_{z}$ contains historical zone features.
- $X^{geo}_{z}$ contains static geographic features.
- $X^{policy}_{z,t}$ contains future policy scenario features.

5. Recommended Model Types

---

Several model types can be used.

Model A: Ridge Regression
-------------------------

A transparent baseline model is:

$$
DisruptionScore_{z,t}^{obs}$$

---
$$\beta_0
+
\beta_1 DS_{z,t}
+
\beta_2 E_{z,t}
+
\beta_3 \log(1+N^{hist}_{z})
+
\beta_4 fare^{hist}_{z}
+
\beta_5 distance^{hist}_{z}
+
\beta_6 airport share^{hist}_{z}
+
\beta_7 Manhattan_{z}
+
\beta_8 borough_{z}
+
\epsilon_{z,t}.
$$

This is useful because it is interpretable and stable when the number of observed zones $X$ is not very large.

Ridge regression is often better than ordinary least squares because many zone features are correlated. For example, burden, distance, fare, Manhattan geography, and exposure may all be related.

Model B: Random Forest Regression
---------------------------------

A random forest model is:

$$
DisruptionScore_{z,t}^{obs}$$
---
$$f_{RF}(X_{z,t})
+
\epsilon_{z,t}.
$$

Random forest is useful if the relationship between zone features and disruption is nonlinear.

For example, the model can learn:

- high exposure matters only above a threshold,
- airport zones behave differently,
- Manhattan-core zones behave differently,
- short-trip zones behave differently,
- provider-heavy zones behave differently.

Model C: Gradient Boosting / XGBoost / LightGBM / CatBoost
----------------------------------------------------------

A gradient boosting model is:

$$
DisruptionScore_{z,t}^{obs}$$
---
$$f_{GBM}(X_{z,t})
+
\epsilon_{z,t}.
$$

This is often strong for tabular data. It can capture nonlinear relationships and interactions, such as:

$$
DS_{z,t} \times E_{z,t},
$$

$$
DS_{z,t} \times Manhattan_{z},
$$

$$
E_{z,t} \times provider share^{hist}_{z},
$$

$$
airport share_{z} \times service_{s}.
$$

Model D: Spatial Smoothing / Neighbor Imputation
------------------------------------------------

If unobserved zones are geographically close to observed zones, a spatial smoothing model can be useful.

A simple version is:

$$
\widehat{DisruptionScore}_{z,t}$$
---
$$\alpha \widehat{f}(X_{z,t})
+
(1-\alpha)
\left[
\frac{1}{|\mathcal{N}_{obs}(z)|}
\sum_{j \in \mathcal{N}_{obs}(z)}
DisruptionScore_{j,t}^{obs}
\right].
$$

Here:

- $\widehat{f}(X_{z,t})$ is the ML prediction,
- the second term is the average disruption score among observed neighboring zones,
- $\alpha \in [0,1]$ controls how much weight is placed on ML prediction versus neighbor smoothing.

This is useful when geographically nearby zones are expected to behave similarly.

Model E: Cluster-Based Imputation
---------------------------------

First cluster zones using historical and geographic features.

Let:

$$
C(z)
$$

denote the cluster of zone $z$.

Then for a missing zone, predict disruption using observed zones in the same cluster:

$$
\widehat{DisruptionScore}_{z,t}$$
---
$$\frac{1}{|\{j \in Z_{obs}: C(j)=C(z)\}|}
\sum_{j \in Z_{obs}: C(j)=C(z)}
DisruptionScore_{j,t}^{obs}.
$$

A more flexible version uses both cluster averages and ML predictions:

$$
\widehat{DisruptionScore}_{z,t}$$
---
$$\alpha \widehat{f}(X_{z,t})
+
(1-\alpha)
\overline{DisruptionScore}_{C(z),t}^{obs}.
$$

Cluster-based imputation is useful because some zones may not be geographically adjacent but may represent similar trip markets.

For example:

- airport zones,
- Manhattan commercial zones,
- outer-borough residential zones,
- high-HVFHV zones,
- Yellow-dominant tourist/business zones.

Model F: Semi-Supervised Learning
---------------------------------

If features are available for all zones but disruption scores are available only for $X$ zones, semi-supervised learning can use both observed and unobserved zones.

The model uses:

- labeled data: zones with disruption scores,
- unlabeled data: zones without disruption scores but with features.

Possible approaches include:

- label propagation,
- graph-based semi-supervised learning,
- self-training,
- semi-supervised random forests,
- representation learning followed by supervised prediction.

This is useful when $X$ is small but the feature structure across all zones is informative.

### Best Practical Approach

---

The best practical approach is usually a combined model:

1. Train a supervised model on observed zones.
2. Add spatial neighbor features.
3. Add cluster features.
4. Predict missing zones.
5. Report prediction uncertainty.

A strong combined model is:

$$
DisruptionScore_{z,t}^{obs}$$
---
$$f(
DS_{z,t},
E_{z,t},
X^{hist}_{z},
X^{geo}_{z},
X^{policy}_{z,t},
NeighborFeatures_{z,t},
ClusterFeatures_{z}
)
+
\epsilon_{z,t}.
$$

For missing zones:

$$
\widehat{DisruptionScore}_{z,t}$$
---
$$\widehat{f}(
DS_{z,t},
E_{z,t},
X^{hist}_{z},
X^{geo}_{z},
X^{policy}_{z,t},
NeighborFeatures_{z,t},
ClusterFeatures_{z}
).
$$

---

#### Important Sampling Issue

The model works best if the observed $X$ zones are representative of all zones.

If the observed zones are selected randomly or cover many market types, prediction is more credible.

But if the observed zones are selected only from Manhattan, or only from high-volume zones, then predictions for outer-borough or low-volume zones may be poor.

This is called sample-selection bias.

Good observed-zone coverage should include:

- Manhattan core zones,
- outer-borough zones,
- airport zones,
- high-volume zones,
- low-volume zones,
- Yellow-heavy zones,
- HVFHV-heavy zones,
- Uber-heavy zones,
- Lyft-heavy zones,
- high-exposure zones,
- low-exposure zones.

If the project can choose the $X$ observed zones, the best strategy is stratified sampling.

For example, choose observed zones across strata defined by:

- borough,
- exposure quartile,
- burden quartile,
- baseline trip-volume quartile,
- service dominance,
- airport/non-airport status,
- zone cluster.

#### Validation Strategy

---

Since future missing-zone scores are not observed, validation must be done using historical complete data.

A good validation design is:

1. Use a year where full data are available, such as 2025.
2. Pretend only $X$ zones are observed.
3. Hide disruption scores for the remaining zones.
4. Train the model on the selected $X$ zones.
5. Predict the hidden zones.
6. Compare predictions to the actual known 2025 disruption scores.

This creates a realistic missing-zone simulation.

Let $Z_{train}$ be the pretend-observed zones and $Z_{test}$ be the pretend-missing zones.

Train on:

$$
z \in Z_{train}.
$$

Predict:

$$
z \in Z_{test}.
$$

Evaluate:

$$
error_{z}$$
---
$$DisruptionScore_{z,2025}$$
-
$$
\widehat{DisruptionScore}_{z,2025}.
$$

Use metrics such as:

$$
RMSE$$
---

$$\sqrt{
\frac{1}{|Z_{test}|}
\sum_{z \in Z_{test}}
\left(DisruptionScore_{z,2025}\right)^2}
$$

Core notation
-------------

Let:

- $z$ denote TLC zone.
- $d$ denote pickup side, dropoff side, or direction.
- $s$ denote service, such as Yellow Taxi or HVFHV.
- $p$ denote HVFHV provider, such as Uber or Lyft.
- $t$ denote month.
- $m$ denote calendar month, such as February, March, April, May, or June.
- $N_{zdst}$ denote completed trip count for zone $z$, side/direction $d$, service $s$, and month $t$.

The preferred panel unit for most ML models is:

$$
(z,d,s,t),
$$

that is, zone by side/direction by service by month.

For provider-specific HVFHV models, the unit can be:

$$
(z,d,p,t).
$$

---

## Main recommended volume target

For trip-volume modeling, the main target is:

$$
Y_{zdst} = \log(1+N_{zdst}).
$$

This target is useful because completed trip counts are highly skewed. Some Manhattan or airport-related zones have very large volumes, while many other zone-side-months have much smaller volumes. Modeling raw trip counts can cause the largest markets to dominate the loss function.

The log transformation compresses the scale and makes model errors interpretable as approximate percentage deviations. If:

$$
r_{zdst}=Y_{zdst}-\widehat{Y}_{zdst},
$$

then for large counts:

$$
r_{zdst}\approx \log\left(\frac{N_{zdst}}{\widehat{N}_{zdst}}\right).
$$

For example, if $r_{zdst}=-0.10$, then:

$$
\exp(-0.10)-1\approx -0.095,
$$

so observed volume is about 9.5 percent below predicted volume.

The $+1$ is included because some cells may have zero trips. Since $\log(0)$ is undefined, $\log(1+N)$ keeps zero-count cells in the data.

---

Main burden target
------------------

At the trip level, define burden as:

$$
DS_i=\frac{congestion fee_i}{cost excluding congestion fee_i}.
$$

A floor-adjusted version is:

$$
DS_i^{floor}=\frac{congestion fee_i}{\max(cost excluding congestion fee_i,f)},
$$

where $f$ is a denominator floor such as 5, 7.5, or 10 dollars.

At the zone-side-service level, a robust burden measure is:

$$
DS_{zds}=median_{i\in zds}\left(\frac{congestion fee_i}{\max(cost excluding congestion fee_i,f)}\right).
$$

This ratio is used because the fee is mostly flat within service, while trip cost varies widely. A fixed surcharge is a much larger burden on short, low-cost trips than on long, high-cost trips.

For example, a \$1.50 fee on a \$10 non-fee trip cost is:

$$
\frac{1.50}{10}=0.15,
$$

or 15 percent.

The same \$1.50 fee on a \$60 non-fee trip cost is:

$$
\frac{1.50}{60}=0.025,
$$

or 2.5 percent.

---

Main exposure target
--------------------

Define pre-policy exposure as:

$$
E^{pre}_{zds}=\frac{CRZ-touching trips_{zds,2024}}{total trips_{zds,2024}}.
$$

This measures how connected a zone-side-service market was to the Congestion Relief Zone before the policy began. It should generally be defined using pre-policy data rather than 2025 data, because 2025 exposure may itself be affected by the policy.

---

# Other models

---

## MODEL 1: Expected Trip-Volume Prediction

Goal
----

Predict expected trip volume at the zone-side-service-month level and compare observed 2025 volume with model-predicted 2025 volume.

Target
------

$$
Y_{zdst}=\log(1+N_{zdst}).
$$

Possible features
-----------------

- TLC zone ID
- pickup/dropoff side or direction
- service type: Yellow or HVFHV
- month
- year
- borough
- Manhattan indicator
- airport indicator
- baseline trip volume
- same-month 2024 trip volume
- lagged trip volume
- average fare excluding congestion fee
- median fare excluding congestion fee
- average trip distance
- median trip distance
- average trip duration
- airport share
- burden score $DS_{zds}$
- pre-policy exposure $E^{pre}_{zds}$
- provider share for HVFHV
- 2023-to-2024 placebo trend, if available

Candidate algorithms
--------------------

- Linear regression
- Ridge regression
- Lasso regression
- Elastic net
- Random forest regression
- Gradient boosted trees
- XGBoost
- LightGBM
- CatBoost

Why this model is useful
------------------------

This model creates an expected-volume benchmark. It asks:

Given historical and market features, what trip volume would the model expect for a zone-side-service-month?

Then the project can compare observed 2025 volume with predicted 2025 volume.

Key output
----------

Define the residual:

$$
r_{zdst}=Y_{zdst}-\widehat{Y}_{zdst}.
$$

A negative residual means observed volume was lower than predicted. A positive residual means observed volume was higher than predicted.

Useful outputs include:

- predicted 2025 volume
- observed 2025 volume
- residuals
- residual converted to approximate percent deviation, $\exp(r_{zdst})-1$
- residual maps
- top negative-residual zones
- residuals by burden bin
- residuals by exposure bin
- residuals by service
- residuals by provider for HVFHV

Interpretation
--------------

This model identifies zone-side-service-months where observed volume was lower or higher than expected. It does not prove that the congestion fee caused the residual.

---
---

## MODEL 2: Year-over-Year Volume Change Model

Goal
----

Model 2024-to-2025 trip-volume change directly.

Target
------

For same-month comparisons:

$$
\Delta Y_{zdsm}=\log(1+N_{zds,2025m})-\log(1+N_{zds,2024m}).
$$

For the collapsed February-June window:

$$
\Delta Y_{zds}=\log(1+N_{zds,2025})-\log(1+N_{zds,2024}).
$$

Why this formula is chosen
--------------------------

The difference of logs approximates a percentage change:

$$
\Delta Y_{zdsm}\approx \log\left(\frac{N_{zds,2025m}}{N_{zds,2024m}}\right).
$$

If:

$$
\Delta Y_{zdsm}=-0.15,
$$

then:

$$
\exp(-0.15)-1\approx -0.139,
$$

so volume declined by about 13.9 percent.

Same-month comparison is useful because taxi and FHV demand is seasonal. February 2025 should be compared to February 2024, March 2025 to March 2024, and so on.

Candidate algorithms
--------------------

- Linear regression
- Ridge regression
- Lasso regression
- Elastic net
- Random forest regression
- Gradient boosted regression
- XGBoost
- LightGBM
- CatBoost

Possible features
-----------------

- burden score $DS_{zds}$
- pre-policy exposure $E^{pre}_{zds}$
- baseline fare
- baseline distance
- baseline trip count
- airport share
- service type
- provider mix
- borough
- Manhattan indicator
- pickup/dropoff side
- zone cluster
- 2023-to-2024 placebo trend

Outputs
-------

- predicted year-over-year volume change
- observed year-over-year volume change
- feature importance
- burden-volume patterns
- exposure-volume patterns
- service-specific predictions
- provider-specific predictions

Interpretation
--------------

This model asks which baseline features predict larger 2024-to-2025 volume declines. It is descriptive and predictive, not automatically causal.

---
MODEL 4: Large-Decline Classification Model
---

Goal
----

Classify whether a zone-side-service market had unusually weak post-policy volume performance.

Targets
-------

Fixed-threshold version:

$$
D_{zds}=1\{\Delta Y_{zds}\leq -0.10\}.
$$

This corresponds to roughly a 9.5 percent or larger decline because:

$$
\exp(-0.10)-1\approx -0.095.
$$

Quantile version:

$$
D_{zds}=1\{\Delta Y_{zds}\leq Q_{25}(\Delta Y)\}.
$$

This labels the weakest-performing quartile as large-decline markets.

Why this formula is chosen
--------------------------

Sometimes the project may not need to predict the exact magnitude of volume change. Instead, it may want to identify whether a zone-side-service market belongs to a high-risk or weak-performance group.

The fixed threshold is easy to interpret. The quantile threshold avoids choosing an arbitrary percentage cutoff and instead identifies the weakest part of the observed distribution.

Candidate algorithms
--------------------

- Logistic regression
- Ridge logistic regression
- Lasso logistic regression
- Decision tree classifier
- Random forest classifier
- Gradient boosting classifier
- XGBoost classifier
- LightGBM classifier
- CatBoost classifier
- Support vector machine
- Explainable boosting machine

Possible features
-----------------

- burden score
- high-burden indicator
- pre-policy exposure
- exposure bin
- baseline volume
- baseline fare
- baseline distance
- airport share
- borough
- Manhattan indicator
- service type
- provider share
- zone cluster
- placebo trend

Outputs
-------

- predicted probability of large decline
- classification labels
- confusion matrix
- ROC-AUC
- precision-recall AUC
- maps of high-risk zones
- feature importance
- decline probability by burden bin
- decline probability by exposure bin

Interpretation
--------------

This model identifies features associated with large observed declines. It does not prove those features caused the declines.

---
MODEL 5: Burden Prediction Model
---

Goal
----

Predict which zone-side-service markets face the highest relative congestion-fee burden.

Continuous target
-----------------

$$
DS_{zds}=median_{i\in zds}\left(\frac{fee_i}{\max(cost excluding fee_i,f)}\right).
$$

Classification target
---------------------

Within-service high-burden indicator:

$$
H_{zds}=1\{DS_{zds}\geq Q_{75}(DS_s)\}.
$$

Top-decile version:

$$
H_{zds}=1\{DS_{zds}\geq Q_{90}(DS_s)\}.
$$

Why this formula is chosen
--------------------------

The burden ratio measures the fee relative to the non-fee trip cost. This is more informative than the dollar surcharge alone because the fee is mostly flat within service, while trip costs vary greatly.

The denominator floor is included because very small costs can make the ratio unstable. The median aggregation is robust to outliers and unusual fare records.

The high-burden classification target is useful because it asks whether a market is among the highest-burden markets within its own service. This matters because Yellow and HVFHV have different nominal surcharge amounts.

Candidate algorithms
--------------------

For continuous $DS_{zds}$:

- Linear regression
- Ridge regression
- Decision tree regression
- Random forest regression
- Gradient boosting regression
- XGBoost
- LightGBM
- CatBoost

For high-burden classification $H_{zds}$:

- Logistic regression
- Decision tree classifier
- Random forest classifier
- Gradient boosting classifier
- Explainable boosting machine

Possible features
-----------------

- average distance
- median distance
- average fare excluding fee
- median fare excluding fee
- average duration
- airport share
- Manhattan indicator
- borough
- pickup/dropoff side
- service
- provider
- CRZ exposure
- percent short trips
- percent airport trips

Outputs
-------

- predicted burden score
- high-burden probability
- feature importance
- decision tree rules
- burden maps
- high-burden zone rankings
- burden by cluster

Interpretation
--------------

This model strengthens the descriptive burden story. It explains which trip-market features are predictive of high relative burden. It does not estimate volume response.

---
MODEL 6: Zone Market Clustering / Market Typology
---

Goal
----

Use unsupervised learning to group TLC zone-side-service markets into similar trip-market types.

Input feature vector
--------------------

For each zone-side-service market, define:

$$
X_{zds}=[\overline{distance}_{zds},\overline{fare}_{zds},DS_{zds},E^{pre}_{zds},airport share_{zds},baseline volume_{zds},Yellow share_{zd},HVFHV share_{zd},Manhattan indicator_{z},borough indicators_{z}].
$$

Standardization
---------------

Before clustering, standardize each feature:

$$
X^{std}_{jk}=\frac{X_{jk}-\overline{X}_k}{s_k},
$$

where $j$ indexes the observation and $k$ indexes the feature.

Why this formula is chosen
--------------------------

Clustering does not have an outcome variable. The goal is to identify similar markets based on characteristics such as distance, fare, burden, exposure, airport dependence, service composition, provider composition, baseline volume, and geography.

Standardization is necessary because features are measured on different scales. Without standardization, large-scale features such as trip count could dominate the clustering.

Candidate algorithms
--------------------

- K-means clustering
- Gaussian mixture models
- Hierarchical clustering
- DBSCAN
- HDBSCAN
- PCA followed by clustering
- UMAP for visualization only

Possible cluster types
----------------------

- short-trip Manhattan-core zones
- airport-connected long-distance zones
- outer-borough residential pickup zones
- CBD commuter dropoff zones
- Yellow-dominant zones
- HVFHV-dominant zones
- Uber-heavy HVFHV zones
- Lyft-heavy HVFHV zones
- mixed-service transition zones

Outputs
-------

- cluster labels
- cluster maps
- cluster summary tables
- burden by cluster
- exposure by cluster
- volume change by cluster
- residuals by cluster
- service composition by cluster
- provider composition by cluster

Interpretation
--------------

Clustering helps compare more similar trip markets. It does not identify causal effects. It is especially useful because high-burden and low-burden zones may otherwise represent very different markets.

---
MODEL 7: Residual-Based Anomaly Detection
---

Goal
----

Flag zone-side-service markets with unusual 2025 behavior relative to model predictions or peer markets.

Residual formula
----------------

$$
r_{zdst}=Y_{zdst}-\widehat{Y}_{zdst}.
$$

Negative anomaly score
----------------------

$$
A_{zdst}=-r_{zdst}.
$$

A larger $A_{zdst}$ means a more negative post-policy deviation.

Standardized residual
---------------------

$$
S_{zdst}=\frac{Y_{zdst}-\widehat{Y}_{zdst}}{\widehat{\sigma}_{zdst}}.
$$

Why this formula is chosen
--------------------------

The residual measures whether the observed volume was above or below predicted volume. Since the outcome is logged, residuals can be interpreted approximately as percentage deviations.

The negative anomaly score is useful when the project wants to rank weak-performing markets, with larger values indicating more negative deviations.

The standardized residual is useful when uncertainty differs across zones. Low-volume zones may naturally be noisier, so standardization can help compare unusualness across markets.

Candidate algorithms
--------------------

- Residual thresholding
- Standardized residual ranking
- Isolation Forest
- Local Outlier Factor
- One-Class SVM
- Robust covariance methods

Possible inputs
---------------

- volume residuals
- year-over-year volume change
- burden score
- exposure
- fare change
- distance change
- provider-share change
- baseline volume
- airport share
- cluster label

Outputs
-------

- anomaly score
- anomaly rank
- top negative-anomaly markets
- anomaly maps
- anomaly rates by burden bin
- anomaly rates by exposure bin
- anomaly rates by service
- anomaly rates by provider

Interpretation
--------------

Anomaly detection flags unusual observations. It does not explain why they are unusual and does not prove the fee caused the anomaly.

---
---
