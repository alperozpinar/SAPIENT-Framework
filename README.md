# SAPIENT — Empirical Validation Codebase

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set API keys (see SETUP_API_KEYS.md for details)
cp .env.example .env
# Edit .env with your keys

# 3. Cost estimate (run this first!)
python run_fast.py --estimate

# 4. Quick test (K=2, fast)
python run_fast.py --exp 1 --K 2

# 5. Full original experiments
python run_fast.py --all --K 10

# 6. Revision experiments only
python run_fast.py --revision --K 5

# 7. GPT-4o backend
python run_fast.py --exp 1 --K 2 --model gpt-4o

# 8. Cross-model comparison (requires both API keys)
python run_fast.py --exp 7 --K 20
```

## Project Structure

```
sapient/
├── config/
│   ├── personas.json              # 8 persona specifications (Scenario 1)
│   ├── personas_scenario2.json    # 8 finance personas (Scenario 2)
│   ├── scenarios.json             # 3 scenarios + signal states + variants
│   ├── models.json                # Supported models & pricing
│   └── env_loader.py              # .env file loader
├── agents/
│   ├── llm_client.py              # Unified LLM client (Anthropic + OpenAI)
│   ├── usage_tracker.py           # Token/cost tracking
│   ├── persona_agent.py           # Persona → LLM API (system prompt builder)
│   ├── moderator_agent.py         # AFG session orchestration (sync)
│   └── parallel_runner.py         # Async parallel runner (~8x faster)
├── metrics/
│   └── analysis.py                # All metrics (stability, collapse, sentiment)
├── experiments/
│   ├── exp1_afg_protocol.py       # 3 variants × K runs
│   ├── exp2_signal_ab.py          # With vs without signal state
│   ├── exp3_multilingual.py       # English vs Turkish
│   ├── exp4_temperature.py        # Variance collapse countermeasures
│   ├── exp5_greenhushing.py       # Greenhushing disclosure dilemma
│   ├── exp6_crisis.py             # Crisis communication strategies
│   ├── exp7_cross_model.py        # Claude vs GPT-4o comparison
│   └── exp8_prompt_sensitivity.py # Original vs paraphrase robustness
├── results/                       # Auto-generated JSON outputs
├── run_fast.py                    # Main runner (parallel, multi-model)
├── run_all.py                     # Legacy sequential runner
├── generate_tables.py             # Results → LaTeX tables for paper
├── .env.example                   # API key template
├── SETUP_API_KEYS.md              # Setup guide
└── EXPERIMENT_PLAN.md             # Mapping: experiments → paper sections
```

## Supported Models

| Model | `--model` Flag | Provider |
|-------|---------------|----------|
| Claude Sonnet 4 | `claude-sonnet-4-20250514` (default) | Anthropic |
| GPT-4o | `gpt-4o` | OpenAI |
| GPT-4o (pinned) | `gpt-4o-2024-11-20` | OpenAI |
| GPT-4o Mini | `gpt-4o-mini` | OpenAI |

## Output → Paper

After experiments run, generate LaTeX tables:

```bash
python generate_tables.py 1 results/exp1_reports_*.json
python generate_tables.py 2 results/exp2_ab_test_*.json
python generate_tables.py 4 results/exp4_variance_*.json
python generate_tables.py 5 results/exp5_greenhushing_*.json
python generate_tables.py 6 results/exp6_crisis_*.json
python generate_tables.py 7 results/exp7_cross_model_*.json
python generate_tables.py 8 results/exp8_prompt_sensitivity_*.json
python generate_tables.py runtime results/runtime_usage_*.json
```

## Cost Guide

| Run | Estimated Cost |
|-----|---------------|
| Quick test (K=2, 1 experiment) | ~$0.50 |
| Single experiment (K=5) | ~$2-3 |
| Original suite (Exp 1-4) | ~$13 |
| Revision suite (Exp 5-8) | ~$10-15 |
| Full suite (all 8 experiments) | ~$25-30 |
