# Locked text

Passages the author has approved. They are not changed without the author's explicit approval, not even for
polish. If a later result or a number check makes a locked passage wrong, flag it to the author and propose the
smallest edit; do not rewrite it.

## Abstract (locked 2026-10-24; 149 words)

Models that predict glioma progression from surveillance MRI can score well without learning much about the tumour.
We built PRISM, which keeps image and treatment-timeline evidence apart and records what each contributed at every
scan. On MU-Glioma-Post, PRISM's first evaluation reached an AUC of 0.80 on one test split, but a model with no
images did better on the same split, and over 500 splits the result averaged 0.72. At the scan where progression
was called, clinical and timeline data alone reached 0.82. Each assumption built into the image model raised its
AUC, from 0.66 to 0.81, but only by encoding the timeline; within a phase of care, images held at about 0.68, as much
as the timeline. PRISM therefore shows both kinds of evidence side by side for every scan, and flags the weeks after
radiotherapy, when pseudoprogression is common and neither has been shown to be reliable.

Sources for each number: [STORY.md](STORY.md) (0.80, 0.72: step 1; 0.82: step 2; 0.66, 0.81, 0.68: step 3).
The ladder (0.66, 0.81, 0.68) is exploratory and must be labelled so in the Methods.
