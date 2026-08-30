from pathlib import Path

import pandas as pd


ROOT = Path("asc_homework")
R = ROOT / "results"

rows = []


# ============================================================
# Baseline
# ============================================================

df = pd.read_csv(R / "baseline.csv")
df = df[df["status"] == "success"]

for n, g in df.groupby("qubits"):
    rows.append({
        "workload": "QFT",
        "qubits": int(n),
        "experiment": "baseline",
        "config": "BLAS=1, serial",
        "timing_scope": "execution_s",
        "runtime_s": g["execution_s"].median(),
        "speedup": 1.0,
        "repeats": len(g),
        "status": "success",
        "command": (
            f"python asc_homework/scripts/"
            f"benchmark_qft.py --qubits {int(n)}"
        ),
    })


# ============================================================
# Thread tuning
# ============================================================

df = pd.read_csv(R / "threads.csv")
df = df[df["status"] == "success"]

base = (
    df[df["threads"] == 1]["execution_s"]
    .median()
)

for t, g in df.groupby("threads"):
    runtime = g["execution_s"].median()

    rows.append({
        "workload": "QFT",
        "qubits": 19,
        "experiment": "thread_tuning",
        "config": f"threads={int(t)}",
        "timing_scope": "execution_s",
        "runtime_s": runtime,
        "speedup": base / runtime,
        "repeats": len(g),
        "status": "success",
        "command": (
            f"OPENBLAS_NUM_THREADS={int(t)} "
            f"OMP_NUM_THREADS={int(t)} "
            "python asc_homework/scripts/"
            "benchmark_qft.py --qubits 19"
        ),
    })


# ============================================================
# Initialization reuse
# ============================================================

df = pd.read_csv(R / "reuse.csv")

base = (
    df[df["mode"] == "separate_processes"]
    ["batch_wall_s"]
    .median()
)

for mode, g in df.groupby("mode"):
    runtime = g["batch_wall_s"].median()

    rows.append({
        "workload": "QFT",
        "qubits": "8,10,12,14,16,18,19",
        "experiment": "initialization_reuse",
        "config": mode,
        "timing_scope": "batch_wall_s",
        "runtime_s": runtime,
        "speedup": base / runtime,
        "repeats": len(g),
        "status": (
            "success"
            if g["success_count"].min() == 7
            else "failed"
        ),
        "command": "asc_homework/scripts/overnight_suite.py",
    })


# ============================================================
# Batch parallelism
# ============================================================

df = pd.read_csv(R / "batch.csv")

base = (
    df[df["workers"] == 1]
    ["batch_wall_s"]
    .median()
)

for workers, g in df.groupby("workers"):
    runtime = g["batch_wall_s"].median()

    rows.append({
        "workload": "QFT",
        "qubits": "mixed 12-19",
        "experiment": "batch_parallelism",
        "config": f"workers={int(workers)}, BLAS=1",
        "timing_scope": "batch_wall_s",
        "runtime_s": runtime,
        "speedup": base / runtime,
        "repeats": len(g),
        "status": (
            "success"
            if g["success_count"].min()
            == g["total_tasks"].min()
            else "failed"
        ),
        "command": "asc_homework/scripts/overnight_suite.py",
    })


# ============================================================
# Task ordering
# ============================================================

order_path = R / "order_sweep.csv"

if order_path.exists():
    df = pd.read_csv(order_path)

    base = (
        df[df["order"] == "ascending"]
        ["batch_wall_s"]
        .median()
    )

    for order, g in df.groupby("order"):
        runtime = g["batch_wall_s"].median()

        rows.append({
            "workload": "QFT",
            "qubits": "8,10,12,14,16,18,19",
            "experiment": "task_order",
            "config": order,
            "timing_scope": "batch_wall_s",
            "runtime_s": runtime,
            "speedup": base / runtime,
            "repeats": len(g),
            "status": (
                "success"
                if g["success"].all()
                else "failed"
            ),
            "command": "python asc_homework/scripts/order_sweep.py",
        })


# ============================================================
# Final combined
# ============================================================

df = pd.read_csv(R / "final_combined.csv")

base = (
    df[
        df["mode"] == "baseline_separate_serial"
    ]["batch_wall_s"].median()
)

for (mode, workers), g in df.groupby(
    ["mode", "workers"]
):
    runtime = g["batch_wall_s"].median()

    rows.append({
        "workload": "QFT",
        "qubits": "8,10,12,14,16,18,19 x3",
        "experiment": "final_combined",
        "config": f"{mode}, workers={workers}",
        "timing_scope": "batch_wall_s",
        "runtime_s": runtime,
        "speedup": base / runtime,
        "repeats": len(g),
        "status": (
            "success"
            if g["success_count"].min()
            == g["tasks"].min()
            else "failed"
        ),
        "command": (
            "python asc_homework/scripts/"
            "final_combined_suite.py"
        ),
    })


out = pd.DataFrame(rows)

out.to_csv(
    R / "results.csv",
    index=False,
)

print(out.to_string(index=False))
print()
print("Saved:", R / "results.csv")
