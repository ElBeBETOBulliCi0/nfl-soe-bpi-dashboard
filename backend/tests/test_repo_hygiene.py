"""Repository hygiene checks: .gitignore rules, forbidden imports, no raw data."""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN_MODULES = {"hypothesis", "pyarrow"}
RAW_SUFFIXES = {".csv", ".parquet", ".feather"}


def _gitignore_lines():
    text = (ROOT / ".gitignore").read_text(encoding="utf-8")
    return [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.strip().startswith("#")]


def _py_files(folder):
    base = ROOT / folder
    if not base.exists():
        return []
    return [p for p in base.rglob("*.py") if "__pycache__" not in p.parts]


def test_gitignore_excludes_tracking_data():
    assert "data/tracking/" in _gitignore_lines()


def test_gitignore_excludes_env_but_keeps_example():
    lines = _gitignore_lines()
    assert ".env" in lines
    assert "!.env.example" in lines


def test_env_example_has_no_real_secrets():
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith(("AWS_ACCESS_KEY_ID=", "AWS_SECRET_ACCESS_KEY=", "AWS_SESSION_TOKEN=")):
            assert line.split("=", 1)[1].strip() == "", f"secret value in .env.example: {line.split('=')[0]}"


def test_no_forbidden_imports_in_backend_or_scripts():
    offenders = []
    for folder in ("backend", "scripts"):
        for path in _py_files(folder):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                    names = [node.module]
                for name in names:
                    if name.split(".")[0] in FORBIDDEN_MODULES:
                        offenders.append(f"{path.relative_to(ROOT)}: {name}")
    assert not offenders, offenders


def test_no_raw_tracking_files_under_backend():
    base = ROOT / "backend"
    offenders = [
        str(p.relative_to(ROOT))
        for p in base.rglob("*")
        if p.is_file()
        and (p.name.startswith("tracking_") or "tracking" in p.parts)
        and p.suffix.lower() in RAW_SUFFIXES
    ]
    assert not offenders, offenders
