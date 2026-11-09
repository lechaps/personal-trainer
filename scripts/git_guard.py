#!/usr/bin/env python3
"""Fail-closed staged-path whitelist: safeguard, not a guarantee against secrets inside source."""
from pathlib import PurePosixPath
import subprocess
import sys

ROOT_FILES = {"README.md", "README.fr.md", "AGENTS.md", ".gitignore", "hooks/pre-commit"}
ALLOWED_SOURCE = {"jxa/notes.js", "personal_trainer/__init__.py", "personal_trainer/core.py",
                  "scripts/personal-trainer.py", "scripts/git_guard.py"}
SKILL_FILES = {".agents/skills/personal-trainer/SKILL.md",
               ".agents/skills/personal-trainer/references/progression.md"}


def allowed(path: str) -> bool:
    if path in ROOT_FILES | ALLOWED_SOURCE | SKILL_FILES:
        return True
    p = PurePosixPath(path)
    return len(p.parts) == 2 and p.parts[0] == "tests" and p.parts[1].startswith("test_") and p.suffix == ".py"


def main() -> int:
    result = subprocess.run(["git", "diff", "--cached", "--name-only", "-z", "--diff-filter=ACMR"],
                            check=True, capture_output=True)
    staged = [p.decode("utf-8", "replace") for p in result.stdout.split(b"\0") if p]
    blocked = [p for p in staged if not allowed(p)]
    if blocked:
        print("Commit refusé : chemins hors liste blanche :", file=sys.stderr)
        for path in blocked:
            print(f"  {path}", file=sys.stderr)
        return 1
    print("Git guard : chemins autorisés (vérifier aussi le contenu des sources).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
