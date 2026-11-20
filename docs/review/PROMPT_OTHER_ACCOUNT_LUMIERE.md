# Task: segment 246 LUMIERE MRI studies with the BraTS 2024 first-place model on this session's 4 GPUs

You are helping another researcher's project. Their repository is
`/project/community/sbandred/prism-gbm-surveillance`. You can **read** it, but you must **not write anything inside
`/project/community/sbandred/`**. Their code is already written and tested; your job is only to run it here, on your
4 GPUs, and leave the outputs somewhere they can read. **Do not edit their code.** The deadline is tight: the maps
are needed by about 07:00 EST today, so start now and work efficiently.

## 1. Check the machine

1. Run `nvidia-smi`. You need **4 GPUs** on one node. If you are on a login node, run everything on your GPU
   allocation instead, e.g. with `srun --jobid=<your job> --overlap ...`.
2. Run `which enroot`; it must exist on the GPU node.
3. Run `df -h /tmp`. The node-local `/tmp` needs **at least 150 GB free**: four unpacked copies of a 32 GB container.
4. Set the local working folder for everything below:
   `LOCAL=/tmp/$USER/brats24 && mkdir -p $LOCAL`.

## 2. Python environment (about 5 minutes)

```bash
uv venv -p 3.11 $LOCAL/venv        # or: python3.11 -m venv $LOCAL/venv
VIRTUAL_ENV=$LOCAL/venv uv pip install numpy pandas nibabel scikit-learn openpyxl \
    torch --index-url https://download.pytorch.org/whl/cpu --extra-index-url https://pypi.org/simple
```
Torch is only imported, never used for inference here, so the CPU wheel is enough.

## 3. Unpack four copies of the container (about 10–15 minutes, run in parallel)

```bash
for k in 0 1 2 3; do
  ENROOT_DATA_PATH=$LOCAL/enroot/data ENROOT_CACHE_PATH=$LOCAL/enroot/cache \
    enroot create -n brats24_1_g$k /project/community/sbandred/containers/brats24_1.sqsh > $LOCAL/create_$k.log 2>&1 &
done; wait; ls $LOCAL/enroot/data      # expect brats24_1_g0 ... brats24_1_g3
```
Why four copies: enroot allows only one writable instance of an unpacked container at a time. The code runs one copy
per GPU, as `brats24_1_g<gpu>`.

## 4. Choose an output folder the researcher can read

The researcher's account (`sbandred`) must be able to read it. Pick a folder on shared storage that you own, e.g.
`/project/community/<your folder>/brats24_lumiere`, and make it readable:
`mkdir -p $OUT && chmod a+rx $OUT` (and every parent directory needs at least `a+x`).

## 5. Run (about 2 hours; detach it)

```bash
REPO=/project/community/sbandred/prism-gbm-surveillance
OUT=<the folder from step 4>
cd $REPO
PYTHONPATH=$REPO PYTHONDONTWRITEBYTECODE=1 PRISM_SKIP_UCSF=0 \
PRISM_ENROOT_DATA=$LOCAL/enroot/data PRISM_BRATS24_WORK=$LOCAL/work PRISM_BRATS24_OUT=$OUT \
setsid nohup $LOCAL/venv/bin/python -m prism.features.reseg_brats24 --cohort lumiere --gpus 4 \
    --tag other_account --ids-file $REPO/outputs/features/seg_brats24/ids_lumiere_other_account.txt --skip-done \
    > $LOCAL/run.log 2>&1 < /dev/null & disown
```

What it does:
- Stages the 246 studies (LUMIERE images reoriented to LPS) into `$LOCAL/work`.
- Runs one container per GPU. Each container's GPU index is passed in with `enroot start --env CUDA_VISIBLE_DEVICES`.
- Writes label maps to `$OUT/lumiere/<patient>/<week>.nii.gz` and a table, `$OUT/volumes_brats24_lumiere.csv`.

## 6. Check that it is running properly

- Within about 10 minutes, `nvidia-smi` should show **all four GPUs** busy, each with a process using about 1–6 GB.
  If only GPU 0 is busy, stop and report it.
- `grep -h "rootfs lock" $LOCAL/work/lumiere/other_account/gpu*/container.log` must print nothing.
- Progress: `grep -c "Running command" $LOCAL/work/lumiere/other_account/gpu0/container.log` counts sub-models done.
  There are 30 sub-models in total, each run over that GPU's ~62 studies.
- `tail $LOCAL/run.log`: at the end, each GPU prints `gpuK: N scans in S s`, then a Dice summary.

## 7. When it finishes

1. Check that there are 246 maps: `find $OUT/lumiere -name '*.nii.gz' | wc -l`. Also check that
   `$OUT/volumes_brats24_lumiere.csv` has 246 rows.
2. Make the outputs readable: `chmod -R a+rX $OUT`.
3. Report back:
   - the full path of `$OUT`;
   - the map count;
   - the four `gpuK: ... s` lines;
   - the Dice summary printed at the end;
   - any errors.

If a GPU fails partway, rerun the same command: `--skip-done` skips studies that already have a map.

## Rules

- **Read only:** write nothing under `/project/community/sbandred/`, and change no code or file there.
- **Fixed model:** do not change the model, its thresholds or the scan list. They are fixed in the researcher's
  pre-specified plan (`docs/results/SEGMENTER_BRATS24_PLAN.md`).
- **No analysis:** do not look at or report any clinical labels or model AUCs. This task is segmentation only.
