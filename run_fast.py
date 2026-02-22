#!/usr/bin/env python3
"""
SAPIENT Fast Runner — Parallel API calls, ~5-8x faster.

Usage:
  SET ANTHROPIC_API_KEY=sk-ant-...
  python run_fast.py --all
  python run_fast.py --exp 1 --K 20
  python run_fast.py --estimate
"""

import os
import sys
import json
import time
import argparse
import copy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.parallel_runner import run_afg_experiment_parallel
from metrics.analysis import (
    generate_full_report, print_summary,
    compute_theme_coverage_comparison
)


def load_config():
    base = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(base, "config", "personas.json")) as f:
        personas = json.load(f)["personas"]
    with open(os.path.join(base, "config", "scenarios.json")) as f:
        scenario = json.load(f)["scenario_1_greenwashing"]
    return personas, scenario


def save_results(data: dict, name: str):
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
    os.makedirs(output_dir, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    path = os.path.join(output_dir, f"{name}_{ts}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str, ensure_ascii=False)
    print(f"Saved: {path}")
    return path


def run_exp1(api_key, K, model):
    """EXP-1: AFG Protocol — 3 variants."""
    personas, scenario = load_config()
    signal_state = scenario["signal_state_rich"]
    probes = scenario["moderator_probes"][:2]
    
    variants = {
        "A_targets": scenario["stimuli"]["variant_A_targets"],
        "B_progress": scenario["stimuli"]["variant_B_progress"],
        "C_accountability": scenario["stimuli"]["variant_C_accountability"],
    }
    
    results = {}
    reports = {}
    
    for vname, stimulus in variants.items():
        print(f"\n{'='*60}")
        print(f"EXP-1 Variant {vname} — K={K} (parallel)")
        print(f"{'='*60}")
        
        result = run_afg_experiment_parallel(
            api_key, personas, stimulus, probes, K=K,
            signal_state=signal_state, temperature_mode="stratified",
            model=model, experiment_label=f"exp1_{vname}"
        )
        results[vname] = result
        report = generate_full_report(result)
        reports[vname] = report
        print_summary(report)
    
    save_results(results, "exp1_raw")
    save_results(reports, "exp1_reports")
    return results, reports


def run_exp2(api_key, K, model):
    """EXP-2: Signal State A/B."""
    personas, scenario = load_config()
    stimulus = scenario["stimuli"]["variant_C_accountability"]
    probes = scenario["moderator_probes"][:2]
    
    print(f"\n{'='*60}")
    print(f"EXP-2 Condition A: Full Signal State — K={K}")
    print(f"{'='*60}")
    result_a = run_afg_experiment_parallel(
        api_key, personas, stimulus, probes, K=K,
        signal_state=scenario["signal_state_rich"],
        temperature_mode="stratified", model=model,
        experiment_label="exp2_condA_signal"
    )
    report_a = generate_full_report(result_a)
    print_summary(report_a)
    
    print(f"\n{'='*60}")
    print(f"EXP-2 Condition B: Generic Only — K={K}")
    print(f"{'='*60}")
    result_b = run_afg_experiment_parallel(
        api_key, personas, stimulus, probes, K=K,
        signal_state=None,
        temperature_mode="stratified", model=model,
        experiment_label="exp2_condB_generic"
    )
    report_b = generate_full_report(result_b)
    print_summary(report_b)
    
    coverage = compute_theme_coverage_comparison(
        result_a["sessions"], result_b["sessions"]
    )
    
    output = {
        "condition_a": {"result": result_a, "report": report_a},
        "condition_b": {"result": result_b, "report": report_b},
        "comparison": coverage,
        "sentiment_comparison": {
            "a_mean": report_a["sentiment"]["overall"].get("mean"),
            "a_std": report_a["sentiment"]["overall"].get("std"),
            "b_mean": report_b["sentiment"]["overall"].get("mean"),
            "b_std": report_b["sentiment"]["overall"].get("std"),
        }
    }
    save_results(output, "exp2_ab_test")
    return output


def run_exp3(api_key, K, model):
    """EXP-3: Multilingual EN vs TR."""
    from experiments.exp3_multilingual import TURKISH_PERSONAS, TURKISH_STIMULUS, TURKISH_PROBES
    
    personas, scenario = load_config()
    stimulus = scenario["stimuli"]["variant_C_accountability"]
    probes = scenario["moderator_probes"][:2]
    signal_state = scenario["signal_state_rich"]
    
    print(f"\n{'='*60}")
    print(f"EXP-3 English — K={K}")
    print(f"{'='*60}")
    result_en = run_afg_experiment_parallel(
        api_key, personas, stimulus, probes, K=K,
        signal_state=signal_state, temperature_mode="stratified",
        model=model, experiment_label="exp3_EN"
    )
    report_en = generate_full_report(result_en)
    print_summary(report_en)
    
    print(f"\n{'='*60}")
    print(f"EXP-3 Turkish — K={K}")
    print(f"{'='*60}")
    result_tr = run_afg_experiment_parallel(
        api_key, TURKISH_PERSONAS, TURKISH_STIMULUS, TURKISH_PROBES, K=K,
        signal_state=signal_state, temperature_mode="stratified",
        model=model, experiment_label="exp3_TR"
    )
    report_tr = generate_full_report(result_tr)
    print_summary(report_tr)
    
    output = {
        "english": {"result": result_en, "report": report_en},
        "turkish": {"result": result_tr, "report": report_tr},
    }
    save_results(output, "exp3_multilingual")
    return output


def run_exp4(api_key, K, model):
    """EXP-4: Variance collapse countermeasures."""
    personas, scenario = load_config()
    stimulus = scenario["stimuli"]["variant_C_accountability"]
    probes = scenario["moderator_probes"][:2]
    signal_state = scenario["signal_state_rich"]
    
    # Adversarial persona
    adv_personas = copy.deepcopy(personas)
    adv = adv_personas[-1]
    adv["id"] = "P_ADV"
    adv["label"] = "Contrarian Skeptic"
    adv["psychographics"]["environmental_concern"] = "very_low"
    adv["psychographics"]["institutional_trust"] = "very_low"
    adv["behavioral_priors"]["engagement_style"] = "contrarian_skeptical"
    
    conditions = {
        "A_uniform": {"personas": personas, "temp": "uniform_low"},
        "B_stratified": {"personas": personas, "temp": "stratified"},
        "C_adversarial": {"personas": adv_personas, "temp": "stratified"},
    }
    
    results = {}
    reports = {}
    
    for cname, cfg in conditions.items():
        print(f"\n{'='*60}")
        print(f"EXP-4 Condition {cname} — K={K}")
        print(f"{'='*60}")
        result = run_afg_experiment_parallel(
            api_key, cfg["personas"], stimulus, probes, K=K,
            signal_state=signal_state, temperature_mode=cfg["temp"],
            model=model, experiment_label=f"exp4_{cname}"
        )
        results[cname] = result
        report = generate_full_report(result)
        reports[cname] = report
        print_summary(report)
    
    save_results({"conditions": results, "reports": reports}, "exp4_variance")
    return results, reports


def estimate_cost(K1, Ko, model):
    n = 8
    calls = n * 2  # initial + followup
    exp1 = K1 * 3 * calls
    exp2 = Ko * 2 * calls
    exp3 = Ko * 2 * calls
    exp4 = Ko * 3 * calls
    total = exp1 + exp2 + exp3 + exp4
    cost = (total * 800 / 1e6) * 3 + (total * 400 / 1e6) * 15
    
    print(f"{'='*60}")
    print(f"COST ESTIMATE (model: {model})")
    print(f"{'='*60}")
    print(f"EXP-1: {exp1:>5} calls (K={K1})")
    print(f"EXP-2: {exp2:>5} calls (K={Ko})")
    print(f"EXP-3: {exp3:>5} calls (K={Ko})")
    print(f"EXP-4: {exp4:>5} calls (K={Ko})")
    print(f"Total: {total:>5} calls  ~${cost:.2f}")
    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(description="SAPIENT Fast Parallel Runner")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--exp", type=int, choices=[1, 2, 3, 4])
    parser.add_argument("--K", type=int, default=None)
    parser.add_argument("--model", default="claude-sonnet-4-20250514")
    parser.add_argument("--estimate", action="store_true")
    args = parser.parse_args()
    
    K1 = args.K or 20
    Ko = args.K or 10
    
    if args.estimate:
        estimate_cost(K1, Ko, args.model)
        return
    
    if not args.all and args.exp is None:
        parser.print_help()
        return
    
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: SET ANTHROPIC_API_KEY=sk-ant-...")
        sys.exit(1)
    
    estimate_cost(K1, Ko, args.model)
    print("\nProceed? [y/N] ", end="")
    if input().strip().lower() != "y":
        return
    
    start = time.time()
    
    if args.all or args.exp == 1:
        run_exp1(api_key, K1, args.model)
    if args.all or args.exp == 2:
        run_exp2(api_key, Ko if not args.K else args.K, args.model)
    if args.all or args.exp == 3:
        run_exp3(api_key, Ko if not args.K else args.K, args.model)
    if args.all or args.exp == 4:
        run_exp4(api_key, Ko if not args.K else args.K, args.model)
    
    elapsed = time.time() - start
    print(f"\n{'='*60}")
    print(f"DONE — {elapsed/60:.1f} minutes")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
