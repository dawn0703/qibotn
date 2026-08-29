import argparse
import json
import resource
import time

import numpy as np
import qibo
from qibo.models import QFT


parser = argparse.ArgumentParser()
parser.add_argument("--qubits", nargs="+", type=int, required=True)
args = parser.parse_args()

total_start = time.perf_counter()

qibo.set_backend(
    backend="qibotn",
    platform="quimb",
)
backend = qibo.get_backend()

cases = []

for n in args.qubits:
    try:
        t0 = time.perf_counter()

        circuit = QFT(n)
        result = backend.execute_circuit(
            circuit,
            return_array=True,
        )

        state = np.asarray(
            result.state()
        ).reshape(-1)

        elapsed = time.perf_counter() - t0

        cases.append({
            "qubits": n,
            "status": "success",
            "runtime_s": elapsed,
            "state_norm": float(np.linalg.norm(state)),
        })

    except Exception as exc:
        cases.append({
            "qubits": n,
            "status": "failed",
            "error": repr(exc),
        })

total_s = time.perf_counter() - total_start

max_rss_mb = (
    resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    / 1024.0
)

record = {
    "status": (
        "success"
        if all(x["status"] == "success" for x in cases)
        else "partial_failure"
    ),
    "total_s": total_s,
    "max_rss_mb": max_rss_mb,
    "cases": cases,
}

print("RESULT_JSON=" + json.dumps(record))
