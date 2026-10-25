# Segmentation figure for report v3

**Written 2026-10-25.** This is the deterministic figure that each PRISM report v3 carries (SYSTEM_PLAN.md section 4).
The LLM never sees images. Code renders the figure from the images and masks, and the report code attaches it.
Nothing in it is learned or random.

- Code: `prism/report/seg_figure.py`. It provides `figure(scan_id, cohort) -> path` and a CLI.
- Tests: `tests/test_seg_figure.py`, with synthetic volumes.
- Output: `outputs/results/analyses/system/figures/<cohort>/<scan_id>.png` and `manifest.csv`. These are git-ignored
  under `/outputs/`, so no patient image goes into git or docs.

```
PYTHONPATH=. .venv/bin/python -m prism.report.seg_figure --examples            # 2 per cohort
PYTHONPATH=. .venv/bin/python -m prism.report.seg_figure --all --workers 6     # all system-population scans
PYTHONPATH=. .venv/bin/python -m prism.report.seg_figure --cohort mu --scan PatientID_0014_Timepoint_6
```

## What the figure shows

One PNG per scan, 1600 × 1040 px.

- **Header:**
  - the cohort;
  - the time of the scan: days from RT start (MU; UCSF in the tick labels where known) or the scan's position (`scan k`);
  - the segmentation source;
  - the orientation convention.

  The figure shows no identifier and no date. The scan id appears only in the file name.
- **Panel A (this scan):** the chosen axial slice twice.
  - On post-contrast T1, with outlines of ET, necrosis and cavity.
  - On FLAIR, with the SNFH / oedema outline.
  - If the scan has no ET, the panel says "no enhancing tumour segmented". If the mask is empty, it says
    "segmentation empty or missing".
- **Panel B (previous scan):** the same two images for the system's own previous scan, which is always strictly
  earlier:
  - MU: `prev_scan_id` from the detection cohort;
  - LUMIERE: `prev_scan_id` from `lumiere_detection()`;
  - UCSF: time1.

  The slice index is the same as in A. The panel title gives the brain-mask Dice between the two scans. With no
  previous scan, the panel says so.
- **Panel C (volumes):** ET, necrosis, cavity and SNFH volumes in cc over the patient's scans up to and including this
  scan, with this scan marked "THIS SCAN".
  - The table on the right gives this scan's and the previous scan's volumes, and doubles as the legend.
  - The history is the system's previous-scan pool:
    - MU: every timepoint in `measurements.csv`;
    - LUMIERE: rated, post-operative studies with a usable segmentation;
    - UCSF: time1 and time2.
  - x-axis by cohort:
    - MU: days from RT start, with the scan position when the RT start date is missing;
    - LUMIERE: scan position, because LUMIERE has no RT dates;
    - UCSF: scan 1 / scan 2, plus days from RT start where known.

## Conventions

- **Orientation:** every volume is reoriented to RAS (`nibabel.as_closest_canonical`). Images are shown in the
  **radiological convention**: the patient's right is on the viewer's left, anterior is at the top, and R / L are
  marked in the top corners. A unit test checks the display transform.
  - MU and UCSF files are stored LPS.
  - LUMIERE atlas files are stored LAS.
- **Spaces and co-registration:** every timepoint is stored in a common atlas space. The same slice index is therefore
  the same anatomy, up to each timepoint's own atlas registration. There is no direct longitudinal registration.
  - MU and UCSF: BraTS / SRI24, 240 × 240 × 155 at 1 mm.
  - LUMIERE: the DeepBraTumIA atlas, 182 × 218 × 182 at 1 mm.

  A previous scan counts as co-registered if the shapes match and the 3-D brain-mask Dice is ≥ 0.80. Otherwise
  panel B shows the previous scan's own chosen slice and labels it "NOT co-registered".
- **Labels:**
  - MU and UCSF use 1 NETC (necrosis), 2 SNFH, 3 ET, 4 RC (cavity).
  - LUMIERE DeepBraTumIA uses atlas `seg_mask.nii.gz` with 1 ET (enhancing core), 2 necrotic / non-enhancing, and
    3 oedema (SNFH). LUMIERE has no separate cavity label: label 2 includes the cavity, and the figure says so.
  - The LUMIERE mapping was checked in two ways. Voxel counts equal `measured_volumes_in_mm3.json` (8 studies).
    Intensity ratios to normal brain fit the labels (6 studies): label 1 is bright on CT1 (×1.3–1.7), label 2 is
    dark on CT1 (×0.4–0.9), and label 3 is bright on FLAIR (×1.3–1.6).
  - The LUMIERE paths are `Imaging/<patient>/<week>/DeepBraTumIA-segmentation/atlas/{segmentation/seg_mask,
    skull_strip/ct1_skull_strip, skull_strip/flair_skull_strip}.nii.gz`. They are read directly from
    `Imaging-v202211.zip`.
- **Colours:** Okabe-Ito, which is colour-blind safe.
  - ET: orange `#E69F00`, solid line, circle marker.
  - Necrosis: reddish purple `#CC79A7`, dashed line, square marker.
  - Cavity: sky blue `#56B4E9`, dotted line, triangle marker.
  - SNFH: bluish green `#009E73`, solid line, diamond marker.

  The palette validator passes with a deutan warning (necrosis vs SNFH ΔE 7.6). Line style and marker are the
  required secondary encoding.
