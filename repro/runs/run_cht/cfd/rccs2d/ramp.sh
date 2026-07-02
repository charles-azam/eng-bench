#!/bin/bash
cd /root/bench/cht/output/cfd/rccs2d
run_stage () {
  local q=$1 endt=$2
  local LAST=$(ls -d [0-9]*/ | tr -d / | sort -n | tail -1)
  sed -i "s/q uniform [0-9.]*;/q uniform ${q};/" $LAST/T
  sed -i "s/^endTime .*/endTime         ${endt};/" system/controlDict
  docker run --rm -v "$PWD":/case opencfd/openfoam-default:2312 bash -c "cd /case && buoyantSimpleFoam > log.ramp_${q} 2>&1"
  local NEW=$(ls -d [0-9]*/ | tr -d / | sort -n | tail -1)
  local Tp=$(strings log.ramp_${q} | grep 'areaAverage(plate) of T =' | tail -1)
  local Tr=$(strings log.ramp_${q} | grep 'areaAverage(riser) of T =' | tail -1)
  local NEG=$(strings log.ramp_${q} | grep -c Negative)
  echo "q=${q} endt=${endt} -> t=${NEW}  ${Tp}  ${Tr}  neg=${NEG}"
}
run_stage 2200 1700
run_stage 3300 2000
run_stage 4400 2300
run_stage 5501 2800
