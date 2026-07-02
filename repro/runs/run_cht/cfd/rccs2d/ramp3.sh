#!/bin/bash
cd /root/bench/cht/output/cfd/rccs2d
run_stage () {
  local q=$1 endt=$2 qrel=$3
  local LAST=$(ls -d [0-9]*/ | tr -d / | sort -n | tail -1)
  sed -i -E "s/^([[:space:]]*)q[[:space:]]+(uniform|constant)[[:space:]]+[0-9.eE+-]+;/\1q uniform ${q};/" $LAST/T
  sed -i -E "s/qrRelaxation[[:space:]]+[0-9.]+/qrRelaxation ${qrel}/g" $LAST/T
  sed -i "s/^endTime .*/endTime         ${endt};/" system/controlDict
  docker run --rm -v "$PWD":/case opencfd/openfoam-default:2312 bash -c "cd /case && buoyantSimpleFoam > log.r3_${q} 2>&1"
  local NEW=$(ls -d [0-9]*/ | tr -d / | sort -n | tail -1)
  local Tp=$(strings log.r3_${q} | grep 'areaAverage(plate) of T =' | tail -1)
  local Tr=$(strings log.r3_${q} | grep 'areaAverage(riser) of T =' | tail -1)
  local NEG=$(strings log.r3_${q} | grep -c Negative)
  echo "q=${q} -> t=${NEW} ${Tp} ${Tr} neg=${NEG}"
}
run_stage 3300 3300 0.08
run_stage 3800 3600 0.08
run_stage 4300 3900 0.08
run_stage 4800 4200 0.08
run_stage 5200 4600 0.08
run_stage 5501 5200 0.1
