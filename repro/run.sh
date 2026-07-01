#!/bin/bash
cd "$(dirname "$0")"
GOAL=$(cat GOAL.txt)
echo "START $(date -Is)" > run.log
claude -p "/goal $GOAL" --model opus \
  --allowedTools "Bash,Read,Write,Edit,MultiEdit,Glob,Grep,WebFetch,WebSearch,Task,TodoWrite" \
  --output-format stream-json --verbose >> run.log 2>&1
echo "EXIT:$? $(date -Is)" >> run.log
