from pathlib import Path
from typing import Dict, List, Optional, Union
import yaml

try:
    from .models import SOP
    from .validator import PolicyValidationError, validate_policy_set
except ImportError:
    from app.policy.models import SOP
    from app.policy.validator import PolicyValidationError, validate_policy_set


class PolicyRegistry:
    """In-memory registry for loaded and validated SOP policies."""

    def __init__(self):
        self._policies: Dict[str, SOP] = {}

    def clear(self) -> None:
        """Clears all registered policies."""
        self._policies.clear()

    def register(self, policy: SOP) -> None:
        """Registers a single SOP."""
        self._policies[policy.id] = policy

    def get(self, policy_id: str) -> Optional[SOP]:
        """Retrieves a policy by ID."""
        return self._policies.get(policy_id)

    def get_all(self) -> List[SOP]:
        """Returns all registered policies."""
        return list(self._policies.values())

    def filter_by_category(self, category: str) -> List[SOP]:
        """Returns policies matching a specific category."""
        return [p for p in self._policies.values() if p.category.lower() == category.lower()]

    def filter_by_activity(self, activity: str) -> List[SOP]:
        """Returns policies matching a specific activity."""
        act_lower = activity.lower()
        return [
            p
            for p in self._policies.values()
            if any(act_lower == a.lower() for a in p.activities)
        ]

    def load(self, directory: Union[str, Path]) -> int:
        """
        Recursively scans directory for .yaml/.yml files,
        parses and validates them as SOP objects,
        and registers them in the registry.

        Raises PolicyValidationError if any validation fails.
        Returns total number of policies loaded.
        """
        dir_path = Path(directory)
        if not dir_path.is_absolute():
            dir_path = dir_path.resolve()

        if not dir_path.exists() or not dir_path.is_dir():
            raise FileNotFoundError(f"Policy directory not found: {dir_path}")

        yaml_files = sorted(list(dir_path.glob("**/*.yaml")) + list(dir_path.glob("**/*.yml")))
        loaded_policies: List[SOP] = []

        for yml_file in yaml_files:
            try:
                with open(yml_file, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                if not data or not isinstance(data, dict):
                    continue

                policy = SOP.model_validate(data)
                loaded_policies.append(policy)
            except Exception as e:
                raise PolicyValidationError(f"Error loading {yml_file.name}: {e}") from e

        # Validate the entire policy set (no duplicates, broken overrides, etc.)
        is_valid, errors = validate_policy_set(loaded_policies)
        if not is_valid:
            error_msg = "\n".join(errors)
            raise PolicyValidationError(f"Policy set validation failed:\n{error_msg}")

        # Register all valid policies
        self.clear()
        for p in loaded_policies:
            self.register(p)

        return len(self._policies)
