"""
Generate LaTeX tables from SAPIENT experiment results.
Output is ready to paste into the paper.
"""

import json
import sys
import os
import numpy as np


def load_results(filepath: str) -> dict:
    with open(filepath) as f:
        return json.load(f)


def generate_exp1_table(reports: dict) -> str:
    """
    Table: Cross-variant comparison from EXP-1.
    Columns: Variant, Sentiment (mean±std), Credibility (mean±std), 
             Theme Stability Ratio, Variance Collapse Score
    """
    rows = []
    for variant, report in reports.items():
        sent = report.get("sentiment", {}).get("overall", {})
        cred = report.get("credibility", {})
        ts = report.get("theme_stability", {})
        vc = report.get("variance_collapse", {})
        
        label = variant.replace("_", " ").title()
        s_mean = sent.get("mean", 0)
        s_std = sent.get("std", 0)
        c_mean = cred.get("mean", 0)
        c_std = cred.get("std", 0)
        sr = ts.get("stability_ratio", 0)
        vcs = vc.get("overall_mean", 0)
        n_themes = ts.get("total_unique_themes", 0)
        
        rows.append(
            f"    {label} & {s_mean:.2f} $\\pm$ {s_std:.2f} & "
            f"{c_mean:.2f} $\\pm$ {c_std:.2f} & "
            f"{n_themes} & {sr:.1%} & {vcs:.4f} \\\\"
        )
    
    table = f"""\\begin{{table}}[H]
\\centering
\\caption{{AFG protocol results across three framing variants of a greenwashing announcement 
(Scenario 1). $K=10$ independent runs per variant, $n=8$ personas. Sentiment and credibility 
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
    return table


def generate_exp2_table(comparison: dict) -> str:
    """Table: A/B signal conditioning comparison."""
    sent_a = comparison.get("sentiment_comparison", {})
    cov = comparison.get("comparison", {})
    
    # Get variance collapse from reports
    vc_a = comparison.get("condition_a", {}).get("report", {}).get("variance_collapse", {})
    vc_b = comparison.get("condition_b", {}).get("report", {}).get("variance_collapse", {})
    
    table = f"""\\begin{{table}}[H]
\\centering
\\caption{{Signal state conditioning A/B test results. Condition A receives full sentinel 
signal state $S_t$; Condition B receives generic topic description only. $K=5$ runs, $n=8$ 
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
    return table


def generate_exp4_table(reports: dict) -> str:
    """Table: Variance collapse countermeasures comparison."""
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
        
        label = labels.get(cond, cond)
        rows.append(
            f"    {label} & {vc.get('overall_mean', 0):.4f} $\\pm$ {vc.get('overall_std', 0):.4f} & "
            f"{vc.get('n_flagged', 0)} & "
            f"{ts.get('total_unique_themes', 0)} & "
            f"{sent.get('std', 0):.2f} \\\\"
        )
    
    table = f"""\\begin{{table}}[H]
\\centering
\\caption{{Effect of variance collapse countermeasures. Mean pairwise cosine similarity 
(lower = more diverse responses). Flagged runs exceed $\\delta = 0.85$ threshold. 
Sentiment std measures opinion spread across personas within runs. $K=5$ runs per condition.}}
\\label{{tab:exp4_variance}}
\\small
\\begin{{tabular}}{{@{{}}lcccc@{{}}}}
\\toprule
\\textbf{{Condition}} & \\textbf{{Cos. Sim. (mean$\\pm$std)}} & \\textbf{{Flagged}} & \\textbf{{Themes}} & \\textbf{{Sent. Std}} \\\\
\\midrule
{chr(10).join(rows)}
\\bottomrule
\\end{{tabular}}
\\end{{table}}"""
    return table


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python generate_tables.py <exp_number> <results_file>")
        print("  python generate_tables.py 1 results/exp1_reports_*.json")
        sys.exit(1)
    
    exp = int(sys.argv[1])
    filepath = sys.argv[2]
    data = load_results(filepath)
    
    if exp == 1:
        print(generate_exp1_table(data))
    elif exp == 2:
        print(generate_exp2_table(data))
    elif exp == 4:
        print(generate_exp4_table(data.get("reports", {})))
