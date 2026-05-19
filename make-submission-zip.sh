#!/bin/bash
# Create a zip file containing only the source files needed for submission.
set -e

OUT="submission.zip"
rm -f "$OUT"

zip "$OUT" \
  main.tex \
  references.bib \
  main.bbl \
  svproc.cls \
  splncs03.bst \
  aliascnt.sty \
  remreset.sty \
  figures/democracy-proposal-state-machine.pdf \
  figures/fig-ceremony-participation.pdf \
  figures/fig-voting-power.pdf \
  figures/fig-aqb-curve.pdf \
  figures/fig-treasury-timeline.pdf

echo "Created $OUT ($(du -h "$OUT" | cut -f1))"
