"""
EXP-7: Cross-Model Comparison — Claude Sonnet 4 vs GPT-4o

Maps to: Revision Exp — Multi-model robustness (R2-4, R2-7)
Tests: Whether AFG protocol produces consistent results across different LLM backends.
Uses Scenario 1 Variant C with both models, then compares metrics.
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
    tracker=None,
):
    """Run EXP-7: Same scenario on Claude and GPT-4o, then compare."""
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

    results = {}
    reports = {}

    for label, (model, api_key) in models.items():
        print(f"\n{'='*60}")
        print(f"EXP-7 Cross-Model: {model} - K={K}")
        print(f"{'='*60}")

        # OpenAI has low TPM limit (30K) -- reduce concurrency
        concurrency = 1 if label == "gpt4o" else 3

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
    print("\n" + "=" * 70)
    print("CROSS-MODEL COMPARISON: Claude Sonnet 4 vs GPT-4o")
    print("=" * 70)

    # Sentiment comparison
    sent_claude = reports["claude"].get("sentiment", {}).get("overall", {})
    sent_gpt = reports["gpt4o"].get("sentiment", {}).get("overall", {})

    # Collect all sentiment scores for t-test
    claude_sentiments = []
    gpt_sentiments = []
    for session in results["claude"]["sessions"]:
        claude_sentiments.extend(session.get("sentiment_scores", []))
    for session in results["gpt4o"]["sessions"]:
        gpt_sentiments.extend(session.get("sentiment_scores", []))

    comparison = {
        "sentiment": {
            "claude_mean": sent_claude.get("mean"),
            "claude_std": sent_claude.get("std"),
            "gpt4o_mean": sent_gpt.get("mean"),
            "gpt4o_std": sent_gpt.get("std"),
        }
    }

    if claude_sentiments and gpt_sentiments:
        t_stat, p_value = stats.ttest_ind(claude_sentiments, gpt_sentiments)
        comparison["sentiment"]["t_statistic"] = round(t_stat, 4)
        comparison["sentiment"]["p_value"] = round(p_value, 4)
        print(f"\nSentiment t-test: t={t_stat:.4f}, p={p_value:.4f}")

    print(f"  Claude: mean={sent_claude.get('mean', 0):.2f}, std={sent_claude.get('std', 0):.2f}")
    print(f"  GPT-4o: mean={sent_gpt.get('mean', 0):.2f}, std={sent_gpt.get('std', 0):.2f}")

    # Theme overlap (Jaccard)
    claude_themes = set()
    gpt_themes = set()
    for session in results["claude"]["sessions"]:
        claude_themes.update(session.get("theme_list", []))
    for session in results["gpt4o"]["sessions"]:
        gpt_themes.update(session.get("theme_list", []))

    shared = claude_themes & gpt_themes
    union = claude_themes | gpt_themes
    jaccard = len(shared) / len(union) if union else 0

    comparison["theme_overlap"] = {
        "claude_unique_themes": len(claude_themes),
        "gpt4o_unique_themes": len(gpt_themes),
        "shared_themes": len(shared),
        "jaccard_index": round(jaccard, 4),
    }

    print(f"\nTheme Overlap:")
    print(f"  Claude unique: {len(claude_themes)}, GPT-4o unique: {len(gpt_themes)}")
    print(f"  Shared: {len(shared)}, Jaccard: {jaccard:.4f}")

    # Variance collapse comparison
    vc_claude = reports["claude"].get("variance_collapse", {})
    vc_gpt = reports["gpt4o"].get("variance_collapse", {})

    comparison["variance_collapse"] = {
        "claude_mean_sim": vc_claude.get("overall_mean"),
        "gpt4o_mean_sim": vc_gpt.get("overall_mean"),
    }

    print(f"\nVariance Collapse:")
    print(f"  Claude mean sim: {vc_claude.get('overall_mean', 0):.4f}")
    print(f"  GPT-4o mean sim: {vc_gpt.get('overall_mean', 0):.4f}")

    # Persona-level correlation
    claude_persona_sent = {}
    gpt_persona_sent = {}
    for session in results["claude"]["sessions"]:
        for resp in session.get("initial_responses", []):
            pid = resp.get("persona_id")
            if pid and resp.get("sentiment") is not None:
                claude_persona_sent.setdefault(pid, []).append(resp["sentiment"])
    for session in results["gpt4o"]["sessions"]:
        for resp in session.get("initial_responses", []):
            pid = resp.get("persona_id")
            if pid and resp.get("sentiment") is not None:
                gpt_persona_sent.setdefault(pid, []).append(resp["sentiment"])

    common_pids = sorted(set(claude_persona_sent.keys()) & set(gpt_persona_sent.keys()))
    if len(common_pids) >= 3:
        claude_means = [np.mean(claude_persona_sent[p]) for p in common_pids]
        gpt_means = [np.mean(gpt_persona_sent[p]) for p in common_pids]
        r, p_val = stats.pearsonr(claude_means, gpt_means)
        comparison["persona_correlation"] = {
            "pearson_r": round(r, 4),
            "p_value": round(p_val, 4),
            "n_personas": len(common_pids),
        }
        print(f"\nPersona-level Sentiment Correlation:")
        print(f"  Pearson r={r:.4f}, p={p_val:.4f} (n={len(common_pids)})")

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
    if not key_claude or not key_openai:
        print("Both ANTHROPIC_API_KEY and OPENAI_API_KEY must be set.")
        sys.exit(1)
    K = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    run_exp7(key_claude, key_openai, K=K)
