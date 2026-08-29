#!/usr/bin/env bash
set -u

cd /root/autodl-tmp/asc-selection/qibotn
source .venv/bin/activate

export CUDA_VISIBLE_DEVICES=""

MASTERLOG="asc_homework/logs/night2_steps.log"

echo "NIGHT2 START $(date)" | tee -a "$MASTERLOG"


echo "===== STEP 1 FINAL COMBINED =====" | tee -a "$MASTERLOG"

timeout 2h \
python asc_homework/scripts/final_combined_suite.py \
>> "$MASTERLOG" 2>&1

echo "FINAL COMBINED EXIT=$?" | tee -a "$MASTERLOG"


echo "===== STEP 2 ANALYSIS =====" | tee -a "$MASTERLOG"

python asc_homework/scripts/analyze_results.py \
>> "$MASTERLOG" 2>&1

echo "ANALYSIS EXIT=$?" | tee -a "$MASTERLOG"


echo "===== STEP 3 FDU REFERENCE =====" | tee -a "$MASTERLOG"

timeout 30m \
bash asc_homework/scripts/fetch_fdu_reference.sh \
>> "$MASTERLOG" 2>&1

echo "FDU FETCH EXIT=$?" | tee -a "$MASTERLOG"


echo "===== STEP 4 BACKUP =====" | tee -a "$MASTERLOG"

bash asc_homework/scripts/night_backup.sh \
>> "$MASTERLOG" 2>&1

echo "BACKUP EXIT=$?" | tee -a "$MASTERLOG"


echo "NIGHT2 COMPLETED $(date)" \
| tee asc_homework/logs/night2_done.txt \
| tee -a "$MASTERLOG"
