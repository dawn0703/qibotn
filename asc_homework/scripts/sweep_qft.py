import csv
import json
import os
import subprocess
import sys
import time
from pathlib import Path


QUBITS = [8, 12, 16, 20, 24, 26, 28, 30]
TIMEOUT_S = 120

SCRIPT = Path(
    "asc_homework/scripts/benchmark_qft.py"
)

OUTPUT = Path(
    "asc_homework/results/probe_sweep.csv"
)

LOGDIR = Path(
    "asc_homework/logs/probe"
)

LOGDIR.mkdir(
    parents=True,
    exist_ok=True,
)

rows = []


for n in QUBITS:

    print(
        f"\n===== probing QFT n={n} =====",
        flush=True,
    )

    env = os.environ.copy()

    env["CUDA_VISIBLE_DEVICES"] = ""
    env["OPENBLAS_NUM_THREADS"] = "1"
    env["OMP_NUM_THREADS"] = "1"
    env["MKL_NUM_THREADS"] = "1"
    env["NUMEXPR_NUM_THREADS"] = "1"

    command = [
        sys.executable,
        str(SCRIPT),
        "--qubits",
        str(n),
    ]

    start = time.perf_counter()

    try:

        proc = subprocess.run(
            command,
            env=env,
            text=True,
            capture_output=True,
            timeout=TIMEOUT_S,
        )

        process_wall_s = (
            time.perf_counter() - start
        )

        log = (
            proc.stdout
            + "\n===== STDERR =====\n"
            + proc.stderr
        )

        (
            LOGDIR
            / f"qft_{n}.log"
        ).write_text(log)

        result = None

        for line in proc.stdout.splitlines():

            if line.startswith(
                "RESULT_JSON="
            ):
                result = json.loads(
                    line.split(
                        "=",
                        1,
                    )[1]
                )

        if (
            proc.returncode != 0
            or result is None
        ):
            row = {
                "qubits": n,
                "status": "failed",
                "process_wall_s": process_wall_s,
                "returncode": proc.returncode,
            }

        else:
            row = result
            row["process_wall_s"] = (
                process_wall_s
            )
            row["returncode"] = (
                proc.returncode
            )

    except subprocess.TimeoutExpired:

        process_wall_s = (
            time.perf_counter() - start
        )

        row = {
            "qubits": n,
            "status": "timeout",
            "process_wall_s": process_wall_s,
            "returncode": "",
        }

        print(
            f"n={n} exceeded "
            f"{TIMEOUT_S}s timeout."
        )

    rows.append(row)

    print(row)

    # Stop increasing problem size on
    # timeout or failure.
    if row["status"] != "success":
        print(
            "Stopping scale-up after "
            "first failed/timeout case."
        )
        break


fieldnames = sorted(
    {
        key
        for row in rows
        for key in row.keys()
    }
)


with OUTPUT.open(
    "w",
    newline="",
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=fieldnames,
    )

    writer.writeheader()
    writer.writerows(rows)


print()
print(f"Saved: {OUTPUT}")
