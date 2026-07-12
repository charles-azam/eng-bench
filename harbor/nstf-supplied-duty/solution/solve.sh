#!/bin/bash
# Oracle: write reference predictions derived from the held-out records, plus the
# calculation note they cite. Proves the verifier wiring end to end (reward ~ 1.0).
set -eu

mkdir -p /app/output

cp /solution/predictions.json /app/output/predictions.json

cat > /app/output/calculation_note.md <<'EOF'
# Oracle reference note

This workspace was produced by the task's oracle solution, not by an agent. The
predictions are the held-out measured values with narrow quantile bands, used to
verify the scoring pipeline end to end.
EOF

echo "oracle solution written to /app/output/"
