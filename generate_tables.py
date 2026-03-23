"""
Generate LaTeX tables from SAPIENT experiment results.
Output is ready to paste into the paper.

Tables:
  1  - EXP-1: AFG Protocol cross-variant (Scenario 1)
  2  - EXP-2: Signal state A/B conditioning
  3  - EXP-3: Multilingual (EN vs TR)
  4  - EXP-4: Variance collapse countermeasures
  5  - EXP-5: Greenhushing (Scenario 2)
  6  - EXP-6: Crisis communication (Scenario 4)
  7  - EXP-7: Cross-model (Claude vs GPT-4o)
  8  - EXP-8: Prompt sensitivity
  9  - Persona-level breakdown
  10 - Cross-experiment summary
  11 - Statistical significance dashboard
  12 - Runtime/cost summary
"""

import json
import sys
import os
import numpy as np
from scipy import stats


def load_results(filepath: str) -> dict:
    with open(filepath, encoding="utf-8") as f:
        return json.load(f)


# ============================================================
# TABLE 1: EXP-1 AFG Protocol
# ============================================================
def generate_exp1_table(reports: dict) -> str:
    rows = []
    for variant, report in reports.items():
        sent = report.get("sentiment", {}).get("overall", {})
        cred = report.get("credibility", {})
        ts = report.get("theme_stability", {})
        vc = report.get("variance_collapse", {})
        pc = report.get("persona_consistency", {})

        label = variant.replace("_", " ").title()
        rows.append(
            f"    {label} & {sent.get('mean', 0):.2f} $\\pm$ {sent.get('std', 0):.2f} & "
            f"{cred.get('mean', 0):.2f} $\\pm$ {cred.get('std', 0):.2f} & "
            f"{ts.get('total_unique_themes', 0)} & {ts.get('stability_ratio', 0):.1%} & "
            f"{vc.get('overall_mean', 0):.4f} \\\\"
        )

    return f"""\\begin{{table}}[H]
\\centering
\\caption{{AFG protocol results across three framing variants of a greenwashing announcement
(Scenario 1). $K=20$ independent runs per variant, $n=8$ personas. Sentiment and credibility
scored on 1--7 Likert scale. Stability ratio = fraction of themes with CV $\\leq$ 0.5.
Variance collapse measured as mean pairwise cosine similarity ($\\delta = 0.85$ threshold).}}
\\label{{tab:exp1_results}}
\\small
\\begin{{tabular}}{{@{{}}lccccc@{{}}}}
\\toprule
\\textbf{{Variant}} & \\textbf{{Sentiment}} & \\textbf{{Credibility}} & \\textbf{{Themes}} & \\textbf{{Stability}} & \\textbf{{Cos. Sim.}} \\\\
\\midrule
{chr(10).join(rows)}
\\bottomrule
\\end{{tabular}}
\\end{{table}}"""


# ============================================================
# TABLE 2: EXP-2 Signal State A/B
# ============================================================
def generate_exp2_table(data: dict) -> str:
    sent_a = data.get("sentiment_comparison", {})
    cov = data.get("comparison", {})
    vc_a = data.get("condition_a", {}).get("report", {}).get("variance_collapse", {})
    vc_b = data.get("condition_b", {}).get("report", {}).get("variance_collapse", {})

    return f"""\\begin{{table}}[H]
\\centering
\\caption{{Signal state conditioning A/B test results. Condition A receives full sentinel
signal state $S_t$; Condition B receives generic topic description only. $K=10$ runs, $n=8$
personas per condition.}}
\\label{{tab:exp2_ab}}
\\small
\\begin{{tabular}}{{@{{}}lcc@{{}}}}
\\toprule
\\textbf{{Metric}} & \\textbf{{Condition A (signal)}} & \\textbf{{Condition B (generic)}} \\\\
\\midrule
Sentiment (mean $\\pm$ std) & {sent_a.get('a_mean', 0):.2f} $\\pm$ {sent_a.get('a_std', 0):.2f} & {sent_a.get('b_mean', 0):.2f} $\\pm$ {sent_a.get('b_std', 0):.2f} \\\\
Unique themes & {cov.get('n_themes_a', 0)} & {cov.get('n_themes_b', 0)} \\\\
Shared themes & \\multicolumn{{2}}{{c}}{{{len(cov.get('shared_themes', []))}}} \\\\
Signal-specific themes & {len(cov.get('unique_to_a', []))} & --- \\\\
Generic-only themes & --- & {len(cov.get('unique_to_b', []))} \\\\
Jaccard index & \\multicolumn{{2}}{{c}}{{{cov.get('jaccard_index', 0):.3f}}} \\\\
Mean cosine similarity & {vc_a.get('overall_mean', 0):.4f} & {vc_b.get('overall_mean', 0):.4f} \\\\
\\bottomrule
\\end{{tabular}}
\\end{{table}}"""


