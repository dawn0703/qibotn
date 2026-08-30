import csv
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path("asc_homework")
PERSIST = ROOT / "scripts" / "persistent_qft_batch.py"
OUT = ROOT / "results" / "order_sweep.csv"
LOGDIR = ROOT / "logs" / "order_sweep"

LOGDIR.mkdir(parents=True, exist_ok=True)

base = [8, 10, 12, 14, 16, 18, 19]

orders = {
    "ascending": base * 3,
    "descending": list(reversed(base)) * 3,
    "interleaved": [19, 8, 18, 10, 16, 12, 14] * 3,
}

REPEATS = 8


def env_cpu():
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = ""
    env["OPENBLAS_NUM_THREADS"] = "1"
    env["OMP_NUM_THREADS"] = "1"
    env["MKL_NUM_THREADS"] = "1"
    env["NUMEXPR_NUM_THREADS"] = "1"
    return env


rows = []

for order_name, tasks in orders.items():

    for rep in range(1, REPEATS + 1):

        print(
            f"order={order_name} rep={rep}/{REPEATS}",
            flush=True,
        )

        cmd = [
            sys.executable,
            str(PERSIST),
            "--qubits",
            *map(str, tasks),
        ]

        start = time.perf_counter()

        try:
            proc = subprocess.run(
                cmd,
                env=env_cpu(),
                capture_output=True,
                text=True,
                timeout=300,
            )

            wall = time.perf_counter() - start

            (
                LOGDIR / f"{order_name}_r{rep}.log"
            ).write_text(
                proc.stdout
                + "\n===== STDERR =====\n"
                + proc.stderr
            )

            result = None

            for line in proc.stdout.splitlines():
                if line.startswith("RESULT_JSON="):
                    result = json.loads(
                        line.split("=", 1)[1]
                    )

            success = (
                proc.returncode == 0
                and result is not None
                and result.get("status") == "success"
            )

        except subprocess.TimeoutExpired:
            wall = 300
            success = False

        rows.append({
            "order": order_name,
            "repeat": rep,
            "tasks": len(tasks),
            "batch_wall_s": wall,
            "success": success,
        })


with OUT.open("w", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "order",
            "repeat",
            "tasks",
            "batch_wall_s",
            "success",
        ],
    )
    writer.writeheader()
    writer.writerows(rows)

print("ORDER SWEEP COMPLETED")
