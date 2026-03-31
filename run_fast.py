#!/usr/bin/env python3
"""
SAPIENT Fast Runner — Parallel API calls, ~5-8x faster.

Usage:
  python run_fast.py --all
  python run_fast.py --exp 1 --K 20
  python run_fast.py --exp 5 --model gpt-4o --K 10
  python run_fast.py --revision --K 5
  python run_fast.py --estimate
"""

import os
import sys
import json
import time
import argparse
import copy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.env_loader import get_api_key
from agents.llm_client import PROVIDER_MAP
from agents.parallel_runner import run_afg_experiment_parallel
from agents.usage_tracker import UsageTracker
from metrics.analysis import (
    generate_full_report, print_summary,
    compute_theme_coverage_comparison
)


def load_config():
    base = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(base, "config", "personas.json")) as f:
        personas = json.load(f)["personas"]
    with open(os.path.join(base, "config", "scenarios.json")) as f:
        scenarios = json.load(f)
    return personas, scenarios


def save_results(data: dict, name: str):
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
    os.makedirs(output_dir, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    path = os.path.join(output_dir, f"{name}_{ts}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str, ensure_ascii=False)
    print(f"Saved: {path}")
    return path


def run_exp1(api_key, K, model, tracker=None):
    """EXP-1: AFG Protocol — 3 variants."""
    personas, scenarios = load_config()
    scenario = scenarios["scenario_1_greenwashing"]
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
        print(f"EXP-1 Variant {vname} - K={K} (parallel)")
        print(f"{'='*60}")

        result = run_afg_experiment_parallel(
            api_key, personas, stimulus, probes, K=K,
            signal_state=signal_state, temperature_mode="stratified",
            model=model, experiment_label=f"exp1_{vname}",
            usage_tracker=tracker,
        )
        results[vname] = result
        report = generate_full_report(result)
        reports[vname] = report
        print_summary(report)

    save_results(results, "exp1_raw")
    save_results(reports, "exp1_reports")
    return results, reports


def run_exp2(api_key, K, model, tracker=None):
    """EXP-2: Signal State A/B."""
    personas, scenarios = load_config()
    scenario = scenarios["scenario_1_greenwashing"]
    stimulus = scenario["stimuli"]["variant_C_accountability"]
    probes = scenario["moderator_probes"][:2]

    print(f"\n{'='*60}")
    print(f"EXP-2 Condition A: Full Signal State - K={K}")
    print(f"{'='*60}")
    result_a = run_afg_experiment_parallel(
        api_key, personas, stimulus, probes, K=K,
        signal_state=scenario["signal_state_rich"],
        temperature_mode="stratified", model=model,
        experiment_label="exp2_condA_signal",
        usage_tracker=tracker,
    )
    report_a = generate_full_report(result_a)
    print_summary(report_a)

    print(f"\n{'='*60}")
    print(f"EXP-2 Condition B: Generic Only - K={K}")
    print(f"{'='*60}")
    result_b = run_afg_experiment_parallel(
        api_key, personas, stimulus, probes, K=K,
        signal_state=None,
        temperature_mode="stratified", model=model,
        experiment_label="exp2_condB_generic",
        usage_tracker=tracker,
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


def run_exp3(api_key, K, model, tracker=None):
    """EXP-3: Multilingual EN vs TR."""
    from experiments.exp3_multilingual import TURKISH_PERSONAS, TURKISH_STIMULUS, TURKISH_PROBES

    personas, scenarios = load_config()
    scenario = scenarios["scenario_1_greenwashing"]
    stimulus = scenario["stimuli"]["variant_C_accountability"]
    probes = scenario["moderator_probes"][:2]
    signal_state = scenario["signal_state_rich"]

    print(f"\n{'='*60}")
    print(f"EXP-3 English - K={K}")
    print(f"{'='*60}")
    result_en = run_afg_experiment_parallel(
        api_key, personas, stimulus, probes, K=K,
        signal_state=signal_state, temperature_mode="stratified",
        model=model, experiment_label="exp3_EN",
        usage_tracker=tracker,
    )
    report_en = generate_full_report(result_en)
    print_summary(report_en)

    print(f"\n{'='*60}")
    print(f"EXP-3 Turkish - K={K}")
    print(f"{'='*60}")
    result_tr = run_afg_experiment_parallel(
        api_key, TURKISH_PERSONAS, TURKISH_STIMULUS, TURKISH_PROBES, K=K,
        signal_state=signal_state, temperature_mode="stratified",
        model=model, experiment_label="exp3_TR",
        usage_tracker=tracker,
    )
    report_tr = generate_full_report(result_tr)
    print_summary(report_tr)

    output = {
        "english": {"result": result_en, "report": report_en},
        "turkish": {"result": result_tr, "report": report_tr},
    }
    save_results(output, "exp3_multilingual")
    return output


def run_exp4(api_key, K, model, tracker=None):
    """EXP-4: Variance collapse countermeasures."""
    personas, scenarios = load_config()
    scenario = scenarios["scenario_1_greenwashing"]
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
        print(f"EXP-4 Condition {cname} - K={K}")
        print(f"{'='*60}")
        result = run_afg_experiment_parallel(
            api_key, cfg["personas"], stimulus, probes, K=K,
            signal_state=signal_state, temperature_mode=cfg["temp"],
            model=model, experiment_label=f"exp4_{cname}",
            usage_tracker=tracker,
        )
        results[cname] = result
        report = generate_full_report(result)
        reports[cname] = report
        print_summary(report)

    save_results({"conditions": results, "reports": reports}, "exp4_variance")
    return results, reports


def run_exp5(api_key, K, model, tracker=None):
    """EXP-5: Greenhushing scenario."""
    from experiments.exp5_greenhushing import run_exp5 as _run
    return _run(api_key, K=K, model=model, tracker=tracker)


def run_exp6(api_key, K, model, tracker=None):
    """EXP-6: Crisis communication."""
    from experiments.exp6_crisis import run_exp6 as _run
    return _run(api_key, K=K, model=model, tracker=tracker)


def run_exp7(key_claude, key_openai, K, key_gemini=None, tracker=None):
    """EXP-7: Cross-model comparison."""
    from experiments.exp7_cross_model import run_exp7 as _run
    return _run(key_claude, key_openai, K=K, key_gemini=key_gemini, tracker=tracker)


def run_exp8(api_key, K, model, tracker=None):
    """EXP-8: Prompt sensitivity."""
    from experiments.exp8_prompt_sensitivity import run_exp8 as _run
    return _run(api_key, K=K, model=model, tracker=tracker)


def estimate_cost(K1, Ko, model):
    from agents.llm_client import PRICING
    n = 8
    calls = n * 2  # initial + followup

    exp1 = K1 * 3 * calls
    exp2 = Ko * 2 * calls
    exp3 = Ko * 2 * calls
    exp4 = Ko * 3 * calls
    exp5 = Ko * 2 * calls
    exp6 = Ko * 3 * calls
    exp7 = Ko * 2 * calls  # two models but same call count per model
    exp8 = Ko * 2 * calls
    total = exp1 + exp2 + exp3 + exp4 + exp5 + exp6 + exp7 + exp8

    pricing = PRICING.get(model, (3.00, 15.00))
    cost = (total * 800 / 1e6) * pricing[0] + (total * 400 / 1e6) * pricing[1]

    print(f"{'='*60}")
    print(f"COST ESTIMATE (model: {model})")
    print(f"{'='*60}")
    print(f"EXP-1: {exp1:>5} calls (K={K1})")
    print(f"EXP-2: {exp2:>5} calls (K={Ko})")
    print(f"EXP-3: {exp3:>5} calls (K={Ko})")
    print(f"EXP-4: {exp4:>5} calls (K={Ko})")
    print(f"EXP-5: {exp5:>5} calls (K={Ko})")
    print(f"EXP-6: {exp6:>5} calls (K={Ko})")
    print(f"EXP-7: {exp7:>5} calls (K={Ko})")
    print(f"EXP-8: {exp8:>5} calls (K={Ko})")
    print(f"Total: {total:>5} calls  ~${cost:.2f}")
    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(description="SAPIENT Fast Parallel Runner")
    parser.add_argument("--all", action="store_true", help="Tüm orijinal deneyleri çalıştır (1-4)")
    parser.add_argument("--exp", type=int, choices=[1, 2, 3, 4, 5, 6, 7, 8])
    parser.add_argument("--K", type=int, default=None)
    parser.add_argument("--model", default="claude-sonnet-4-20250514",
                        help="Model: claude-sonnet-4-20250514, gpt-4o, gemini-2.5-flash")
    parser.add_argument("--estimate", action="store_true")
    parser.add_argument("--revision", action="store_true", help="Sadece revision deneylerini çalıştır (5-8)")
    args = parser.parse_args()

    K1 = args.K or 20
    Ko = args.K or 10

    if args.estimate:
        estimate_cost(K1, Ko, args.model)
        return

    if not args.all and not args.revision and args.exp is None:
        parser.print_help()
        return

    # API key yükleme — provider'a göre
    provider = PROVIDER_MAP.get(args.model, "anthropic")
    try:
        api_key = get_api_key(provider)
    except EnvironmentError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    estimate_cost(K1, Ko, args.model)
    print("\nProceed? [y/N] ", end="")
    if input().strip().lower() != "y":
        return

    start = time.time()
    tracker = UsageTracker()

    if args.all or args.exp == 1:
        run_exp1(api_key, K1, args.model, tracker)
    if args.all or args.exp == 2:
        run_exp2(api_key, Ko if not args.K else args.K, args.model, tracker)
    if args.all or args.exp == 3:
        run_exp3(api_key, Ko if not args.K else args.K, args.model, tracker)
    if args.all or args.exp == 4:
        run_exp4(api_key, Ko if not args.K else args.K, args.model, tracker)

    if args.revision or args.exp == 5:
        run_exp5(api_key, Ko if not args.K else args.K, args.model, tracker)
    if args.revision or args.exp == 6:
        run_exp6(api_key, Ko if not args.K else args.K, args.model, tracker)
    if args.revision or args.exp == 7:
        try:
            key_claude = get_api_key("anthropic")
            key_openai = get_api_key("openai")
            try:
                key_gemini = get_api_key("google")
            except EnvironmentError:
                key_gemini = None
                print("GEMINI_API_KEY bulunamadı — Gemini kolu atlanacak.")
            run_exp7(key_claude, key_openai, K=args.K or 20, key_gemini=key_gemini, tracker=tracker)
        except EnvironmentError as e:
            print(f"EXP-7 atlaniyor (her iki key gerekli): {e}")
    if args.revision or args.exp == 8:
        run_exp8(api_key, K=args.K or 5, model=args.model, tracker=tracker)

    elapsed = time.time() - start

    # Usage summary
    usage = tracker.summary()
    if usage:
        print(f"\n{'='*60}")
        print("API USAGE SUMMARY")
        print(f"{'='*60}")
        print(f"  Total calls:    {usage['total_calls']}")
        print(f"  Input tokens:   {usage['total_input_tokens']:,}")
        print(f"  Output tokens:  {usage['total_output_tokens']:,}")
        print(f"  Total cost:     ${usage['total_cost_usd']:.4f}")
        print(f"  Mean latency:   {usage['mean_latency_ms']:.0f} ms")

    print(f"\n{'='*60}")
    print(f"DONE - {elapsed/60:.1f} minutes")
    print(f"{'='*60}")

    # Save usage data
    if usage:
        save_results({"usage": usage, "elapsed_minutes": round(elapsed/60, 1)}, "runtime_usage")


if __name__ == "__main__":
    main()
