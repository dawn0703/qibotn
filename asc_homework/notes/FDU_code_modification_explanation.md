# Code Modification Explanation

## Overview

This document describes the code modifications made for the optimized QiboTN submission. The changes are limited to backend execution, selected tensor-network hot modules, and progress logging. They accelerate MPS-based execution while computing the same benchmark observables.

No frozen parameters, JSON runcards (except MPI_enabled), random seeds, or benchmark driver logic were altered. The organizer-supplied qibojit-benchmarks code package (compare.py, benchmarks/libraries/qibo.py, and the qibotn_benchmark function in benchmarks/scripts.py) is used as provided and was not modified by our team.

## Scope of Changes

All modifications fall into three categories:

1. Performance optimization via a native C++ MPS simulator
2. Performance optimization via Cythonized Quimb hot modules
3. Diagnostic progress logging for MPI runs

The following table distinguishes team modifications from organizer baseline code:

```text
TEAM-MODIFIED FILES:
  qibotn/cpp/pyproject.toml          (new - C++ build config)
  qibotn/cpp/setup.py                (new - C++ build script)
  qibotn/cpp/CMakeLists.txt          (new - C++ build config)
  qibotn/cpp/src/mps_simulator.hpp   (new - C++ MPS simulator header)
  qibotn/cpp/src/mps_simulator.cpp   (new - C++ MPS simulator impl)
  qibotn/cpp/src/bindings.cpp        (new - pybind11 bindings)
  qibotn/src/qibotn/backends/quimb.py  (modified - C++ fast-path integration)
  qibojit-benchmarks/benchmarks/scripts.py  (modified - progress logging only)

ORGANIZER BASELINE (not modified by team):
  qibojit-benchmarks/compare.py
  qibojit-benchmarks/benchmarks/libraries/qibo.py
  qibojit-benchmarks/benchmarks/logger.py
  All JSON runcards (dense_vector_mps_mpi_*.json)
  All workload shell scripts (problem*.sh)
```

## Runtime Cythonized Quimb Modules

The following Cython-compiled modules are loaded at runtime via PYTHONPATH, placed ahead of the installed Quimb package:

```text
quimb_cython_exp/quimb/tensor/tn1d/core.cpython-312-x86_64-linux-gnu.so
quimb_cython_exp/quimb/tensor/tensor_core.cpython-312-x86_64-linux-gnu.so
quimb_cython_exp/quimb/tensor/decomp.py
```

The third module (decomp.py) is present in the same overlay directory and is loaded alongside the compiled .so modules when PYTHONPATH includes the quimb_cython_exp directory. This is visible in run.log warnings from the QAOA workload:

```text
/tmp/opencode/quimb_cython_exp/quimb/tensor/decomp.py:1028: UserWarning:
Got: Internal algorithm failed to converge., falling back to scipy gesvd driver.
```

These warnings are expected per the README and do not affect correctness.

All three modules are source-identical to the upstream Quimb package. The .so files are Cython compilations of the original Python source, and decomp.py is an unmodified copy included for import path consistency. They execute the same tensor-network algorithms as the installed Quimb package but with reduced Python interpreter overhead.

Note: The Cythonized modules were used at runtime from a temporary path on the cluster. They are not currently included in the src/ directory of this submission. The original Quimb source files from which they were compiled are:

```text
quimb/tensor/tn1d/core.py      -> compiled to core.cpython-312-x86_64-linux-gnu.so
quimb/tensor/tensor_core.py    -> compiled to tensor_core.cpython-312-x86_64-linux-gnu.so
quimb/tensor/decomp.py         -> unmodified copy
```

## Native C++ MPS Extension

A C++ MPS extension was added under:

```text
qibotn/cpp/
```

It is exposed to Python as:

```text
qibotn_cpp
```

The extension implements an MPS simulator using Eigen and pybind11. The internal scalar type is double-precision complex:

```cpp
using Complex = std::complex<double>;
using Mat = Eigen::MatrixXcd;
using Vec = Eigen::VectorXcd;
```

The simulator supports:

