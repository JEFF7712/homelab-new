import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
errors = []
for path in ROOT.rglob("*.md"):
    if ".git" in path.parts or ".agent-state" in path.parts:
        continue
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.rstrip() != line:
            errors.append(f"{path.relative_to(ROOT)}:{number}: trailing whitespace")
if errors:
    print("\n".join(errors), file=sys.stderr)
raise SystemExit(bool(errors))
