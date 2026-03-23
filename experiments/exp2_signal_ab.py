"""
EXP-2: Signal State Conditioning A/B Test

Maps to: Paper Stage 3 (§5.1)
Tests: Does conditioning personas on S_t improve simulation quality vs generic context?

Condition A: Full signal state (rich context from sentinel monitoring)
Condition B: Generic topic description only

Key hypothesis: Signal-conditioned personas produce more specific, diverse, and
contextually grounded responses than generically prompted personas.
"""

import os
import sys
import json
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.moderator_agent import run_afg_experiment
from metrics.analysis import (
    generate_full_report, print_summary,
    compute_theme_coverage_comparison, compute_variance_collapse
)


def run_exp2(api_key: str, K: int = 5, model: str = "claude-sonnet-4-20250514"):
    """
    A/B comparison: signal-conditioned vs generic personas.
    """
    with open(os.path.join(os.path.dirname(__file__), "..", "config", "personas.json")) as f:
        personas = json.load(f)["personas"]

    with open(os.path.join(os.path.dirname(__file__), "..", "config", "scenarios.json")) as f:
        scenario = json.load(f)["scenario_1_greenwashing"]

    stimulus = scenario["stimuli"]["variant_C_accountability"]  # Most nuanced variant
    probes = scenario["moderator_probes"][:2]

    # --- Condition A: Full signal state ---
    print("\n" + "=" * 60)
    print("CONDITION A: Full Signal State")
    print("=" * 60)

    result_a = run_afg_experiment(
        api_key=api_key,
        personas=personas,
        stimulus=stimulus,
        probes=probes,
        K=K,
        signal_state=scenario["signal_state_rich"],
        temperature_mode="stratified",
        model=model,
        experiment_label="exp2_condA_signal"
    )
    report_a = generate_full_report(result_a)
    print_summary(report_a)

    # --- Condition B: Generic topic only ---
    print("\n" + "=" * 60)
    print("CONDITION B: Generic Topic Only")
    print("=" * 60)

    result_b = run_afg_experiment(
        api_key=api_key,
        personas=personas,
        stimulus=stimulus,
        probes=probes,
        K=K,
        signal_state=None,  # No signal state
        temperature_mode="stratified",
        model=model,
        experiment_label="exp2_condB_generic"
    )
    report_b = generate_full_report(result_b)
    print_summary(report_b)

    # --- Comparative analysis ---
    print("\n" + "=" * 70)
    print("A/B COMPARISON: Signal-Conditioned vs Generic")
    print("=" * 70)

    sessions_a = result_a["sessions"]
    sessions_b = result_b["sessions"]

    # Theme coverage comparison
    coverage = compute_theme_coverage_comparison(sessions_a, sessions_b)
    print(f"\nTheme Coverage:")
    print(f"  Condition A (signal): {coverage['n_themes_a']} unique themes")
    print(f"  Condition B (generic): {coverage['n_themes_b']} unique themes")
    print(f"  Shared themes: {len(coverage['shared_themes'])}")
    print(f"  Unique to A (signal-informed): {len(coverage['unique_to_a'])}")
    print(f"  Unique to B (generic-only): {len(coverage['unique_to_b'])}")
    print(f"  Jaccard similarity: {coverage['jaccard_index']:.3f}")

    if coverage['unique_to_a']:
        print(f"\n  Signal-specific themes (only in Condition A):")
        for t in coverage['unique_to_a'][:10]:
            print(f"    - {t}")

    # Sentiment comparison
    sent_a = report_a.get("sentiment", {}).get("overall", {})
    sent_b = report_b.get("sentiment", {}).get("overall", {})
    print(f"\nSentiment Comparison:")
    print(f"  A (signal): mean={sent_a.get('mean', 0):.2f}, std={sent_a.get('std', 0):.2f}")
    print(f"  B (generic): mean={sent_b.get('mean', 0):.2f}, std={sent_b.get('std', 0):.2f}")

    # Variance collapse comparison
    vc_a = report_a.get("variance_collapse", {})
    vc_b = report_b.get("variance_collapse", {})
    print(f"\nResponse Diversity:")
    print(f"  A (signal) mean similarity: {vc_a.get('overall_mean', 0):.4f}")
    print(f"  B (generic) mean similarity: {vc_b.get('overall_mean', 0):.4f}")
    print(f"  (Lower = more diverse responses)")

    # Save
    output_dir = os.path.join(os.path.dirname(__file__), "..", "results")
    os.makedirs(output_dir, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")

    full_output = {
        "condition_a": {"result": result_a, "report": report_a},
        "condition_b": {"result": result_b, "report": report_b},
        "comparison": coverage,
        "sentiment_comparison": {
            "a_mean": sent_a.get("mean"), "a_std": sent_a.get("std"),
            "b_mean": sent_b.get("mean"), "b_std": sent_b.get("std"),
        }
    }

    with open(os.path.join(output_dir, f"exp2_ab_test_{timestamp}.json"), "w") as f:
        json.dump(full_output, f, indent=2, default=str)

    print(f"\nResults saved to {output_dir}/exp2_ab_test_{timestamp}.json")
    return full_output


if __name__ == "__main__":
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Set ANTHROPIC_API_KEY environment variable.")
        sys.exit(1)

    K = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    model = sys.argv[2] if len(sys.argv) > 2 else "claude-sonnet-4-20250514"

    run_exp2(api_key, K=K, model=model)
