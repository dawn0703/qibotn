#!/usr/bin/env bash
set -u

CURRENT_REPO="/root/autodl-tmp/asc-selection/qibotn"
FDU_REPO="/root/autodl-tmp/asc-selection/FDU-QiboTN-optimized"

mkdir -p "$CURRENT_REPO/asc_homework/notes"

source /etc/network_turbo || true

rm -rf "$FDU_REPO"

SUCCESS=0

for attempt in 1 2 3; do
    echo "FDU clone attempt $attempt"

    if git -c http.version=HTTP/1.1 clone \
        --depth 1 \
        https://github.com/FDU-SC/QiboTN-optimized.git \
        "$FDU_REPO"; then

        SUCCESS=1
        break
    fi

    sleep 20
done

unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY

if [ "$SUCCESS" -ne 1 ]; then
    echo "FDU CLONE FAILED"
    exit 0
fi

cd "$FDU_REPO"

git rev-parse HEAD \
    > "$CURRENT_REPO/asc_homework/notes/fdu_reference_commit.txt"

cp code_modification_explanation.md \
   "$CURRENT_REPO/asc_homework/notes/FDU_code_modification_explanation.md"

{
    echo "===== FDU repository ====="
    git remote -v

    echo
    echo "===== Commit ====="
    git rev-parse HEAD

    echo
    echo "===== Top-level files ====="
    find . -maxdepth 2 -type f | sort

    echo
    echo "===== C++ files ====="
    find . -type f \( \
        -name '*.cpp' -o \
        -name '*.hpp' -o \
        -name 'CMakeLists.txt' -o \
        -name 'setup.py' \
    \) | sort
} > "$CURRENT_REPO/asc_homework/notes/fdu_inventory.txt"

echo "FDU REFERENCE FETCH COMPLETED"
