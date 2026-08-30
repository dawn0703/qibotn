import os
import numpy as np
import qibo
import qibotn
import qibotn.backends.quimb as qb
from qibo.models import QFT


N = 4

print("===== FDU C++ FAST-PATH PROBE =====")
print("qibotn source =", qibotn.__file__)
print("CPP dir       =", qb._CPP_DIR)
print("_HAS_CPP      =", qb._HAS_CPP)
print("CUDA_VISIBLE_DEVICES =", repr(os.environ.get("CUDA_VISIBLE_DEVICES")))


# ==================================================
# 1. Qibojit CPU reference
# ==================================================

qibo.set_backend(
    "qibojit",
    platform="numba",
)

ref_backend = qibo.get_backend()

ref_circuit = QFT(N)

ref_result = ref_backend.execute_circuit(
    ref_circuit
)

reference = np.asarray(
    ref_result.state()
).reshape(-1)


# ==================================================
# 2. FDU QiboTN / Quimb
# ==================================================

qibo.set_backend(
    backend="qibotn",
    platform="quimb",
)

backend = qibo.get_backend()

print("backend       =", backend)
print("ansatz        =", getattr(backend, "ansatz", None))
print("array backend =", getattr(backend, "backend", None))
print(
    "max bond      =",
    getattr(backend, "max_bond_dimension", None),
)
print(
    "svd cutoff    =",
    getattr(backend, "svd_cutoff", None),
)


# ==================================================
# 3. Instrument C++ execution method
# ==================================================

if not qb._HAS_CPP:
    raise SystemExit("FAILED: _HAS_CPP is False")

if not hasattr(backend, "_execute_circuit_cpp"):
    raise SystemExit(
        "FAILED: backend has no _execute_circuit_cpp"
    )

cpp_calls = {"count": 0}

original_cpp_execute = (
    backend._execute_circuit_cpp
)


def counted_cpp_execute(
    circuit,
    nshots,
    return_array,
):
    cpp_calls["count"] += 1

    return original_cpp_execute(
        circuit,
        nshots,
        return_array,
    )


backend._execute_circuit_cpp = (
    counted_cpp_execute
)

backend._last_cpp_fallback_reason = None


# ==================================================
# 4. Execute QFT
# ==================================================

circuit = QFT(N)

result = backend.execute_circuit(
    circuit,
    return_array=True,
)

candidate = np.asarray(
    result.state()
).reshape(-1)


# ==================================================
# 5. Align global phase
# ==================================================

overlap = np.vdot(
    reference,
    candidate,
)

if abs(overlap) > 0:
    candidate = (
        candidate
        * np.exp(
            -1j * np.angle(overlap)
        )
    )


# ==================================================
# 6. Correctness
# ==================================================

max_error = float(
    np.max(
        np.abs(
            reference - candidate
        )
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

fallback_reason = getattr(
    backend,
    "_last_cpp_fallback_reason",
    None,
)

print()
print("cpp_calls       =", cpp_calls["count"])
print("fallback_reason =", fallback_reason)
print("reference shape =", reference.shape)
print("candidate shape =", candidate.shape)
print("reference norm  =", np.linalg.norm(reference))
print("candidate norm  =", np.linalg.norm(candidate))
print("max_abs_error   =", max_error)
print("correct         =", correct)


fast_path_ok = (
    cpp_calls["count"] >= 1
    and not fallback_reason
)

if not correct:
    raise SystemExit(
        "FAILED: numerical correctness"
    )

if not fast_path_ok:
    raise SystemExit(
        "FAILED: C++ fast path was not completed"
    )

print()
print("FDU CPP FAST PATH PASSED")
