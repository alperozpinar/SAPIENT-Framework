# SAPIENT Empirical Validation — Experiment Plan

## Overview

This codebase implements a subset of the 5-stage evaluation plan described in the paper.
The goal: transform SAPIENT from "architecture-only" to "architecture + proof-of-concept evidence."

## Mapping to Paper Evaluation Stages

| Experiment | Paper Stage | What It Tests | Paper Section |
|---|---|---|---|
| EXP-1 | Stage 2 (partial) | AFG protocol: theme stability, variance collapse, sentiment | §5, Table 1 |
| EXP-2 | Stage 3 | Signal conditioning A/B: does S_t improve simulation? | §5.1, Stage 3 |
| EXP-3 | Stage 4a | Multilingual: EN vs TR consistency | §5.1, Stage 4 |
| EXP-4 | — | Variance collapse countermeasures: temperature effect | §3.3.1, §3.3.6 |

## Experiment Details

### EXP-1: AFG Protocol Proof-of-Concept (Greenwashing Scenario)
- **Scenario**: Scenario 1 from paper (net-zero announcement)
- **3 framing variants**: (A) targets-focused, (B) past-progress, (C) accountability
- **8 personas**: activist, ESG investor, retail consumer, journalist, regulator, employee, competitor analyst, academic
- **K = 10 runs** per variant (30 total AFG sessions)
- **Mode**: Independent (each persona responds without seeing others)
- **Metrics**:
  - Theme frequency stability (CV per theme across K runs)
  - Sentiment distribution per variant (mean, std, skewness)
  - Variance collapse score (mean pairwise cosine similarity)
  - Persona stance consistency (same persona across runs)

### EXP-2: Signal State Conditioning A/B Test
- **Same scenario, 2 conditions**:
  - Condition A: Full signal state (rich context about the company, recent controversies, competitor actions)
  - Condition B: Generic topic only ("company announces net-zero target")
- **8 personas, K = 5 per condition** (10 sessions)
- **Metrics**:
  - Theme coverage (breadth of themes identified)
  - Hallucinated theme rate (themes with no basis in stimulus or signal state)
  - Response specificity (concreteness of claims and concerns)

### EXP-3: Multilingual Stress Test
- **Same scenario in English and Turkish**
- **8 personas (matched demographics), K = 5 per language** (10 sessions)
- **Metrics**:
  - Cross-lingual theme overlap (Jaccard index on translated themes)
  - Sentiment distribution comparison
  - Response diversity per language (cosine similarity)

### EXP-4: Variance Collapse Countermeasures
- **3 conditions**:
  - (A) Uniform temperature τ = 0.7, no adversarial persona
  - (B) Stratified temperature τ ∈ [0.6, 1.1], no adversarial persona
  - (C) Stratified temperature + adversarial persona injection
- **8 personas, K = 5 per condition** (15 sessions)
- **Metric**: Mean pairwise cosine similarity (lower = more diverse = better)

## Estimated API Cost

| Experiment | API Calls | Est. Tokens | Est. Cost (Sonnet) |
|---|---|---|---|
| EXP-1 | ~720 | ~1.4M | ~$6 |
| EXP-2 | ~240 | ~480K | ~$2 |
| EXP-3 | ~240 | ~480K | ~$2 |
| EXP-4 | ~360 | ~720K | ~$3 |
| **Total** | **~1560** | **~3M** | **~$13** |

## Output for Paper

Each experiment produces:
1. Raw JSON transcripts (for reproducibility)
2. Summary statistics table (LaTeX-ready)
3. Metric scores with confidence intervals
