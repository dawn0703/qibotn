import os
import numpy as np
import qibo
from qibo import Circuit, gates

print("CUDA_VISIBLE_DEVICES =", repr(os.environ.get("CUDA_VISIBLE_DEVICES")))

qibo.set_backend(
    backend="qibotn",
    platform="quimb",
)

backend = qibo.get_backend()

circuit = Circuit(2)
circuit.add(gates.H(0))
circuit.add(gates.H(1))

result = backend.execute_circuit(
    circuit,
    return_array=True,
)

state = np.asarray(result.state()).reshape(-1)

expected = np.full(4, 0.5 + 0j)

max_error = np.max(np.abs(state - expected))
correct = np.allclose(
    state,
    expected,
    rtol=1e-10,
    atol=1e-12,
)

print("backend =", backend)
print("state =", state)
print("expected =", expected)
print("max_abs_error =", max_error)
print("correct =", correct)

if not correct:
    raise SystemExit("SMOKE TEST FAILED")

print("SMOKE TEST PASSED")
