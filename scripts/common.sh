# Shared setup for the scripts in this folder. Source it; do not run it.
#
# Environment overrides (all optional):
#   PRISM_DATA, PRISM_MU, PRISM_LUMIERE, PRISM_OUTPUTS, PRISM_WORKERS   see prism/config.py
#   BLAS_THREADS   threads per process for numpy/scikit-learn (default 4; stages parallelise over processes)

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"

export PATH="$HOME/.local/bin:$PATH"   # where the uv installer puts uv
unset VIRTUAL_ENV                       # an activated venv from another project confuses uv

export PRISM_DATA="${PRISM_DATA:-$REPO/data}"
export PRISM_MU="${PRISM_MU:-$PRISM_DATA/mu-glioma-post}"
export PRISM_LUMIERE="${PRISM_LUMIERE:-$PRISM_DATA/lumiere}"
export PRISM_OUTPUTS="${PRISM_OUTPUTS:-$REPO/outputs}"
REFERENCE_FEATURES="$PRISM_DATA/mu-reference-processed/postoperative_progression_surveillance/features"

BLAS_THREADS="${BLAS_THREADS:-4}"
export OMP_NUM_THREADS="$BLAS_THREADS" OPENBLAS_NUM_THREADS="$BLAS_THREADS" MKL_NUM_THREADS="$BLAS_THREADS"

LOG_DIR="$PRISM_OUTPUTS/logs"
mkdir -p "$LOG_DIR"

die() { echo "ERROR: $*" >&2; exit 1; }

# Run inside the locked uv environment without re-resolving it. `python -m prism` from the repository root works
# whether or not the package's console script is installed in the environment (cwd and PYTHONPATH both = $REPO).
export PYTHONPATH="$REPO${PYTHONPATH:+:$PYTHONPATH}"
prism() { (cd "$REPO" && uv run --frozen --no-sync --project "$REPO" python -m prism "$@"); }
py() { (cd "$REPO" && uv run --frozen --no-sync --project "$REPO" python "$@"); }

VENV="${UV_PROJECT_ENVIRONMENT:-$REPO/.venv}"

require_env() {
  command -v uv >/dev/null || die "uv not found - run scripts/setup_env.sh first"
  [[ -x "$VENV/bin/python" ]] || die "no environment at $VENV - run scripts/setup_env.sh first"
}

require_file() {  # require_file <path> <what it is / how to get it>
  [[ -e "$1" ]] || die "missing $1 ($2). See README.md, section Data."
}

require_mu() {
  require_file "$PRISM_MU/MU-Glioma-Post" "MU-Glioma-Post images from TCIA"
  require_file "$PRISM_MU/MU-Glioma-Post_ClinicalData-July2025.xlsx" "MU-Glioma-Post clinical workbook"
}

require_lumiere() {
  require_file "$PRISM_LUMIERE/LUMIERE-ExpertRating-v202211.csv" "LUMIERE expert ratings from figshare"
  require_file "$PRISM_LUMIERE/LUMIERE-Demographics_Pathology.csv" "LUMIERE demographics from figshare"
}

require_reference() {
  require_file "$REFERENCE_FEATURES" "original PRISM radiomics; run scripts/01_prepare_data.sh --reference"
}

require_output() {  # require_output <file under $PRISM_OUTPUTS> <script that makes it>
  [[ -e "$PRISM_OUTPUTS/$1" ]] || die "missing outputs/$1 - run $2 first"
}

# run_step <log name> <command...>: run, show output, keep a log, report the time taken.
run_step() {
  local name="$1"; shift
  local log="$LOG_DIR/$name.log" start=$SECONDS
  echo "== $name  ($(date '+%F %T'), log: ${log#$REPO/})"
  if "$@" 2>&1 | tee "$log"; then
    echo "== $name done in $((SECONDS - start)) s"
  else
    die "$name failed after $((SECONDS - start)) s - see ${log#$REPO/}"
  fi
}

# Populations for c2/c3: arguments if given, else both.
populations() { if (($#)); then echo "$@"; else echo "grade4 all_glioma"; fi; }
