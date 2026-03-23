"""
EXP-8: Prompt Sensitivity — Original vs Paraphrase

Maps to: Revision Exp — Prompt robustness check (R2-3)
Tests: Whether semantically equivalent but differently worded stimuli produce
       statistically similar persona responses.
Uses Scenario 1 Variant C original and its paraphrase. Single model. K=5.
"""

import os
import sys
import json
import time

import numpy as np
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.parallel_runner import run_afg_experiment_parallel
from metrics.analysis import generate_full_report, print_summary, compute_theme_coverage_comparison


def run_exp8(api_key: str, K: int = 5, model: str = "claude-sonnet-4-20250514", tracker=None):
    """Run EXP-8: Original vs paraphrase prompt sensitivity test."""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    with open(os.path.join(base, "config", "personas.json")) as f:
        personas = json.load(f)["personas"]

    with open(os.path.join(base, "config", "scenarios.json")) as f:
        scenario = json.load(f)["scenario_1_greenwashing"]

    signal_state = scenario["signal_state_rich"]
    probes = scenario["moderator_probes"][:2]

    variants = {
        "original": scenario["stimuli"]["variant_C_accountability"],
        "paraphrase": scenario["stimuli"]["variant_C_paraphrase"],
    }

    results = {}
    reports = {}

    for vname, stimulus in variants.items():
        print(f"\n{'='*60}")
        print(f"EXP-8 Prompt Sensitivity: {vname} - K={K} (model: {model})")
        print(f"{'='*60}")

        result = run_afg_experiment_parallel(
            api_key, personas, stimulus, probes, K=K,
            signal_state=signal_state, temperature_mode="stratified",
            model=model, experiment_label=f"exp8_{vname}",
            usage_tracker=tracker,
        )
        results[vname] = result
        report = generate_full_report(result)
        reports[vname] = report
        print_summary(report)

    # --- Sensitivity analysis ---
    print("\n" + "=" * 70)
    print("PROMPT SENSITIVITY ANALYSIS: Original vs Paraphrase")
    print("=" * 70)

    # Sentiment comparison
    orig_sentiments = []
    para_sentiments = []
    for session in results["original"]["sessions"]:
        orig_sentiments.extend(session.get("sentiment_scores", []))
    for session in results["paraphrase"]["sessions"]:
        para_sentiments.extend(session.get("sentiment_scores", []))

    comparison = {}

    if orig_sentiments and para_sentiments:
        t_stat, p_value = stats.ttest_ind(orig_sentiments, para_sentiments)
        comparison["sentiment_ttest"] = {
            "original_mean": round(np.mean(orig_sentiments), 4),
            "paraphrase_mean": round(np.mean(para_sentiments), 4),
            "t_statistic": round(t_stat, 4),
            "p_value": round(p_value, 4),
            "significant_at_05": p_value < 0.05,
        }
        print(f"\nSentiment t-test:")
        print(f"  Original:   mean={np.mean(orig_sentiments):.2f}, std={np.std(orig_sentiments):.2f}")
        print(f"  Paraphrase: mean={np.mean(para_sentiments):.2f}, std={np.std(para_sentiments):.2f}")
        print(f"  t={t_stat:.4f}, p={p_value:.4f} {'*' if p_value < 0.05 else '(n.s.)'}")

    # Credibility comparison
    orig_cred = []
    para_cred = []
    for session in results["original"]["sessions"]:
        orig_cred.extend(session.get("credibility_scores", []))
    for session in results["paraphrase"]["sessions"]:
        para_cred.extend(session.get("credibility_scores", []))

    if orig_cred and para_cred:
        t_stat, p_value = stats.ttest_ind(orig_cred, para_cred)
        comparison["credibility_ttest"] = {
            "original_mean": round(np.mean(orig_cred), 4),
            "paraphrase_mean": round(np.mean(para_cred), 4),
            "t_statistic": round(t_stat, 4),
            "p_value": round(p_value, 4),
            "significant_at_05": p_value < 0.05,
        }
        print(f"\nCredibility t-test:")
        print(f"  Original:   mean={np.mean(orig_cred):.2f}")
        print(f"  Paraphrase: mean={np.mean(para_cred):.2f}")
        print(f"  t={t_stat:.4f}, p={p_value:.4f} {'*' if p_value < 0.05 else '(n.s.)'}")

    # Theme overlap
    coverage = compute_theme_coverage_comparison(
        results["original"]["sessions"], results["paraphrase"]["sessions"]
    )
    comparison["theme_overlap"] = coverage

    print(f"\nTheme Overlap:")
    print(f"  Original: {coverage['n_themes_a']} themes")
    print(f"  Paraphrase: {coverage['n_themes_b']} themes")
    print(f"  Jaccard: {coverage['jaccard_index']:.4f}")

    # Interpretation
    all_ns = True
    for key in ["sentiment_ttest", "credibility_ttest"]:
        if key in comparison and comparison[key].get("significant_at_05"):
            all_ns = False

    if all_ns:
        print(f"\n  RESULT: No significant differences - prompt is robust to paraphrasing.")
    else:
        print(f"\n  RESULT: Significant differences found - prompt sensitivity detected.")

    output = {
        "results": results,
        "reports": reports,
        "comparison": comparison,
        "model": model,
    }

    output_dir = os.path.join(base, "results")
    os.makedirs(output_dir, exist_ok=True)
    ts_str = time.strftime("%Y%m%d_%H%M%S")
    path = os.path.join(output_dir, f"exp8_prompt_sensitivity_{ts_str}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str, ensure_ascii=False)
    print(f"\nSaved: {path}")

    return output


if __name__ == "__main__":
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Set ANTHROPIC_API_KEY environment variable.")
        sys.exit(1)
    K = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    model = sys.argv[2] if len(sys.argv) > 2 else "claude-sonnet-4-20250514"
    run_exp8(api_key, K=K, model=model)
