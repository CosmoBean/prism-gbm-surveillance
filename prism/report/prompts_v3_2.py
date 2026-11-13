"""Prompt v3.5 for report v3.2 (docs/results/REVISION_DATA_PLAN.md, R4): prompt v3.4 (prompts_v3_1) with the model
names of the paper and the v3.2 keys. No rule, line or order changes. Section tag "pathways" becomes "models".
"""

from __future__ import annotations

import copy
import json
import re

from prism.report import prompts_v3_1 as P31

VERSION = "v3.5"
SECTIONS = ("scan", "models", "combined", "trust")
SCHEMA = copy.deepcopy(P31.SCHEMA)
SCHEMA["properties"]["sentences"]["items"]["properties"]["section"]["enum"] = list(SECTIONS)
SUBS = [(r"\bpathway\.timeline\.", "model.clinical_history."), (r"\bpathway\.images\.", "model.imaging."),
        (r"\bpathway\.combined\.", "model.combined."), (r"\bpathways\.", "models."),
        (r'PATHWAYS \(section "pathways"\)', 'MODELS (section "models")'), (r'"pathways" \|', '"models" |'),
        (r"\bthe timeline pathway\b", "the clinical-history model"), (r"\bthe image pathway\b", "the imaging model")]


def system_prompt(F: dict) -> str:
    s = P31.system_prompt(F)
    for a, b in SUBS:
        s = re.sub(a, b, s)
    assert not re.search(r"timeline|pathway", s, re.I), "old model names left in the prompt"
    return s


def grounded_v3_2(F: dict) -> list[dict]:
    return [{"role": "system", "content": system_prompt(F)},
            {"role": "user", "content": "FACTS:\n" + json.dumps(F, indent=1, ensure_ascii=False)}]
