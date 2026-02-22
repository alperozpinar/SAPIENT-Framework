"""
Moderator Agent for SAPIENT AFG Protocol.
Controls session flow, collects responses, produces session debrief.
"""

import anthropic
import json
from typing import Optional
from .persona_agent import get_persona_response, get_persona_followup


def run_afg_session(
    client: anthropic.Anthropic,
    personas: list[dict],
    stimulus: str,
    probes: list[str],
    signal_state: Optional[dict] = None,
    temperatures: Optional[list[float]] = None,
    model: str = "claude-sonnet-4-20250514",
    session_id: str = "session_0"
) -> dict:
    """
    Execute one complete AFG session (one run k out of K).
    
    Algorithm 1 from paper:
    1. Build personas (already provided)
    2. Initialize (fresh session, no memory carryover)
    3. Stimulus presentation + initial response
    4. Follow-up probes
    5. Session debrief
    
    Returns structured session transcript.
    """
    n_personas = len(personas)
    
    # Temperature assignment
    if temperatures is None:
        # Default: stratified temperatures as per paper §3.3.1
        import numpy as np
        temperatures = np.linspace(0.6, 1.0, n_personas).tolist()
    elif isinstance(temperatures, (int, float)):
        temperatures = [float(temperatures)] * n_personas
    
    session = {
        "session_id": session_id,
        "n_personas": n_personas,
        "model": model,
        "signal_state_provided": signal_state is not None,
        "temperatures": temperatures,
        "initial_responses": [],
        "followup_responses": [],
        "all_themes": [],
        "sentiment_scores": [],
        "credibility_scores": []
    }
    
    # --- Phase 1: Initial stimulus response ---
    for i, persona in enumerate(personas):
        temp = temperatures[i] if i < len(temperatures) else 0.8
        
        resp = get_persona_response(
            client=client,
            persona=persona,
            stimulus=stimulus,
            probe=probes[0],  # First probe with stimulus
            signal_state=signal_state,
            temperature=temp,
            model=model
        )
        session["initial_responses"].append(resp)
        
        # Collect metrics
        if resp.get("sentiment") is not None:
            session["sentiment_scores"].append(resp["sentiment"])
        if resp.get("credibility") is not None:
            session["credibility_scores"].append(resp["credibility"])
        if resp.get("key_themes"):
            session["all_themes"].extend(resp["key_themes"])
    
    # --- Phase 2: Follow-up probe ---
    if len(probes) > 1:
        followup_probe = probes[1]
        for i, persona in enumerate(personas):
            temp = temperatures[i] if i < len(temperatures) else 0.8
            initial = session["initial_responses"][i]
            
            fu = get_persona_followup(
                client=client,
                persona=persona,
                stimulus=stimulus,
                initial_response=initial,
                followup_probe=followup_probe,
                signal_state=signal_state,
                temperature=temp,
                model=model
            )
            session["followup_responses"].append(fu)
            
            if fu.get("new_themes"):
                session["all_themes"].extend(fu["new_themes"])
    
    # --- Phase 3: Compute session-level summaries ---
    session["theme_list"] = _normalize_themes(session["all_themes"])
    session["mean_sentiment"] = (
        sum(session["sentiment_scores"]) / len(session["sentiment_scores"])
        if session["sentiment_scores"] else None
    )
    session["mean_credibility"] = (
        sum(session["credibility_scores"]) / len(session["credibility_scores"])
        if session["credibility_scores"] else None
    )
    
    return session


def _normalize_themes(theme_list: list[str]) -> list[str]:
    """Basic theme normalization: lowercase, strip, deduplicate."""
    seen = set()
    normalized = []
    for t in theme_list:
        t_clean = t.lower().strip().rstrip(".")
        if t_clean and t_clean not in seen:
            seen.add(t_clean)
            normalized.append(t_clean)
    return normalized


def run_afg_experiment(
    client: anthropic.Anthropic,
    personas: list[dict],
    stimulus: str,
    probes: list[str],
    K: int = 10,
    signal_state: Optional[dict] = None,
    temperature_mode: str = "stratified",
    model: str = "claude-sonnet-4-20250514",
    experiment_label: str = "exp"
) -> dict:
    """
    Run K independent AFG sessions (full AFG protocol).
    
    temperature_mode: 
      "stratified" -> τ ∈ [0.6, 1.1] spread across personas
      "uniform_low" -> all τ = 0.7
      "uniform_high" -> all τ = 1.0
    """
    import numpy as np
    from tqdm import tqdm
    
    n = len(personas)
    
    if temperature_mode == "stratified":
        temps = np.linspace(0.6, 1.0, n).tolist()
    elif temperature_mode == "uniform_low":
        temps = [0.7] * n
    elif temperature_mode == "uniform_high":
        temps = [1.0] * n
    else:
        temps = [0.8] * n
    
    sessions = []
    
    for k in tqdm(range(K), desc=f"AFG runs ({experiment_label})"):
        session = run_afg_session(
            client=client,
            personas=personas,
            stimulus=stimulus,
            probes=probes,
            signal_state=signal_state,
            temperatures=temps,
            model=model,
            session_id=f"{experiment_label}_run_{k}"
        )
        sessions.append(session)
    
    return {
        "experiment_label": experiment_label,
        "K": K,
        "n_personas": n,
        "temperature_mode": temperature_mode,
        "model": model,
        "sessions": sessions
    }