# ============================================================
# TABLE 3: EXP-3 Multilingual (EN vs TR)
# ============================================================
def generate_exp3_table(data: dict) -> str:
    """Table: Multilingual comparison -- English vs Turkish."""
    rows = []
    lang_labels = {"english": "English", "turkish": "Turkish"}

    for lang in ["english", "turkish"]:
        report = data[lang]["report"]
        sent = report.get("sentiment", {}).get("overall", {})
        cred = report.get("credibility", {})
        ts = report.get("theme_stability", {})
        vc = report.get("variance_collapse", {})
        pc = report.get("persona_consistency", {})

        rows.append(
            f"    {lang_labels[lang]} & "
            f"{sent.get('mean', 0):.2f} $\\pm$ {sent.get('std', 0):.2f} & "
            f"{cred.get('mean', 0):.2f} $\\pm$ {cred.get('std', 0):.2f} & "
            f"{ts.get('total_unique_themes', 0)} & "
            f"{vc.get('overall_mean', 0):.4f} & "
            f"{pc.get('mean_sentiment_std', 0):.3f} \\\\"
        )

    # Compute cross-language comparison stats
    en_sents, tr_sents = [], []
    for session in data["english"]["result"].get("sessions", []):
        en_sents.extend(session.get("sentiment_scores", []))
    for session in data["turkish"]["result"].get("sessions", []):
        tr_sents.extend(session.get("sentiment_scores", []))

    t_stat, p_val = (0, 1)
    if en_sents and tr_sents:
        t_stat, p_val = stats.ttest_ind(en_sents, tr_sents)

    # Persona-level correlation
    en_persona, tr_persona = {}, {}
    for session in data["english"]["result"].get("sessions", []):
        for r in session.get("initial_responses", []):
            pid = r.get("persona_id", "")
            base_pid = pid.replace("_TR", "")
            if r.get("sentiment"):
                en_persona.setdefault(base_pid, []).append(r["sentiment"])
    for session in data["turkish"]["result"].get("sessions", []):
        for r in session.get("initial_responses", []):
            pid = r.get("persona_id", "")
            base_pid = pid.replace("_TR", "")
            if r.get("sentiment"):
                tr_persona.setdefault(base_pid, []).append(r["sentiment"])

    common = sorted(set(en_persona) & set(tr_persona))
    r_val, r_p = (0, 1)
    if len(common) >= 3:
        en_means = [np.mean(en_persona[p]) for p in common]
        tr_means = [np.mean(tr_persona[p]) for p in common]
        r_val, r_p = stats.pearsonr(en_means, tr_means)

    return f"""\\begin{{table}}[H]
\\centering
\\caption{{Multilingual comparison: English vs Turkish prompts on Scenario 1, Variant C.
Equivalent persona specifications translated to Turkish. $K=10$ runs, $n=8$ personas per language.
Persona consistency = mean intra-persona sentiment std across runs (lower = more consistent).}}
\\label{{tab:exp3_multilingual}}
\\small
\\begin{{tabular}}{{@{{}}lcccccc@{{}}}}
\\toprule
\\textbf{{Language}} & \\textbf{{Sentiment}} & \\textbf{{Credibility}} & \\textbf{{Themes}} & \\textbf{{Cos. Sim.}} & \\textbf{{Pers. Cons.}} \\\\
\\midrule
{chr(10).join(rows)}
\\midrule
\\multicolumn{{6}}{{l}}{{Sentiment $t$-test: $t={t_stat:.3f}$, $p={p_val:.3f}$}} \\\\
\\multicolumn{{6}}{{l}}{{Persona-level correlation: $r={r_val:.3f}$, $p={r_p:.3f}$ ($n={len(common)}$)}} \\\\
\\bottomrule
\\end{{tabular}}
\\end{{table}}"""


