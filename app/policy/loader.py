from pathlib import Path
from typing import Union
from app.policy.registry import PolicyRegistry


def load_policies(directory: Union[str, Path] = "policies") -> PolicyRegistry:
    """Convenience function to load and return a populated PolicyRegistry."""
    registry = PolicyRegistry()
    registry.load(directory)
    return registry


__all__ = ["PolicyRegistry", "load_policies"]
