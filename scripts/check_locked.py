"""Fail when approved wording in docs/manuscript/LOCKED.md (```locked blocks) is missing from paper/main.tex.

Whitespace and line breaks are ignored. Run by paper/build.sh; exits 1 and lists each missing item.
"""
import re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
norm = lambda t: re.sub(r"\s+", " ", t).strip()
paper = norm((ROOT / "paper/main.tex").read_text())
blocks = re.findall(r"```locked\n(.*?)```", (ROOT / "docs/manuscript/LOCKED.md").read_text(), re.S)
items = []
for b in blocks:
    lines = [l for l in b.strip().split("\n") if l.strip()]
    items += [norm(b)] if len(lines) == 1 else [norm(l) for l in lines]
missing = [i for i in items if i not in paper]
for m in missing:
    print(f"LOCKED wording changed or missing: {m[:110]}{'...' if len(m) > 110 else ''}", file=sys.stderr)
sys.exit(1 if missing else 0)