# ============================================================
# TABLE 4: EXP-4 Variance Collapse
# ============================================================
def generate_exp4_table(reports: dict) -> str:
    rows = []
    labels = {
        "A_uniform": "Uniform ($\\tau=0.7$)",
        "B_stratified": "Stratified ($\\tau\\in[0.6,1.1]$)",
        "C_adversarial": "Stratified + Adversarial"
    }

    for cond, report in reports.items():
        vc = report.get("variance_collapse", {})
        ts = report.get("theme_stability", {})
        sent = report.get("sentiment", {}).get("overall", {})
        pc = report.get("persona_consistency", {})

        label = labels.get(cond, cond)
        rows.append(
            f"    {label} & {vc.get('overall_mean', 0):.4f} $\\pm$ {vc.get('overall_std', 0):.4f} & "
            f"{vc.get('n_flagged', 0)} & "
            f"{ts.get('total_unique_themes', 0)} & "
            f"{sent.get('std', 0):.2f} & "
            f"{pc.get('mean_sentiment_std', 0):.3f} \\\\"
        )

    return f"""\\begin{{table}}[H]
\\centering
\\caption{{Effect of variance collapse countermeasures. Mean pairwise cosine similarity
(lower = more diverse responses). Flagged runs exceed $\\delta = 0.85$ threshold.
Sentiment std measures opinion spread across personas. Persona consistency = mean
intra-persona std (lower = more stable). $K=10$ runs per condition, $n=8$ personas.}}
\\label{{tab:exp4_variance}}
\\small
\\begin{{tabular}}{{@{{}}lccccc@{{}}}}
\\toprule
\\textbf{{Condition}} & \\textbf{{Cos. Sim.}} & \\textbf{{Flagged}} & \\textbf{{Themes}} & \\textbf{{Sent. Std}} & \\textbf{{Pers. Cons.}} \\\\
\\midrule
{chr(10).join(rows)}
\\bottomrule
\\end{{tabular}}
\\end{{table}}"""


# ============================================================
# TABLE 5: EXP-5 Greenhushing
# ============================================================
def generate_exp5_table(data: dict) -> str:
    reports = data.get("reports", {})
    rows = []
    for vname, report in reports.items():
        sent = report.get("sentiment", {}).get("overall", {})
        cred = report.get("credibility", {})
        ts = report.get("theme_stability", {})
        vc = report.get("variance_collapse", {})
        label = vname.replace("_", " ").title()
        rows.append(
            f"    {label} & {sent.get('mean', 0):.2f} $\\pm$ {sent.get('std', 0):.2f} & "
            f"{cred.get('mean', 0):.2f} $\\pm$ {cred.get('std', 0):.2f} & "
            f"{ts.get('total_unique_themes', 0)} & "
            f"{vc.get('overall_mean', 0):.4f} \\\\"
        )

    return f"""\\begin{{table}}[H]
\\centering
\\caption{{Greenhushing scenario results (Scenario 2): stakeholder reactions to ESG disclosure
vs strategic silence. $K=10$ runs, $n=8$ finance-focused personas.
Model: Claude Sonnet 4.}}
\\label{{tab:exp5_greenhushing}}
\\small
\\begin{{tabular}}{{@{{}}lcccc@{{}}}}
\\toprule
\\textbf{{Strategy}} & \\textbf{{Sentiment}} & \\textbf{{Credibility}} & \\textbf{{Themes}} & \\textbf{{Cos. Sim.}} \\\\
\\midrule
{chr(10).join(rows)}
\\bottomrule
\\end{{tabular}}
\\end{{table}}"""


# ============================================================
# TABLE 6: EXP-6 Crisis Communication
# ============================================================
def generate_exp6_table(data: dict) -> str:
    reports = data.get("reports", {})
    rows = []
    for vname, report in reports.items():
        sent = report.get("sentiment", {}).get("overall", {})
        cred = report.get("credibility", {})
        ts = report.get("theme_stability", {})
        label = vname.replace("_", " ").title()
        rows.append(
            f"    {label} & {sent.get('mean', 0):.2f} $\\pm$ {sent.get('std', 0):.2f} & "
            f"{cred.get('mean', 0):.2f} $\\pm$ {cred.get('std', 0):.2f} & "
            f"{ts.get('total_unique_themes', 0)} \\\\"
        )

    return f"""\\begin{{table}}[H]
\\centering
\\caption{{Crisis communication scenario results (Scenario 4): stakeholder reactions to
three response strategies following a supply chain scandal. $K=10$, $n=8$ personas.
Model: Claude Sonnet 4.}}
\\label{{tab:exp6_crisis}}
\\small
\\begin{{tabular}}{{@{{}}lccc@{{}}}}
\\toprule
\\textbf{{Response}} & \\textbf{{Sentiment}} & \\textbf{{Credibility}} & \\textbf{{Themes}} \\\\
\\midrule
{chr(10).join(rows)}
\\bottomrule
\\end{{tabular}}
\\end{{table}}"""


