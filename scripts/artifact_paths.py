"""Keep audit CLI outputs inside dedicated repository artifact directories."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOTS = (ROOT / "output", ROOT / "docs/evidence", ROOT / "eval/runs")


def artifact_path(value: Path, *, directory: bool = False) -> Path:
    path = value.resolve()
    allowed = any(base.resolve().is_relative_to(ROOT)
                  and path.is_relative_to(base.resolve()) and path != base.resolve()
                  for base in ARTIFACT_ROOTS)
    if path == ROOT / "eval/cache-calibration.json":
        allowed = True
    if not allowed or (not directory and path.suffix != ".json"):
        raise ValueError("use a JSON artifact under output/, docs/evidence/ or eval/runs/")
    if path.exists() and (path.is_dir() != directory):
        raise ValueError("artifact path has the wrong file type")
    return path


def cases_path(value: Path) -> Path:
    path = value.resolve(strict=True)
    if not path.is_relative_to(ROOT / "eval") or path.suffix not in {".yaml", ".yml"}:
        raise ValueError("cache cases must be a YAML file inside eval/")
    return path
