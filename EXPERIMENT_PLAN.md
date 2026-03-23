# SAPIENT Empirical Validation — Experiment Plan

## Overview

This codebase implements the evaluation plan described in the paper, including
both original experiments (Exp 1-4) and revision experiments (Exp 5-8) for
multi-model validation and additional scenarios.

## Mapping to Paper Evaluation Stages

| Experiment | Paper Stage | What It Tests | Paper Section |
|---|---|---|---|
| EXP-1 | Stage 2 (partial) | AFG protocol: theme stability, variance collapse, sentiment | §5, Table 1 |
| EXP-2 | Stage 3 | Signal conditioning A/B: does S_t improve simulation? | §5.1, Stage 3 |
| EXP-3 | Stage 4a | Multilingual: EN vs TR consistency | §5.1, Stage 4 |
| EXP-4 | — | Variance collapse countermeasures: temperature effect | §3.3.1, §3.3.6 |
| EXP-5 | Revision | New scenario: Greenhushing (ESG disclosure dilemma) | R2-4 |
| EXP-6 | Revision | New scenario: Crisis communication (supply chain scandal) | R2-4 |
| EXP-7 | Revision | Cross-model: Claude Sonnet 4 vs GPT-4o | R2-4, R2-7 |
| EXP-8 | Revision | Prompt sensitivity: original vs paraphrase | R2-3 |

## Original Experiments (Exp 1-4)

### EXP-1: AFG Protocol Proof-of-Concept (Greenwashing Scenario)
- **Scenario**: Scenario 1 from paper (net-zero announcement)
- **3 framing variants**: (A) targets-focused, (B) past-progress, (C) accountability
- **8 personas**: activist, ESG investor, retail consumer, journalist, regulator, employee, competitor analyst, academic
- **K = 10 runs** per variant (30 total AFG sessions)
- **Mode**: Independent (each persona responds without seeing others)

### EXP-2: Signal State Conditioning A/B Test
- **Same scenario, 2 conditions**: Full signal state vs generic topic only
- **8 personas, K = 5 per condition** (10 sessions)

### EXP-3: Multilingual Stress Test
- **Same scenario in English and Turkish**
- **8 personas (matched demographics), K = 5 per language** (10 sessions)

### EXP-4: Variance Collapse Countermeasures
- **3 conditions**: Uniform temp, Stratified temp, Stratified + adversarial persona
- **8 personas, K = 5 per condition** (15 sessions)

## Revision Experiments (Exp 5-8)

### EXP-5: Greenhushing — ESG Disclosure Dilemma (Scenario 2)
- **New scenario**: MeridianFinance ESG disclosure vs strategic silence
- **2 variants**: (A) full disclosure, (B) silence while competitor discloses
- **8 finance-focused personas** (new persona set)
- **K = 10, dual-model** (run with Claude and GPT-4o separately)

### EXP-6: Crisis Communication (Scenario 4)
- **New scenario**: EcoHarvest supply chain scandal response
- **3 variants**: (A) immediate apology, (B) factual rebuttal, (C) 72h delay
- **8 personas** (Scenario 1 set for consistency)
- **K = 5, dual-model**

### EXP-7: Cross-Model Comparison
- **Scenario 1, Variant C** run on both Claude Sonnet 4 and GPT-4o
- **K = 20 per model** (40 total sessions)
- **Metrics**: Sentiment t-test, theme Jaccard, persona Pearson correlation, cosine similarity

### EXP-8: Prompt Sensitivity
- **Scenario 1, Variant C** — original vs semantically equivalent paraphrase
- **Single model (Claude), K = 5 per variant**
- **Metrics**: t-test on sentiment/credibility, theme Jaccard overlap

## Estimated API Cost

| Experiment | API Calls | Est. Cost (Sonnet) | Est. Cost (GPT-4o) |
|---|---|---|---|
| EXP-1 | ~720 | ~$6 | ~$4 |
| EXP-2 | ~240 | ~$2 | ~$1.5 |
| EXP-3 | ~240 | ~$2 | ~$1.5 |
| EXP-4 | ~360 | ~$3 | ~$2 |
| EXP-5 | ~240 | ~$2 | ~$1.5 |
| EXP-6 | ~360 | ~$3 | ~$2 |
| EXP-7 | ~480 | ~$4 (split) | ~$3 (split) |
| EXP-8 | ~240 | ~$2 | ~$1.5 |
| **Total** | **~2880** | **~$24** | **~$17** |

## Output for Paper

Each experiment produces:
1. Raw JSON transcripts (for reproducibility)
2. Summary statistics table (LaTeX-ready via `generate_tables.py`)
3. API usage/cost summary (via `UsageTracker`)
