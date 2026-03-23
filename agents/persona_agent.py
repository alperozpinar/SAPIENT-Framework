"""
Persona Agent for SAPIENT AFG Protocol.
Maps persona specification θ_i = ⟨d_i, p_i, r_i, b_i, ℓ_i⟩ to LLM API calls.
"""

import json
from typing import Optional

from .llm_client import chat


def build_persona_system_prompt(persona: dict, signal_state: Optional[dict] = None) -> str:
    """
    Construct a system prompt that conditions the LLM to behave as persona θ_i.

    The prompt encodes demographics, psychographics, role, and behavioral priors
    without revealing the simulation context to the model.
    """
    d = persona["demographics"]
    p = persona["psychographics"]
    r = persona["role"]
    b = persona["behavioral_priors"]

    prompt = f"""You are participating in a discussion about a corporate sustainability announcement.
Respond authentically from the perspective described below. Do not break character.

YOUR BACKGROUND:
- Age: {d['age_bracket']}, Gender: {d['gender']}, Education: {d['education']}
- Income range: {d['income_range']}, Region: {d['region']}
- Professional role: {r} ({persona['label']})

YOUR ATTITUDES AND VALUES:
- Environmental concern level: {p['environmental_concern']}
- Brand loyalty tendency: {p['brand_loyalty']}
- Primary information sources: {p['media_consumption']}
- Trust in institutions: {p['institutional_trust']}

YOUR COMMUNICATION STYLE:
- Engagement approach: {b['engagement_style']}
- You are particularly attentive to: {b['frame_susceptibility']}
- Information-seeking tendency: {b['info_seeking']}

RESPONSE RULES:
1. Respond as this person would—with their biases, concerns, knowledge gaps, and priorities.
2. Do not be uniformly positive or negative. Real people have mixed reactions.
3. If you are uncertain about something, say so—do not fabricate expertise you would not have.
4. Keep responses to 150-250 words unless the question calls for more detail.
5. You may express strong opinions consistent with your background.
"""

    if signal_state and "topics" in signal_state:
        prompt += f"""
CURRENT CONTEXT (information you have been exposed to recently):
- There has been rising discussion about greenwashing in the chemical industry.
- Sentiment in online discussions about corporate net-zero pledges is mixed (positive: {signal_state['topics'].get('net_zero_pledges', {}).get('sentiment', 'unknown')}).
- Active critics include: {', '.join(signal_state.get('entities', {}).get('active_critics', ['various environmental groups']))}.
- Competitor announcements: {', '.join(signal_state.get('entities', {}).get('competitors_mentioned', ['other companies have made similar pledges']))}.
- A recent investigative report about supply chain violations has been gaining attention (anomaly score: {signal_state.get('anomalies', {}).get('supplier_violation_story_resurgence', {}).get('score', 'N/A')}).
"""

    return prompt


def get_persona_response(
    api_key: str,
    persona: dict,
    stimulus: str,
    probe: str,
    signal_state: Optional[dict] = None,
    temperature: float = 0.8,
    model: str = "claude-sonnet-4-20250514"
) -> dict:
    """
    Run a single persona through one AFG turn: stimulus + probe.
    Returns structured response.
    """
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

    response = chat(
        system_prompt=system_prompt,
        user_message=user_message,
        model=model,
        temperature=temperature,
        max_tokens=800,
        api_key=api_key,
    )

    raw_text = response.content.strip()

    # Parse JSON, handling potential markdown wrapping
    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.strip()

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        parsed = {
            "interpretation": raw_text,
            "sentiment": None,
            "credibility": None,
            "concerns": [],
            "positive_aspects": [],
            "missing_information": [],
            "likely_action": "unknown",
            "key_themes": [],
            "_parse_error": True
        }

    parsed["persona_id"] = persona["id"]
    parsed["persona_label"] = persona["label"]
    parsed["_raw"] = raw_text
    parsed["_model"] = model
    parsed["_temperature"] = temperature

    return parsed


def get_persona_followup(
    api_key: str,
    persona: dict,
    stimulus: str,
    initial_response: dict,
    followup_probe: str,
    signal_state: Optional[dict] = None,
    temperature: float = 0.8,
    model: str = "claude-sonnet-4-20250514"
) -> dict:
    """
    Second turn: moderator follow-up probe after initial response.
    """
    system_prompt = build_persona_system_prompt(persona, signal_state)

    messages = [
        {
            "role": "user",
            "content": f"ANNOUNCEMENT: {stimulus}\n\nWhat is your initial reaction to this announcement?"
        },
        {
            "role": "assistant",
            "content": json.dumps({
                "interpretation": initial_response.get("interpretation", ""),
                "sentiment": initial_response.get("sentiment"),
                "key_concerns": initial_response.get("concerns", [])[:2]
            })
        },
        {
            "role": "user",
            "content": f"""FOLLOW-UP QUESTION: {followup_probe}

Respond with a JSON object:
{{
  "followup_response": "Your answer (3-5 sentences)",
  "sentiment_shift": <integer 1-7, same scale as before—has your view changed?>,
  "new_themes": ["any new theme labels that emerged from this reflection"]
}}

Respond ONLY with the JSON object."""
        }
    ]

    response = chat(
        system_prompt=system_prompt,
        user_message="",
        model=model,
        temperature=temperature,
        max_tokens=500,
        api_key=api_key,
        messages=messages,
    )

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
