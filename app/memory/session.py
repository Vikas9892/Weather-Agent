from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SessionFact(BaseModel):
    last_location: Optional[str] = None
    last_activity: Optional[str] = None
    last_sop_id: Optional[str] = None
    last_decision: Optional[str] = None
    history: List[Dict[str, str]] = Field(default_factory=list)


class SessionMemoryStore:
    """
    In-memory session-scoped memory store.
    Carries facts across follow-up turns within the same session.
    Never persists across restarts or overrides active weather.
    """

    def __init__(self):
        self._sessions: Dict[str, SessionFact] = {}

    def get_session_facts(self, session_id: str) -> Dict[str, Any]:
        session = self._sessions.get(session_id)
        if not session:
            return {}
        return session.model_dump()

    def update_session(
        self,
        session_id: str,
        user_query: str,
        response: str,
        location: Optional[str] = None,
        activity: Optional[str] = None,
        sop_id: Optional[str] = None,
        decision: Optional[str] = None,
    ) -> None:
        session = self._sessions.setdefault(session_id, SessionFact())
        if location:
            session.last_location = location
        if activity:
            session.last_activity = activity
        if sop_id:
            session.last_sop_id = sop_id
        if decision:
            session.last_decision = decision

        session.history.append({"query": user_query, "response": response})
        # Keep last 10 turns
        if len(session.history) > 10:
            session.history = session.history[-10:]

    def clear_session(self, session_id: str) -> None:
        if session_id in self._sessions:
            del self._sessions[session_id]

    def clear_all(self) -> None:
        self._sessions.clear()


session_memory_store = SessionMemoryStore()