```text
single-qubit gates: H, X, Y, Z, S, T, RX, RY, RZ, U3
two-qubit gates: CNOT, CZ, CU1, RZZ, SWAP, iSWAP
batched gate application
statevector extraction
sampling
Pauli-string expectation
Pauli-sum expectation
```

The MPS tensors are updated directly in C++. Two-qubit non-adjacent gates are handled by nearest-neighbor MPS swaps, followed by gate application and SVD splitting. The same MPS controls are used by the simulator:

```text
max_bond_dimension
svd_cutoff
complex128 arithmetic
```

This reduces Python dispatch overhead during MPS evolution and moves repeated tensor updates into native code.

### C++ Fast-Path Activation Criteria

The C++ path activates only when ALL of the following conditions hold:

```text
1. qibotn_cpp is available (built from qibotn/cpp/)
2. ansatz is "mps"
3. initial_state is None (default |0...0>)
4. backend is "numpy" (not jax or torch)
5. circuit is "QFT-like" (gate set check, see below)
```

The gate-set check (_is_qft_like_circuit) accepts:

```text
QFT circuits:        {h, cu1, swap}
Supremacy circuits:  {h, cz, t, rx, ry, rz} with cz present
```

QAOA circuits are explicitly excluded from the C++ path because they contain RZZ gates and were validated against the original Quimb MPS truncation trajectory only.

When MPI is enabled (MPI_enabled=true in the runcard), the code takes the MPI path in quimb.py (dense_vector_tn_mpi_qu or exp_value_observable_symbolic_mpi_qu), which uses Quimb directly. The C++ fast path is therefore only reached for non-MPI single-process execution. If the C++ path fails for any reason, it falls back silently to the standard Quimb MPS path.

## C++ Pauli Expectation

The C++ extension computes observables of the form:

```text
sum_k c_k P_k
```

where each `P_k` is a Pauli string. Each term is evaluated as:

```text
<psi| P_k |psi>
```

using MPS transfer-matrix contraction. The final result is:

```text
sum_k c_k <psi| P_k |psi>
```

This is the same symbolic Hamiltonian expectation requested by the benchmark backend interface, evaluated without repeated Python-level tensor-network calls.

## QiboTN Quimb Backend Integration

The backend integration is implemented in:

```text
qibotn/src/qibotn/backends/quimb.py
```

### Changes vs Upstream (mpi_support_quimb branch)

The following elements were added to quimb.py:

```text
ADDED (new code):
  _CPP_DIR, _HAS_CPP              - C++ module discovery at import
  _CPP_GATE_1Q, _CPP_GATE_2Q      - gate matrix factory tables
  _is_qft_like_circuit()           - gate-set classifier for fast-path eligibility
  _cpp_gate_matrix()               - gate matrix extraction for C++ path
  _append_cpp_gate_ops()           - single-qubit fusion + C++ op builder
  _build_cpp_ops()                 - full circuit -> C++ ops conversion
  _build_cpp_simulator()           - C++ MPSSimulator construction + execution
  _execute_circuit_cpp()           - circuit execution via C++ path
  _exp_value_observable_symbolic_cpp() - expectation via C++ path

CHANGED (from upstream):
  @lru_cache on _string_to_quimb_operator  - caches Pauli operator construction
  exp_value_observable_symbolic()  - tries C++ path first, falls back to Quimb
  execute_circuit()                - tries C++ path first, falls back to Quimb

UNCHANGED (from upstream mpi_support_quimb):
  dense_vector_tn_mpi_qu()         - MPI dense-vector contraction
  exp_value_observable_symbolic_mpi_qu() - MPI expectation contraction
  _qibo_circuit_to_quimb()         - Qibo-to-Quimb circuit conversion
  configure_tn_simulation()        - runcard parameter loading
  setup_backend_specifics()        - backend engine selection
  _generate_backend()              - dynamic class construction
```

The backend loads `qibotn_cpp` from the local source tree:

```text
qibotn/cpp/
```

For supported MPS circuits, the backend converts the Qibo gate queue into C++ gate operations and executes:

```python
sim = qibotn_cpp.MPSSimulator(circuit.nqubits, max_bond, cutoff)
sim.apply_gates(ops)
```

For symbolic Pauli expectations, it executes:

```python
sim.expectation_pauli_sum(operators, sites, coeffs)
```

