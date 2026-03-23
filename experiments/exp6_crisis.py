"""
EXP-6: Crisis Communication — Supply Chain Scandal Response

Maps to: Revision Exp — New scenario (Scenario 4)
Tests: Stakeholder reactions to 3 different crisis response strategies.
3 variants (apologize, rebut, delay), 8 personas (Scenario 1 set), K=5.
"""

import os
import sys
import json
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.parallel_runner import run_afg_experiment_parallel
from metrics.analysis import generate_full_report, print_summary


def run_exp6(api_key: str, K: int = 5, model: str = "claude-sonnet-4-20250514", tracker=None):
    """Run EXP-6: Crisis communication — 3 response strategies."""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Use Scenario 1 personas for consistency
    with open(os.path.join(base, "config", "personas.json")) as f:
        personas = json.load(f)["personas"]

    with open(os.path.join(base, "config", "scenarios.json")) as f:
        scenario = json.load(f)["scenario_4_crisis"]

    signal_state = scenario["signal_state_rich"]
    probes = scenario["moderator_probes"][:2]

    variants = {
        "A_apologize": scenario["stimuli"]["variant_A_apologize"],
        "B_rebut": scenario["stimuli"]["variant_B_rebut"],
        "C_delay": scenario["stimuli"]["variant_C_delay"],
    }

    results = {}
    reports = {}

    for vname, stimulus in variants.items():
        print(f"\n{'='*60}")
        print(f"EXP-6 Crisis Variant {vname} - K={K} (model: {model})")
        print(f"{'='*60}")

        result = run_afg_experiment_parallel(
            api_key, personas, stimulus, probes, K=K,
            signal_state=signal_state, temperature_mode="stratified",
            model=model, experiment_label=f"exp6_{vname}",
            usage_tracker=tracker,
        )
        results[vname] = result
        report = generate_full_report(result)
        reports[vname] = report
        print_summary(report)

    # Cross-variant comparison
    print("\n" + "=" * 70)
    print("CRISIS RESPONSE COMPARISON")
    print("=" * 70)
    print(f"\n{'Variant':<25} {'Sentiment':>12} {'Credibility':>14} {'Themes':>8}")
    print("-" * 62)

    for vname, report in reports.items():
        sent = report.get("sentiment", {}).get("overall", {})
        cred = report.get("credibility", {})
        ts = report.get("theme_stability", {})
        print(f"{vname:<25} {sent.get('mean', 0):>12.2f} {cred.get('mean', 0):>14.2f} {ts.get('total_unique_themes', 0):>8}")

    output = {
        "variants": results,
        "reports": reports,
        "model": model,
    }

    output_dir = os.path.join(base, "results")
    os.makedirs(output_dir, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    path = os.path.join(output_dir, f"exp6_crisis_{model.split('-')[0]}_{ts}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str, ensure_ascii=False)
    print(f"\nSaved: {path}")

    return output


if __name__ == "__main__":
    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Set ANTHROPIC_API_KEY or OPENAI_API_KEY environment variable.")
        sys.exit(1)
    K = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    model = sys.argv[2] if len(sys.argv) > 2 else "claude-sonnet-4-20250514"
    run_exp6(api_key, K=K, model=model)
