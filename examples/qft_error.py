# Copyright IBM 2025.

"""A QFT error scaling example."""

import numpy as np
import matplotlib.pyplot as plt
from qiskit.quantum_info import get_clifford_gate_names

from ft_resource_estimation.library.aqft import AQFT
from ft_resource_estimation.graphs import CallGraph
from ft_resource_estimation.error_models import GrossErrorModel
from ft_resource_estimation.topologies import Linear
from ft_resource_estimation.target import Target

cliffords = get_clifford_gate_names()

error_model = GrossErrorModel(p=4)
data = []
ns = [3, 5, 10, 20, 25]
for n in ns:
    aqft = AQFT(n)
    topo = Linear(num_modules=int(np.ceil(n / 11)))
    target = Target(topo, error_model)
    graph = CallGraph(aqft)
    base_count = graph.count_basis(["AQFT"])
    # base_count_plain = graph.count_basis()
    fid = target.estimate_fidelity(base_count)
    print(f"{n=}: {fid=}")
    data.append(1 - fid)

plt.loglog(ns, data, "o-")
plt.xlabel("num qubits")
plt.ylabel("error (1 - fidelity)")
plt.show()
