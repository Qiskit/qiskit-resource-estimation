# Copyright IBM 2025.

"""An example on how to use the callgraph with Qiskit ``Instruction``s."""

from time import time

from ft_resource_estimation.library import Add
from ft_resource_estimation.graphs import CallGraph


def build(num_qubits, use_circuit=False):
    add = Add(num_qubits, apply_qft=True)

    if use_circuit:
        add = add.definition

    return CallGraph(add)


for use_circuit in [False, True]:
    print("Use circuit?", use_circuit)

    for n in [20, 200, 2000]:
        start = time()
        graph = build(n, use_circuit)
        end = time()
        print(f"n = {n} took {time() - start:.3f}s \t\t\t {graph.count_basis()}")