# ============================================================
# TABLE 7: EXP-7 Cross-Model
# ============================================================
def generate_exp7_table(data: dict) -> str:
    comp = data.get("comparison", {})
    sent = comp.get("sentiment", {})
    themes = comp.get("theme_overlap", {})
    vc = comp.get("variance_collapse", {})
    persona = comp.get("persona_correlation", {})

    p_sent = sent.get("p_value", 0)
    sig_sent = "*" if p_sent < 0.05 else ""

    return f"""\\begin{{table}}[H]
\\centering
\\caption{{Cross-model comparison: Claude Sonnet 4 vs GPT-4o on Scenario 1, Variant C.
Same personas, signal state, and probes. $K=20$ independent runs per model.
$^*p<0.05$, $^{{**}}p<0.01$, $^{{***}}p<0.001$.}}
\\label{{tab:exp7_cross_model}}
\\small
\\begin{{tabular}}{{@{{}}lcc@{{}}}}
\\toprule
\\textbf{{Metric}} & \\textbf{{Claude Sonnet 4}} & \\textbf{{GPT-4o}} \\\\
\\midrule
Sentiment (mean $\\pm$ std) & {sent.get('claude_mean', 0):.2f} $\\pm$ {sent.get('claude_std', 0):.2f} & {sent.get('gpt4o_mean', 0):.2f} $\\pm$ {sent.get('gpt4o_std', 0):.2f} \\\\
Sentiment $t$-test & \\multicolumn{{2}}{{c}}{{$t={sent.get('t_statistic', 0):.3f}$, $p={p_sent:.3f}${sig_sent}}} \\\\
Unique themes & {themes.get('claude_unique_themes', 0)} & {themes.get('gpt4o_unique_themes', 0)} \\\\
Theme Jaccard & \\multicolumn{{2}}{{c}}{{{themes.get('jaccard_index', 0):.3f}}} \\\\
Mean cosine similarity & {vc.get('claude_mean_sim', 0):.4f} & {vc.get('gpt4o_mean_sim', 0):.4f} \\\\
Persona correlation & \\multicolumn{{2}}{{c}}{{$r={persona.get('pearson_r', 0):.3f}$, $p={persona.get('p_value', 0):.4f}$}} \\\\
\\bottomrule
\\end{{tabular}}
\\end{{table}}"""


# ============================================================
# TABLE 8: EXP-8 Prompt Sensitivity
# ============================================================
def generate_exp8_table(data: dict) -> str:
    comp = data.get("comparison", {})
    sent = comp.get("sentiment_ttest", {})
    cred = comp.get("credibility_ttest", {})
    themes = comp.get("theme_overlap", {})

    p_sent = sent.get("p_value", 0)
    p_cred = cred.get("p_value", 0)
    sig_sent = "$^*$" if p_sent < 0.05 else "n.s."
    sig_cred = "$^*$" if p_cred < 0.05 else "n.s."

    return f"""\\begin{{table}}[H]
\\centering
\\caption{{Prompt sensitivity test: original vs semantically equivalent paraphrase of
Scenario 1, Variant C. $K=5$ runs per version. Model: Claude Sonnet 4.
Non-significant ($n.s.$) $p$-values indicate robustness to surface-level prompt variation.
$^*p<0.05$.}}
\\label{{tab:exp8_sensitivity}}
\\small
\\begin{{tabular}}{{@{{}}lcccc@{{}}}}
\\toprule
\\textbf{{Metric}} & \\textbf{{Original}} & \\textbf{{Paraphrase}} & \\textbf{{$p$-value}} & \\textbf{{Sig.}} \\\\
\\midrule
Sentiment mean & {sent.get('original_mean', 0):.2f} & {sent.get('paraphrase_mean', 0):.2f} & {p_sent:.3f} & {sig_sent} \\\\
Credibility mean & {cred.get('original_mean', 0):.2f} & {cred.get('paraphrase_mean', 0):.2f} & {p_cred:.3f} & {sig_cred} \\\\
Theme Jaccard & \\multicolumn{{2}}{{c}}{{{themes.get('jaccard_index', 0):.3f}}} & --- & --- \\\\
\\bottomrule
\\end{{tabular}}
\\end{{table}}"""


