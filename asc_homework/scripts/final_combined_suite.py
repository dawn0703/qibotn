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
PERSIST = ROOT / "scripts" / "persistent_qft_batch.py"
OUT = ROOT / "results" / "final_combined.csv"
LOGDIR = ROOT / "logs" / "final_combined"

LOGDIR.mkdir(parents=True, exist_ok=True)

# Same computational workload for every mode.
# Seven QFT sizes, repeated three times = 21 tasks.
TASKS = [8, 10, 12, 14, 16, 18, 19] * 3

REPEATS = 5
TIMEOUT = 600


def cpu_env():
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = ""
    env["OPENBLAS_NUM_THREADS"] = "1"
    env["OMP_NUM_THREADS"] = "1"
    env["MKL_NUM_THREADS"] = "1"
    env["NUMEXPR_NUM_THREADS"] = "1"
    return env


def parse_result(stdout):
    for line in stdout.splitlines():
        if line.startswith("RESULT_JSON="):
            return json.loads(line.split("=", 1)[1])
    return None


def run_single(n, tag):
    start = time.perf_counter()

    p = subprocess.run(
        [
            sys.executable,
            str(BENCH),
            "--qubits",
            str(n),
        ],
        env=cpu_env(),
        capture_output=True,
        text=True,
        timeout=180,
    )

    wall = time.perf_counter() - start

    (LOGDIR / f"{tag}.log").write_text(
        p.stdout + "\n===== STDERR =====\n" + p.stderr
    )

    result = parse_result(p.stdout)

    return (
        result is not None
        and result.get("status") == "success"
        and p.returncode == 0
    ), wall


def run_persistent_chunk(chunk, tag):
    if not chunk:
        return True, 0.0

    start = time.perf_counter()

    p = subprocess.run(
        [
            sys.executable,
            str(PERSIST),
            "--qubits",
            *map(str, chunk),
        ],
        env=cpu_env(),
        capture_output=True,
        text=True,
        timeout=TIMEOUT,
    )

    wall = time.perf_counter() - start

    (LOGDIR / f"{tag}.log").write_text(
        p.stdout + "\n===== STDERR =====\n" + p.stderr
    )

    result = parse_result(p.stdout)

    ok = (
        p.returncode == 0
        and result is not None
        and result.get("status") == "success"
    )

    return ok, wall


def chunks_for_workers(tasks, workers):
    chunks = [[] for _ in range(workers)]

    for i, task in enumerate(tasks):
        chunks[i % workers].append(task)

    return chunks


rows = []


# --------------------------------------------------
# A. Baseline:
# each task starts an independent Python process,
# all tasks serial.
# --------------------------------------------------

for rep in range(1, REPEATS + 1):

    print(f"baseline separate serial rep={rep}/{REPEATS}", flush=True)

    start = time.perf_counter()
    successes = 0

    for i, n in enumerate(TASKS):
        ok, _ = run_single(
            n,
            f"baseline_r{rep}_i{i}_n{n}",
        )
        successes += int(ok)

    wall = time.perf_counter() - start

    rows.append({
        "mode": "baseline_separate_serial",
        "workers": 1,
        "repeat": rep,
        "tasks": len(TASKS),
        "success_count": successes,
        "batch_wall_s": wall,
    })


# --------------------------------------------------
# B. Reuse only:
# one persistent process, one backend initialization.
# --------------------------------------------------

for rep in range(1, REPEATS + 1):

    print(f"persistent serial rep={rep}/{REPEATS}", flush=True)

    ok, wall = run_persistent_chunk(
        TASKS,
        f"persistent_serial_r{rep}",
    )

    rows.append({
        "mode": "persistent_serial",
        "workers": 1,
        "repeat": rep,
        "tasks": len(TASKS),
        "success_count": len(TASKS) if ok else 0,
        "batch_wall_s": wall,
    })


# --------------------------------------------------
# C. Combined:
# N persistent Python workers.
# Each initializes backend once, then processes chunk.
# --------------------------------------------------

for workers in [2, 4, 8]:

    chunks = chunks_for_workers(
        TASKS,
        workers,
    )

    for rep in range(1, REPEATS + 1):

        print(
            f"persistent workers={workers} "
            f"rep={rep}/{REPEATS}",
            flush=True,
        )

        start = time.perf_counter()

        success_count = 0

        with ThreadPoolExecutor(
            max_workers=workers
        ) as pool:

            futures = {
                pool.submit(
                    run_persistent_chunk,
                    chunk,
                    f"combined_w{workers}_r{rep}_chunk{i}",
                ): len(chunk)
                for i, chunk in enumerate(chunks)
            }

            for future in as_completed(futures):
                ok, _ = future.result()

                if ok:
                    success_count += futures[future]

        wall = time.perf_counter() - start

        rows.append({
            "mode": f"persistent_parallel_{workers}",
            "workers": workers,
            "repeat": rep,
            "tasks": len(TASKS),
            "success_count": success_count,
            "batch_wall_s": wall,
        })


with OUT.open("w", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "mode",
            "workers",
            "repeat",
            "tasks",
            "success_count",
            "batch_wall_s",
        ],
    )
    writer.writeheader()
    writer.writerows(rows)


print(f"Saved {OUT}")
print("FINAL COMBINED SUITE COMPLETED")
