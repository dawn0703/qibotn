from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path("asc_homework")
RESULTS = ROOT / "results"
PLOTS = ROOT / "plots"
NOTES = ROOT / "notes"

PLOTS.mkdir(parents=True, exist_ok=True)
NOTES.mkdir(parents=True, exist_ok=True)


# ==========================================
# Baseline
# ==========================================

baseline = pd.read_csv(
    RESULTS / "baseline.csv"
)

baseline_ok = baseline[
    baseline["status"] == "success"
].copy()

baseline_summary = (
    baseline_ok
    .groupby("qubits")
    .agg(
        execution_median_s=("execution_s", "median"),
        execution_mean_s=("execution_s", "mean"),
        execution_std_s=("execution_s", "std"),
        process_wall_median_s=("process_wall_s", "median"),
        max_rss_median_mb=("max_rss_mb", "median"),
        success_count=("status", "count"),
    )
    .reset_index()
)

baseline_summary.to_csv(
    RESULTS / "baseline_summary.csv",
    index=False,
)


# Runtime scaling
fig = plt.figure(figsize=(7, 4.5))
plt.plot(
    baseline_summary["qubits"],
    baseline_summary["execution_median_s"],
    marker="o",
)
plt.xlabel("Qubits")
plt.ylabel("Median execution time (s)")
plt.title("QFT baseline scaling")
plt.grid(True, alpha=0.3)
plt.tight_layout()
fig.savefig(
    PLOTS / "baseline_runtime_vs_qubits.png",
    dpi=180,
)
plt.close(fig)


# Memory scaling
fig = plt.figure(figsize=(7, 4.5))
plt.plot(
    baseline_summary["qubits"],
    baseline_summary["max_rss_median_mb"],
    marker="o",
)
plt.xlabel("Qubits")
plt.ylabel("Median peak RSS (MB)")
plt.title("QFT memory usage")
plt.grid(True, alpha=0.3)
plt.tight_layout()
fig.savefig(
    PLOTS / "memory_vs_qubits.png",
    dpi=180,
)
plt.close(fig)


# ==========================================
# Threads
# ==========================================

threads = pd.read_csv(
    RESULTS / "threads.csv"
)

threads_ok = threads[
    threads["status"] == "success"
].copy()

thread_summary = (
    threads_ok
    .groupby("threads")
    .agg(
        execution_median_s=("execution_s", "median"),
        execution_mean_s=("execution_s", "mean"),
        execution_std_s=("execution_s", "std"),
        process_wall_median_s=("process_wall_s", "median"),
    )
    .reset_index()
)

t1 = float(
    thread_summary.loc[
        thread_summary["threads"] == 1,
        "execution_median_s",
    ].iloc[0]
)

thread_summary["speedup_vs_1thread"] = (
    t1 / thread_summary["execution_median_s"]
)

thread_summary["parallel_efficiency"] = (
    thread_summary["speedup_vs_1thread"]
    / thread_summary["threads"]
)

thread_summary.to_csv(
    RESULTS / "threads_summary.csv",
    index=False,
)


fig = plt.figure(figsize=(7, 4.5))
plt.plot(
    thread_summary["threads"],
    thread_summary["execution_median_s"],
    marker="o",
)
plt.xlabel("BLAS / OMP threads")
plt.ylabel("Median execution time (s)")
plt.title("QFT thread scaling at 19 qubits")
plt.grid(True, alpha=0.3)
plt.tight_layout()
fig.savefig(
    PLOTS / "threads_vs_runtime.png",
    dpi=180,
)
plt.close(fig)


# ==========================================
# Initialization reuse
# ==========================================

reuse = pd.read_csv(
    RESULTS / "reuse.csv"
)

reuse_summary = (
    reuse
    .groupby("mode")
    .agg(
        batch_wall_median_s=("batch_wall_s", "median"),
        batch_wall_mean_s=("batch_wall_s", "mean"),
        batch_wall_std_s=("batch_wall_s", "std"),
        success_min=("success_count", "min"),
    )
    .reset_index()
)

sep_time = float(
    reuse_summary.loc[
        reuse_summary["mode"] == "separate_processes",
        "batch_wall_median_s",
    ].iloc[0]
)

reuse_summary["speedup_vs_separate"] = (
    sep_time / reuse_summary["batch_wall_median_s"]
)

reuse_summary.to_csv(
    RESULTS / "reuse_summary.csv",
    index=False,
)


fig = plt.figure(figsize=(7, 4.5))
plt.bar(
    reuse_summary["mode"],
    reuse_summary["batch_wall_median_s"],
)
plt.ylabel("Median batch wall time (s)")
plt.title("Effect of backend/process reuse")
plt.xticks(rotation=15)
plt.tight_layout()
fig.savefig(
    PLOTS / "reuse_comparison.png",
    dpi=180,
)
plt.close(fig)


