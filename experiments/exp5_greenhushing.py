"""
EXP-5: Greenhushing — ESG Disclosure Dilemma

Maps to: Revision Exp — New scenario (Scenario 2)
Tests: Stakeholder reactions to ESG disclosure vs silence strategy.
2 variants (disclose vs silent), 8 finance-focused personas, K runs per variant.
"""

import os
import sys
import json
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.parallel_runner import run_afg_experiment_parallel
from metrics.analysis import generate_full_report, print_summary, compute_theme_coverage_comparison


def run_exp5(api_key: str, K: int = 10, model: str = "claude-sonnet-4-20250514", tracker=None):
    """Run EXP-5: Greenhushing scenario — disclosure vs silence."""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    with open(os.path.join(base, "config", "personas_scenario2.json")) as f:
        personas = json.load(f)["personas"]

    with open(os.path.join(base, "config", "scenarios.json")) as f:
        scenario = json.load(f)["scenario_2_greenhushing"]

    signal_state = scenario["signal_state_rich"]
    probes = scenario["moderator_probes"][:2]

    variants = {
        "A_disclose": scenario["stimuli"]["variant_A_disclose"],
        "B_silent": scenario["stimuli"]["variant_B_silent"],
    }

    results = {}
    reports = {}

    for vname, stimulus in variants.items():
        print(f"\n{'='*60}")
        print(f"EXP-5 Greenhushing Variant {vname} - K={K} (model: {model})")
        print(f"{'='*60}")

        result = run_afg_experiment_parallel(
            api_key, personas, stimulus, probes, K=K,
            signal_state=signal_state, temperature_mode="stratified",
            model=model, experiment_label=f"exp5_{vname}",
            usage_tracker=tracker,
        )
        results[vname] = result
        report = generate_full_report(result)
        reports[vname] = report
        print_summary(report)

    # Cross-variant comparison
    coverage = compute_theme_coverage_comparison(
        results["A_disclose"]["sessions"], results["B_silent"]["sessions"]
    )

    output = {
        "variants": results,
        "reports": reports,
        "comparison": coverage,
        "model": model,
    }

    output_dir = os.path.join(base, "results")
    os.makedirs(output_dir, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    path = os.path.join(output_dir, f"exp5_greenhushing_{model.split('-')[0]}_{ts}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str, ensure_ascii=False)
    print(f"\nSaved: {path}")

    return output


if __name__ == "__main__":
    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Set ANTHROPIC_API_KEY or OPENAI_API_KEY environment variable.")
        sys.exit(1)
    K = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    model = sys.argv[2] if len(sys.argv) > 2 else "claude-sonnet-4-20250514"
    run_exp5(api_key, K=K, model=model)
