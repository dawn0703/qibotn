import argparse
import json
import os
import resource
import time

import numpy as np
import qibo
from qibo.models import QFT


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--qubits", type=int, required=True)
    args = parser.parse_args()

    n = args.qubits

    record = {
        "workload": "QFT",
        "qubits": n,
        "status": "failed",
        "openblas_threads": os.environ.get("OPENBLAS_NUM_THREADS", ""),
        "omp_threads": os.environ.get("OMP_NUM_THREADS", ""),
        "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES", None),
    }

    try:
        total_start = time.perf_counter()

        # Backend initialization
        t0 = time.perf_counter()
        qibo.set_backend(
            backend="qibotn",
            platform="quimb",
        )
        backend = qibo.get_backend()
        backend_setup_s = time.perf_counter() - t0

        # Circuit creation
        t0 = time.perf_counter()
        circuit = QFT(n)
        creation_s = time.perf_counter() - t0

        # Tensor-network execution + dense state reconstruction
        t0 = time.perf_counter()
        result = backend.execute_circuit(
            circuit,
            return_array=True,
        )
        execution_s = time.perf_counter() - t0

        state = np.asarray(result.state()).reshape(-1)

        total_s = time.perf_counter() - total_start

        norm = float(np.linalg.norm(state))

        # Simple reproducible output fingerprints
        checksum_real = float(np.sum(state.real))
        checksum_imag = float(np.sum(state.imag))

        # Linux ru_maxrss is KiB
        max_rss_mb = (
            resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            / 1024.0
        )

        record.update(
            {
                "status": "success",
                "backend": str(backend),
                "backend_setup_s": backend_setup_s,
                "creation_s": creation_s,
                "execution_s": execution_s,
                "total_s": total_s,
                "state_size": int(state.size),
                "state_norm": norm,
                "checksum_real": checksum_real,
                "checksum_imag": checksum_imag,
                "max_rss_mb": max_rss_mb,
            }
        )

    except Exception as exc:
        record["error"] = repr(exc)

    print("RESULT_JSON=" + json.dumps(record, sort_keys=True))


if __name__ == "__main__":
    main()
