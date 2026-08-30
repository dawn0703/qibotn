#!/usr/bin/env bash

set +e

FDU="/root/autodl-tmp/asc-selection/FDU-QiboTN-optimized"
MAIN="/root/autodl-tmp/asc-selection/qibotn"
LOG="$MAIN/asc_homework/logs/fdu_build_probe.log"
RESULT="$MAIN/asc_homework/notes/fdu_build_result.txt"
VENV="$FDU/.venv-build-probe"

{
echo "===== FDU BUILD PROBE ====="
echo "Start: $(date)"
echo "Repository: $FDU"

cd "$FDU" || exit 0

echo
echo "===== COMMIT ====="
git rev-parse HEAD

echo
echo "===== COMPILER ====="
gcc --version | head -1
g++ --version | head -1
cmake --version | head -1 || true

echo
echo "===== SETUP.PY ====="
sed -n '1,240p' src/qibotn/cpp/setup.py

echo
echo "===== CMAKE ====="
sed -n '1,260p' src/qibotn/cpp/CMakeLists.txt

echo
echo "===== CREATE ISOLATED BUILD ENV ====="

rm -rf "$VENV"
python3 -m venv "$VENV"

source "$VENV/bin/activate"

python -m pip install --upgrade \
    pip setuptools wheel \
    numpy pybind11 cmake ninja

echo
echo "===== BUILD ATTEMPT ====="

cd "$FDU/src/qibotn/cpp" || exit 0

timeout 25m \
python setup.py build_ext --inplace

BUILD_EXIT=$?

echo
echo "BUILD_EXIT=$BUILD_EXIT"

echo
echo "===== GENERATED SHARED OBJECTS ====="
find "$FDU" -type f -name '*.so' -print

echo
echo "Finish: $(date)"

} > "$LOG" 2>&1

BUILD_EXIT_LINE=$(
    grep 'BUILD_EXIT=' "$LOG" | tail -1
)

{
echo "FDU public optimization reproduction probe"
echo "$BUILD_EXIT_LINE"
echo
echo "Full log:"
echo "asc_homework/logs/fdu_build_probe.log"
} > "$RESULT"

exit 0
