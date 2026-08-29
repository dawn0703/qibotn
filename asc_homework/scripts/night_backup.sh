#!/usr/bin/env bash
set -e

REPO="/root/autodl-tmp/asc-selection/qibotn"
BACKUP="/autodl-fs/data/asc-selection-backup"

mkdir -p "$BACKUP"

rsync -av \
    "$REPO/asc_homework/" \
    "$BACKUP/asc_homework/"

cd /root/autodl-tmp/asc-selection

STAMP=$(date +%Y%m%d_%H%M%S)

tar \
    --exclude='qibotn/.venv' \
    --exclude='qibotn/.git' \
    --exclude='qibotn/**/__pycache__' \
    -czf "$BACKUP/qibotn_clean_${STAMP}.tar.gz" \
    qibotn

echo "BACKUP COMPLETED: $STAMP"
