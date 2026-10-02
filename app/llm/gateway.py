from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from app.config import settings

logger = logging.getLogger(__name__)

# Canonical activity categories
ACTIVITY_SYNONYMS = {
    "playground": ["monkey bars", "jungle gym", "swings", "slides", "play with kid", "take my kid to the park", "playground"],
    "picnic": ["sandwiches", "spreading a blanket", "lunch basket", "picnic", "outing", "bbq", "barbecue", "lawn games", "gathering"],
    "hiking": ["hike", "hiking", "trek", "trekking", "backpacking", "climbing", "climb", "mountaineering", "pass"],
    "cycling": ["cycle", "cycling", "bike", "biking", "bicycle", "two-wheeler", "motorcycle", "scooter"],
    "running": ["run", "running", "jog", "jogging", "sprint"],
    "exercise": ["workout", "exercise", "training", "fitness", "calisthenics", "sports"],
    "travel": ["drive", "driving", "commute", "road trip", "highway", "travel"],
    "stroll": ["walk", "walking", "stroll", "stroller"],
}


class QueryIntent(BaseModel):
    """Structured intent parsed from natural language user query."""
    activity: str = Field(default="general_outdoor", description="Normalized activity name")
    location: Optional[str] = Field(None, description="Extracted city or region name")
    time: Optional[str] = Field(None, description="Extracted time window")
    raw_query: str = ""


