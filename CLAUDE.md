# SAPIENT Project

## Project Overview
SAPIENT (Simulated Audience Protocol for Integrated Evaluation of Narrative Trajectories) — TUBITAK academic paper revision codebase. Multi-model LLM-based focus group simulation for corporate sustainability communication analysis.

## Tech Stack
- Python 3.13
- Anthropic SDK (Claude Sonnet 4) + OpenAI SDK (GPT-4o)
- Async parallel API calls (asyncio)
- NumPy, Pandas, SciPy, scikit-learn, sentence-transformers

## Architecture
- `agents/llm_client.py` — Unified sync+async LLM client (Anthropic + OpenAI)
- `agents/persona_agent.py` — Persona system prompt builder + API calls
- `agents/moderator_agent.py` — AFG session orchestrator (sync path)
- `agents/parallel_runner.py` — Async parallel runner (~8x faster)
- `agents/usage_tracker.py` — Token/cost tracking
- `config/env_loader.py` — .env file loader for API keys
- `experiments/exp1-8` — 8 experiment implementations
- `run_fast.py` — Main CLI runner (parallel, multi-model)
- `generate_tables.py` — JSON results → LaTeX tables

## Key Commands
```bash
# Cost estimate
python run_fast.py --estimate

# Run single experiment
python run_fast.py --exp 1 --K 2

# Run with GPT-4o
python run_fast.py --exp 1 --K 2 --model gpt-4o

# Run revision experiments only
python run_fast.py --revision --K 5

# Generate LaTeX tables
python generate_tables.py <exp_num> results/<file>.json
```

## Conventions
- API keys are in `.env` (never commit)
- All LLM calls go through `agents/llm_client.py` — never import anthropic/openai directly
- Results saved as timestamped JSON in `results/`
- Prompt templates are duplicated in `persona_agent.py` and `parallel_runner.py` — changes must be made in BOTH
- Turkish comments/docs are OK — this is a TUBITAK project
- Language: code in English, user interaction in Turkish

## Experiments
| Exp | Description | Scenario |
|-----|-------------|----------|
| 1 | AFG Protocol PoC (3 variants) | Greenwashing |
| 2 | Signal State A/B | Greenwashing |
| 3 | Multilingual EN vs TR | Greenwashing |
| 4 | Variance Collapse Countermeasures | Greenwashing |
| 5 | Greenhushing Disclosure | ESG Finance |
| 6 | Crisis Communication | Supply Chain |
| 7 | Cross-Model (Claude vs GPT-4o) | Greenwashing |
| 8 | Prompt Sensitivity | Greenwashing |
