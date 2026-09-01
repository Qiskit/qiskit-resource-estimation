# Copyright IBM 2025.

"""An example on QPE."""

from qiskit.circuit import QuantumCircuit
from qiskit.circuit.library import PauliEvolutionGate, phase_estimation
from qiskit.quantum_info import SparseObservable

from ft_resource_estimation.graphs import CallGraph, InstructionNode
from ft_resource_estimation.error_models import GrossErrorModel
from ft_resource_estimation.topologies import Linear
from ft_resource_estimation.error_models.bicycle.routing import TeleportationRouting
from ft_resource_estimation.topologies.topology import Allocation

# define the Hamiltonian for QPE
n = 100
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
num_eval_qubits = 100
circuit = QuantumCircuit(num_eval_qubits + n)

qpe = phase_estimation(num_eval_qubits, unitary)
circuit.append(initial, circuit.qubits[-n:])
circuit.compose(qpe, inplace=True)

print("Circuit counts:")
for item, counts in circuit.count_ops().items():
    print("  ", item, counts)

# define the error model and topology
topo = Linear(num_modules=circuit.num_qubits // 11 + 1)
# routing = TeleportationRouting(allocation=Allocation.BEST)
routing = None  # or SwapRouting()
error_model = GrossErrorModel(topology=topo, p=4, routing=routing)

basis = ["qft_dg", "PauliEvolution"]  # or None to unroll fully

# build the call graph and estimate metrics
graph = CallGraph.from_circuit(circuit)

metrics = graph.estimate(
    basis=basis,
    error_models={InstructionNode: error_model},
)

print("\nResource graph counts:")
for node, count in graph.count_basis(basis).items():
    print("  ", node, count)

print("\nMetrics:")
for metric, value in metrics.items():
    print(f"  {type(metric).__name__}: {float(value):.5f}")
