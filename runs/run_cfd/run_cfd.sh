#!/bin/bash
set -e
cd /case
blockMesh > log.blockMesh 2>&1
faceAgglomerate -dict constant/viewFactorsDict > log.faceAgglomerate 2>&1
viewFactorsGen > log.viewFactorsGen 2>&1
buoyantSimpleFoam > log.buoyantSimpleFoam 2>&1
echo "=== DONE ==="
tail -3 log.buoyantSimpleFoam
