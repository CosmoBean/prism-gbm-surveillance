"""Deterministic parts of the v3 report (no LLM), rendered from facts_v3, plus the LLM's four prose sections.

Layout: header; segmentation figure (attached here, never shown to the LLM); for each section the LLM prose followed
by its deterministic table (1 what the scan shows, 2 the two pathways, 3 the combined score, 4 how much to trust
this here); flags; standing limitations. Markdown and a self-contained HTML page (figure embedded as base64).
"""

from __future__ import annotations

import base64
import html
from pathlib import Path

from prism.report.facts_v3 import FLAGS, PATHWAYS

TITLES = {"scan": "1. What the scan shows", "pathways": "2. The two pathways",
          "combined": "3. The combined score", "trust": "4. How much to trust this here"}
LIMITATIONS = (
    "PRISM's scores rank scans for whether this is the scan at which progression is called. They are not a "
    "diagnosis and this report gives no recommendation or decision. The models were developed at one institution "
    "(MU-Glioma-Post, scores out-of-fold); external cohorts use models locked on MU-Glioma-Post. Volumes come from an "
    "automatic segmentation and are indicative, not a RANO assessment. The reliability card is a lookup of results "
    "already measured, defined after those results were seen; few situations have enough scans to be tested. "
    "Conformal sets are calibrated on MU-Glioma-Post. No clinician has evaluated this report.")


def _v(F, k, fmt="{}"):
    return "–" if k not in F else fmt.format(F[k])


def tables(F: dict) -> dict:
    t = {}
    rows = [("Timing", F["scan.phase"] + (f"; {F['scan.days_since_previous']} days after the previous scan"
                                          if "scan.days_since_previous" in F else "; no previous scan")
             + (f"; rater: within 3 months after RT: {F['scan.rater_within_3_months_after_rt']}"
                if "scan.rater_within_3_months_after_rt" in F else ""))]
    if F["meas.available"] == "yes":
        for k, n in (("enhancing", "Enhancing tumour"), ("flair_hyperintensity", "FLAIR hyperintensity")):
            prev = (f"{F[f'meas.{k}_change_since_previous_cc']:+.1f} cc"
                    + (f" ({F[f'meas.{k}_change_since_previous_percent']:+d}%)"
                       if f"meas.{k}_change_since_previous_percent" in F else "")) \
                if f"meas.{k}_change_since_previous_cc" in F else "no previous scan"
            rows.append((n, f"{F[f'meas.{k}_cc']:.1f} cc; vs previous: {prev}"))
        if "meas.enhancing_change_since_earlier_minimum_cc" in F:
            rows.append(("Enhancing vs smallest earlier", f"{F['meas.enhancing_earlier_minimum_cc']:.1f} cc; change "
                         f"{F['meas.enhancing_change_since_earlier_minimum_cc']:+.1f} cc"
                         + (f" ({F['meas.enhancing_change_since_earlier_minimum_percent']:+d}%)"
                            if "meas.enhancing_change_since_earlier_minimum_percent" in F else "")))
        if "meas.necrosis_and_cavity_cc" in F:
            rows.append(("Necrosis and cavity", f"{F['meas.necrosis_and_cavity_cc']:.1f} cc"))
        else:
            rows += [("Necrosis", _v(F, "meas.necrosis_cc", "{:.1f} cc")),
                     ("Resection cavity", _v(F, "meas.cavity_cc", "{:.1f} cc"))]
        rows.append(("Note", F["meas.label"]))
    else:
        rows.append(("Volumes", "no usable segmentation"))
    t["scan"] = (["Item", "Value"], rows)
    t["pathways"] = (["Pathway", "Based on", "Score", "Cohort median", "Side", "80% set", "90% set"],
                     [(F[f"pathway.{p}.name"], F[f"pathway.{p}.based_on"], f"{F[f'pathway.{p}.score']:.2f}",
                       _v(F, f"pathway.{p}.cohort_median", "{:.2f}"), _v(F, f"pathway.{p}.side"),
                       _v(F, f"conformal.{p}.80.set"), _v(F, f"conformal.{p}.90.set")) for p in PATHWAYS])
    t["combined"] = (["Item", "Value"], [("Agreement", F["pathways.agreement_statement"]),
                                         ("What a score is", F["pathways.score_meaning"]),
                                         ("Conformal method", F["conformal.method"])])
    trows = [("Situation", F["card.situation"]), ("Tier", F["card.tier_statement"]), ("Tier rule", F["card.tier_rule"])]
    if "card.agreement_statement" in F:
        trows.append(("Agreement, measured", F["card.agreement_statement"]))
    trows.append(("Card", F["card.status"]))
    for f in FLAGS:
        trows.append((f"Flag: {F[f'flags.{f}.name']}", "RAISED: " + F[f"flags.{f}.reason"] if F[f"flags.{f}.active"]
                      else "not raised"))
    t["trust"] = (["Item", "Value"], trows)
    return t


