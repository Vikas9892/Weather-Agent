from __future__ import annotations

from typing import Any, Dict
from app.graph.state import SafetyState
from app.llm.gateway import LLMGateway
from app.memory.session import session_memory_store


def load_session(state: SafetyState) -> Dict[str, Any]:
    """Retrieves previous turn context from session memory if available."""
    session_id = state.get("session_id", "default_session")
    history = session_memory_store.get_session_facts(session_id)
    updates: Dict[str, Any] = {"session_id": session_id}

    # If the user previously specified a location and this query lacks one, carry it forward
    if history.get("last_location"):
        updates["location_query"] = history["last_location"]
    if history.get("last_activity"):
        updates["activity"] = history["last_activity"]

    return updates


def understand_query(state: SafetyState, llm_gateway: LLMGateway) -> Dict[str, Any]:
    """Parses natural language query into activity, location, and time window."""
    query = state.get("user_query", "")
    intent = llm_gateway.understand_query(query)

    updates: Dict[str, Any] = {
        "activity": intent.activity,
        "requested_time": intent.time,
    }

    # If location was found in current query, use it; otherwise preserve existing session location
    if intent.location:
        updates["location_query"] = intent.location
    elif not state.get("location_query"):
        # Default fallback city if completely unspecified
        updates["location_query"] = "Bhopal"

    return updates
