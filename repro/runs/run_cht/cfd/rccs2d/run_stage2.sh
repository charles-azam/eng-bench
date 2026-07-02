#!/bin/bash
cd /case
LAST=$(ls -d [0-9]*/ 2>/dev/null | tr -d / | sort -n | tail -1)
echo "restart from t=$LAST"
cp 0.orig/T $LAST/T           # real flux(plate)+coefficient(riser) BCs; keep converged internal field
foamDictionary -entry startFrom -set latestTime system/controlDict >/dev/null
foamDictionary -entry endTime   -set 6000 system/controlDict >/dev/null
foamDictionary -entry radiation.solverFreq -set 2 constant/radiationProperties >/dev/null
echo "=== plate BC now: ==="; sed -n '/plate/,/}/p' $LAST/T | head -6
buoyantSimpleFoam > log.stage2 2>&1
echo "stage2 exit $?  final time: $(ls -d [0-9]*/ | tr -d / | sort -n | tail -1)"