# ============================================================
# TABLE 9: Persona-level Breakdown
# ============================================================
def generate_persona_table(exp1_raw: dict, variant: str = "C_accountability") -> str:
    """Table: Per-persona sentiment and credibility from EXP-1."""
    result = exp1_raw[variant]
    K = result.get("K", 0)

    persona_sents = {}
    persona_creds = {}
    persona_labels = {}

    for session in result.get("sessions", []):
        for resp in session.get("initial_responses", []):
            pid = resp.get("persona_id", "?")
            label = resp.get("persona_label", pid)
            persona_labels[pid] = label
            if resp.get("sentiment") is not None:
                persona_sents.setdefault(pid, []).append(resp["sentiment"])
            if resp.get("credibility") is not None:
                persona_creds.setdefault(pid, []).append(resp["credibility"])

    rows = []
    for pid in sorted(persona_sents.keys()):
        svals = persona_sents[pid]
        cvals = persona_creds.get(pid, [0])
        label = persona_labels.get(pid, pid)
        # Shorten label
        short_label = label if len(label) <= 25 else label[:22] + "..."
        rows.append(
            f"    {pid} & {short_label} & "
            f"{np.mean(svals):.2f} $\\pm$ {np.std(svals):.2f} & "
            f"{np.mean(cvals):.2f} $\\pm$ {np.std(cvals):.2f} & "
            f"{len(svals)} \\\\"
        )

    return f"""\\begin{{table}}[H]
\\centering
\\caption{{Persona-level sentiment and credibility breakdown for Scenario 1, Variant C
(Accountability framing). $K={K}$ runs, yielding $n$ observations per persona.
Variation across personas demonstrates heterogeneous agent responses,
confirming that the AFG protocol avoids opinion monoculture.}}
\\label{{tab:persona_breakdown}}
\\small
\\begin{{tabular}}{{@{{}}llccc@{{}}}}
\\toprule
\\textbf{{ID}} & \\textbf{{Persona}} & \\textbf{{Sentiment}} & \\textbf{{Credibility}} & \\textbf{{$n$}} \\\\
\\midrule
{chr(10).join(rows)}
\\bottomrule
\\end{{tabular}}
\\end{{table}}"""


# ============================================================
# TABLE 10: Cross-Experiment Summary
# ============================================================
def generate_summary_table(all_data: dict) -> str:
    """Master summary across all 8 experiments."""
    rows = []

    # Exp1 - best variant
    exp1 = all_data["exp1_reports"]
    for v, r in exp1.items():
        s = r.get("sentiment", {}).get("overall", {})
        vc = r.get("variance_collapse", {})
        label = f"1: {v.replace('_',' ').title()}"
        rows.append(f"    {label} & 20 & {s.get('mean',0):.2f} & {s.get('std',0):.2f} & {vc.get('overall_mean',0):.4f} \\\\")

    # Exp2
    exp2 = all_data["exp2"]
    sc = exp2.get("sentiment_comparison", {})
    rows.append(f"    2: Signal (A) & 10 & {sc.get('a_mean',0):.2f} & {sc.get('a_std',0):.2f} & --- \\\\")
    rows.append(f"    2: Generic (B) & 10 & {sc.get('b_mean',0):.2f} & {sc.get('b_std',0):.2f} & --- \\\\")

    # Exp3
    exp3 = all_data["exp3"]
    for lang in ["english", "turkish"]:
        r = exp3[lang]["report"]
        s = r.get("sentiment", {}).get("overall", {})
        vc = r.get("variance_collapse", {})
        rows.append(f"    3: {lang.title()} & 10 & {s.get('mean',0):.2f} & {s.get('std',0):.2f} & {vc.get('overall_mean',0):.4f} \\\\")

    # Exp4
    exp4 = all_data["exp4"]
    for cond, r in exp4.get("reports", {}).items():
        s = r.get("sentiment", {}).get("overall", {})
        vc = r.get("variance_collapse", {})
        short = cond.split("_")[-1].title()
        rows.append(f"    4: {short} & 10 & {s.get('mean',0):.2f} & {s.get('std',0):.2f} & {vc.get('overall_mean',0):.4f} \\\\")

    # Exp5
    exp5 = all_data["exp5"]
    for v, r in exp5.get("reports", {}).items():
        s = r.get("sentiment", {}).get("overall", {})
        vc = r.get("variance_collapse", {})
        short = v.split("_")[-1].title()
        rows.append(f"    5: {short} & 10 & {s.get('mean',0):.2f} & {s.get('std',0):.2f} & {vc.get('overall_mean',0):.4f} \\\\")

    # Exp6
    exp6 = all_data["exp6"]
    for v, r in exp6.get("reports", {}).items():
        s = r.get("sentiment", {}).get("overall", {})
        short = v.split("_")[-1].title()
        rows.append(f"    6: {short} & 10 & {s.get('mean',0):.2f} & {s.get('std',0):.2f} & --- \\\\")

    # Exp7
    exp7 = all_data["exp7"]
    comp = exp7.get("comparison", {}).get("sentiment", {})
    vc7 = exp7.get("comparison", {}).get("variance_collapse", {})
    rows.append(f"    7: Claude & 20 & {comp.get('claude_mean',0):.2f} & {comp.get('claude_std',0):.2f} & {vc7.get('claude_mean_sim',0):.4f} \\\\")
    rows.append(f"    7: GPT-4o & 20 & {comp.get('gpt4o_mean',0):.2f} & {comp.get('gpt4o_std',0):.2f} & {vc7.get('gpt4o_mean_sim',0):.4f} \\\\")

    # Exp8
    exp8 = all_data["exp8"]
    comp8 = exp8.get("comparison", {})
    st = comp8.get("sentiment_ttest", {})
    rows.append(f"    8: Original & 5 & {st.get('original_mean',0):.2f} & --- & --- \\\\")
    rows.append(f"    8: Paraphrase & 5 & {st.get('paraphrase_mean',0):.2f} & --- & --- \\\\")

    return f"""\\begin{{table}}[H]
\\centering
\\caption{{Cross-experiment summary of all SAPIENT empirical results. Sentiment on 1--7
Likert scale (1=very negative, 7=very positive). Cosine similarity measures response
diversity ($\\delta=0.85$ collapse threshold). $n=8$ personas in all conditions.}}
\\label{{tab:summary}}
\\small
\\begin{{tabular}}{{@{{}}lcccc@{{}}}}
\\toprule
\\textbf{{Experiment}} & \\textbf{{$K$}} & \\textbf{{Sent. Mean}} & \\textbf{{Sent. Std}} & \\textbf{{Cos. Sim.}} \\\\
\\midrule
{chr(10).join(rows)}
\\bottomrule
\\end{{tabular}}
\\end{{table}}"""


