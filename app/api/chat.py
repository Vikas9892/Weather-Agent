from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.graph.graph import SafetyAgentGraph
from app.policy.loader import load_policies

router = APIRouter(prefix="/api", tags=["Safety Chat"])

# Global graph instance
agent_graph = SafetyAgentGraph()


class ChatRequest(BaseModel):
    message: str = Field(..., description="User question or statement regarding outdoor safety")
    session_id: str = Field(default="default_session", description="Session identifier for multi-turn conversational context")


class ChatResponse(BaseModel):
    response: str
    activity: str
    location: Optional[Dict[str, Any]] = None
    weather: Optional[Dict[str, Any]] = None
    weather_status: str
    safety_status: str
    selected_sop: Optional[Dict[str, Any]] = None
    matched_sops: List[Dict[str, Any]] = Field(default_factory=list)
    policy_decision: Optional[Dict[str, Any]] = None
    resolution_reason: str = ""
    decision_trace: Optional[Dict[str, Any]] = None


@router.post("/chat", response_model=ChatResponse)
def chat_endpoint(payload: ChatRequest):
    """
    Main chat endpoint executing the LangGraph safety agent.
    Returns the grounded advice, weather facts, and complete decision trace.
    """
    result = agent_graph.run(query=payload.message, session_id=payload.session_id)

    return ChatResponse(
        response=result.get("response", ""),
        activity=result.get("activity", "general_outdoor"),
        location=result.get("location"),
        weather=result.get("weather", {}).get("weather"),
        weather_status=result.get("weather_status", "unknown"),
        safety_status=result.get("safety_status", "APPROVED"),
        selected_sop=result.get("selected_sop"),
        matched_sops=result.get("matched_sops", []),
        policy_decision=result.get("policy_decision"),
        resolution_reason=result.get("resolution_reason", ""),
        decision_trace=result.get("decision_trace"),
    )


@router.get("/policies")
def list_policies():
    """Lists all registered Standard Operating Procedures (SOPs)."""
    policies = agent_graph.registry.get_all()
    return {
        "count": len(policies),
        "policies": [
            {
                "id": p.id,
                "title": p.title,
                "category": p.category,
                "severity": p.severity,
                "priority": p.priority,
                "overrides": p.overrides,
                "activities": p.activities,
            }
            for p in policies
        ],
    }


@router.get("/session/{session_id}")
def get_session_memory(session_id: str):
    """Retrieves session-scoped memory facts for a conversation."""
    facts = agent_graph.memory.get_session_facts(session_id)
    return {"session_id": session_id, "memory": facts}
