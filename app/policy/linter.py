import sys
from pathlib import Path

# Fix Windows console UTF-8 output encoding for checkmark symbols
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Add backend directory and repo root to sys.path
current_dir = Path(__file__).resolve().parent
backend_dir = current_dir.parent.parent
repo_root = backend_dir.parent

for p in [str(backend_dir), str(repo_root)]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from app.policy.loader import PolicyRegistry
    from app.policy.validator import validate_policy_set
except ImportError:
    from backend.app.policy.loader import PolicyRegistry
    from backend.app.policy.validator import validate_policy_set


def find_policies_dir() -> Path:
    candidates = [
        Path("policies"),
        repo_root / "policies",
        backend_dir / "policies",
        Path.cwd() / "policies",
    ]
    for c in candidates:
        if c.exists() and c.is_dir():
            return c.resolve()
    return (repo_root / "policies").resolve()


def run_linter() -> bool:
    print("Loading policies...\n")
    policies_dir = find_policies_dir()

    registry = PolicyRegistry()
    try:
        count = registry.load(policies_dir)
        policies = registry.get_all()
    except Exception as e:
        print(f"✗ Failed to load policies: {e}")
        return False

    is_valid, errors = validate_policy_set(policies)

    if not is_valid:
        print("✗ Policy validation FAILED:")
        for err in errors:
            print(f"  - {err}")
        return False

    print(f"✓ {count} policies found")
    print(f"✓ {count} valid IDs")
    print(f"✓ {count} valid schemas")
    print("✓ No duplicate IDs")
    print("✓ No invalid operators")
    print("✓ No broken override references")
    print("\nPolicy validation PASSED")
    return True


if __name__ == "__main__":
    success = run_linter()
    sys.exit(0 if success else 1)