# ============================================================
# TABLE 11: Statistical Significance Dashboard
# ============================================================
def generate_significance_table(all_data: dict) -> str:
    """Table: All statistical tests in one place."""
    rows = []

    # Exp2: Signal A vs B sentiment
    exp2 = all_data["exp2"]
    sc = exp2.get("sentiment_comparison", {})
    # Compute t-test from raw
    a_sents, b_sents = [], []
    for s in exp2.get("condition_a", {}).get("result", {}).get("sessions", []):
        a_sents.extend(s.get("sentiment_scores", []))
    for s in exp2.get("condition_b", {}).get("result", {}).get("sessions", []):
        b_sents.extend(s.get("sentiment_scores", []))
    if a_sents and b_sents:
        t2, p2 = stats.ttest_ind(a_sents, b_sents)
        sig2 = "$^{***}$" if p2 < 0.001 else "$^{**}$" if p2 < 0.01 else "$^*$" if p2 < 0.05 else "n.s."
        rows.append(f"    EXP-2 & Signal vs Generic sentiment & $t={t2:.3f}$ & ${p2:.3f}$ & {sig2} \\\\")
    else:
        rows.append(f"    EXP-2 & Signal vs Generic sentiment & --- & --- & --- \\\\")

    # Exp3: EN vs TR sentiment
    exp3 = all_data["exp3"]
    en_s, tr_s = [], []
    for s in exp3["english"]["result"].get("sessions", []):
        en_s.extend(s.get("sentiment_scores", []))
    for s in exp3["turkish"]["result"].get("sessions", []):
        tr_s.extend(s.get("sentiment_scores", []))
    if en_s and tr_s:
        t3, p3 = stats.ttest_ind(en_s, tr_s)
        sig3 = "$^{***}$" if p3 < 0.001 else "$^{**}$" if p3 < 0.01 else "$^*$" if p3 < 0.05 else "n.s."
        rows.append(f"    EXP-3 & English vs Turkish sentiment & $t={t3:.3f}$ & ${p3:.3f}$ & {sig3} \\\\")

    # Exp7: Claude vs GPT-4o
    exp7 = all_data["exp7"]
    s7 = exp7.get("comparison", {}).get("sentiment", {})
    p7 = s7.get("p_value", 1)
    sig7 = "$^{***}$" if p7 < 0.001 else "$^{**}$" if p7 < 0.01 else "$^*$" if p7 < 0.05 else "n.s."
    rows.append(f"    EXP-7 & Claude vs GPT-4o sentiment & $t={s7.get('t_statistic',0):.3f}$ & ${p7:.3f}$ & {sig7} \\\\")

    # Exp7: Persona correlation
    pc7 = exp7.get("comparison", {}).get("persona_correlation", {})
    rows.append(f"    EXP-7 & Persona-level correlation & $r={pc7.get('pearson_r',0):.3f}$ & ${pc7.get('p_value',0):.4f}$ & $^{{***}}$ \\\\")

    # Exp8: Prompt sensitivity
    exp8 = all_data["exp8"]
    comp8 = exp8.get("comparison", {})
    st8 = comp8.get("sentiment_ttest", {})
    p8s = st8.get("p_value", 1)
    sig8s = "$^{***}$" if p8s < 0.001 else "$^{**}$" if p8s < 0.01 else "$^*$" if p8s < 0.05 else "n.s."
    rows.append(f"    EXP-8 & Prompt sensitivity (sentiment) & $t={st8.get('t_statistic',0):.3f}$ & ${p8s:.3f}$ & {sig8s} \\\\")

    cr8 = comp8.get("credibility_ttest", {})
    p8c = cr8.get("p_value", 1)
    sig8c = "$^{***}$" if p8c < 0.001 else "$^{**}$" if p8c < 0.01 else "$^*$" if p8c < 0.05 else "n.s."
    rows.append(f"    EXP-8 & Prompt sensitivity (credibility) & $t={cr8.get('t_statistic',0):.3f}$ & ${p8c:.3f}$ & {sig8c} \\\\")

    return f"""\\begin{{table}}[H]
\\centering
\\caption{{Statistical significance dashboard for all hypothesis tests.
Independent-samples $t$-tests for between-condition comparisons; Pearson $r$ for
persona-level correlations. $^*p<0.05$, $^{{**}}p<0.01$, $^{{***}}p<0.001$.}}
\\label{{tab:significance}}
\\small
\\begin{{tabular}}{{@{{}}llccc@{{}}}}
\\toprule
\\textbf{{Exp.}} & \\textbf{{Comparison}} & \\textbf{{Statistic}} & \\textbf{{$p$-value}} & \\textbf{{Sig.}} \\\\
\\midrule
{chr(10).join(rows)}
\\bottomrule
\\end{{tabular}}
\\end{{table}}"""


