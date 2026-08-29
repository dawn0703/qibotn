import csv
import os
import time

import numpy as np
import qibo
from qibo.models import QFT


QUBITS = [4, 6, 8, 10]
OUTPUT = "asc_homework/results/correctness.csv"


def align_global_phase(reference, candidate):
    overlap = np.vdot(reference, candidate)

    if abs(overlap) == 0:
        return candidate

    return candidate * np.exp(-1j * np.angle(overlap))


# Qibojit CPU reference
qibo.set_backend(
    "qibojit",
    platform="numba",
)
reference_backend = qibo.get_backend()

# Trigger JIT before measurements.
warmup = QFT(2)
_ = reference_backend.execute_circuit(warmup)


# QiboTN CPU
qibo.set_backend(
    backend="qibotn",
    platform="quimb",
)
tn_backend = qibo.get_backend()


rows = []

for n in QUBITS:
    print(f"Checking QFT n={n} ...", flush=True)

    # Reference
    ref_circuit = QFT(n)

    t0 = time.perf_counter()
    ref_result = reference_backend.execute_circuit(ref_circuit)
    ref_s = time.perf_counter() - t0

    reference = np.asarray(
        ref_result.state()
    ).reshape(-1)

    # QiboTN
    tn_circuit = QFT(n)

    t0 = time.perf_counter()
    tn_result = tn_backend.execute_circuit(
        tn_circuit,
        return_array=True,
    )
    tn_s = time.perf_counter() - t0

    candidate = np.asarray(
        tn_result.state()
    ).reshape(-1)

    candidate = align_global_phase(
        reference,
        candidate,
    )

    max_error = float(
        np.max(
            np.abs(reference - candidate)
        )
    )

    correct = bool(
        np.allclose(
            reference,
            candidate,
            rtol=1e-8,
            atol=1e-10,
        )
    )

    print(
        f"n={n}: "
        f"error={max_error:.3e}, "
        f"correct={correct}"
    )

    rows.append(
        {
            "workload": "QFT",
            "qubits": n,
            "reference": "qibojit-numba-cpu",
            "candidate": "qibotn-quimb-cpu",
            "reference_runtime_s": ref_s,
            "qibotn_runtime_s": tn_s,
            "max_abs_error": max_error,
            "correct": correct,
        }
    )


with open(OUTPUT, "w", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=rows[0].keys(),
    )
    writer.writeheader()
    writer.writerows(rows)


if not all(row["correct"] for row in rows):
    raise SystemExit("CORRECTNESS CHECK FAILED")

print(f"Saved: {OUTPUT}")
print("ALL CORRECTNESS CHECKS PASSED")
