"""The dependency rule: imports point downward, and stages never import stages.

core   <- pure helpers, depends on nothing of ours
data   <- storage and features, may use core
stages <- scrape/train/run, may use core and data, never another stage
"""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTERNAL = {"core", "data", "stages"}
MAY_IMPORT = {"core": set(), "data": {"core"}, "stages": {"core", "data"}}


def _imported_modules(path: Path):
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            yield node.module


def test_imports_only_point_downward():
    violations = []
    for layer in sorted(INTERNAL):
        for path in sorted((ROOT / layer).rglob("*.py")):
            parts = path.relative_to(ROOT).parts
            stage = parts[1] if layer == "stages" and len(parts) > 2 else None
            for module in _imported_modules(path):
                root = module.split(".")[0]
                if root not in INTERNAL:
                    continue
                where = path.relative_to(ROOT)
                if root != layer and root not in MAY_IMPORT[layer]:
                    violations.append(f"{where}: {layer} may not import {root} ({module})")
                elif root == "stages" and layer == "stages":
                    other = module.split(".")[1] if "." in module else None
                    if other and stage and other != stage:
                        violations.append(f"{where}: stage {stage!r} may not import stage {other!r} ({module})")
    assert not violations, "layering violations:\n  " + "\n  ".join(violations)


def test_only_repositories_touch_the_database():
    """SQLAlchemy and the ORM models stay behind the repository package."""
    allowed = {Path("data/storage/db.py"), Path("data/storage/models.py"), Path("data/storage/mapping.py")}
    offenders = []
    for layer in sorted(INTERNAL):
        for path in sorted((ROOT / layer).rglob("*.py")):
            where = path.relative_to(ROOT)
            if where in allowed or where.parts[:3] == ("data", "storage", "repositories"):
                continue
            for module in _imported_modules(path):
                if module.split(".")[0] == "sqlalchemy" or module == "data.storage.models":
                    offenders.append(f"{where}: {module} may only be used inside data/storage/repositories")
    assert not offenders, "database access outside the repositories:\n  " + "\n  ".join(offenders)