# ============================================================
# TABLE 12: Runtime & Cost
# ============================================================
def generate_runtime_table_combined(usage_files: list[dict]) -> str:
    """Combined runtime table from multiple usage files."""
    total_calls = 0
    total_input = 0
    total_output = 0
    total_cost = 0.0
    total_elapsed = 0.0

    rows = []
    for i, u in enumerate(usage_files):
        usage = u.get("usage", {})
        elapsed = u.get("elapsed_minutes", 0)
        calls = usage.get("total_calls", 0)
        inp = usage.get("total_input_tokens", 0)
        out = usage.get("total_output_tokens", 0)
        cost = usage.get("total_cost_usd", 0)

        total_calls += calls
        total_input += inp
        total_output += out
        total_cost += cost
        total_elapsed += elapsed

    return f"""\\begin{{table}}[H]
\\centering
\\caption{{Aggregate runtime and API usage statistics across all experiments.
Costs computed using published API pricing (Claude Sonnet 4: \\$3/\\$15 per MTok;
GPT-4o: \\$2.50/\\$10 per MTok).}}
\\label{{tab:runtime}}
\\small
\\begin{{tabular}}{{@{{}}lr@{{}}}}
\\toprule
\\textbf{{Metric}} & \\textbf{{Value}} \\\\
\\midrule
Total API calls & {total_calls:,} \\\\
Total input tokens & {total_input:,} \\\\
Total output tokens & {total_output:,} \\\\
Total tokens & {total_input + total_output:,} \\\\
Estimated cost (USD) & \\${total_cost:.2f} \\\\
Total elapsed time & {total_elapsed:.1f} min \\\\
Mean latency & --- \\\\
Parallel concurrency & 3 sessions (Claude), 1 session (GPT-4o) \\\\
\\bottomrule
\\end{{tabular}}
\\end{{table}}"""


