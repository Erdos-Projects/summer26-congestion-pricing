# HVFHV Zone Disruption Score Outputs

Authoritative run guide for `scripts/EDA_adithya/01_pipeline.py` and related exports. See also [`docs/methodology_notes.md`](../../docs/methodology_notes.md) for full methodology.

Run from the repository root:

```bash
python scripts/EDA_adithya/01_pipeline.py
```

## Inputs

- `data/processed/00_standardized_trips/hvfhv/2024/*.parquet`
- `data/processed/00_standardized_trips/hvfhv/2025/*.parquet`
- `data/taxi_zone_lookup.csv`

## Outputs

- `hvfhv_zone_disruption_score.csv`: primary zone-direction DS_z table.
- `hvfhv_behavioral_shift.csv`: 2024 vs 2025 zone-direction volume and fare summaries.
- `hvfhv_ds_z_vs_volume_change.csv`: descriptive join of DS_z and volume change.
- `hvfhv_ds_floor_sensitivity.csv`: DS_z under denominator floors of $0.50, $1.00, $2.00, and $5.00, with mean and median rankings.
- `hvfhv_ds_rank_stability.csv`: Spearman rank correlations and rank deltas versus the primary definition.
- `hvfhv_ds_top_zone_overlap.csv`: top-10 and top-20 overlap versus the primary definition.

## Definition

For zone `z`, direction `pickup` or `dropoff`, and qualifying 2025 HVFHV trips:

```text
DS_z = mean(cbd_congestion_fee / round(passenger_cost_pretip - cbd_congestion_fee, 2))
```

The primary definition uses trips with `charged_cbd_flag = true`, positive
`cbd_congestion_fee`, and a rounded base-cost denominator of at least $1.00.
The median of the same trip-level burden is also reported.

## Interpretation Warnings

These outputs are descriptive/inferential, not causal proof. DS_z measures the
relative rider burden among observed post-policy fee-charged trips; it is not a
randomized treatment assignment.

Do not regress `pct_volume_change` on a disruption score that includes volume
change. The current DS_z definition does not include volume change directly, but
downstream models should still use pre-policy controls only when explaining
post-policy outcomes.
