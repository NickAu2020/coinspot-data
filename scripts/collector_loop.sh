#!/bin/bash
# Backup trigger: every ~60s check last snapshot commit age on origin; if >14 min, dispatch workflow.
# If dispatch fails, run snapshot locally and push. Clock-aware: catches up after sleep.
cd /workspace/coinspot-data
LOG=/workspace/coinspot-data/.collector.log
last_dispatch=0
while true; do
  now=$(date +%s)
  git fetch -q origin main 2>>$LOG
  last=$(git log -1 --format=%ct origin/main 2>/dev/null || echo 0)
  age=$(( now - last ))
  if [ $age -gt 840 ] && [ $(( now - last_dispatch )) -gt 600 ]; then
    if gh workflow run snapshot.yml >>$LOG 2>&1; then
      echo "$(date -Is) age=${age}s dispatched" >>$LOG
    else
      echo "$(date -Is) dispatch failed, local run" >>$LOG
      git pull -q --rebase origin main && python3 scripts/snapshot.py && python3 scripts/accel.py && \
      git add data && git commit -qm "snapshot local $(date -u +%FT%TZ)" && git push -q origin HEAD:main >>$LOG 2>&1
    fi
    last_dispatch=$now
  fi
  sleep 60
done