class LLMGateway:
    """
    Unified LLM Gateway supporting OpenAI (GPT-4o-mini), Google Gemini Flash, and xAI Grok.
    LiteLLM abstracts the provider interfaces. The LLM translates natural language into structured
    intents and explains deterministic decisions. It NEVER determines safety rules or thresholds.
    """

    def __init__(self, preferred_model: Optional[str] = None):
        self.preferred_model = preferred_model or settings.LLM_MODEL or "gpt-4o-mini"

    def get_active_model_and_key(self) -> Tuple[str, Optional[str]]:
        """
        Dynamically selects the active model and corresponding API key among:
        1. Gemini Flash (gemini/gemini-2.0-flash, gemini/gemini-1.5-flash)
        2. xAI Grok (xai/grok-beta, xai/grok-2)
        3. OpenAI (gpt-4o-mini, gpt-4o)
        """
        req_model = self.preferred_model.lower()

        # 1. Gemini requested
        if "gemini" in req_model:
            gemini_key = settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY")
            if gemini_key and not gemini_key.startswith("your_"):
                model_tag = self.preferred_model if self.preferred_model.startswith("gemini/") else f"gemini/{self.preferred_model}"
                return model_tag, gemini_key

        # 2. Grok / xAI requested
        if "grok" in req_model or "xai" in req_model:
            grok_key = settings.XAI_API_KEY or settings.GROK_API_KEY or os.environ.get("XAI_API_KEY") or os.environ.get("GROK_API_KEY")
            if grok_key and not grok_key.startswith("your_"):
                model_tag = "xai/grok-beta" if not self.preferred_model.startswith("xai/") else self.preferred_model
                return model_tag, grok_key

        # 3. OpenAI requested
        openai_key = settings.OPENAI_API_KEY or settings.LLM_API_KEY or os.environ.get("OPENAI_API_KEY")
        if openai_key and not openai_key.startswith("mock") and not openai_key.startswith("your_"):
            return self.preferred_model, openai_key

        # Fallback chain: check if any provider key is active
        gemini_key = settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY")
        if gemini_key and not gemini_key.startswith("your_"):
            return "gemini/gemini-2.0-flash", gemini_key

        grok_key = settings.XAI_API_KEY or settings.GROK_API_KEY or os.environ.get("XAI_API_KEY")
        if grok_key and not grok_key.startswith("your_"):
            return "xai/grok-beta", grok_key

        return self.preferred_model, None

    def has_active_llm(self) -> bool:
        _, key = self.get_active_model_and_key()
        return bool(key and len(key) > 5)

    def understand_query(self, query: str) -> QueryIntent:
        """Parses user query into structured intent (activity, location, time)."""
        model, api_key = self.get_active_model_and_key()

        if api_key and len(api_key) > 5:
            try:
                import litellm
                prompt = (
                    "You are a query parser for an outdoor activity safety system. "
                    "Extract the activity, location, and time window from the query. "
                    "Return ONLY valid JSON matching this schema:\n"
                    '{"activity": "<normalized_activity_or_general_outdoor>", "location": "<city_or_null>", "time": "<time_or_null>"}\n\n'
                    f'Query: "{query}"\nJSON:'
                )
                response = litellm.completion(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    api_key=api_key,
                    temperature=0.0,
                    max_tokens=150,
                )
                text = response.choices[0].message.content.strip()
                clean_json = re.sub(r"^```json\s*|\s*```$", "", text, flags=re.MULTILINE).strip()
                data = json.loads(clean_json)
                return QueryIntent(
                    activity=self.normalize_activity(data.get("activity", "")),
                    location=data.get("location"),
                    time=data.get("time"),
                    raw_query=query,
                )
            except Exception as e:
                logger.warning(f"LiteLLM ({model}) understand_query fallback due to error: {e}")

        return self._rule_based_understand(query)

    def normalize_activity(self, raw_activity: str) -> str:
        if not raw_activity:
            return "general_outdoor"
        act_lower = raw_activity.lower().strip()
        for canonical, synonyms in ACTIVITY_SYNONYMS.items():
            if act_lower == canonical or any(syn in act_lower for syn in synonyms):
                return canonical
        return act_lower

    def _rule_based_understand(self, query: str) -> QueryIntent:
        q_lower = query.lower()

        detected_activity = "general_outdoor"
        for canonical, synonyms in ACTIVITY_SYNONYMS.items():
            if any(syn in q_lower for syn in synonyms):
                detected_activity = canonical
                break

        location = None
        loc_match = re.search(r"\b(?:in|at|near|for|around)\s+([A-Z][a-zA-Z\s]+?)(?:\s+(?:today|tomorrow|now|this|at|\?|$))", query)
        if loc_match:
            location = loc_match.group(1).strip()
        else:
            words = query.split()
            for w in words:
                clean_w = re.sub(r"[^\w]", "", w)
                if clean_w in ["Bhopal", "Delhi", "Mumbai", "London", "Berlin", "Paris", "Bengaluru", "Chennai"]:
                    location = clean_w
                    break

        time_window = None
        for t in ["this evening", "evening", "tomorrow", "today", "afternoon", "morning", "night", "now"]:
            if t in q_lower:
                time_window = t
                break

        return QueryIntent(
            activity=detected_activity,
            location=location,
            time=time_window,
            raw_query=query,
        )

    def generate_response(
        self,
        query: str,
        activity: str,
        location_name: str,
        weather_summary: Dict[str, Any],
        selected_sop: Optional[Dict[str, Any]],
        safety_status: str,
        decision: Optional[str],
        severity: Optional[str],
        rationale: Optional[str],
        supporting_sops: Optional[list] = None,
    ) -> str:
        """Generates natural language explanation grounded strictly in the deterministic decisions."""
        if not selected_sop:
            return (
                f"We checked the weather in {location_name} ({self._format_weather_summary(weather_summary)}), "
                f"but we currently have no specific Standard Operating Procedure (SOP) safety policy covering '{activity}'. "
                f"As a strict safety policy, our system does not invent unverified safety guidance. "
                f"Please proceed with caution and consult local advisories."
            )

        sop_id = selected_sop.get("id", "SOP")
        sop_title = selected_sop.get("title", "")
        sev = (severity or selected_sop.get("severity", "moderate")).upper()
        act_dec = decision or selected_sop.get("decision", "")
        rat = rationale or selected_sop.get("rationale", "")

        weather_str = self._format_weather_summary(weather_summary)
        model, api_key = self.get_active_model_and_key()

        if api_key and len(api_key) > 5:
            try:
                import litellm
                system_prompt = (
                    "You are the voice of the Outdoor Safety Agent. You explain safety decisions to users.\n"
                    "CRITICAL CONSTRAINTS:\n"
                    f"1. You must explicitly name the cited SOP ID: {sop_id}.\n"
                    "2. You must strictly cite ONLY the weather numbers provided in context.\n"
                    "3. You must NOT invent advice, downplay severity, or contradict the policy decision.\n"
                    f"4. Severity is {sev}. Decision is: {act_dec}.\n"
                )
                user_prompt = (
                    f"User Query: '{query}'\n"
                    f"Location: {location_name}\n"
                    f"Observed Weather Facts: {weather_str}\n"
                    f"Cited SOP: {sop_id} - {sop_title}\n"
                    f"Severity Level: {sev}\n"
                    f"Policy Decision: {act_dec}\n"
                    f"Rationale: {rat}\n"
                    "Write a clear, empathetic 2-3 sentence response communicating the safety decision and citing the exact SOP."
                )
                resp = litellm.completion(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    api_key=api_key,
                    temperature=0.2,
                    max_tokens=250,
                )
                return resp.choices[0].message.content.strip()
            except Exception as e:
                logger.warning(f"LiteLLM ({model}) response generation fallback: {e}")

        # Deterministic high-quality template response
        return (
            f"Based on current weather conditions in {location_name} ({weather_str}), "
            f"safety policy [{sop_id}: {sop_title}] applies at {sev} severity. "
            f"Recommendation: {act_dec} "
            f"Rationale: {rat}"
        )

    @staticmethod
    def _format_weather_summary(w: Dict[str, Any]) -> str:
        parts = []
        if "temperature_2m" in w and w["temperature_2m"] is not None:
            parts.append(f"{w['temperature_2m']}°C")
        if "wind_speed_10m" in w and w["wind_speed_10m"] is not None:
            parts.append(f"wind {w['wind_speed_10m']} km/h")
        if "wind_gusts_10m" in w and w["wind_gusts_10m"] is not None:
            parts.append(f"gusts {w['wind_gusts_10m']} km/h")
        if "precipitation" in w and w["precipitation"] is not None:
            parts.append(f"rain {w['precipitation']} mm")
        if "precipitation_probability" in w and w["precipitation_probability"] is not None:
            parts.append(f"rain probability {w['precipitation_probability']}%")
        if "uv_index" in w and w["uv_index"] is not None:
            parts.append(f"UV index {w['uv_index']}")
        return ", ".join(parts) if parts else "live metrics recorded"