def render_md(scan_label: str, F: dict, prose: dict | None, figure: str | None = None) -> str:
    L = [f"# PRISM report (v3): {scan_label}", "", f"Detection at the scan; cohort: {F['system.cohort']}.", ""]
    if figure:
        L += [f"![Segmentation]({figure})", ""]
    for s, (head, rows) in tables(F).items():
        L += [f"## {TITLES[s]}", "", " ".join((prose or {}).get(s) or ["(not generated)"]), "",
              "| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
        L += ["| " + " | ".join(str(x) for x in r) + " |" for r in rows]
        L.append("")
    L += ["## Limitations", "", LIMITATIONS, ""]
    return "\n".join(L)


CSS = """:root{--bg:#fff;--ink:#1f2933;--muted:#52606d;--line:#d9dee4;--flag:#8a3b12}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#15191d;--ink:#e6e9ec;--muted:#a8b0b8;--line:#39424b;--flag:#f0a46e}}
:root[data-theme="dark"]{--bg:#15191d;--ink:#e6e9ec;--muted:#a8b0b8;--line:#39424b;--flag:#f0a46e}
body{background:var(--bg);color:var(--ink);font:15px/1.5 Georgia,serif;max-width:920px;margin:0 auto;padding:16px}
h1{font-size:1.35rem}h2{font-size:1.05rem;margin-top:1.6em;border-bottom:1px solid var(--line)}
p.prose{margin:.4em 0 .8em}table{border-collapse:collapse;width:100%;font:13px/1.4 system-ui,sans-serif}
td,th{border:1px solid var(--line);padding:4px 6px;vertical-align:top;text-align:left}.muted{color:var(--muted)}
.raised{color:var(--flag);font-weight:600}img{max-width:100%;height:auto}.wrap{overflow-x:auto}"""


def render_html(scan_label: str, F: dict, prose: dict | None, figure_path: str | Path | None = None) -> str:
    e = html.escape
    B = [f"<!doctype html><html lang='en-GB'><head><meta charset='utf-8'><meta name='viewport' "
         f"content='width=device-width,initial-scale=1'><title>PRISM report v3</title><style>{CSS}</style></head><body>",
         f"<h1>PRISM report (v3): {e(scan_label)}</h1>",
         f"<p class='muted'>Detection at the scan; cohort: {e(F['system.cohort'])}. The text below each heading is "
         "written by a local language model from the fields in the tables only; the model does not see the images.</p>"]
    if figure_path and Path(figure_path).exists():
        b64 = base64.b64encode(Path(figure_path).read_bytes()).decode()
        B.append(f"<figure><img alt='Segmentation of this scan' src='data:image/png;base64,{b64}'>"
                 "<figcaption class='muted'>Automatic segmentation (attached deterministically).</figcaption></figure>")
    else:
        B.append("<p class='muted'>Segmentation figure: not available.</p>")
    for s, (head, rows) in tables(F).items():
        B.append(f"<h2>{e(TITLES[s])}</h2><p class='prose'>{e(' '.join((prose or {}).get(s) or ['(not generated)']))}</p>")
        B.append("<div class='wrap'><table><tr>" + "".join(f"<th>{e(h)}</th>" for h in head) + "</tr>")
        for r in rows:
            B.append("<tr>" + "".join(f"<td class='{'raised' if str(x).startswith('RAISED') else ''}'>{e(str(x))}</td>"
                                      for x in r) + "</tr>")
        B.append("</table></div>")
    B.append(f"<h2>Limitations</h2><p class='muted'>{e(LIMITATIONS)}</p></body></html>")
    return "\n".join(B)
