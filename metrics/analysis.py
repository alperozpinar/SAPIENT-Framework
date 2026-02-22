"""
Metrics module for SAPIENT evaluation.
Computes metrics described in Table 1 of the paper:
  - Theme stability (CV across K runs)
  - Variance collapse (mean pairwise cosine similarity)
  - Sentiment distribution statistics
  - Persona consistency (stance across runs)
"""

import numpy as np
from collections import Counter
from typing import Optional
import json


# ============================================================
# Theme Stability (Table 1: "Run-to-run variance of themes")
# ============================================================

def compute_theme_stability(sessions: list[dict]) -> dict:
    """
    For each theme j identified across K runs, compute:
      - frequency f_j^(k) in each run
      - mean frequency across runs
      - coefficient of variation CV_j
      - classification: stable (CV <= 0.5) or unstable (CV > 0.5)
    
    Directly implements Section 3.3.6 item (2).
    """
    K = len(sessions)
    
    # Collect all themes across all runs
    all_themes = set()
    for s in sessions:
        all_themes.update(s.get("theme_list", []))
    
    if not all_themes:
        return {"themes": {}, "n_stable": 0, "n_unstable": 0, "stability_ratio": 0.0}
    
    theme_stats = {}
    for theme in all_themes:
        freqs = []
        for s in sessions:
            run_themes = s.get("theme_list", [])
            # Binary: did this theme appear in this run?
            freqs.append(1.0 if theme in run_themes else 0.0)
        
        freqs = np.array(freqs)
        mean_f = np.mean(freqs)
        std_f = np.std(freqs)
        cv = std_f / mean_f if mean_f > 0 else float("inf")
        
        theme_stats[theme] = {
            "frequency_per_run": freqs.tolist(),
            "appearance_rate": float(mean_f),
            "std": float(std_f),
            "cv": float(cv),
            "stable": cv <= 0.5,
            "appears_in_k_of_K": int(np.sum(freqs)),
        }
    
    n_stable = sum(1 for t in theme_stats.values() if t["stable"])
    n_unstable = sum(1 for t in theme_stats.values() if not t["stable"])
    
    return {
        "themes": theme_stats,
        "total_unique_themes": len(all_themes),
        "n_stable": n_stable,
        "n_unstable": n_unstable,
        "stability_ratio": n_stable / len(all_themes) if all_themes else 0.0,
        "K": K
    }


# ============================================================
# Variance Collapse (Table 1: "Persona consistency" + §3.3.6)
# ============================================================

def compute_variance_collapse(sessions: list[dict], use_embeddings: bool = False) -> dict:
    """
    Compute mean pairwise cosine similarity among persona responses within each run.
    
    If use_embeddings=True, uses sentence-transformers (requires model download).
    If use_embeddings=False, uses simple bag-of-words TF-IDF as a faster proxy.
    
    Threshold δ = 0.85: if exceeded, run is flagged for variance collapse.
    """
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    
    DELTA = 0.85  # Paper threshold
    run_scores = []
    flagged_runs = []
    
    for s in sessions:
        responses = s.get("initial_responses", [])
        if len(responses) < 2:
            continue
        
        texts = []
        for r in responses:
            text = r.get("interpretation", "") + " " + " ".join(r.get("concerns", []))
            texts.append(text)
        
        if use_embeddings:
            similarities = _compute_embedding_similarity(texts)
        else:
            similarities = _compute_tfidf_similarity(texts)
        
        # Mean pairwise (excluding diagonal)
        n = len(texts)
        if n > 1:
            mask = np.ones((n, n), dtype=bool)
            np.fill_diagonal(mask, False)
            mean_sim = float(np.mean(similarities[mask]))
        else:
            mean_sim = 0.0
        
        run_scores.append(mean_sim)
        if mean_sim > DELTA:
            flagged_runs.append(s.get("session_id", "unknown"))
    
    return {
        "per_run_mean_similarity": run_scores,
        "overall_mean": float(np.mean(run_scores)) if run_scores else None,
        "overall_std": float(np.std(run_scores)) if run_scores else None,
        "delta_threshold": DELTA,
        "n_flagged": len(flagged_runs),
        "flagged_run_ids": flagged_runs,
        "collapse_detected": len(flagged_runs) > 0
    }


