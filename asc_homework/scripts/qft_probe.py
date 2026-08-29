import os
import time
import numpy as np
import qibo
from qibo.models import QFT

NQUBITS = 4

print("===== QFT PROBE =====")
print("qubits =", NQUBITS)
print("CUDA_VISIBLE_DEVICES =", repr(os.environ.get("CUDA_VISIBLE_DEVICES")))


# --------------------------------------------------
# Reference: Qibojit CPU
# --------------------------------------------------

qibo.set_backend(
    "qibojit",
    platform="numba",
)

reference_backend = qibo.get_backend()

reference_circuit = QFT(NQUBITS)

t0 = time.perf_counter()
reference_result = reference_backend.execute_circuit(reference_circuit)
reference_time = time.perf_counter() - t0

reference_state = np.asarray(
    reference_result.state()
).reshape(-1)


# --------------------------------------------------
# QiboTN + Quimb CPU
# --------------------------------------------------

qibo.set_backend(
    backend="qibotn",
    platform="quimb",
)

tn_backend = qibo.get_backend()

tn_circuit = QFT(NQUBITS)

t0 = time.perf_counter()
tn_result = tn_backend.execute_circuit(
    tn_circuit,
    return_array=True,
)
tn_time = time.perf_counter() - t0

tn_state = np.asarray(
    tn_result.state()
).reshape(-1)


# --------------------------------------------------
# Global-phase alignment
# --------------------------------------------------

overlap = np.vdot(reference_state, tn_state)

if abs(overlap) > 0:
    tn_state_aligned = (
        tn_state
        * np.exp(-1j * np.angle(overlap))
    )
else:
    tn_state_aligned = tn_state


# --------------------------------------------------
# Correctness
# --------------------------------------------------

max_abs_error = np.max(
    np.abs(reference_state - tn_state_aligned)
)

correct = np.allclose(
    reference_state,
    tn_state_aligned,
    rtol=1e-8,
    atol=1e-10,
)

print()
print("Reference backend :", reference_backend)
print("QiboTN backend    :", tn_backend)

print()
print("Reference shape :", reference_state.shape)
print("QiboTN shape    :", tn_state.shape)

print()
print("Reference norm :", np.linalg.norm(reference_state))
print("QiboTN norm    :", np.linalg.norm(tn_state))

print()
print("Qibojit runtime_s :", reference_time)
print("QiboTN runtime_s  :", tn_time)

print()
print("max_abs_error =", max_abs_error)
print("correct =", correct)

if not correct:
    raise SystemExit("QFT PROBE FAILED")

print()
print("QFT PROBE PASSED")
