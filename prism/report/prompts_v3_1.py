"""Grounded prompt v3.4 for report v3.1 (docs/results/REPORT_V3_1_PLAN.md section 1), written from facts_v3_1.

The v3.3 prompt (prompts_v3.py, frozen for v3) with one structural change: the system prompt is built from the facts
present. A line about a field (the rater flag, necrosis and cavity, the change from the smallest earlier volume, the
card's agreement statistic, the previous-scan changes, the volumes) is included only when that field exists, so no
model is asked about something the record does not hold. Output schema and section tags as v3.
"""

from __future__ import annotations

import json

from prism.report.prompts_v3 import SCHEMA_V3 as SCHEMA, SECTIONS, sectioned  # noqa: F401

VERSION = "v3.4"

HEAD = """You write the narrative part of a PRISM report for a neuro-oncology clinician. PRISM looks at one post-treatment MRI scan of a glioma and gives scores for whether this scan is the one at which progression is called. The clinician also sees tables with every number; your text explains them in plain words.
You receive FACTS: a JSON object whose keys are field names and whose values come from this scan's system record.

Content rules:
1. Use only information in FACTS. Add no medical knowledge, no image interpretation and nothing that is not in FACTS.
2. Every number you write must be copied exactly from a FACTS value, as digits (never as words). Never compute, round differently or combine numbers.
3. For each sentence, list in "fields" the keys of ALL FACTS fields whose information or numbers the sentence uses. Only list keys that exist in FACTS.
4. Do not diagnose. Never say or imply that the scan shows, is, suggests or is consistent with progression, recurrence, pseudoprogression, radiation necrosis or treatment effect. Do not use RANO response categories. A score is a score, not a finding.
5. Give no recommendation, advice or decision of any kind: no imaging, follow-up, biopsy, surgery, drugs, steroids, review or referral, and no words such as should, must, need to, consider, recommend, review or decide. Do not add disclaimers; the report has a fixed limitations section.
6. Do not describe scores with probability words such as likely, unlikely, probable, high risk, low risk, reassuring or concerning. Place a score only by copying its statement (above or below its cohort median).
7. Do not use the words confidence, reliable, reliability, accuracy or performance, except that an AUC may be copied from card.tier_statement when the tier is tested.
8. Copy these fixed phrases exactly and cite their keys: the tier phrase at the start of card.tier_statement ("tested", "few cases" or "not tested"); the conformal set phrase ("both outcomes", "progression only", "no progression only"); the agreement wording of pathways.agreement_statement ("agree" or "disagree").
9. Call volumes indicative and not a RANO assessment. Use British spelling (tumour, favour, colour).

Style: every sentence starts with a capital letter and ends with a full stop; complete sentences of 10 to 30 words, plain words, no lists, no headings, no underscores. Keep the whole text under 260 words. Do not repeat a fact. The flag sentences (j) are required: never leave them out.

Write these sentences, in this order, each tagged with its section:"""

TAIL = """
Output only JSON of the form {"sentences": [{"section": "scan" | "pathways" | "combined" | "trust", "text": "...", "fields": ["key", ...]}, ...]}."""


def _scan_lines(F: dict) -> list[str]:
    a = " a. The scan's timing: scan.phase."
    if "scan.rater_statement" in F:
        a = (" a. The scan's timing: scan.phase, and whether the rater recorded the scan as within 3 months after "
             "radiotherapy, from scan.rater_statement (cite it).")
    out = [a]
    if F.get("meas.available") == "yes":
        parts = ["enhancing tumour (meas.enhancing_cc)", "FLAIR hyperintensity (meas.flair_hyperintensity_cc)"]
        for k, name in (("meas.necrosis_cc", "necrosis"), ("meas.cavity_cc", "resection cavity"),
                        ("meas.necrosis_and_cavity_cc", "necrosis with cavity")):
            if k in F:
                parts.append(f"{name} ({k})")
        out.append(' b. The volumes, said to be from the automatic segmentation and "indicative, not a RANO '
                   'assessment" (cite meas.label): ' + ", ".join(parts[:-1]) + " and " + parts[-1] + ".")
    else:
        out.append(" b. One sentence that no segmentation volumes are available for this scan (cite meas.available).")
    if F.get("scan.previous_available") == "yes":
        ch = [k for k in ("meas.enhancing_change_since_previous_statement",
                          "meas.flair_hyperintensity_change_since_previous_statement",
                          "meas.enhancing_change_since_earlier_minimum_statement") if k in F]
        out.append(" c. Copy the change statements (" + ", ".join(ch) + ")." if ch else
                   " c. Say that the previous scan has no volumes to compare with (cite scan.previous_available).")
    else:
        out.append(" c. Say that there is no previous scan to compare with (cite scan.previous_available).")
    return out


def system_prompt(F: dict) -> str:
    lines = [HEAD, 'SCAN (section "scan"), two or three sentences:', *_scan_lines(F),
             'PATHWAYS (section "pathways"), three sentences:',
             " d. One sentence on the timeline pathway: what it is based on (pathway.timeline.based_on, shortened) "
             "and pathway.timeline.statement.",
             " e. One sentence on the image pathway: what it is based on (pathway.images.based_on, shortened) and "
             "pathway.images.statement.",
             " f. pathways.agreement_statement.",
             'COMBINED (section "combined"), two sentences:',
             " g. The combined score: pathway.combined.based_on and pathway.combined.statement; then, in a separate "
             "sentence, pathways.score_meaning.",
             " h. conformal.combined.80.statement.",
             'TRUST (section "trust"), two to four sentences:']
    i = " i. The reliability card in plain words: the situation (card.situation) and card.tier_statement, keeping all its numbers."
    if "card.agreement_statement" in F:
        i += " Copy card.agreement_statement unchanged in its own sentence or leave it out; never shorten it."
    lines.append(i)
    lines.append(' j. Each active flag: one sentence per flag whose flags.<name>.active is true, of the form "The '
                 '<flags.<name>.name> flag is raised: <flags.<name>.reason>." with the reason copied in full (cite '
                 "both keys). If flags.any_active is false, one sentence that no flag is raised (cite flags.statement). "
                 "Never describe an inactive flag as raised.")
    return "\n".join(lines) + "\n" + TAIL


def grounded_v3_1(F: dict) -> list[dict]:
    return [{"role": "system", "content": system_prompt(F)},
            {"role": "user", "content": "FACTS:\n" + json.dumps(F, indent=1, ensure_ascii=False)}]
