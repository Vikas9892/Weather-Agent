from __future__ import annotations

from typing import Any, Dict, Optional
from langgraph.graph import StateGraph, START, END

from app.graph.state import SafetyState
from app.graph.nodes.understand import load_session, understand_query
from app.graph.nodes.weather import (
    resolve_location_node,
    fetch_weather_node,
    location_fallback_node,
    weather_fallback_node,
)
from app.graph.nodes.policy import (
    retrieve_candidate_sops_node,
    evaluate_sops_node,
    resolve_conflicts_node,
    no_sop_fallback_node,
)
from app.graph.nodes.safety import safety_gate_node
from app.graph.nodes.response import (
    generate_response_node,
    validate_response_node,
    persist_session_node,
)

from app.policy.registry import PolicyRegistry
from app.policy.loader import load_policies
from app.policy.evaluator import PolicyEvaluator
from app.policy.resolver import PolicyResolver
from app.weather.gateway import WeatherGateway
from app.llm.gateway import LLMGateway
from app.safety.gate import SafetyGate
from app.safety.validator import ResponseValidator
from app.memory.session import session_memory_store, SessionMemoryStore


class SafetyAgentGraph:
    """
    Production LangGraph agent orchestrating outdoor safety reasoning.
    Enforces deterministic safety gating, genuine branching, and observability.
    """

    def __init__(
        self,
        registry: Optional[PolicyRegistry] = None,
        weather_gateway: Optional[WeatherGateway] = None,
        llm_gateway: Optional[LLMGateway] = None,
        evaluator: Optional[PolicyEvaluator] = None,
        resolver: Optional[PolicyResolver] = None,
        safety_gate: Optional[SafetyGate] = None,
        validator: Optional[ResponseValidator] = None,
        memory: Optional[SessionMemoryStore] = None,
    ):
        self.registry = registry or load_policies("policies")
        self.weather_gateway = weather_gateway or WeatherGateway()
        self.llm_gateway = llm_gateway or LLMGateway()
        self.evaluator = evaluator or PolicyEvaluator()
        self.resolver = resolver or PolicyResolver()
        self.safety_gate = safety_gate or SafetyGate()
        self.validator = validator or ResponseValidator(registry=self.registry)
        self.memory = memory or session_memory_store

        self.graph = self._build_graph()

    def _build_graph(self):
        builder = StateGraph(SafetyState)

        # 1. Register Nodes
        builder.add_node("load_session", load_session)
        builder.add_node(
            "understand_query",
            lambda s: understand_query(s, self.llm_gateway),
        )
        builder.add_node(
            "resolve_location",
            lambda s: resolve_location_node(s, self.weather_gateway),
        )
        builder.add_node("location_fallback", location_fallback_node)
        builder.add_node(
            "fetch_weather",
            lambda s: fetch_weather_node(s, self.weather_gateway),
        )
        builder.add_node("weather_fallback", weather_fallback_node)
        builder.add_node(
            "retrieve_candidate_sops",
            lambda s: retrieve_candidate_sops_node(s, self.registry, self.evaluator),
        )
        builder.add_node(
            "evaluate_sops",
            lambda s: evaluate_sops_node(s, self.evaluator),
        )
        builder.add_node(
            "resolve_conflicts",
            lambda s: resolve_conflicts_node(s, self.resolver),
        )
        builder.add_node("no_sop_fallback", no_sop_fallback_node)
        builder.add_node(
            "safety_gate",
            lambda s: safety_gate_node(s, self.safety_gate),
        )
        builder.add_node(
            "generate_response",
            lambda s: generate_response_node(s, self.llm_gateway),
        )
        builder.add_node(
            "validate_response",
            lambda s: validate_response_node(s, self.validator),
        )
        builder.add_node(
            "persist_session",
            lambda s: persist_session_node(s, self.memory),
        )

        # 2. Sequential & Branching Edges
        builder.add_edge(START, "load_session")
        builder.add_edge("load_session", "understand_query")
        builder.add_edge("understand_query", "resolve_location")

        # Branch 1: Location Resolution Check
        def route_after_location(state: SafetyState) -> str:
            if not state.get("location"):
                return "location_fallback"
            return "fetch_weather"

        builder.add_conditional_edges(
            "resolve_location",
            route_after_location,
            {
                "location_fallback": "location_fallback",
                "fetch_weather": "fetch_weather",
            },
        )
        builder.add_edge("location_fallback", "persist_session")

        # Branch 2: Weather Availability Check
        def route_after_weather(state: SafetyState) -> str:
            if not state.get("weather") or state.get("weather_status") == "unavailable":
                return "weather_fallback"
            return "retrieve_candidate_sops"

        builder.add_conditional_edges(
            "fetch_weather",
            route_after_weather,
            {
                "weather_fallback": "weather_fallback",
                "retrieve_candidate_sops": "retrieve_candidate_sops",
            },
        )
        builder.add_edge("weather_fallback", "persist_session")

        # Policy Retrieval & Evaluation Flow
        builder.add_edge("retrieve_candidate_sops", "evaluate_sops")

        # Branch 3: Policy Match Check
        def route_after_evaluation(state: SafetyState) -> str:
            matches = state.get("matched_sops", [])
            if not matches:
                return "no_sop_fallback"
            return "resolve_conflicts"

        builder.add_conditional_edges(
            "evaluate_sops",
            route_after_evaluation,
            {
                "no_sop_fallback": "no_sop_fallback",
                "resolve_conflicts": "resolve_conflicts",
            },
        )

        # Main Success Path
        builder.add_edge("resolve_conflicts", "safety_gate")
        builder.add_edge("safety_gate", "generate_response")
        builder.add_edge("generate_response", "validate_response")
        builder.add_edge("validate_response", "persist_session")

        # No-SOP path joins response validation
        builder.add_edge("no_sop_fallback", "validate_response")

        builder.add_edge("persist_session", END)

        return builder.compile()

    def run(self, query: str, session_id: str = "default_session") -> SafetyState:
        """Executes the safety graph synchronously for a user query."""
        initial_state: SafetyState = {
            "session_id": session_id,
            "user_query": query,
        }
        final_state = self.graph.invoke(initial_state)
        return final_state
