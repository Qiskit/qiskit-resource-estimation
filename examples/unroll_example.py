# Copyright IBM 2026

"""An example on unrolling."""

from time import time
from qiskit import transpile
from qiskit.circuit import QuantumCircuit
from qiskit.circuit.library import PauliEvolutionGate, phase_estimation
from qiskit.quantum_info import SparseObservable

from qiskit_resource_estimation.graphs import CallGraph

# define the Hamiltonian for QPE
n = 1000
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
num_eval_qubits = 500
circuit = QuantumCircuit(num_eval_qubits + n)

qpe = phase_estimation(num_eval_qubits, unitary)
circuit.append(initial, circuit.qubits[-n:])
circuit.compose(qpe, inplace=True)

print("Circuit counts:")
for item, counts in circuit.count_ops().items():
    print("  ", item, counts)

# build the call graph and estimate metrics
start = time()
graph = CallGraph.from_circuit(circuit)
print(graph.count_basis(), "in", time() - start)


start = time()
unrolled = transpile(circuit, basis_gates=["u", "cx"], optimization_level=0)
print(unrolled.count_ops(), "in", time() - start)
