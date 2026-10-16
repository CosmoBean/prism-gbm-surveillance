"""Text style metrics and the public reference-report profile (no model, no randomness).

Used by prism/analyses/report_usefulness.py to (i) describe public brain-MRI report corpora (section structure,
length, reading level, hedging and post-treatment vocabulary) and (ii) put the same numbers on PRISM report text.

Reading level: Flesch-Kincaid grade, FKGL = 0.39 * words/sentence + 11.8 * syllables/word - 15.59, with a vowel-group
syllable counter (no dictionary; numbers count as one word of one syllable). Approximate, used only for comparisons
made with the same counter. Reading time: words / 200 per minute (a plain fixed rate, not a measured clinician rate).

The lexicons are fixed lists written before counting (common radiology-report hedging expressions and the structured
follow-up reporting vocabulary of BT-RADS / RANO); the corpora only supply their frequencies.
"""

from __future__ import annotations

import re
from collections import Counter

WPM = 200
_WORD = re.compile(r"[A-Za-z][A-Za-z'\-]*|\d+(?:\.\d+)?")


def sentences(text: str) -> list[str]:
    t = re.sub(r"\s+", " ", text.strip())
    t = re.sub(r"\b(e\.g|i\.e|approx|vs|Fig|cf)\.", lambda m: m.group(1) + "<dot>", t)
    out = [s.replace("<dot>", ".").strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z(\[])", t)]
    return [s for s in out if _WORD.search(s)]


def words(text: str) -> list[str]:
    return _WORD.findall(text)


def syllables(w: str) -> int:
    if w[0].isdigit():
        return 1
    w = w.lower().strip("'-")
    if len(w) <= 3:
        return 1
    w = re.sub(r"(?:[^laeiouy]es|ed|[^laeiouy]e)$", "", w)
    w = re.sub(r"^y", "", w)
    return max(1, len(re.findall(r"[aeiouy]{1,2}", w)))


def fkgl(text: str) -> float:
    ss, ws = sentences(text), words(text)
    if not ss or not ws:
        return float("nan")
    return 0.39 * len(ws) / len(ss) + 11.8 * sum(map(syllables, ws)) / len(ws) - 15.59


# Hedging / uncertainty expressions common in radiology reports (fixed list, written before counting).
HEDGES = {
    "may/might/could": r"\b(may|might|could)\b",
    "possible/possibly": r"\bpossib(le|ly|ility)\b",
    "probable/probably/likely": r"\b(probabl[ey]|likely)\b",
    "unlikely": r"\bunlikely\b",
    "suggest(ive)": r"\bsuggest(s|ed|ive|ing)?\b",
    "consistent with / compatible with": r"\b(consistent|compatible) with\b",
    "cannot be excluded / ruled out": r"\b(cannot|can not|could not) be (excluded|ruled out)\b",
    "considered / consideration": r"\bconsider(ed|ation)\b",
    "concerning / suspicious / worrisome": r"\b(concerning|suspicious|worrisome)\b",
    "indeterminate / equivocal / uncertain": r"\b(indeterminate|equivocal|uncertain|unclear)\b",
    "favour / favor": r"\bfavou?r(s|ed|ing)?\b",
    "approximately / about / estimated": r"\b(approximately|about|estimated?)\b",
    "appears / seems": r"\b(appears?|seems?)\b",
    "correlate / correlation": r"\bcorrelat(e|ion)\b",
}
# Post-treatment change vocabulary (BT-RADS / RANO follow-up wording); counted, not prescribed.
POST_TREATMENT = {
    "enhancement": r"\benhanc(ement|ing)\b", "FLAIR / T2 signal": r"\b(FLAIR|T2)[- ]?(hyperintens\w*|signal)\b",
    "edema / oedema": r"\bo?edema\b", "resection cavity": r"\b(resection|surgical) cavity\b",
    "post-treatment / treatment-related": r"\b(post-?treatment|treatment[- ]related)\b",
    "pseudoprogression": r"\bpseudo-?progression\b", "radiation necrosis": r"\bradiation necrosis\b",
    "recurrence": r"\brecurren(ce|t)\b", "progression": r"(?<!pseudo)(?<!pseudo-)\bprogress(ion|ive|ed)?\b",
    "stable / unchanged": r"\b(stable|unchanged|no (significant )?change)\b",
    "interval change / increase / decrease": r"\b(interval|increas\w*|decreas\w*|enlarg\w*|reduc\w*)\b",
    "compared with prior / previous": r"\b(compared (with|to)|prior|previous)\b",
    "mass effect / midline shift": r"\b(mass effect|midline)\b", "follow-up": r"\bfollow[- ]?up\b",
    "perfusion / diffusion": r"\b(perfusion|diffusion|rCBV|ADC)\b",
}
SECTION_HEADS = r"(?im)^\s*(clinical (history|information|indication)|indication|history|technique|comparison|findings|" \
                r"impression|conclusion|recommendation)s?\s*:"


def lexicon_counts(texts: list[str], lex: dict) -> dict:
    """Per lexicon entry: share of sentences containing it."""
    ss = [s for t in texts for s in sentences(t)]
    n = max(len(ss), 1)
    return {k: sum(bool(re.search(p, s, re.I)) for s in ss) / n for k, p in lex.items()}


def profile(texts: list[str]) -> dict:
    """Length, reading level and lexicon rates of a list of report texts."""
    import numpy as np
    w = np.array([len(words(t)) for t in texts], float)
    s = np.array([len(sentences(t)) for t in texts], float)
    g = np.array([fkgl(t) for t in texts], float)
    q = lambda a: {"median": float(np.nanmedian(a)), "q1": float(np.nanpercentile(a, 25)),
                   "q3": float(np.nanpercentile(a, 75))}
    return {"n": len(texts), "words": q(w), "sentences": q(s), "words_per_sentence": q(w / np.maximum(s, 1)),
            "fkgl": q(g), "reading_time_s": q(60 * w / WPM),
            "hedge_sentence_share": lexicon_counts(texts, HEDGES),
            "post_treatment_sentence_share": lexicon_counts(texts, POST_TREATMENT)}


def top_bigrams(texts: list[str], heads: tuple = ("enhancement", "enhancing", "change", "changes", "edema", "signal",
                                                  "cavity", "progression", "necrosis", "lesion"), k: int = 40) -> list:
    """Most frequent bigrams ending in one of `heads` (data-driven vocabulary for describing change)."""
    c = Counter()
    for t in texts:
        ws = [x.lower() for x in words(t)]
        c.update(f"{a} {b}" for a, b in zip(ws, ws[1:]) if b in heads and a.isalpha() and len(a) > 2)
    return c.most_common(k)
