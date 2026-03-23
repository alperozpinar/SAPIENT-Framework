#!/usr/bin/env python3
"""
SAPIENT Empirical Validation — Master Runner

Usage:
  # Run all experiments with default settings (K=10 for exp1, K=5 for others)
  export ANTHROPIC_API_KEY="sk-ant-..."
  python run_all.py --all

  # Run specific experiment
  python run_all.py --exp 1 --K 3        # Quick test with K=3
  python run_all.py --exp 2 --K 5
  python run_all.py --exp 1 --K 10       # Full run

  # Estimate cost only
  python run_all.py --estimate

  # Use a different model
  python run_all.py --all --model claude-sonnet-4-20250514
"""

import os
import sys
import argparse
import json
import time


def estimate_cost(K_exp1: int = 10, K_other: int = 5, model: str = "claude-sonnet-4-20250514"):
    """Estimate API costs before running."""
    n_personas = 8
    calls_per_run = n_personas * 2  # initial + followup
    
    exp1_calls = K_exp1 * 3 * calls_per_run  # 3 variants
    exp2_calls = K_other * 2 * calls_per_run  # 2 conditions
    exp3_calls = K_other * 2 * calls_per_run  # 2 languages
    exp4_calls = K_other * 3 * calls_per_run  # 3 conditions
    total = exp1_calls + exp2_calls + exp3_calls + exp4_calls
    
    # Sonnet pricing: ~$3/M input, $15/M output
    avg_input = 800   # tokens per call
    avg_output = 400   # tokens per call
    input_cost = (total * avg_input / 1_000_000) * 3
    output_cost = (total * avg_output / 1_000_000) * 15
    total_cost = input_cost + output_cost
    
    print("=" * 60)
    print("COST ESTIMATION")
    print("=" * 60)
    print(f"Model: {model}")
    print(f"\nEXP-1 (AFG Protocol):     {exp1_calls:>5} calls  (K={K_exp1}, 3 variants)")
    print(f"EXP-2 (Signal A/B):       {exp2_calls:>5} calls  (K={K_other}, 2 conditions)")
    print(f"EXP-3 (Multilingual):     {exp3_calls:>5} calls  (K={K_other}, 2 languages)")
    print(f"EXP-4 (Temperature):      {exp4_calls:>5} calls  (K={K_other}, 3 conditions)")
    print(f"{'':->50}")
    print(f"Total API calls:          {total:>5}")
    print(f"\nEstimated cost:  ${total_cost:.2f}  (input: ${input_cost:.2f}, output: ${output_cost:.2f})")
    print(f"\nNote: Actual cost depends on response lengths. This is an estimate.")
    print("=" * 60)
    
    return total_cost


def main():
    parser = argparse.ArgumentParser(description="SAPIENT Empirical Validation Runner")
    parser.add_argument("--all", action="store_true", help="Run all 4 experiments")
    parser.add_argument("--exp", type=int, choices=[1, 2, 3, 4], help="Run specific experiment")
    parser.add_argument("--K", type=int, default=None, help="Number of AFG runs (overrides defaults)")
    parser.add_argument("--model", type=str, default="claude-sonnet-4-20250514", help="Claude model to use")
    parser.add_argument("--estimate", action="store_true", help="Print cost estimate and exit")
    args = parser.parse_args()
    
    if args.estimate:
        K1 = args.K or 10
        Ko = args.K or 5
        estimate_cost(K1, Ko, args.model)
        return
    
    if not args.all and args.exp is None:
        parser.print_help()
        print("\nExamples:")
        print("  python run_all.py --estimate")
        print("  python run_all.py --exp 1 --K 3")
        print("  python run_all.py --all")
        return
    
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from config.env_loader import get_api_key
    from agents.llm_client import PROVIDER_MAP
    provider = PROVIDER_MAP.get(args.model, "anthropic")
    try:
        api_key = get_api_key(provider)
    except EnvironmentError as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    
    # Print cost estimate first
    K_exp1 = args.K or 10
    K_other = args.K or 5
    estimate_cost(K_exp1, K_other, args.model)
    
    print("\nProceed? [y/N] ", end="")
    if input().strip().lower() != "y":
        print("Aborted.")
        return
    
    start_time = time.time()
    
    # Add experiments dir to path
    exp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "experiments")
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    if args.all or args.exp == 1:
        print("\n" + "#" * 70)
        print("# EXPERIMENT 1: AFG Protocol Proof-of-Concept")
        print("#" * 70)
        from experiments.exp1_afg_protocol import run_exp1
        run_exp1(api_key, K=K_exp1, model=args.model)
    
    if args.all or args.exp == 2:
        print("\n" + "#" * 70)
        print("# EXPERIMENT 2: Signal State A/B Test")
        print("#" * 70)
        from experiments.exp2_signal_ab import run_exp2
        run_exp2(api_key, K=K_other, model=args.model)
    
    if args.all or args.exp == 3:
        print("\n" + "#" * 70)
        print("# EXPERIMENT 3: Multilingual Stress Test")
        print("#" * 70)
        from experiments.exp3_multilingual import run_exp3
        run_exp3(api_key, K=K_other, model=args.model)
    
    if args.all or args.exp == 4:
        print("\n" + "#" * 70)
        print("# EXPERIMENT 4: Variance Collapse Countermeasures")
        print("#" * 70)
        from experiments.exp4_temperature import run_exp4
        run_exp4(api_key, K=K_other, model=args.model)
    
    elapsed = time.time() - start_time
    print(f"\n{'='*70}")
    print(f"ALL EXPERIMENTS COMPLETE - Total time: {elapsed/60:.1f} minutes")
    print(f"Results saved in: sapient/results/")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
