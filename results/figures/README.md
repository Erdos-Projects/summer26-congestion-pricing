# Model-1 figures — burden ranking (Goal 1)

Charts for the `DS_z` burden **ranking** — the Goal-1 deliverable ("which zone-sides bear the fee
most"). These are Model-1 outputs, not EDA exploration, so they live here rather than in
`results/eda/`. Each is extracted from its source notebook's output.

| Figure | What it shows | Source |
|---|---|---|
| `yellow_model1_top_ds_zones.png` | Top-15 Yellow zone-sides by `DS_z` (stable units, `N_z >= 100`) — dense Manhattan core (Kips Bay, Flatiron, Union Sq, West Village…) leads. | `notebooks/yellow_model1_model2.ipynb`, Model-1 burden-ranking section |
| `hvfhv_model1_dsz_outputs.png` | Top-20 HVFHV zone-sides by `DS_z` + `DS_z` vs YoY volume change. | `notebooks/hvfhv_full_EDA.ipynb` §13 (DS_z outputs) |

Note: the ranking is stable to the non-movement cleaning rule (`DS_z` is unchanged by it), so these do
not need the volume-model regeneration pass.
