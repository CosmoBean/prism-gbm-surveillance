#!/usr/bin/env bash
# Install uv (if needed) and create .venv with every package the pipeline needs, from uv.lock.
#
#   scripts/setup_env.sh              core pipeline (prism/)
#   scripts/setup_env.sh --legacy     also the archived code in legacy/ (torch, MONAI, LightGBM, SHAP, ...)
#   scripts/setup_env.sh --all        legacy + notebook extras
#
# Note: uv sync is exact - running without --legacy removes legacy packages from an existing .venv.

source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

extras=()
for arg in "$@"; do
  case "$arg" in
    --legacy) extras+=(--extra legacy) ;;
    --all) extras+=(--all-extras) ;;
    -h|--help) sed -n '2,9p' "$0"; exit 0 ;;
    *) die "unknown option $arg" ;;
  esac
done

if ! command -v uv >/dev/null; then
  echo "== installing uv into ~/.local/bin"
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi
echo "== $(uv --version)"

# Python version from .python-version (3.11); uv downloads it if the system has none.
uv python install "$(cat .python-version)"

echo "== syncing $VENV from uv.lock ${extras[*]:-}"
uv sync --frozen "${extras[@]}"

echo "== checking imports"
uv run --frozen --no-sync python - <<'EOF'
import numpy, pandas, sklearn, sksurv, nibabel, SimpleITK, radiomics, openpyxl, prism
print("numpy", numpy.__version__, "| pandas", pandas.__version__, "| scikit-learn", sklearn.__version__,
      "| scikit-survival", sksurv.__version__, "| pyradiomics", radiomics.__version__)
EOF
if ((${#extras[@]})); then
  uv run --frozen --no-sync python -c "import torch, monai, lightgbm, shap; print('torch', torch.__version__, '| cuda', torch.cuda.is_available())"
fi

echo "== unit tests"
uv run --frozen --no-sync python -m unittest discover -s tests

echo "== environment ready: $VENV"
