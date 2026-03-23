"""
Parallel (async) AFG runner — calls all personas concurrently within each run.
Replaces sequential calls with asyncio, ~8x speedup per run.

Usage: Import run_afg_experiment_parallel instead of run_afg_experiment.
"""

import asyncio
import json
import time
import numpy as np
from typing import Optional

from .persona_agent import build_persona_system_prompt
from .llm_client import achat


async def _async_persona_call(
    api_key: str,
    persona: dict,
    stimulus: str,
    probe: str,
    signal_state: Optional[dict],
    temperature: float,
    model: str,
    usage_tracker=None,
) -> dict:
    """Single async persona API call."""
    system_prompt = build_persona_system_prompt(persona, signal_state)

    user_message = f"""ANNOUNCEMENT TO EVALUATE:
{stimulus}

DISCUSSION QUESTION:
{probe}

Please respond with a JSON object containing:
{{
  "interpretation": "How you understand this announcement (2-3 sentences)",
  "sentiment": <integer 1-7, where 1=very negative, 4=neutral, 7=very positive>,
  "credibility": <integer 1-7, where 1=not at all credible, 7=very credible>,
  "concerns": ["list of specific concerns you have"],
  "positive_aspects": ["list of aspects you view positively, if any"],
  "missing_information": ["what information you would need to see"],
  "likely_action": "what you would likely do in response (share, investigate, ignore, criticize, support, etc.)",
  "key_themes": ["3-5 word theme labels that capture your main reaction points"]
}}

Respond ONLY with the JSON object, no other text."""

    response = await achat(
        system_prompt=system_prompt,
        user_message=user_message,
        model=model,
        temperature=temperature,
        max_tokens=800,
        api_key=api_key,
    )
    if usage_tracker:
        usage_tracker.record(response)

    raw_text = response.content.strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.strip()

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        parsed = {
            "interpretation": raw_text, "sentiment": None, "credibility": None,
            "concerns": [], "positive_aspects": [], "missing_information": [],
            "likely_action": "unknown", "key_themes": [], "_parse_error": True
        }

    parsed["persona_id"] = persona["id"]
    parsed["persona_label"] = persona["label"]
    parsed["_raw"] = raw_text
    parsed["_model"] = model
    parsed["_temperature"] = temperature
    return parsed


async def _async_followup_call(
    api_key: str,
    persona: dict,
    stimulus: str,
    initial_response: dict,
    followup_probe: str,
    signal_state: Optional[dict],
    temperature: float,
    model: str,
    usage_tracker=None,
) -> dict:
    """Single async followup call."""
    system_prompt = build_persona_system_prompt(persona, signal_state)

    messages = [
        {"role": "user", "content": f"ANNOUNCEMENT: {stimulus}\n\nWhat is your initial reaction?"},
        {"role": "assistant", "content": json.dumps({
            "interpretation": initial_response.get("interpretation", ""),
            "sentiment": initial_response.get("sentiment"),
            "key_concerns": initial_response.get("concerns", [])[:2]
        })},
        {"role": "user", "content": f"""FOLLOW-UP QUESTION: {followup_probe}

Respond with a JSON object:
{{
  "followup_response": "Your answer (3-5 sentences)",
  "sentiment_shift": <integer 1-7, same scale as before>,
  "new_themes": ["any new theme labels"]
}}

Respond ONLY with the JSON object."""}
    ]

    response = await achat(
        system_prompt=system_prompt,
        user_message="",
        model=model,
        temperature=temperature,
        max_tokens=500,
        api_key=api_key,
        messages=messages,
    )
    if usage_tracker:
        usage_tracker.record(response)

    raw_text = response.content.strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.strip()

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        parsed = {"followup_response": raw_text, "sentiment_shift": None, "new_themes": [], "_parse_error": True}

    parsed["persona_id"] = persona["id"]
    return parsed


