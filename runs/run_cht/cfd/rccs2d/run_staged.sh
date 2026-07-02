#!/bin/bash
cd /case
rm -rf 0 processor* [1-9]* && cp -r 0.orig 0
rm -f 0/T.stage1
# STAGE 1: fixed-T walls, establish flow + radiation (400 iters)
cp 0.orig/T.stage1 0/T
foamDictionary -entry endTime -set 400 system/controlDict >/dev/null 2>&1
echo "=== STAGE 1 (fixed-T init) ==="
buoyantSimpleFoam > log.stage1 2>&1
echo "stage1 exit $? ; last time:"; grep -E "^Time = " log.stage1 | tail -1
# STAGE 2: switch to flux(plate)+coefficient(riser) BCs -> temperatures become OUTPUT
LAST=$(foamListTimes -latestTime 2>/dev/null | tail -1)
echo "restart from t=$LAST"
cp 0.orig/T $LAST/T          # real flux/coefficient BC, keep internal field from stage1
foamDictionary -entry startFrom -set latestTime system/controlDict >/dev/null 2>&1
foamDictionary -entry endTime -set 3000 system/controlDict >/dev/null 2>&1
foamDictionary -entry radiation.solverFreq -set 2 constant/radiationProperties >/dev/null 2>&1 || true
echo "=== STAGE 2 (flux BC, T solved) ==="
buoyantSimpleFoam > log.stage2 2>&1
echo "stage2 exit $?"
