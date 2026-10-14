import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import settings


def generate_linkedin_benchmark_chart(
    data: dict = None,
    output_path: Path = None,
) -> Path:
    """
    Generates a clean, high-impact 2-metric visualizer for Jev System One vs Sarvam 105B:
      1. Latency (Wall-clock Turnaround in ms)
      2. Cost (Cost per 1,000 Decisions in USD)
    """
    if output_path is None:
        output_path = settings.RESULTS_DIR / "jev_benchmark_comparison.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    concurrency = [1, 5, 10]
    if data is not None and "concurrency" in data:
        concurrency = data["concurrency"]
    elif data is not None and "e2e_without" in data:
        concurrency = [1, 5, 10][:len(data["e2e_without"])]

    # Default empirical benchmark numbers if not provided
    if data is None or "e2e_without" not in data:
        data = {
            "e2e_without": [475.1, 752.3, 778.3],
            "e2e_with":    [75.0,  88.0,   95.0],
            # Cost per 1,000 decisions
            "cost_without_1k": [1.75, 1.75, 1.75],
            "cost_with_1k":    [0.01, 0.01, 0.01],
        }

    plt.style.use("dark_background")
    bg = "#090d16"
    surface = "#111827"
    color_llm = "#F43F5E"    # Pinkish red for slow/expensive LLM
    color_jev = "#10B981"    # Vibrant emerald for fast/cheap Jev

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6), facecolor=bg)
    fig.subplots_adjust(top=0.82, bottom=0.15, left=0.08, right=0.95, wspace=0.28)

    x = np.arange(len(concurrency))
    w = 0.35

    def style_axis(ax, title, ylabel):
        ax.set_facecolor(surface)
        ax.set_title(title, fontsize=12, fontweight="bold", color="#F8FAFC", pad=12)
        ax.set_ylabel(ylabel, fontsize=10, color="#94A3B8")
        ax.tick_params(colors="#94A3B8", labelsize=10)
        ax.grid(True, linestyle="--", alpha=0.15, color="#94A3B8")
        ax.spines[:].set_color("#1F2937")

    # -------------------------------------------------------------
    # Chart 1: Latency (Turnaround Time in ms)
    # -------------------------------------------------------------
    rects1 = ax1.bar(x - w/2, data["e2e_without"], w, color=color_llm, label="1. Sarvam AI 105B (Generative LLM)", alpha=0.9)
    rects2 = ax1.bar(x + w/2, data["e2e_with"],    w, color=color_jev, label="2. Jev (System 1 Decision Model)", alpha=0.95)

    ax1.set_xticks(x)
    ax1.set_xticklabels([f"Concurrency {c}" for c in concurrency])
    ax1.legend(fontsize=9, facecolor="#1F2937", edgecolor="#374151")
    style_axis(ax1, "① Decision Latency (Lower is Better)", "Turnaround Time (ms)")

    for r in rects1:
        h = r.get_height()
        ax1.annotate(f"{h:.0f}ms", xy=(r.get_x() + r.get_width()/2, h), xytext=(0, 4),
                     textcoords="offset points", ha="center", va="bottom", fontsize=9, color="#FDA4AF", fontweight="bold")
    for r in rects2:
        h = r.get_height()
        ax1.annotate(f"{h:.0f}ms", xy=(r.get_x() + r.get_width()/2, h), xytext=(0, 4),
                     textcoords="offset points", ha="center", va="bottom", fontsize=9, color="#6EE7B7", fontweight="bold")

    # -------------------------------------------------------------
    # Chart 2: Cost per 1,000 Decisions (USD)
    # -------------------------------------------------------------
    cost_without = data.get("cost_without_1k", [1.75, 1.75, 1.75])
    cost_with = data.get("cost_with_1k", [0.01, 0.01, 0.01])

    rects3 = ax2.bar(x - w/2, cost_without, w, color=color_llm, label="1. Sarvam AI 105B ($1.75 / 1k)", alpha=0.9)
    rects4 = ax2.bar(x + w/2, cost_with,    w, color=color_jev, label="2. Jev ($0.01 / 1k — 99% Cheaper)", alpha=0.95)

    ax2.set_xticks(x)
    ax2.set_xticklabels([f"Concurrency {c}" for c in concurrency])
    ax2.legend(fontsize=9, facecolor="#1F2937", edgecolor="#374151")
    style_axis(ax2, "② Cost per 1,000 Decisions (Lower is Better)", "Cost (USD)")

    for r in rects3:
        h = r.get_height()
        ax2.annotate(f"${h:.2f}", xy=(r.get_x() + r.get_width()/2, h), xytext=(0, 4),
                     textcoords="offset points", ha="center", va="bottom", fontsize=9, color="#FDA4AF", fontweight="bold")
    for r in rects4:
        h = r.get_height()
        ax2.annotate(f"${h:.2f}", xy=(r.get_x() + r.get_width()/2, h), xytext=(0, 4),
                     textcoords="offset points", ha="center", va="bottom", fontsize=9, color="#6EE7B7", fontweight="bold")

    fig.suptitle(
        "Empirical Benchmark: 1. Sarvam AI 105B (Generative LLM) vs 2. Jev (System 1 Decision Model)\n"
        "Workload: Programmatic Classification, Gating & Decision Routing",
        fontsize=13, fontweight="bold", color="#38BDF8", y=0.95
    )

    plt.savefig(output_path, dpi=300, bbox_inches="tight", facecolor=bg)
    plt.close()
    return output_path


if __name__ == "__main__":
    p = generate_linkedin_benchmark_chart()
    print(f"Clean 2-metric infographic saved: {p}")
