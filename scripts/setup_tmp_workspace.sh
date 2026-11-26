#!/usr/bin/env bash
# Fast working copy on local /tmp (the shared /project drive is slow when full): a clone from GitHub, a small
# Python env pinned to the versions of the main .venv, and links to data/ and outputs/ on the shared drive.
# Work and commit here; push to GitHub; `git pull` in the /project copy keeps only final versions there.
# /tmp is wiped when the machine resets, so push often. Rerun this script to rebuild.
set -euo pipefail
NFS=/project/community/sbandred/prism-gbm-surveillance
W=/tmp/$USER-prism
BRANCH="${1:-$(git -C "$NFS" rev-parse --abbrev-ref HEAD)}"
mkdir -p "$W"; cd "$W"
export UV_CACHE_DIR="$W/uv-cache"
[ -x venv/bin/python ] || uv venv -q --python 3.11 venv
uv pip install -q --python venv/bin/python matplotlib==3.10.8 numpy==2.2.6 nibabel==5.4.2 pandas==2.3.3 \
  scipy openpyxl scikit-learn pillow
[ -d repo ] || git clone -q --branch "$BRANCH" "$(git -C "$NFS" remote get-url origin)" repo
cd repo
ln -sfn "$NFS/data" data; ln -sfn "$NFS/outputs" outputs
grep -qx data .git/info/exclude || printf 'data\noutputs\n' >> .git/info/exclude
git config user.name "$(git -C "$NFS" config user.name)"; git config user.email "$(git -C "$NFS" config user.email)"
echo "ready: cd $W/repo; python: $W/venv/bin/python; paper: bash paper/build.sh"