# ==========================================
# Batch parallelism
# ==========================================

batch = pd.read_csv(
    RESULTS / "batch.csv"
)

batch_summary = (
    batch
    .groupby("workers")
    .agg(
        batch_wall_median_s=("batch_wall_s", "median"),
        batch_wall_mean_s=("batch_wall_s", "mean"),
        batch_wall_std_s=("batch_wall_s", "std"),
        success_min=("success_count", "min"),
    )
    .reset_index()
)

w1 = float(
    batch_summary.loc[
        batch_summary["workers"] == 1,
        "batch_wall_median_s",
    ].iloc[0]
)

batch_summary["speedup_vs_1worker"] = (
    w1 / batch_summary["batch_wall_median_s"]
)

batch_summary["parallel_efficiency"] = (
    batch_summary["speedup_vs_1worker"]
    / batch_summary["workers"]
)

batch_summary.to_csv(
    RESULTS / "batch_summary.csv",
    index=False,
)


fig = plt.figure(figsize=(7, 4.5))
plt.plot(
    batch_summary["workers"],
    batch_summary["speedup_vs_1worker"],
    marker="o",
)
plt.xlabel("Workers")
plt.ylabel("Speedup vs 1 worker")
plt.title("QFT batch throughput scaling")
plt.grid(True, alpha=0.3)
plt.tight_layout()
fig.savefig(
    PLOTS / "batch_speedup.png",
    dpi=180,
)
plt.close(fig)


# ==========================================
# Final combined optimization
# ==========================================

final_path = RESULTS / "final_combined.csv"

if final_path.exists():

    final = pd.read_csv(final_path)

    final_summary = (
        final
        .groupby(["mode", "workers"])
        .agg(
            batch_wall_median_s=("batch_wall_s", "median"),
            batch_wall_mean_s=("batch_wall_s", "mean"),
            batch_wall_std_s=("batch_wall_s", "std"),
            success_min=("success_count", "min"),
        )
        .reset_index()
    )

    base = float(
        final_summary.loc[
            final_summary["mode"] == "baseline_separate_serial",
            "batch_wall_median_s",
        ].iloc[0]
    )

    final_summary["speedup_vs_baseline"] = (
        base / final_summary["batch_wall_median_s"]
    )

    final_summary.to_csv(
        RESULTS / "final_combined_summary.csv",
        index=False,
    )

    fig = plt.figure(figsize=(8, 4.8))

    plt.bar(
        final_summary["mode"],
        final_summary["batch_wall_median_s"],
    )

    plt.ylabel("Median wall time (s)")
    plt.title("Final combined optimization")
    plt.xticks(rotation=20, ha="right")
    plt.tight_layout()

    fig.savefig(
        PLOTS / "final_combined_runtime.png",
        dpi=180,
    )

    plt.close(fig)


# ==========================================
# Automatic textual summary
# ==========================================

best_thread_row = thread_summary.loc[
    thread_summary["execution_median_s"].idxmin()
]

best_batch_row = batch_summary.loc[
    batch_summary["batch_wall_median_s"].idxmin()
]

persistent_row = reuse_summary.loc[
    reuse_summary["mode"] == "persistent_process"
].iloc[0]


lines = [
    "# Automatic QiboTN result summary",
    "",
    "## Baseline",
    "",
    baseline_summary.to_markdown(index=False),
    "",
    "## Thread tuning",
    "",
    thread_summary.to_markdown(index=False),
    "",
    f"Best measured thread count: {int(best_thread_row['threads'])}",
    f"Best thread speedup vs 1 thread: {best_thread_row['speedup_vs_1thread']:.3f}x",
    "",
    "## Initialization reuse",
    "",
    reuse_summary.to_markdown(index=False),
    "",
    f"Persistent-process speedup: {persistent_row['speedup_vs_separate']:.3f}x",
    "",
    "## Batch parallelism",
    "",
    batch_summary.to_markdown(index=False),
    "",
    f"Best worker count tested: {int(best_batch_row['workers'])}",
    f"Best batch speedup: {best_batch_row['speedup_vs_1worker']:.3f}x",
]

if (RESULTS / "final_combined_summary.csv").exists():

    fsum = pd.read_csv(
        RESULTS / "final_combined_summary.csv"
    )

    lines += [
        "",
        "## Final combined optimization",
        "",
        fsum.to_markdown(index=False),
    ]


(NOTES / "automatic_analysis.md").write_text(
    "\n".join(lines)
)

print("ANALYSIS COMPLETED")
print("Generated summaries, plots, and automatic_analysis.md")