async def _run_session_async(
    api_key: str,
    personas: list[dict],
    stimulus: str,
    probes: list[str],
    signal_state: Optional[dict],
    temperatures: list[float],
    model: str,
    session_id: str,
    usage_tracker=None,
) -> dict:
    """Run one AFG session with all personas in parallel."""

    session = {
        "session_id": session_id,
        "n_personas": len(personas),
        "model": model,
        "signal_state_provided": signal_state is not None,
        "temperatures": temperatures,
        "initial_responses": [],
        "followup_responses": [],
        "all_themes": [],
        "sentiment_scores": [],
        "credibility_scores": []
    }

    # Phase 1: All initial responses in parallel
    tasks = [
        _async_persona_call(
            api_key, persona, stimulus, probes[0], signal_state,
            temperatures[i] if i < len(temperatures) else 0.8, model,
            usage_tracker=usage_tracker,
        )
        for i, persona in enumerate(personas)
    ]
    initial_responses = await asyncio.gather(*tasks)
    session["initial_responses"] = list(initial_responses)

    for resp in initial_responses:
        if resp.get("sentiment") is not None:
            session["sentiment_scores"].append(resp["sentiment"])
        if resp.get("credibility") is not None:
            session["credibility_scores"].append(resp["credibility"])
        if resp.get("key_themes"):
            session["all_themes"].extend(resp["key_themes"])

    # Phase 2: All followups in parallel
    if len(probes) > 1:
        fu_tasks = [
            _async_followup_call(
                api_key, persona, stimulus, initial_responses[i], probes[1],
                signal_state, temperatures[i] if i < len(temperatures) else 0.8, model,
                usage_tracker=usage_tracker,
            )
            for i, persona in enumerate(personas)
        ]
        followup_responses = await asyncio.gather(*fu_tasks)
        session["followup_responses"] = list(followup_responses)

        for fu in followup_responses:
            if fu.get("new_themes"):
                session["all_themes"].extend(fu["new_themes"])

    # Normalize themes
    seen = set()
    normalized = []
    for t in session["all_themes"]:
        t_clean = t.lower().strip().rstrip(".")
        if t_clean and t_clean not in seen:
            seen.add(t_clean)
            normalized.append(t_clean)
    session["theme_list"] = normalized

    session["mean_sentiment"] = (
        sum(session["sentiment_scores"]) / len(session["sentiment_scores"])
        if session["sentiment_scores"] else None
    )
    session["mean_credibility"] = (
        sum(session["credibility_scores"]) / len(session["credibility_scores"])
        if session["credibility_scores"] else None
    )

    return session


async def _run_experiment_async(
    api_key: str,
    personas: list[dict],
    stimulus: str,
    probes: list[str],
    K: int,
    signal_state: Optional[dict],
    temperature_mode: str,
    model: str,
    experiment_label: str,
    max_concurrent_runs: int = 3,
    usage_tracker=None,
) -> dict:
    """
    Run K AFG sessions with concurrency at two levels:
    - Within each session: all 8 personas run in parallel
    - Across sessions: up to max_concurrent_runs sessions run simultaneously
    """
    n = len(personas)

    if temperature_mode == "stratified":
        temps = np.linspace(0.6, 1.0, n).tolist()
    elif temperature_mode == "uniform_low":
        temps = [0.7] * n
    elif temperature_mode == "uniform_high":
        temps = [1.0] * n
    else:
        temps = [0.8] * n

    semaphore = asyncio.Semaphore(max_concurrent_runs)

    async def _bounded_session(k):
        async with semaphore:
            print(f"  [{experiment_label}] Starting run {k+1}/{K}")
            result = await _run_session_async(
                api_key, personas, stimulus, probes, signal_state,
                temps, model, f"{experiment_label}_run_{k}",
                usage_tracker=usage_tracker,
            )
            print(f"  [{experiment_label}] Completed run {k+1}/{K}")
            return result

    sessions = await asyncio.gather(*[_bounded_session(k) for k in range(K)])

    return {
        "experiment_label": experiment_label,
        "K": K,
        "n_personas": n,
        "temperature_mode": temperature_mode,
        "model": model,
        "sessions": list(sessions)
    }


def run_afg_experiment_parallel(
    api_key: str,
    personas: list[dict],
    stimulus: str,
    probes: list[str],
    K: int = 10,
    signal_state: Optional[dict] = None,
    temperature_mode: str = "stratified",
    model: str = "claude-sonnet-4-20250514",
    experiment_label: str = "exp",
    max_concurrent_runs: int = 4,
    usage_tracker=None,
) -> dict:
    """
    Synchronous wrapper for the async experiment runner.
    Drop-in replacement for run_afg_experiment.
    """
    return asyncio.run(_run_experiment_async(
        api_key, personas, stimulus, probes, K,
        signal_state, temperature_mode, model,
        experiment_label, max_concurrent_runs,
        usage_tracker=usage_tracker,
    ))
