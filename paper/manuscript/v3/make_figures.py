#!/usr/bin/env python3
"""Create paper figures from frozen aggregate artifacts only.

This script never opens references, videos, frames, mappings, or annotations.
It reads the frozen aggregate pair-effect CSV and writes presentation-only
figures; it does not compute a new scientific endpoint.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

OUT = Path(__file__).resolve().parent / "figures"


def make_overview() -> None:
    fig, ax = plt.subplots(figsize=(12.0, 3.0))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    boxes = [
        (0.015, 0.22, 0.17, 0.58, "Fixed panel", "2 attributes\n20 matched pairs\n40 units × 4 seeds"),
        (0.215, 0.22, 0.17, 0.58, "Observational audit", "Phase-S trace\nscalar linkage\n640 token margins"),
        (0.415, 0.22, 0.17, 0.58, "Prospective intervention", "baseline\nprojection exchange\northogonal sham"),
        (0.615, 0.22, 0.17, 0.58, "Blind outcomes", "480 videos\n3,360 frame states\n2 annotators + adjudication"),
        (0.815, 0.22, 0.17, 0.58, "Causal readout", "20 pair effects\nsparse, mixed,\ncentered near zero"),
    ]
    colors = ["#E8F0FE", "#E8F5E9", "#FFF3E0", "#F3E5F5", "#FCE8E6"]
    for (x, y, w, h, title, body), color in zip(boxes, colors):
        patch = FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.012,rounding_size=0.018",
            linewidth=1.15, edgecolor="#37474F", facecolor=color
        )
        ax.add_patch(patch)
        ax.text(x + w / 2, y + h * 0.76, title, ha="center", va="center", fontsize=10.5, fontweight="bold")
        ax.text(x + w / 2, y + h * 0.39, body, ha="center", va="center", fontsize=9.2, linespacing=1.25)
    for left, right in zip(boxes[:-1], boxes[1:]):
        start = (left[0] + left[2] + 0.006, 0.51)
        end = (right[0] - 0.006, 0.51)
        ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=13, linewidth=1.2, color="#455A64"))
    ax.text(
        0.5, 0.065,
        "Evidence ladder: readability and covariation motivate—but do not substitute for—paired intervention.",
        ha="center", va="center", fontsize=10.2, fontstyle="italic", color="#263238"
    )
    fig.tight_layout(pad=0.2)
    fig.savefig(OUT / "audit_overview.pdf", bbox_inches="tight")
    fig.savefig(OUT / "audit_overview.png", dpi=240, bbox_inches="tight")
    plt.close(fig)


def make_pair_effects(pair_effects: Path) -> None:
    with pair_effects.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    fig, axes = plt.subplots(2, 1, figsize=(10.2, 5.9), sharey=True)
    specs = [
        ("eyeglasses", "Eyeglasses", "#3B78E7"),
        ("facial_hair", "Facial hair", "#A142F4"),
    ]
    for ax, (key, title, base_color) in zip(axes, specs):
        subset = [row for row in rows if row["attribute"] == key]
        labels = [row["formal_pair_id"] for row in subset]
        values = [float(row["primary_target_vs_sham_effect"]) for row in subset]
        colors = [
            base_color if value > 1e-8 else ("#D93025" if value < -1e-8 else "#B0BEC5")
            for value in values
        ]
        ax.bar(labels, values, color=colors, edgecolor="#37474F", linewidth=0.45)
        ax.axhline(0, color="#263238", linewidth=0.9)
        ax.set_title(title, loc="left", fontsize=11, fontweight="bold")
        ax.grid(axis="y", alpha=0.22, linewidth=0.7)
        ax.tick_params(axis="x", labelrotation=35, labelsize=8.5)
        ax.tick_params(axis="y", labelsize=8.5)
        ax.set_ylim(-0.14, 0.07)
    axes[0].set_ylabel("Pair effect $E_{a,p}$")
    axes[1].set_ylabel("Pair effect $E_{a,p}$")
    axes[1].set_xlabel("Frozen matched pair")
    fig.text(
        0.995, 0.005,
        "Blue/purple: predicted direction; red: opposite direction; gray: preregistered tie.",
        ha="right", va="bottom", fontsize=8.5
    )
    fig.tight_layout(rect=(0, 0.035, 1, 1))
    fig.savefig(OUT / "pair_effects.pdf", bbox_inches="tight")
    fig.savefig(OUT / "pair_effects.png", dpi=240, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--pair-effects",
        required=True,
        type=Path,
        help="Frozen aggregate pair_effects_v1.csv (SHA256 d5d56c6a...).",
    )
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    make_overview()
    make_pair_effects(args.pair_effects)


if __name__ == "__main__":
    main()
