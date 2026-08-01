"""
Sweep physical error rate across several code distances and plot the logical
error rate. This reproduces, in miniature, the central plot of any QEC paper:
larger distance codes suppress errors faster once you're below threshold, and
the whole point of going to a bigger code only pays off below that threshold.

Author: Aanha Islam
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from repetition_code import run_single_trial


def logical_error_rate(distance: int, p_error: float, trials: int, rng: np.random.Generator) -> float:
    failures = 0
    for _ in range(trials):
        logical_state = int(rng.integers(0, 2))
        survived = run_single_trial(distance, p_error, logical_state, rng)
        if not survived:
            failures += 1
    return failures / trials


def main():
    rng = np.random.default_rng(0)
    distances = [3, 5, 7]
    physical_rates = np.linspace(0.01, 0.45, 12)
    trials_per_point = 300

    results = {d: [] for d in distances}
    for d in distances:
        for p in physical_rates:
            rate = logical_error_rate(d, p, trials_per_point, rng)
            results[d].append(rate)
            print(f"distance={d}  p_physical={p:.3f}  p_logical={rate:.4f}")

    plt.figure(figsize=(7, 5))
    for d in distances:
        plt.plot(physical_rates, results[d], marker="o", label=f"distance {d}")
    plt.plot(physical_rates, physical_rates, "k--", alpha=0.4, label="break-even (p_logical = p_physical)")
    plt.xlabel("Physical error rate")
    plt.ylabel("Logical error rate")
    plt.title("Repetition code: logical vs. physical error rate")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig("../results/threshold_plot.png", dpi=150)
    print("\nSaved plot to ../results/threshold_plot.png")


if __name__ == "__main__":
    main()
