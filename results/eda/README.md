# EDA Results — selected plots

The EDA charts, in [`figures/`](figures). Each PNG is extracted directly from the
output of the EDA notebooks.

Source notebooks: `notebooks/yellow_taxi_full_EDA.ipynb`, `notebooks/hvfhv_full_EDA.ipynb`, and
`notebooks/yellow_taxi_sample_EDA.ipynb`. 

## Yellow Taxi

| Figure | What it shows | Supports |
|---|---|---|
| `yellow_full_volume_flex_confound.png` | Total Yellow volume YoY % by month + Flex-fare share by year (full EDA §2) | The raw Yellow volume rise is Flex adoption, not the fee — non-Flex is flat, Flex share climbs; why the volume outcome excludes Flex. |
| `yellow_full_hourly_cbd_exposure.png` | 2025 charged share + median burden by pickup hour (full EDA §6) | CBD exposure is uneven across the day (low early morning, high late night) — an exposure KPI. |
| `yellow_full_charged_vs_uncharged.png` | Median cost / distance / airport-trip share, charged vs not-charged (full EDA §9) | Charged trips are a route/geography selection (longer, far less airport-heavy), not uncharged trips plus a fee. |
| `yellow_full_burden_by_distance.png` | Charged share + median base-cost burden by distance bucket (full EDA §10) | Fee burden is regressive in trip length — short trips carry the largest fee share. |

## HVFHV

| Figure | What it shows | Supports |
|---|---|---|
| `hvfhv_full_volume_and_provider_mix.png` | Total HVFHV volume YoY % + provider share by month (full EDA §3) | HVFHV volume is roughly flat; provider mix shifts modestly toward Lyft in 2025. |
| `hvfhv_full_hourly_2025_panel.png` | 2025 charged share + median burden by hour (full EDA §5) | Hourly CBD-exposure pattern (peak ≈ 9 PM, lowest ≈ 7 AM) — an exposure KPI. |
| `hvfhv_full_charged_comparison_2025.png` | Median cost / distance / driver-pay / airport-fee share, charged vs not (full EDA §8) | Charged HVFHV trips are longer, more expensive, and more airport-exposed — composition, not just the fee. |
| `hvfhv_full_burden_quantiles_2025.png` | 2025 CBD burden quantiles (full EDA §9) | Burden distribution and tail behavior for the HVFHV burden metric. |
| `hvfhv_full_distance_exposure_2025.png` | Charged share + median burden by distance bucket (full EDA §9) | Fee burden is regressive in trip length, as for Yellow. |

