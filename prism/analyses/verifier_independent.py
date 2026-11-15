"""Independent planted errors for the bound verifier (exploratory, 2026-11-15, after the internal referee's review).

The errors were written by a separate agent that had not seen the checker or verifier code, on the 52 synthetic
records only (docs/results/independent_mutants_2026-11-15.json): D direction stated wrongly in new wording, L a value
under the wrong entity, S a score on the wrong side of its median in new wording, CONTROL a correct paraphrase.

    PYTHONPATH=. .venv/bin/python -m prism.analyses.verifier_independent
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pandas as pd

from prism.analyses import verifier_mutation as VM
from prism.report import checker
from prism.report import verifier as V

SRC = Path(__file__).resolve().parents[2] / "docs" / "results" / "independent_mutants_2026-11-15.json"


def main():
    base = {rid: (C, F) for rid, C, F in VM.synthetic()}
    rows = []
    for m in json.loads(SRC.read_text()):
        C, F = base[m["record"]]
        D = copy.deepcopy(C)
        if m["index"] is None:
            D.append(m["claim"])
        else:
            D[m["index"]] = m["claim"]
        fz = checker.check(D, F, card=True)
        vr = V.verify(D, F)
        rows.append({"class": m["class"], "frozen_rejected": not fz["pass"], "verifier_rejected": not vr["pass"],
                     "binding_rejected": bool(vr["bound"])})
    df = pd.DataFrame(rows)
    s = df.groupby("class").agg(n=("class", "size"), frozen=("frozen_rejected", "mean"),
                                verifier=("verifier_rejected", "mean"), binding=("binding_rejected", "mean"))
    print(s.round(3).to_string())
    s.to_csv(Path("outputs/results/analyses/verifier_mutation/independent.csv"))


if __name__ == "__main__":
    main()
