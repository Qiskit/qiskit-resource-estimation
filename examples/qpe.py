# Copyright IBM 2025.

"""An example on QPE."""

from qiskit.circuit import QuantumCircuit
from qiskit.circuit.library import PauliEvolutionGate, phase_estimation
from qiskit.quantum_info import SparseObservable

from ft_resource_estimation.graphs import CallGraph
from ft_resource_estimation.error_models import GrossErrorModel
from ft_resource_estimation.topologies import Linear
from ft_resource_estimation.target import Target

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
num_eval_qubits = 20
circuit = QuantumCircuit(num_eval_qubits + n)

qpe = phase_estimation(num_eval_qubits, unitary)
circuit.append(initial, circuit.qubits[-n:])
circuit.compose(qpe, inplace=True)

print("Circuit counts:")
for item, counts in circuit.count_ops().items():
    print("  ", item, counts)

# define the Target we compile to
error_model = GrossErrorModel(p=4)
topo = Linear(num_modules=n // 11 + 1)
target = Target(topo, error_model)

# create the resource graph from the circuit
graph = CallGraph(circuit)
base_count = graph.count_basis(["qft_dg", "PauliEvolution"])  # count final leafs
print("\n\nResource graph counts")
for item, counts in base_count.items():
    print("  ", item, counts)

# Estimate the fidelity
base_fid = target.estimate_fidelity(base_count)
print("Fidelity:", base_fid)