The public backend API remains:

```python
exp_value_observable_symbolic(circuit, operators, sites, coeffs, nqubits)
```

so the benchmark driver still calls the same QiboTN method.

## Mathematical Equivalence of the C++ Path

The optimized C++ path evaluates the same quantum operation as the Python MPS path:

```text
same initial computational state
same gate matrices
same gate order
same logical qubit indices
same Pauli terms
same coefficients
same MPS truncation parameters
```

For QFT, the equivalence is directly verifiable. QFT maps `|0...0>` to `|+...+>`. Therefore, for a single-qubit Pauli term:

```text
<X> = 1
<Y> = 0
<Z> = 0
```

The automatic Pauli pattern then gives an analytic expected value equal to the number of `X` symbols in the pattern. The C++ MPS path evaluates the same sum of Pauli expectations.

The same C++ MPS execution and Pauli-expectation implementation is used for the QFT and Supremacy workloads.

## Progress Logging

Progress logging was added in:

```text
qibojit-benchmarks/benchmarks/scripts.py
```

The change is limited to the progress-reporting section within the existing qibotn_benchmark function. The organizer-supplied computation logic (MPI round-robin partitioning, qubit sweep, expectation collection, and .dat file generation) was not modified.

The specific additions are:

```text
ADDED LINES (progress logging only):
  progress_verbose = os.environ.get("QIBOTN_PROGRESS_VERBOSE") == "1"
  progress_every_n = int(os.environ.get("QIBOTN_PROGRESS_EVERY_N", "256"))
  progress_selected = (progress_verbose or rank == progress_rank or ...)
  print("QIBOTN_PROGRESS event=start ...")  (when QIBOTN_PROGRESS_VERBOSE=1)
  print("QIBOTN_PROGRESS event=done ...")   (at selected intervals)
```

The logger prints low-frequency lines to `run.log` during long MPI sweeps:

```text
QIBOTN_PROGRESS event=done rank=... local=... nqubits=... elapsed=... expectation_abs=...
```

This is diagnostic logging only. It is controlled by environment variables and does not execute by default unless the variables are set. The final values in the output `.dat` files are still produced by the benchmark logger fields:

```text
simulation_times_mean
expectation_result
expectation_by_nqubits
```

No other lines in scripts.py were modified by the team.

## Frozen Parameters and Runcards

The following were NOT modified:

```text
compare.py arguments (--circuit, --circuit-options, --nqubits, --filename,
  --library-options, --backend, --platform, --computation_settings,
  --nreps, --precision) - used as provided by organizer

JSON runcards (dense_vector_mps_mpi_*.json) - used as provided by organizer
  (MPI_enabled is the only field teams may flip per README section 3.1)

Random seeds - default seed=123 preserved in benchmarks/circuits/qasm.py
  and in qibotn_benchmark (base_seed = int(_kw.get("seed", 123)))

Workload shell scripts (problem*.sh) - used as provided by organizer
```

## Correctness Criterion

The benchmark compares the submitted mean expectation value `v` with the reference value `v0` using:

```text
|v - v0| * 100% <= 0.0001% * |v0| + t    (where t = 1e-12)
```

The optimized code computes the same expectation expressions with the same MPS controls and double-precision complex arithmetic. The C++ path evaluates the circuit and observable directly in MPS form, and the Cythonized modules execute the same Quimb tensor-network operations in compiled form.

## Summary

The modifications improve execution by:

```text
1. adding a native C++ MPS simulator (qibotn/cpp/),
2. adding native C++ Pauli-sum expectation evaluation (qibotn/cpp/),
3. integrating the C++ simulator into the QiboTN Quimb backend (quimb.py),
4. compiling selected Quimb tensor-network hot modules with Cython
   (tn1d/core.py, tensor_core.py, loaded via PYTHONPATH with decomp.py),
5. adding low-frequency progress logging for long MPI runs (scripts.py),
6. caching Pauli operator construction with @lru_cache (quimb.py).
```

No computation logic, frozen parameters, random seeds, or benchmark driver behavior was altered. The C++ path and Cythonized modules are performance-only changes that preserve mathematical equivalence with the original Quimb MPS computation.
