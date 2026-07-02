#!/bin/bash
cd /root/bench/cht/output/cfd/rccs2d
run_stage () {
  local q=$1 iters=$2 qrel=$3
  local LAST=$(ls -d [0-9]*/ | tr -d / | sort -n | tail -1)
  local ENDT=$((LAST + iters))
  sed -i -E "s/^([[:space:]]*)q[[:space:]]+(uniform|constant)[[:space:]]+[0-9.eE+-]+;/\1q uniform ${q};/" $LAST/T
  sed -i -E "s/qrRelaxation[[:space:]]+[0-9.]+/qrRelaxation ${qrel}/g" $LAST/T
  sed -i "s/^endTime .*/endTime         ${ENDT};/" system/controlDict
  docker run --rm -v "$PWD":/case opencfd/openfoam-default:2312 bash -c "cd /case && buoyantSimpleFoam > log.r4_${q} 2>&1"
  local NEW=$(ls -d [0-9]*/ | tr -d / | sort -n | tail -1)
  local Tp=$(strings log.r4_${q} | grep 'areaAverage(plate) of T =' | tail -1 | grep -oE '[0-9.]+$')
  local Tr=$(strings log.r4_${q} | grep 'areaAverage(riser) of T =' | tail -1 | grep -oE '[0-9.]+$')
  local NEG=$(strings log.r4_${q} | grep -c Negative)
  echo "q=${q} t=${NEW} Tplate=${Tp}K Triser=${Tr}K neg=${NEG}"
}
for q in 4500 4700 4900 5100 5300 5501; do run_stage $q 350 0.06; done
