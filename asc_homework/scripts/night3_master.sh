#!/usr/bin/env bash

set -u

cd /root/autodl-tmp/asc-selection/qibotn
source .venv/bin/activate

export CUDA_VISIBLE_DEVICES=""

LOG="asc_homework/logs/night3_steps.log"

echo "NIGHT3 START $(date)" | tee "$LOG"


echo "===== STEP 1 ORDER SWEEP =====" | tee -a "$LOG"

timeout 1h \
python asc_homework/scripts/order_sweep.py \
>> "$LOG" 2>&1

echo "ORDER EXIT=$?" | tee -a "$LOG"


echo "===== STEP 2 FINAL CONFIRMATION 1 =====" | tee -a "$LOG"

timeout 1h \
python asc_homework/scripts/final_combined_suite.py \
>> "$LOG" 2>&1

CONFIRM1_EXIT=$?

cp asc_homework/results/final_combined.csv \
   asc_homework/results/final_combined_confirm1.csv

echo "CONFIRM1 EXIT=$CONFIRM1_EXIT" | tee -a "$LOG"


echo "===== STEP 3 FINAL CONFIRMATION 2 =====" | tee -a "$LOG"

timeout 1h \
python asc_homework/scripts/final_combined_suite.py \
>> "$LOG" 2>&1

CONFIRM2_EXIT=$?

cp asc_homework/results/final_combined.csv \
   asc_homework/results/final_combined_confirm2.csv

echo "CONFIRM2 EXIT=$CONFIRM2_EXIT" | tee -a "$LOG"


echo "===== RESTORE NIGHT2 PRIMARY RESULT =====" | tee -a "$LOG"

cp asc_homework/results/final_combined_night2.csv \
   asc_homework/results/final_combined.csv


echo "===== STEP 4 FDU C++ BUILD PROBE =====" | tee -a "$LOG"

timeout 35m \
bash asc_homework/scripts/fdu_build_probe.sh \
>> "$LOG" 2>&1

echo "FDU BUILD PROBE EXIT=$?" | tee -a "$LOG"


echo "===== STEP 5 BACKUP =====" | tee -a "$LOG"

bash asc_homework/scripts/night_backup.sh \
>> "$LOG" 2>&1

echo "BACKUP EXIT=$?" | tee -a "$LOG"


echo "NIGHT3 COMPLETED $(date)" \
| tee asc_homework/logs/night3_done.txt \
| tee -a "$LOG"
