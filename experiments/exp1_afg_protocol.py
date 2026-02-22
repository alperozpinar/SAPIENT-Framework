"""
EXP-1: AFG Protocol Proof-of-Concept — Greenwashing Backlash Prediction

Maps to: Paper Stage 2 (partial), Scenario 1 (§4.1)
Tests: Theme stability, variance collapse, sentiment distribution across 3 framing variants.
Runs: K=10 per variant, 8 personas, independent mode.

Expected output: Evidence that the AFG protocol produces stable, diverse results.
"""

import os
import sys
import json
import time

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import anthropic
from agents.moderator_agent import run_afg_experiment
from metrics.analysis import generate_full_report, print_summary


def run_exp1(api_key: str, K: int = 10, model: str = "claude-sonnet-4-20250514"):
    """
    Run EXP-1: AFG protocol on 3 framing variants of a greenwashing announcement.
    """
    client = anthropic.Anthropic(api_key=api_key)
    
    # Load configs
    with open(os.path.join(os.path.dirname(__file__), "..", "config", "personas.json")) as f:
        personas = json.load(f)["personas"]
    
    with open(os.path.join(os.path.dirname(__file__), "..", "config", "scenarios.json")) as f:
        scenario = json.load(f)["scenario_1_greenwashing"]
    
    signal_state = scenario["signal_state_rich"]
    probes = scenario["moderator_probes"][:2]  # Use first 2 probes
    
    variants = {
        "A_targets": scenario["stimuli"]["variant_A_targets"],
        "B_progress": scenario["stimuli"]["variant_B_progress"],
        "C_accountability": scenario["stimuli"]["variant_C_accountability"],
    }
    
    results = {}
    reports = {}
    
    for variant_name, stimulus in variants.items():
        print(f"\n{'='*60}")
        print(f"Running Variant {variant_name} — K={K} runs")
        print(f"{'='*60}\n")
        
        exp_result = run_afg_experiment(
            client=client,
            personas=personas,
            stimulus=stimulus,
            probes=probes,
            K=K,
            signal_state=signal_state,
            temperature_mode="stratified",
            model=model,
            experiment_label=f"exp1_{variant_name}"
        )
        
        results[variant_name] = exp_result
        report = generate_full_report(exp_result)
        reports[variant_name] = report
        print_summary(report)
    
    # --- Cross-variant comparison ---
    print("\n" + "=" * 70)
    print("CROSS-VARIANT COMPARISON")
    print("=" * 70)
    
    for vname, report in reports.items():
        sent = report.get("sentiment", {}).get("overall", {})
        cred = report.get("credibility", {})
        ts = report.get("theme_stability", {})
        vc = report.get("variance_collapse", {})
        
        print(f"\n{vname}:")
        print(f"  Sentiment: mean={sent.get('mean', 0):.2f}, std={sent.get('std', 0):.2f}")
        print(f"  Credibility: mean={cred.get('mean', 0):.2f}")
        print(f"  Theme stability ratio: {ts.get('stability_ratio', 0):.2%}")
        print(f"  Variance collapse (mean sim): {vc.get('overall_mean', 0):.4f}")
    
    # Save all results
    output_dir = os.path.join(os.path.dirname(__file__), "..", "results")
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    
    # Save raw sessions
    with open(os.path.join(output_dir, f"exp1_raw_{timestamp}.json"), "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    # Save reports
    with open(os.path.join(output_dir, f"exp1_reports_{timestamp}.json"), "w") as f:
        json.dump(reports, f, indent=2, default=str)
    
    print(f"\nResults saved to {output_dir}/exp1_*_{timestamp}.json")
    
    return results, reports


if __name__ == "__main__":
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Set ANTHROPIC_API_KEY environment variable.")
        sys.exit(1)
    
    # Parse arguments
    K = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    model = sys.argv[2] if len(sys.argv) > 2 else "claude-sonnet-4-20250514"
    
    run_exp1(api_key, K=K, model=model)