- **Intensity window:** the 0.5–99.5 percentiles of brain voxels, per image. Images are cropped to the brain bounding
  box with a 6-voxel margin, and A and B share one crop when co-registered.

## How the slice is chosen (`choose_slice`)

The rules are tried in order (unit-tested):

1. the axial slice with the largest ET area;
2. without ET, the largest lesion area (ET + necrosis + SNFH);
3. if only a cavity is labelled, the largest cavity area;
4. with no label at all, the largest brain cross-section.

Ties go to the lowest (most inferior) index. Panel A's subtitle states the slice index and the rule that was used.

## No later scans

`past_only(hist, scan_id)` keeps rows strictly earlier than the current scan, plus the current scan itself. It asserts
that:
- the history ends at the current scan;
- nothing in it is later;
- the order is monotonic;
- the current scan appears exactly once.

Same-day other scans are dropped. The previous scan must be in this history (asserted). `render` asserts the rule
again before drawing panel C. The unit tests cover out-of-order input, the first scan, a missing current scan and a
duplicated current scan.

## Counts and runtime

The run covered all 631 system-population scans with no errors. It took 227 s on 6 CPUs, about 2 s per figure per
CPU (3 s for UCSF).

| cohort | population | rendered | largest ET | no ET → lesion | no labels → brain | images not available | previous shown, same slice | brain Dice min / median |
|---|---|---|---|---|---|---|---|---|
| MU | grade-4 detection scans (235 of them in the intended use) | 313 | 295 | 18 | 0 | 0 | 187 | 0.85 / 0.97 |
| LUMIERE | detection scans (`lumiere_detection`) | 178 | 123 | 40 | 8 | 7 | 161 (+7 own slice, see below) | 0.86 / 0.96 |
| UCSF | grade-4 scan 2 | 140 | 119 | 21 | 0 | 0 | 140 | 0.95 / 0.98 |

In all 624 figures with images, the panel-C volumes of this scan equal the voxel counts of the mask shown (maximum
difference 0.0 cc), so the figure and the record agree.

## Failure cases found and how they are handled

1. **Duplicate LUMIERE ratings.** Three studies are rated twice (Patient-010 week-001, Patient-042 week-010,
   Patient-043 week-106). Panel C's history uses one row per study (the first), and the `past_only` duplicate
   assertion caught this.
2. **LUMIERE scans without atlas images (7).** These studies have no DeepBraTumIA output; for example, Patient-009
   week-026 has no FLAIR.
   - Panel A says "images not available".
   - Panel B shows the previous scan at its own chosen slice, labelled as such.
   - Panel C shows the history and says "no volumes for this scan".
3. **Empty or missing LUMIERE segmentation (8: Patient-043 × 5, Patient-023 × 2, Patient-030 × 1).**
   - The slice falls back to the largest brain section, and the panel says "segmentation empty or missing".
   - The volumes are n/a, matching the system, which treats an all-empty DeepBraTumIA mask as a failed
     segmentation (NaN).
4. **No ET (79 scans).** The slice is the largest lesion, and the panel says "no enhancing tumour segmented".
5. **The co-registration fallback never fired.** The lowest brain Dice was 0.85 (MU PatientID_0268 Timepoint_3), so
   every previous scan with images is shown at the same slice. The lowest pair reflects incomplete brain coverage
   in the current acquisition, not a registration failure, and is shown as acquired. The fallback rendering was
   checked once by forcing the threshold to 0.99 on one scan; that output went to scratch and was not kept.
6. **Image quality as acquired.** Some LUMIERE FLAIRs have thick slices or a limited field of view, so they look
   blurred or truncated after atlas resampling. Strongly enhancing lesions can saturate at the 99.5th-percentile
   window. Neither is altered.
7. **Layout issues fixed while checking the examples:**
   - the legend overlapped the panel titles;
   - the orientation letters overlapped posterior lesions (they are now in the top corners);
   - ET was hidden under the necrosis line at 0 cc (ET is now drawn last);
   - crowded or long histories had overlapping or clipped ticks (they are now rotated).

## Checks done

I read eight figures, and they were correct on four points:
- **Orientation:** radiological, with R / L marked.
- **Outlines:** ET outlines sit on enhancing rims, cavity outlines on the dark T1c cavity, and SNFH outlines on the
  FLAIR hyperintensity.
- **Slice:** the rule is stated, and the ET slice contains the largest ET section.
- **History:** panel C ends at "THIS SCAN", with no later scans.

The eight were:
- the six examples (`manifest_examples.csv`): MU PatientID_0014_Timepoint_6 and PatientID_0029_Timepoint_4 (no ET),
  LUMIERE Patient-029_week-223 (12-scan history) and Patient-002_week-021 (no ET), and UCSF 100004_time2 and
  100028_time2 (no ET);
- MU PatientID_0268_Timepoint_3 (lowest Dice);
- LUMIERE Patient-043_week-018 (empty segmentation, no previous scan).

The fallback renderings, a forced not-co-registered panel B and a scan without images (Patient-009_week-026), were also
read.

`PYTHONPATH=. .venv/bin/python -m unittest discover -s tests`: all 79 pass (6 new in test_seg_figure.py; the rest include concurrent report-v3 tests).
