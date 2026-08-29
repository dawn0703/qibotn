import csv
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


ROOT = Path("asc_homework")
BENCH = ROOT / "scripts" / "benchmark_qft.py"
PERSISTENT = ROOT / "scripts" / "persistent_qft_batch.py"

RESULTS = ROOT / "results"
LOGS = ROOT / "logs" / "overnight"

RESULTS.mkdir(parents=True, exist_ok=True)
LOGS.mkdir(parents=True, exist_ok=True)

TIMEOUT = 180


def save_csv(path, rows):
    keys = sorted({
        key
        for row in rows
        for key in row.keys()
    })

    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=keys,
        )
        writer.writeheader()
        writer.writerows(rows)


def child_env(threads):
    env = os.environ.copy()

    env["CUDA_VISIBLE_DEVICES"] = ""
    env["OPENBLAS_NUM_THREADS"] = str(threads)
    env["OMP_NUM_THREADS"] = str(threads)
    env["MKL_NUM_THREADS"] = str(threads)
    env["NUMEXPR_NUM_THREADS"] = str(threads)

    return env


def run_one(n, threads, tag):
    env = child_env(threads)

    cmd = [
        sys.executable,
        str(BENCH),
        "--qubits",
        str(n),
    ]

    start = time.perf_counter()

    try:
        proc = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
        )

        wall = time.perf_counter() - start

        logpath = LOGS / f"{tag}.log"
        logpath.write_text(
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

        if result is None:
            return {
                "qubits": n,
                "threads": threads,
                "status": "parse_failed",
                "process_wall_s": wall,
                "returncode": proc.returncode,
            }

        result["threads"] = threads
        result["process_wall_s"] = wall
        result["returncode"] = proc.returncode

        return result

    except subprocess.TimeoutExpired:
        return {
            "qubits": n,
            "threads": threads,
            "status": "timeout",
            "process_wall_s": TIMEOUT,
        }


print("===== ASC QiboTN OVERNIGHT SUITE =====", flush=True)
print("Start:", time.ctime(), flush=True)


# ==================================================
# 1. BASELINE
# ==================================================

print("\n===== 1/4 BASELINE =====", flush=True)

baseline_qubits = [8, 10, 12, 14, 16, 18, 19]
baseline_rows = []

for n in baseline_qubits:
    for rep in range(1, 6):
        print(
            f"baseline n={n} rep={rep}/5",
            flush=True,
        )

        row = run_one(
            n,
            1,
            f"baseline_n{n}_r{rep}",
        )

        row["phase"] = "baseline"
        row["repeat"] = rep

        baseline_rows.append(row)

save_csv(
    RESULTS / "baseline.csv",
    baseline_rows,
)

print("baseline.csv saved.", flush=True)


# ==================================================
# 2. THREAD SWEEP
# ==================================================

print("\n===== 2/4 THREAD SWEEP =====", flush=True)

thread_rows = []
representative_n = 19

for threads in [1, 2, 4, 8, 16, 24]:
    for rep in range(1, 6):

        print(
            f"threads={threads} "
            f"n={representative_n} "
            f"rep={rep}/5",
            flush=True,
        )

        row = run_one(
            representative_n,
            threads,
            f"threads_t{threads}_r{rep}",
        )

        row["phase"] = "thread_sweep"
        row["repeat"] = rep

        thread_rows.append(row)

save_csv(
    RESULTS / "threads.csv",
    thread_rows,
)

print("threads.csv saved.", flush=True)


# ==================================================
# 3. INITIALIZATION / PROCESS REUSE
# ==================================================

print("\n===== 3/4 PROCESS REUSE =====", flush=True)

reuse_qubits = [8, 10, 12, 14, 16, 18, 19]
reuse_rows = []


# --- A. separate Python processes ---

for rep in range(1, 4):

    print(
        f"separate-process batch rep={rep}/3",
        flush=True,
    )

    start = time.perf_counter()
    statuses = []

    for i, n in enumerate(reuse_qubits):
        row = run_one(
            n,
            1,
            f"reuse_sep_r{rep}_i{i}_n{n}",
        )
        statuses.append(row.get("status"))

    wall = time.perf_counter() - start

    reuse_rows.append({
        "mode": "separate_processes",
        "repeat": rep,
        "batch_wall_s": wall,
        "success_count": statuses.count("success"),
        "total_cases": len(statuses),
    })


# --- B. one persistent Python process ---

for rep in range(1, 4):

    print(
        f"persistent-process batch rep={rep}/3",
        flush=True,
    )

    env = child_env(1)

    cmd = [
        sys.executable,
        str(PERSISTENT),
        "--qubits",
        *[str(n) for n in reuse_qubits],
    ]

    start = time.perf_counter()

    try:
        proc = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=TIMEOUT * 2,
        )

        wall = time.perf_counter() - start

        (
            LOGS
            / f"reuse_persistent_r{rep}.log"
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

        success_count = 0

        if result is not None:
            success_count = sum(
                case.get("status") == "success"
                for case in result.get("cases", [])
            )

        reuse_rows.append({
            "mode": "persistent_process",
            "repeat": rep,
            "batch_wall_s": wall,
            "success_count": success_count,
            "total_cases": len(reuse_qubits),
        })

    except subprocess.TimeoutExpired:

        reuse_rows.append({
            "mode": "persistent_process",
            "repeat": rep,
            "batch_wall_s": TIMEOUT * 2,
            "success_count": 0,
            "total_cases": len(reuse_qubits),
        })


save_csv(
    RESULTS / "reuse.csv",
    reuse_rows,
)

print("reuse.csv saved.", flush=True)


# ==================================================
# 4. BATCH PARALLELISM
# ==================================================

print("\n===== 4/4 BATCH PARALLELISM =====", flush=True)

batch_tasks = [
    12, 14, 16, 18, 19,
    12, 14, 16, 18, 19,
]

batch_rows = []


def run_parallel_batch(workers, rep):

    start = time.perf_counter()

    rows = []

    with ThreadPoolExecutor(
        max_workers=workers
    ) as pool:

        futures = []

        for i, n in enumerate(batch_tasks):

            futures.append(
                pool.submit(
                    run_one,
                    n,
                    1,
                    f"batch_w{workers}_r{rep}_i{i}_n{n}",
                )
            )

        for future in as_completed(futures):
            rows.append(future.result())

    wall = time.perf_counter() - start

    success_count = sum(
        row.get("status") == "success"
        for row in rows
    )

    return {
        "workers": workers,
        "repeat": rep,
        "batch_wall_s": wall,
        "success_count": success_count,
        "total_tasks": len(batch_tasks),
    }


for workers in [1, 2, 4, 8]:

    for rep in range(1, 4):

        print(
            f"workers={workers} rep={rep}/3",
            flush=True,
        )

        row = run_parallel_batch(
            workers,
            rep,
        )

        batch_rows.append(row)

        print(row, flush=True)


save_csv(
    RESULTS / "batch.csv",
    batch_rows,
)

print("batch.csv saved.", flush=True)


# ==================================================
# DONE
# ==================================================

summary = ROOT / "logs" / "overnight_done.txt"

summary.write_text(
    "ASC QiboTN overnight suite completed.\n"
    f"Finish time: {time.ctime()}\n"
)

print()
print("======================================")
print("OVERNIGHT SUITE COMPLETED")
print("Finish:", time.ctime())
print("======================================")
