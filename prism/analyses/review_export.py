"""Export reports for the author's own reading (2026-11-16): the one evaluation report the verifier rejected, and a
random sample of evaluation reports with their records for a spot check against the record.

Writes files for a human to open locally; prints only counts and paths, never report text.

    PRISM_SKIP_UCSF=1 PYTHONPATH=. .venv/bin/python -m prism.analyses.review_export [--n 20] [--seed 20261116]
    -> outputs/review/{rejected/,sample/,spot_check.csv}
"""

from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd

from prism.analyses import report_v3_2 as RV
from prism.config import OUTPUTS
from prism.report import checker
from prism.report import verifier as V
from prism.report.facts_v3_1 import facts_v3_1
from prism.report.facts_v3_2 import back_claims

OUT = OUTPUTS / "review"


def render(sid, rec, text, claims, F, vr):
    lines = [f"# {sid}", "", "## Report (as generated)", ""]
    for c in claims:
        lines.append(f"- {c.get('text', '')}  (cites: {', '.join(c.get('fields', []))})")
    lines += ["", "## Verifier", "", f"pass: {vr['pass']}"]
    for k, v in vr["bound"].items():
        for b in v:
            lines.append(f"- {k}: {b}")
    lines += ["", "## Record fields", ""]
    for k, v in F.items():
        lines.append(f"- {k}: {v}")
    lines += ["", "## Raw model output", "", "```", text, "```"]
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--seed", type=int, default=20261116)
    a = ap.parse_args(argv)
    (OUT / "rejected").mkdir(parents=True, exist_ok=True)
    (OUT / "sample").mkdir(parents=True, exist_ok=True)
    recs = RV.load_set("eval")
    outs = {o["id"]: o for o in map(json.loads, open(RV.OUT / "llm" / "outputs_eval_v3_2.jsonl"))}
    items = []
    for sid, rec in recs.items():
        if rec["cohort"] not in ("mu", "lumiere"):
            continue
        o = outs.get(f"eval|{sid}")
        claims = checker.parse_structured(o["text"]) if o else None
        if claims is None:
            continue
        F = facts_v3_1(rec)
        C = back_claims(claims, F)
        fz = checker.check(C, F, card=True)["pass"]
        vr = V.verify(C, F)
        items.append((sid, rec, o["text"], C, F, fz, vr))
    n_rej = 0
    for sid, rec, text, C, F, fz, vr in items:
        if fz and not vr["pass"]:
            n_rej += 1
            (OUT / "rejected" / f"{sid.replace('|', '_')}.md").write_text(render(sid, rec, text, C, F, vr))
    rng = np.random.default_rng(a.seed)
    pick = rng.choice(len(items), size=min(a.n, len(items)), replace=False)
    rows = []
    for i in pick:
        sid, rec, text, C, F, fz, vr = items[i]
        name = f"{sid.replace('|', '_')}.md"
        (OUT / "sample" / name).write_text(render(sid, rec, text, C, F, vr))
        rows.append({"file": name, "cohort": rec["cohort"], "factual_error (y/n)": "", "misleading_emphasis (y/n)": "",
                     "missing_important (y/n)": "", "notes": ""})
    pd.DataFrame(rows).to_csv(OUT / "spot_check.csv", index=False)
    print(f"{len(items)} MU and LUMIERE evaluation reports; rejected by the verifier after passing the checker: {n_rej}")
    print(f"wrote {OUT / 'rejected'} ({n_rej} files), {OUT / 'sample'} ({len(rows)} files), {OUT / 'spot_check.csv'}")


if __name__ == "__main__":
    main()
