# Copyright IBM 2025.

"""An example on QPE."""

import numpy as np
from time import time

from qiskit.circuit import QuantumCircuit
from qiskit.circuit.library import PauliEvolutionGate, phase_estimation
from qiskit.quantum_info import SparseObservable

from ft_resource_estimation.graphs import CallGraph, InstructionNode
from ft_resource_estimation.error_models import GrossErrorModel, TwoGrossErrorModel
from ft_resource_estimation.topologies import Linear
from ft_resource_estimation.error_models.bicycle.routing import TeleportationRouting
from ft_resource_estimation.topologies.topology import Allocation


def estimate_qpe(n: int, num_eval_qubits: int) -> QuantumCircuit:
    # define the Hamiltonian for QPE
    hamiltonian = SparseObservable.from_sparse_list(
        [(term, [i, i + 1], -1) for i in range(n - 1) for term in ["XX", "YY", "ZZ"]]
        + [("Z", [i], 0.5) for i in range(n)],
        num_qubits=n,
    )

    # build the unitary
    unitary = PauliEvolutionGate(hamiltonian, time=0.1)

    # define the initial state -- here we use a placeholder
    qc = QuantumCircuit(n)
    qc.h(qc.qubits)
    initial = qc.to_gate()

    # build the QPE circuit
    circuit = QuantumCircuit(num_eval_qubits + n)
    qpe = phase_estimation(num_eval_qubits, unitary)
    circuit.append(initial, circuit.qubits[-n:])
    circuit.compose(qpe, inplace=True)

    # inst = circuit.to_instruction()

    # define the error model and topology
    topo = Linear(num_modules=circuit.num_qubits // 11 + 1)
    # routing = TeleportationRouting(allocation=Allocation.WORST)
    routing = None  # or SwapRouting()
    error_model = TwoGrossErrorModel(topology=topo, p=4, routing=routing)

    basis = ["qft_dg", "PauliEvolution"]
    # basis = [inst.name]
    # basis = None

    # build the call graph and estimate metrics
    start = time()

    graph = CallGraph.from_circuit(circuit)
    # graph = CallGraph(InstructionNode(inst))
    # print(graph.count_basis(basis))
    metrics = graph.estimate(
        basis=basis,
        error_models={InstructionNode: error_model},
    )
    end = time()

    return metrics, end - start


data = {}

num_eval_qubits = 20
for n in 2 ** np.arange(2, 12):
    datum = {}
    metrics, runtime = estimate_qpe(n, num_eval_qubits)
    print(f"{num_eval_qubits=} {n=} {runtime=}")

    datum["runtime"] = runtime
    for metric, value in metrics.items():
        datum[metric.__class__.__name__] = value

    data[(num_eval_qubits, n)] = datum

np.save("qpe_swaproute_g2p4.npy", data)
