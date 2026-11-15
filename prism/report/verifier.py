"""Bound verifier (plan: docs/results/METHODS_PLAN.md, M3, commit 1363773): the frozen checker plus two binding rules.

The frozen checker (checker.py, blob 26d6637a) accepts a number if it equals a number in any cited field, and does
not read direction words. Two rules bind a claim to what it refers to. Both work on v3.1-vocabulary claims (v3.2
reports through facts_v3_2.back_claims) and on the clause: the text between , ; : and the word "and".
  V1 entity binding: a number in a clause that names an entity (enhancing; FLAIR or oedema; necrosis; cavity; the
     timeline, image or combined score) must equal a value of a cited field whose key names the nearest such entity.
  V2 direction binding: a direction word (larger, increased, grew, rose, higher; smaller, decreased, shrank, fell,
     lower) must agree with every cited direction source for the clause's entity (or all cited sources when the
     clause names none): a field whose text holds direction words of one kind, or a numeric change field by its sign.
     A direction word in a clause naming a volume entity with no cited direction source is unsupported.
Terms and windows were fixed before the evaluation reports were checked.
"""

from __future__ import annotations

import re

from prism.report import checker

ENTITIES = {  # entity: (text pattern, key tokens)
    "enhancing": (r"\benhancing\b", ("enhancing",)),
    "flair": (r"\bFLAIR\b|\boedema\b|\bedema\b", ("flair",)),
    "necrosis": (r"\bnecro\w*", ("necrosis",)),
    "cavity": (r"\bcavity\b", ("cavity",)),
    "timeline": (r"\btimeline\b", ("pathway.timeline",)),
    "image": (r"\bimage\b", ("pathway.images",)),
    "combined": (r"\bcombined\b", ("combined",)),
}
VOLUME = {"enhancing", "flair", "necrosis", "cavity"}
UP = r"\b(larger|increased|increase|grew|grown|rose|risen|higher)\b"
DOWN = r"\b(smaller|decreased|decrease|shrank|shrunk|fell|fallen|lower)\b(?![- ](third|tier))"
CLAUSE = re.compile(r"[,;:]|\band\b")


def clauses(text: str) -> list[str]:
    return [c for c in CLAUSE.split(text) if c.strip()]


def entity_at(clause: str, pos: int) -> str | None:
    best, dist = None, None
    for e, (pat, _) in ENTITIES.items():
        for m in re.finditer(pat, clause, re.I if e not in ("flair",) else 0):
            d = min(abs(m.start() - pos), abs(m.end() - pos))
            if dist is None or d < dist:
                best, dist = e, d
    return best


def _keys_for(e: str, cited: list[str]) -> list[str]:
    return [k for k in cited if any(t in k for t in ENTITIES[e][1])]


def direction_of(v, key: str) -> str | None:
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, (int, float)):
        if "change" not in key or v == 0:
            return None
        return "up" if v > 0 else "down"
    s = str(v)
    u, d = bool(re.search(UP, s, re.I)), bool(re.search(DOWN, s, re.I))
    return "up" if u and not d else "down" if d and not u else None


def bind_claim(claim: dict, F: dict) -> list[str]:
    cited = [k for k in claim.get("fields", []) if k in F]
    out = []
    for cl in clauses(claim.get("text", "")):
        t = checker.STRUCTURAL.sub(" ", cl.replace("−", "-"))
        # V1
        for m in checker.NUM.finditer(t):
            e = entity_at(t, m.start())
            if e is None:
                continue
            keys = _keys_for(e, cited)
            vals = [x for k in keys for x in checker._field_numbers(F[k])]
            pc = re.match(r"\s*(%|percent)", t[m.end():]) is not None
            if not checker.matches(m.group(0), vals, pc):
                out.append(f"V1 {m.group(0)} not a value of a cited {e} field")
        # V2
        for m in re.finditer(f"{UP}|{DOWN}", t, re.I):
            w = "up" if re.fullmatch(UP, m.group(0), re.I) else "down"
            e = entity_at(t, m.start())
            keys = _keys_for(e, cited) if e else cited
            src = {k: direction_of(F[k], k) for k in keys}
            src = {k: v for k, v in src.items() if v}
            if any(v != w for v in src.values()):
                out.append(f"V2 '{m.group(0)}' disagrees with {sorted(k for k, v in src.items() if v != w)}")
            elif not src and e in VOLUME:
                out.append(f"V2 '{m.group(0)}' for {e} with no cited direction source")
    return out


def verify(claims: list[dict] | None, F: dict, **kw) -> dict:
    """Frozen check (checker.check(claims, F, card=True)) plus V1 and V2. F: v3.1 facts."""
    r = checker.check(claims, F, card=True, **kw)
    bound = {i: v for i, c in enumerate(claims or []) if (v := bind_claim(c, F))}
    r = dict(r)
    r["bound"] = bound
    r["frozen_pass"] = r["pass"]
    r["pass"] = r["pass"] and not bound
    return r


def verify_v3_2(claims: list[dict] | None, rec: dict) -> dict:
    from prism.report.facts_v3_1 import facts_v3_1
    from prism.report.facts_v3_2 import back_claims
    F1 = facts_v3_1(rec)
    return verify(back_claims(claims, F1), F1)
