# SAPIENT — Empirical Validation Codebase

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set API key
export ANTHROPIC_API_KEY="sk-ant-api03-..."

# 3. Cost estimate (run this first!)
python run_all.py --estimate

# 4. Quick test (K=2, fast)
python run_all.py --exp 1 --K 2

# 5. Full experiment
python run_all.py --exp 1 --K 10
python run_all.py --exp 2 --K 5
python run_all.py --exp 3 --K 5
python run_all.py --exp 4 --K 5

# 6. Run everything
python run_all.py --all
```

## Project Structure

```
sapient/
├── config/
│   ├── personas.json         # 8 persona specifications (θ_i tuples)
│   └── scenarios.json        # Scenario 1 + signal states + 3 stimulus variants
├── agents/
│   ├── persona_agent.py      # Persona → Claude API (system prompt builder)
│   └── moderator_agent.py    # AFG session orchestration (Algorithm 1)
├── metrics/
│   └── analysis.py           # All Table 1 metrics (stability, collapse, sentiment)
├── experiments/
│   ├── exp1_afg_protocol.py  # 3 variants × K runs
│   ├── exp2_signal_ab.py     # With vs without signal state
│   ├── exp3_multilingual.py  # English vs Turkish
│   └── exp4_temperature.py   # Variance collapse countermeasures
├── results/                  # Auto-generated JSON outputs
├── run_all.py                # Master runner
├── generate_tables.py        # Results → LaTeX tables for paper
└── EXPERIMENT_PLAN.md        # Mapping: experiments → paper sections
```

## Output → Paper

After experiments run, generate LaTeX tables:

```bash
python generate_tables.py 1 results/exp1_reports_*.json
python generate_tables.py 2 results/exp2_ab_test_*.json
python generate_tables.py 4 results/exp4_variance_*.json
```

These tables are designed to slot directly into the paper's Evaluation section.

## Model Selection

Default: `claude-sonnet-4-20250514` (best cost/quality balance).

Override with: `python run_all.py --all --model claude-sonnet-4-20250514`

## Cost Guide

| Run | Estimated Cost |
|-----|---------------|
| Quick test (K=2, 1 experiment) | ~$0.50 |
| Single experiment (K=5) | ~$2-3 |
| Full suite (all 4 experiments) | ~$13 |
