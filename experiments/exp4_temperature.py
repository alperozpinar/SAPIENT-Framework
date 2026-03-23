"""
EXP-4: Variance Collapse Countermeasures Test

Maps to: Paper §3.3.1 (temperature stratification, adversarial persona injection)
Tests: Whether the paper's proposed countermeasures actually reduce variance collapse.

3 conditions:
  A) Uniform temperature τ=0.7, standard personas
  B) Stratified temperature τ∈[0.6, 1.1], standard personas
  C) Stratified temperature + adversarial persona injection
"""

import os
import sys
import json
import time
import copy

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.moderator_agent import run_afg_experiment
from metrics.analysis import generate_full_report, print_summary, compute_variance_collapse


def make_adversarial_persona(base_personas: list[dict]) -> list[dict]:
    """
    Replace last persona with an adversarial (contrarian) version.
    Paper §3.3.1: 'at least one persona per session is assigned a contrarian stance'.
    """
    modified = copy.deepcopy(base_personas)
    adversarial = modified[-1]
    adversarial["id"] = "P_ADV"
    adversarial["label"] = "Contrarian Skeptic"
    adversarial["psychographics"]["environmental_concern"] = "very_low"
    adversarial["psychographics"]["institutional_trust"] = "very_low"
    adversarial["psychographics"]["brand_loyalty"] = "none"
    adversarial["behavioral_priors"]["engagement_style"] = "contrarian_skeptical"
    adversarial["behavioral_priors"]["frame_susceptibility"] = "anti_corporate_any_direction"
    adversarial["behavioral_priors"]["info_seeking"] = "very_high"
    return modified


def run_exp4(api_key: str, K: int = 5, model: str = "claude-sonnet-4-20250514"):
    """Run variance collapse countermeasure comparison."""
    with open(os.path.join(os.path.dirname(__file__), "..", "config", "personas.json")) as f:
        personas = json.load(f)["personas"]

    with open(os.path.join(os.path.dirname(__file__), "..", "config", "scenarios.json")) as f:
        scenario = json.load(f)["scenario_1_greenwashing"]

    stimulus = scenario["stimuli"]["variant_C_accountability"]
    probes = scenario["moderator_probes"][:2]
    signal_state = scenario["signal_state_rich"]

    conditions = {}
    reports = {}

    # --- Condition A: Uniform low temperature ---
    print("\n" + "=" * 60)
    print("CONDITION A: Uniform tau=0.7")
    print("=" * 60)

    result_a = run_afg_experiment(
        api_key=api_key, personas=personas, stimulus=stimulus, probes=probes,
        K=K, signal_state=signal_state, temperature_mode="uniform_low",
        model=model, experiment_label="exp4_condA_uniform"
    )
    conditions["A_uniform"] = result_a
    reports["A_uniform"] = generate_full_report(result_a)
    print_summary(reports["A_uniform"])

    # --- Condition B: Stratified temperature ---
    print("\n" + "=" * 60)
    print("CONDITION B: Stratified tau in [0.6, 1.1]")
    print("=" * 60)

    result_b = run_afg_experiment(
        api_key=api_key, personas=personas, stimulus=stimulus, probes=probes,
        K=K, signal_state=signal_state, temperature_mode="stratified",
        model=model, experiment_label="exp4_condB_stratified"
    )
    conditions["B_stratified"] = result_b
    reports["B_stratified"] = generate_full_report(result_b)
    print_summary(reports["B_stratified"])

    # --- Condition C: Stratified + adversarial persona ---
    print("\n" + "=" * 60)
    print("CONDITION C: Stratified + Adversarial Persona")
    print("=" * 60)

    adv_personas = make_adversarial_persona(personas)
    result_c = run_afg_experiment(
        api_key=api_key, personas=adv_personas, stimulus=stimulus, probes=probes,
        K=K, signal_state=signal_state, temperature_mode="stratified",
        model=model, experiment_label="exp4_condC_adversarial"
    )
    conditions["C_adversarial"] = result_c
    reports["C_adversarial"] = generate_full_report(result_c)
    print_summary(reports["C_adversarial"])

    # --- Comparison ---
    print("\n" + "=" * 70)
    print("VARIANCE COLLAPSE COMPARISON")
    print("=" * 70)
    print(f"\n{'Condition':<30} {'Mean Cosine Sim':>16} {'Flagged Runs':>14}")
    print("-" * 62)

    for cond_name, report in reports.items():
        vc = report.get("variance_collapse", {})
        mean_sim = vc.get("overall_mean", 0)
        n_flagged = vc.get("n_flagged", 0)
        print(f"{cond_name:<30} {mean_sim:>16.4f} {n_flagged:>10}/{K}")

    print(f"\n(Lower cosine similarity = more diverse responses)")
    print(f"(Threshold delta = 0.85; runs above are flagged)")

    # Save
    output_dir = os.path.join(os.path.dirname(__file__), "..", "results")
    os.makedirs(output_dir, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")

    with open(os.path.join(output_dir, f"exp4_variance_{timestamp}.json"), "w") as f:
        json.dump({
            "conditions": conditions,
            "reports": reports
        }, f, indent=2, default=str)

    print(f"\nResults saved to {output_dir}/exp4_variance_{timestamp}.json")


if __name__ == "__main__":
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Set ANTHROPIC_API_KEY environment variable.")
        sys.exit(1)
    K = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    run_exp4(api_key, K=K)
