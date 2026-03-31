"""
EXP-7: Cross-Model Comparison — Claude Sonnet 4 vs GPT-4o vs Gemini 2.5 Flash

Maps to: Revision Exp — Multi-model robustness (R2-4, R2-7)
Tests: Whether AFG protocol produces consistent results across different LLM backends.
Uses Scenario 1 Variant C with all models, then compares metrics.
"""

import os
import sys
import json
import time

import numpy as np
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.parallel_runner import run_afg_experiment_parallel
from metrics.analysis import generate_full_report, print_summary


def run_exp7(
    key_claude: str,
    key_openai: str,
    K: int = 20,
    key_gemini: str = None,
    tracker=None,
):
    """Run EXP-7: Same scenario on Claude, GPT-4o, and optionally Gemini, then compare."""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    with open(os.path.join(base, "config", "personas.json")) as f:
        personas = json.load(f)["personas"]

    with open(os.path.join(base, "config", "scenarios.json")) as f:
        scenario = json.load(f)["scenario_1_greenwashing"]

    stimulus = scenario["stimuli"]["variant_C_accountability"]
    probes = scenario["moderator_probes"][:2]
    signal_state = scenario["signal_state_rich"]

    models = {
        "claude": ("claude-sonnet-4-20250514", key_claude),
        "gpt4o": ("gpt-4o", key_openai),
    }
    if key_gemini:
        models["gemini"] = ("gemini-2.5-flash", key_gemini)

    results = {}
    reports = {}

    for label, (model, api_key) in models.items():
        print(f"\n{'='*60}")
        print(f"EXP-7 Cross-Model: {model} - K={K}")
        print(f"{'='*60}")

        # Concurrency limits per provider
        if label == "gpt4o":
            concurrency = 1  # OpenAI low TPM limit (30K)
        elif label == "gemini":
            concurrency = 2  # Gemini: start conservative
        else:
            concurrency = 3

        result = run_afg_experiment_parallel(
            api_key, personas, stimulus, probes, K=K,
            signal_state=signal_state, temperature_mode="stratified",
            model=model, experiment_label=f"exp7_{label}",
            max_concurrent_runs=concurrency,
            usage_tracker=tracker,
        )
        results[label] = result
        report = generate_full_report(result)
        reports[label] = report
        print_summary(report)

    # --- Cross-model comparison ---
    model_labels = list(results.keys())
    model_display = {
        "claude": "Claude Sonnet 4",
        "gpt4o": "GPT-4o",
        "gemini": "Gemini 2.5 Flash",
    }

    print("\n" + "=" * 70)
    print(f"CROSS-MODEL COMPARISON: {' vs '.join(model_display.get(m, m) for m in model_labels)}")
    print("=" * 70)

    # Collect all sentiment scores per model
    model_sentiments = {}
    for label in model_labels:
        sents = []
        for session in results[label]["sessions"]:
            sents.extend(session.get("sentiment_scores", []))
        model_sentiments[label] = sents

    # Sentiment summary per model
    comparison = {"sentiment": {}}
    for label in model_labels:
        sent_report = reports[label].get("sentiment", {}).get("overall", {})
        comparison["sentiment"][label] = {
            "mean": sent_report.get("mean"),
            "std": sent_report.get("std"),
        }
        print(f"  {model_display.get(label, label)}: mean={sent_report.get('mean', 0):.2f}, std={sent_report.get('std', 0):.2f}")

    # Pairwise sentiment t-tests
    comparison["pairwise_ttests"] = {}
    for i, m1 in enumerate(model_labels):
        for m2 in model_labels[i+1:]:
            if model_sentiments[m1] and model_sentiments[m2]:
                t_stat, p_value = stats.ttest_ind(model_sentiments[m1], model_sentiments[m2])
                pair_key = f"{m1}_vs_{m2}"
                comparison["pairwise_ttests"][pair_key] = {
                    "t_statistic": round(t_stat, 4),
                    "p_value": round(p_value, 4),
                }
                print(f"\n  Sentiment t-test ({m1} vs {m2}): t={t_stat:.4f}, p={p_value:.4f}")

    # Theme overlap (pairwise Jaccard)
    model_themes = {}
    for label in model_labels:
        themes = set()
        for session in results[label]["sessions"]:
            themes.update(session.get("theme_list", []))
        model_themes[label] = themes

    comparison["theme_overlap"] = {}
    print(f"\nTheme Overlap (Jaccard):")
    for i, m1 in enumerate(model_labels):
        for m2 in model_labels[i+1:]:
            shared = model_themes[m1] & model_themes[m2]
            union = model_themes[m1] | model_themes[m2]
            jaccard = len(shared) / len(union) if union else 0
            pair_key = f"{m1}_vs_{m2}"
            comparison["theme_overlap"][pair_key] = {
                f"{m1}_unique_themes": len(model_themes[m1]),
                f"{m2}_unique_themes": len(model_themes[m2]),
                "shared_themes": len(shared),
                "jaccard_index": round(jaccard, 4),
            }
            print(f"  {m1} vs {m2}: Jaccard={jaccard:.4f} (shared={len(shared)}, union={len(union)})")

    # Variance collapse comparison
    comparison["variance_collapse"] = {}
    print(f"\nVariance Collapse:")
    for label in model_labels:
        vc = reports[label].get("variance_collapse", {})
        comparison["variance_collapse"][label] = {
            "mean_sim": vc.get("overall_mean"),
        }
        print(f"  {model_display.get(label, label)} mean sim: {vc.get('overall_mean', 0):.4f}")

    # Persona-level correlation (pairwise Spearman)
    model_persona_sent = {}
    for label in model_labels:
        persona_sent = {}
        for session in results[label]["sessions"]:
            for resp in session.get("initial_responses", []):
                pid = resp.get("persona_id")
                if pid and resp.get("sentiment") is not None:
                    persona_sent.setdefault(pid, []).append(resp["sentiment"])
        model_persona_sent[label] = persona_sent

    comparison["persona_correlation"] = {}
    print(f"\nPersona-level Sentiment Correlation (Spearman):")
    for i, m1 in enumerate(model_labels):
        for m2 in model_labels[i+1:]:
            common_pids = sorted(
                set(model_persona_sent[m1].keys()) & set(model_persona_sent[m2].keys())
            )
            if len(common_pids) >= 3:
                means_1 = [np.mean(model_persona_sent[m1][p]) for p in common_pids]
                means_2 = [np.mean(model_persona_sent[m2][p]) for p in common_pids]
                r_spearman, p_spearman = stats.spearmanr(means_1, means_2)
                r_pearson, p_pearson = stats.pearsonr(means_1, means_2)
                pair_key = f"{m1}_vs_{m2}"
                comparison["persona_correlation"][pair_key] = {
                    "spearman_r": round(r_spearman, 4),
                    "spearman_p": round(p_spearman, 4),
                    "pearson_r": round(r_pearson, 4),
                    "pearson_p": round(p_pearson, 4),
                    "n_personas": len(common_pids),
                    "persona_means_1": {p: round(np.mean(model_persona_sent[m1][p]), 3) for p in common_pids},
                    "persona_means_2": {p: round(np.mean(model_persona_sent[m2][p]), 3) for p in common_pids},
                }
                print(f"  {m1} vs {m2}: Spearman r={r_spearman:.4f} (p={p_spearman:.4f}), "
                      f"Pearson r={r_pearson:.4f} (p={p_pearson:.4f}), n={len(common_pids)}")

    output = {
        "results": results,
        "reports": reports,
        "comparison": comparison,
    }

    output_dir = os.path.join(base, "results")
    os.makedirs(output_dir, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    path = os.path.join(output_dir, f"exp7_cross_model_{ts}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str, ensure_ascii=False)
    print(f"\nSaved: {path}")

    return output


if __name__ == "__main__":
    key_claude = os.environ.get("ANTHROPIC_API_KEY")
    key_openai = os.environ.get("OPENAI_API_KEY")
    key_gemini = os.environ.get("GEMINI_API_KEY")
    if not key_claude or not key_openai:
        print("Both ANTHROPIC_API_KEY and OPENAI_API_KEY must be set.")
        sys.exit(1)
    if not key_gemini:
        print("Warning: GEMINI_API_KEY not set, Gemini arm will be skipped.")
    K = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    run_exp7(key_claude, key_openai, K=K, key_gemini=key_gemini)