def _compute_tfidf_similarity(texts: list[str]) -> np.ndarray:
    """Fast TF-IDF based cosine similarity."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    
    vectorizer = TfidfVectorizer(stop_words="english", max_features=500)
    tfidf = vectorizer.fit_transform(texts)
    return cosine_similarity(tfidf)


def _compute_embedding_similarity(texts: list[str]) -> np.ndarray:
    """Sentence-transformer based cosine similarity (more accurate but slower)."""
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    
    model = SentenceTransformer("all-MiniLM-L6-v2")
    embeddings = model.encode(texts)
    return cosine_similarity(embeddings)


# ============================================================
# Sentiment Distribution (Table 1: various)
# ============================================================

def compute_sentiment_stats(sessions: list[dict]) -> dict:
    """
    Compute sentiment distribution statistics across K runs.
    """
    all_sentiments = []
    per_run = []
    
    for s in sessions:
        run_sentiments = [
            r["sentiment"] for r in s.get("initial_responses", [])
            if r.get("sentiment") is not None
        ]
        if run_sentiments:
            per_run.append({
                "mean": float(np.mean(run_sentiments)),
                "std": float(np.std(run_sentiments)),
                "median": float(np.median(run_sentiments)),
                "min": int(min(run_sentiments)),
                "max": int(max(run_sentiments))
            })
            all_sentiments.extend(run_sentiments)
    
    if not all_sentiments:
        return {"error": "no sentiment data"}
    
    arr = np.array(all_sentiments)
    from scipy.stats import skew, kurtosis
    
    return {
        "overall": {
            "mean": float(np.mean(arr)),
            "std": float(np.std(arr)),
            "median": float(np.median(arr)),
            "skewness": float(skew(arr)),
            "kurtosis": float(kurtosis(arr)),
            "n": len(arr)
        },
        "per_run": per_run,
        "run_mean_std": float(np.std([r["mean"] for r in per_run])),
        "distribution": dict(Counter(int(x) for x in arr))
    }


def compute_credibility_stats(sessions: list[dict]) -> dict:
    """Compute credibility score distribution."""
    all_cred = []
    for s in sessions:
        for r in s.get("initial_responses", []):
            if r.get("credibility") is not None:
                all_cred.append(r["credibility"])
    
    if not all_cred:
        return {"error": "no credibility data"}
    
    arr = np.array(all_cred)
    return {
        "mean": float(np.mean(arr)),
        "std": float(np.std(arr)),
        "median": float(np.median(arr)),
        "distribution": dict(Counter(int(x) for x in arr)),
        "n": len(arr)
    }


# ============================================================
# Persona Consistency (Table 1: "Stance consistency")
# ============================================================

def compute_persona_consistency(sessions: list[dict]) -> dict:
    """
    For each persona, measure stance consistency across K runs.
    A persona that gives sentiment=2 in one run and sentiment=6 in another is inconsistent.
    """
    persona_sentiments = {}
    persona_actions = {}
    
    for s in sessions:
        for r in s.get("initial_responses", []):
            pid = r.get("persona_id", "unknown")
            if pid not in persona_sentiments:
                persona_sentiments[pid] = []
                persona_actions[pid] = []
            if r.get("sentiment") is not None:
                persona_sentiments[pid].append(r["sentiment"])
            if r.get("likely_action"):
                persona_actions[pid].append(r["likely_action"])
    
    results = {}
    for pid in persona_sentiments:
        sents = np.array(persona_sentiments[pid])
        actions = persona_actions.get(pid, [])
        
        # Action consistency: fraction of runs where the most common action appears
        if actions:
            action_counts = Counter(actions)
            most_common_action, most_common_count = action_counts.most_common(1)[0]
            action_consistency = most_common_count / len(actions)
        else:
            action_consistency = None
            most_common_action = None
        
        results[pid] = {
            "sentiment_mean": float(np.mean(sents)) if len(sents) > 0 else None,
            "sentiment_std": float(np.std(sents)) if len(sents) > 0 else None,
            "sentiment_range": int(np.ptp(sents)) if len(sents) > 0 else None,
            "n_runs": len(sents),
            "action_consistency": action_consistency,
            "most_common_action": most_common_action
        }
    
    # Overall consistency score
    all_stds = [v["sentiment_std"] for v in results.values() if v["sentiment_std"] is not None]
    
    return {
        "per_persona": results,
        "mean_sentiment_std": float(np.mean(all_stds)) if all_stds else None,
        "max_sentiment_std": float(np.max(all_stds)) if all_stds else None,
    }


# ============================================================
# Theme Coverage (for A/B experiment)
# ============================================================

def compute_theme_coverage_comparison(sessions_a: list[dict], sessions_b: list[dict]) -> dict:
    """
    Compare theme coverage between two conditions (e.g., with vs without signal state).
    """
    themes_a = set()
    themes_b = set()
    
    for s in sessions_a:
        themes_a.update(s.get("theme_list", []))
    for s in sessions_b:
        themes_b.update(s.get("theme_list", []))
    
    intersection = themes_a & themes_b
    union = themes_a | themes_b
    jaccard = len(intersection) / len(union) if union else 0.0
    
    return {
        "condition_a_themes": sorted(themes_a),
        "condition_b_themes": sorted(themes_b),
        "n_themes_a": len(themes_a),
        "n_themes_b": len(themes_b),
        "shared_themes": sorted(intersection),
        "unique_to_a": sorted(themes_a - themes_b),
        "unique_to_b": sorted(themes_b - themes_a),
        "jaccard_index": float(jaccard)
    }


# ============================================================
# Full Report Generator
# ============================================================

def generate_full_report(experiment_result: dict) -> dict:
    """
    Generate complete metrics report from an AFG experiment.
    """
    sessions = experiment_result.get("sessions", [])
    
    report = {
        "experiment": experiment_result.get("experiment_label", "unknown"),
        "K": experiment_result.get("K"),
        "n_personas": experiment_result.get("n_personas"),
        "model": experiment_result.get("model"),
        "theme_stability": compute_theme_stability(sessions),
        "variance_collapse": compute_variance_collapse(sessions, use_embeddings=False),
        "sentiment": compute_sentiment_stats(sessions),
        "credibility": compute_credibility_stats(sessions),
        "persona_consistency": compute_persona_consistency(sessions),
    }
    
    return report


def print_summary(report: dict):
    """Print a human-readable summary of the report."""
    print("=" * 70)
    print(f"SAPIENT AFG Experiment Report: {report['experiment']}")
    print(f"K={report['K']} runs, n={report['n_personas']} personas, model={report['model']}")
    print("=" * 70)
    
    ts = report.get("theme_stability", {})
    print(f"\n--- Theme Stability ---")
    print(f"Total unique themes: {ts.get('total_unique_themes', 'N/A')}")
    print(f"Stable themes (CV ≤ 0.5): {ts.get('n_stable', 'N/A')}")
    print(f"Unstable themes (CV > 0.5): {ts.get('n_unstable', 'N/A')}")
    print(f"Stability ratio: {ts.get('stability_ratio', 0):.2%}")
    
    vc = report.get("variance_collapse", {})
    print(f"\n--- Variance Collapse Check ---")
    print(f"Mean pairwise similarity: {vc.get('overall_mean', 'N/A'):.4f}" if vc.get('overall_mean') else "N/A")
    print(f"Threshold δ = {vc.get('delta_threshold', 0.85)}")
    print(f"Flagged runs: {vc.get('n_flagged', 0)} / {report['K']}")
    
    sent = report.get("sentiment", {}).get("overall", {})
    print(f"\n--- Sentiment Distribution ---")
    print(f"Mean: {sent.get('mean', 'N/A'):.2f}" if sent.get('mean') else "N/A")
    print(f"Std: {sent.get('std', 'N/A'):.2f}" if sent.get('std') else "N/A")
    print(f"Skewness: {sent.get('skewness', 'N/A'):.3f}" if sent.get('skewness') else "N/A")
    
    cred = report.get("credibility", {})
    print(f"\n--- Credibility ---")
    print(f"Mean: {cred.get('mean', 'N/A'):.2f}" if cred.get('mean') else "N/A")
    print(f"Std: {cred.get('std', 'N/A'):.2f}" if cred.get('std') else "N/A")
    
    pc = report.get("persona_consistency", {})
    print(f"\n--- Persona Consistency ---")
    print(f"Mean sentiment std across personas: {pc.get('mean_sentiment_std', 'N/A'):.3f}" if pc.get('mean_sentiment_std') else "N/A")
    
    print("\n" + "=" * 70)
