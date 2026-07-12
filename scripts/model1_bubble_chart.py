"""Shared TLC bubble-chart styling for the Yellow and HVFHV Model 1 figures."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D


COLORS = {"pickup": "#1D9E75", "dropoff": "#D85A30"}


def plot_model1_bubble_chart(
    data,
    service_label: str,
    output_path: str | Path,
    *,
    xlim: tuple[float, float],
    ylim: tuple[float, float],
    min_burden_n: int | None = None,
):
    """Plot DS_z against volume change with bubble area proportional to N_z."""
    keep = (
        (~data["low_n_flag"].astype(bool))
        & data["DS_z"].notna()
        & data["pct_volume_change"].notna()
        & data["N_z"].notna()
    )
    if min_burden_n is not None:
        keep &= data["N_z"].ge(min_burden_n)
    frame = data.loc[keep].copy()

    x = frame["DS_z"].to_numpy(dtype=float) * 100
    y = frame["pct_volume_change"].to_numpy(dtype=float) * 100
    r = float(np.corrcoef(x, y)[0, 1])
    max_volume = float(frame["N_z"].max())

    fig, ax = plt.subplots(figsize=(12.1, 5.96), facecolor="white")

    # Draw the overall trend first so the bubbles remain the visual focus, as in the HTML chart.
    slope, intercept = np.polyfit(x, y, 1)
    trend_x = np.array(xlim)
    ax.plot(
        trend_x,
        intercept + slope * trend_x,
        color="#888780",
        linewidth=1.3,
        linestyle=(0, (6, 4)),
        alpha=0.22,
        zorder=1,
    )

    for direction in ("pickup", "dropoff"):
        group = frame.loc[frame["direction"].eq(direction)]
        bubble_area = 12 + 4000 * group["N_z"].to_numpy(dtype=float) / max_volume
        ax.scatter(
            group["DS_z"] * 100,
            group["pct_volume_change"] * 100,
            s=bubble_area,
            facecolor=COLORS[direction],
            edgecolor=COLORS[direction],
            linewidth=0.8,
            alpha=0.48,
            zorder=2,
        )

    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_xlabel("Zone Disruption Score / Fee Burden (%)", color="#5F5E5A")
    ax.set_ylabel("Trip Volume Change (%)", color="#5F5E5A")
    ax.grid(color="#000000", alpha=0.11, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(colors="#5F5E5A")
    for spine in ax.spines.values():
        spine.set_color("#D6D3D1")
        spine.set_linewidth(0.8)

    r_text = f"{r:.3f}".replace("-", "−")
    fig.text(
        0.105,
        0.94,
        "Each bubble is one TLC zone, split by pickup or dropoff direction. "
        f"Bubble size reflects trip volume (N_z). Pearson r = {r_text}.",
        ha="left",
        va="top",
        fontsize=10.5,
        color="#44403C",
    )
    legend_handles = [
        Line2D([0], [0], marker="o", linestyle="none", markersize=7,
               markerfacecolor=COLORS[d], markeredgecolor=COLORS[d], label=d.title())
        for d in ("pickup", "dropoff")
    ]
    fig.legend(
        handles=legend_handles,
        loc="lower left",
        bbox_to_anchor=(0.095, 0.04),
        ncol=2,
        frameon=False,
        handletextpad=0.4,
        columnspacing=1.2,
        fontsize=9.5,
        labelcolor="#5F5E5A",
    )

    fig.subplots_adjust(left=0.15, right=0.73, bottom=0.22, top=0.83)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=100, facecolor="white")
    return fig, ax, frame, r


def main():
    """Regenerate both durable Model 1 bubble-chart PNGs from pipeline outputs."""
    import pandas as pd

    repo = Path(__file__).resolve().parents[1]
    data_dir = repo / "data" / "processed" / "disruption_score"
    figure_dir = repo / "results" / "modeling" / "figures"
    specs = [
        ("yellow", "Yellow Taxi", (0.5, 5.0), (-50, 110), 100),
        ("hvfhv", "Uber/Lyft", (1.0, 7.0), (-20, 50), None),
    ]
    for service, label, xlim, ylim, min_burden_n in specs:
        data = pd.read_csv(data_dir / f"{service}_ds_z_vs_volume_change.csv")
        output = figure_dir / f"{service}_model1_dsz_vs_volume.png"
        fig, _, used, r = plot_model1_bubble_chart(
            data, label, output, xlim=xlim, ylim=ylim, min_burden_n=min_burden_n
        )
        plt.close(fig)
        print(f"Wrote {output.relative_to(repo)} ({len(used)} zone-sides; r={r:.3f})")


if __name__ == "__main__":
    main()