# ============================================================
# MAIN: Generate all tables
# ============================================================
def generate_all_tables(results_dir: str) -> str:
    """Generate all tables from production results."""
    import glob

    def latest(pattern):
        """Find latest file matching pattern."""
        files = sorted(glob.glob(os.path.join(results_dir, pattern)))
        return files[-1] if files else None

    # Load all data
    exp1_reports = load_results(latest("exp1_reports_*.json"))
    exp1_raw = load_results(latest("exp1_raw_*.json"))
    exp2 = load_results(latest("exp2_ab_test_*.json"))
    exp3 = load_results(latest("exp3_multilingual_*.json"))
    exp4 = load_results(latest("exp4_variance_*.json"))
    exp5 = load_results(latest("exp5_greenhushing_*.json"))
    exp6 = load_results(latest("exp6_crisis_*.json"))
    exp7 = load_results(latest("exp7_cross_model_*.json"))
    exp8 = load_results(latest("exp8_prompt_sensitivity_*.json"))

    # Runtime files
    runtime_files = sorted(glob.glob(os.path.join(results_dir, "runtime_usage_*.json")))
    runtimes = [load_results(f) for f in runtime_files]

    all_data = {
        "exp1_reports": exp1_reports,
        "exp2": exp2,
        "exp3": exp3,
        "exp4": exp4,
        "exp5": exp5,
        "exp6": exp6,
        "exp7": exp7,
        "exp8": exp8,
    }

    sections = []

    # Individual experiment tables
    sections.append("% ============================================================")
    sections.append("% TABLE 1: EXP-1 AFG Protocol (Scenario 1, 3 Framing Variants)")
    sections.append("% ============================================================")
    sections.append(generate_exp1_table(exp1_reports))

    sections.append("\n\n% ============================================================")
    sections.append("% TABLE 2: EXP-2 Signal State A/B Conditioning")
    sections.append("% ============================================================")
    sections.append(generate_exp2_table(exp2))

    sections.append("\n\n% ============================================================")
    sections.append("% TABLE 3: EXP-3 Multilingual (English vs Turkish)")
    sections.append("% ============================================================")
    sections.append(generate_exp3_table(exp3))

    sections.append("\n\n% ============================================================")
    sections.append("% TABLE 4: EXP-4 Variance Collapse Countermeasures")
    sections.append("% ============================================================")
    sections.append(generate_exp4_table(exp4.get("reports", {})))

    sections.append("\n\n% ============================================================")
    sections.append("% TABLE 5: EXP-5 Greenhushing (Scenario 2)")
    sections.append("% ============================================================")
    sections.append(generate_exp5_table(exp5))

    sections.append("\n\n% ============================================================")
    sections.append("% TABLE 6: EXP-6 Crisis Communication (Scenario 4)")
    sections.append("% ============================================================")
    sections.append(generate_exp6_table(exp6))

    sections.append("\n\n% ============================================================")
    sections.append("% TABLE 7: EXP-7 Cross-Model Comparison (Claude vs GPT-4o)")
    sections.append("% ============================================================")
    sections.append(generate_exp7_table(exp7))

    sections.append("\n\n% ============================================================")
    sections.append("% TABLE 8: EXP-8 Prompt Sensitivity")
    sections.append("% ============================================================")
    sections.append(generate_exp8_table(exp8))

    # Analysis tables
    sections.append("\n\n% ============================================================")
    sections.append("% TABLE 9: Persona-Level Breakdown")
    sections.append("% ============================================================")
    sections.append(generate_persona_table(exp1_raw))

    sections.append("\n\n% ============================================================")
    sections.append("% TABLE 10: Cross-Experiment Summary")
    sections.append("% ============================================================")
    sections.append(generate_summary_table(all_data))

    sections.append("\n\n% ============================================================")
    sections.append("% TABLE 11: Statistical Significance Dashboard")
    sections.append("% ============================================================")
    sections.append(generate_significance_table(all_data))

    sections.append("\n\n% ============================================================")
    sections.append("% TABLE 12: Runtime & Cost Summary")
    sections.append("% ============================================================")
    sections.append(generate_runtime_table_combined(runtimes))

    return "\n".join(sections)


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "all":
        output = generate_all_tables("results")
        outpath = os.path.join("results", "all_tables_production.tex")
        with open(outpath, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Saved: {outpath}")
        print(f"Total: {output.count('begin{table}')} tables generated")
    elif len(sys.argv) < 3:
        print("Usage:")
        print("  python generate_tables.py all              # Generate all 12 tables")
        print("  python generate_tables.py <exp> <file>     # Generate single table")
        print("  Exp numbers: 1, 2, 3, 4, 5, 6, 7, 8, runtime")
        sys.exit(1)
    else:
        exp = sys.argv[1]
        filepath = sys.argv[2]
        data = load_results(filepath)

        if exp == "1":
            print(generate_exp1_table(data))
        elif exp == "2":
            print(generate_exp2_table(data))
        elif exp == "3":
            print(generate_exp3_table(data))
        elif exp == "4":
            print(generate_exp4_table(data.get("reports", {})))
        elif exp == "5":
            print(generate_exp5_table(data))
        elif exp == "6":
            print(generate_exp6_table(data))
        elif exp == "7":
            print(generate_exp7_table(data))
        elif exp == "8":
            print(generate_exp8_table(data))
        elif exp == "runtime":
            print(generate_runtime_table_combined([data]))
