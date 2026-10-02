from __future__ import annotations

import sys
from pathlib import Path

# Fix UTF-8 encoding on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from app.graph.graph import SafetyAgentGraph
from app.weather.gateway import WeatherGateway
from app.weather.models import Location, WeatherState
from evals.fixtures.replay_fixtures import REPLAY_FIXTURES


def run_mutation_test():
    """
    Phase 13 Mutation Test:
    Takes CYC-001 threshold (wind_speed >= 40.0 km/h) and mutates it to (wind_speed >= 50.0 km/h).
    Then verifies that the test suite catches the mutation and reports a change in behavior.
    """
    print("==================================================")
    print("PHASE 13: MUTATION TESTING")
    print("Testing sensitivity: mutating CYC-001 wind threshold")
    print("==================================================\n")

    policy_file = root_dir / "policies" / "cycling" / "CYC-001.yaml"
    with open(policy_file, "r", encoding="utf-8") as f:
        original_content = f.read()

    try:
        # Step 1: Baseline check with original policy (wind 42.0 km/h triggers CYC-001)
        gw = WeatherGateway()
        agent_baseline = SafetyAgentGraph(weather_gateway=gw)
        gw.set_mock_location(Location.model_validate(REPLAY_FIXTURES["high_wind_crosswind"]["location"]))
        gw.set_mock_weather(WeatherState.model_validate(REPLAY_FIXTURES["high_wind_crosswind"]["weather"]))

        res_baseline = agent_baseline.run("Can I cycle in Chennai?")
        sel_baseline = res_baseline.get("selected_sop", {}).get("id")
        assert sel_baseline == "CYC-001", f"Baseline check failed: expected CYC-001, got {sel_baseline}"
        print(f"✓ Baseline check PASSED: Wind 42 km/h triggers CYC-001 threshold (>= 40.0 km/h).")

        # Step 2: Apply mutation: change threshold from 40.0 to 50.0
        mutated_content = original_content.replace("value: 40.0", "value: 50.0")
        with open(policy_file, "w", encoding="utf-8") as f:
            f.write(mutated_content)

        # Step 3: Run with mutated policy
        agent_mutated = SafetyAgentGraph(weather_gateway=gw)
        res_mutated = agent_mutated.run("Can I cycle in Chennai?")
        sel_mutated = (res_mutated.get("selected_sop") or {}).get("id")

        print(f"✓ Mutation applied: CYC-001 threshold shifted from 40.0 -> 50.0 km/h.")
        print(f"  Result with mutation: Selected SOP changed from {sel_baseline} -> {sel_mutated}")

        # The mutation MUST be killed (behavior must change!)
        if sel_mutated != "CYC-001":
            print("\n✓ MUTATION KILLED: Evaluation suite successfully detected behavioral divergence!")
            print("  This proves the policy engine and test suite are sensitive to threshold mutations.")
            return True
        else:
            print("\n✗ MUTATION SURVIVED: Evaluation suite failed to detect threshold change.")
            return False

    finally:
        # Always restore original policy content cleanly
        with open(policy_file, "w", encoding="utf-8") as f:
            f.write(original_content)
        print("✓ Policy restored to original specification.\n")


if __name__ == "__main__":
    success = run_mutation_test()
    sys.exit(0 if success else 1)
