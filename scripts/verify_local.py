"""Capture repeatable checks without claiming unavailable cluster/model runs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(command, cwd=ROOT):
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True,
                            encoding="utf-8", errors="replace", timeout=600,
                            env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    output = (result.stdout + result.stderr).replace(str(ROOT), "<repo>")
    output = output.replace(sys.prefix, "<venv>")
    if command[-1] == "scripts/check_submission.py":
        # Retain the real verdict/warnings rather than recursively embedding the
        # checker's own placeholder-marker vocabulary in a file it scans.
        output = "\n".join(line for line in output.splitlines() if
                           line.strip().startswith(("warn", "FAIL")) or
                           re.search(r"\d+ passed.*\d+ failures", line)) + "\n"
    print(f"{'PASS' if result.returncode == 0 else 'FAIL'}: {' '.join(command)}", flush=True)
    return {"command": command[1:] if command[0] == sys.executable else command,
            "exit_code": result.returncode, "output": output}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("docs/evidence/local-validation.json"))
    args = parser.parse_args()
    args.out.unlink(missing_ok=True) # replace this generated report, never source files
    checks = [
        run([sys.executable, "-m", "ruff", "check", "api", "indexer", "eval", "corpus", "scripts"]),
        run([sys.executable, "-m", "mypy", "app"], ROOT / "api"),
        run([sys.executable, "-m", "mypy", "pipeline"], ROOT / "indexer"),
        run([sys.executable, "-m", "pytest", "-q", "-c", "api/pyproject.toml", "api/tests",
             "--cov=api/app", "--cov-branch", "--cov-fail-under=60", "-p", "no:cacheprovider"]),
        run([sys.executable, "-m", "pytest", "-q", "-c", "indexer/pyproject.toml", "indexer/tests",
             "-p", "no:cacheprovider"]),
        run([sys.executable, "-m", "pytest", "-q", "-c", "eval/pyproject.toml", "eval/tests",
             "-p", "no:cacheprovider"]),
        run([sys.executable, "scripts/check_submission.py"]),
    ]
    git = shutil.which("git")
    fingerprint = hashlib.sha256()
    commit = "unavailable"
    if git:
        commit = subprocess.check_output([git, "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        paths = subprocess.check_output([git, "ls-files", "--cached", "--others", "--exclude-standard"],
                                        cwd=ROOT, text=True).splitlines()
        for path in sorted(set(paths)):
            if path == args.out.as_posix() or not (ROOT / path).is_file():
                continue
            fingerprint.update(path.encode() + b"\0" + (ROOT / path).read_bytes())
    report = {"timestamp": datetime.now(timezone.utc).isoformat(), "base_commit": commit,
              "source_fingerprint": fingerprint.hexdigest(),
              "scope": "local Python checks only; no new live-model/cluster claim", "checks": checks}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return int(any(row["exit_code"] for row in checks))


if __name__ == "__main__":
    raise SystemExit(main())
