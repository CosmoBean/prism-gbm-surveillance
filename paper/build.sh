#!/usr/bin/env bash
# Build main.pdf and supplement.pdf with tectonic (XeTeX + BibTeX). Fails loudly on errors,
# undefined references/citations and overfull boxes wider than 10pt; prints page counts.
set -euo pipefail
cd "$(dirname "$0")"

TECTONIC="${TECTONIC:-$HOME/.local/opt/texenv/bin/tectonic}"
command -v "$TECTONIC" >/dev/null 2>&1 || { echo "ERROR: tectonic not found at $TECTONIC" >&2; exit 1; }
mkdir -p build

status=0
for doc in main supplement; do
  echo "==> building $doc.tex"
  log="build/$doc.tectonic.log"
  if ! "$TECTONIC" -X compile --keep-logs --keep-intermediates --outdir build "$doc.tex" >"$log" 2>&1; then
    cat "$log" >&2
    echo "ERROR: tectonic failed on $doc.tex (see $log)" >&2
    exit 1
  fi
  cp "build/$doc.pdf" "$doc.pdf"

  texlog="build/$doc.log"
  if grep -nE "undefined (references|citations)|Citation .* undefined|Reference .* undefined" "$texlog"; then
    echo "ERROR: undefined references or citations in $doc" >&2; status=1
  fi
  # overfull boxes wider than 10pt
  if awk '/^Overfull \\hbox \(/ { w=$3; gsub(/[(pt]/,"",w); if (w+0 > 10) { print; bad=1 } } END { exit !bad }' "$texlog"; then
    echo "ERROR: overfull boxes > 10pt in $doc" >&2; status=1
  fi
  if grep -qE "error message|^I was expecting|^I'm skipping" "build/$doc.blg" 2>/dev/null; then
    cat "build/$doc.blg" >&2; echo "ERROR: BibTeX errors in $doc" >&2; status=1
  fi
  if grep -q "^Warning--" "build/$doc.blg" 2>/dev/null; then
    echo "BibTeX warnings ($doc):"; grep "^Warning--" "build/$doc.blg" | sed 's/^/  /'
  fi
  pages=$(grep -aoE "Output written on [^ ]+ \(([0-9]+) page" "$texlog" | grep -oE "[0-9]+ page" | grep -oE "[0-9]+" || true)
  if [ -z "$pages" ]; then
    pages=$(grep -ac "/Type */Page[^s]" "$doc.pdf" || true)
  fi
  echo "    $doc.pdf: $pages pages"
done
exit $status
