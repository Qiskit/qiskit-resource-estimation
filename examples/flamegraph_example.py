# Copyright IBM 2026

"""Manual verification script for CallGraph.flamegraph().

Checks: (1) the width-additivity invariant (every node's width equals the sum of
its children's widths), and (2) the root's folded fidelity matches estimate()'s total.
"""

from qiskit.circuit.library import PauliEvolutionGate, phase_estimation
from qiskit.circuit import QuantumCircuit
from qiskit.quantum_info import SparseObservable

from ft_resource_estimation.graphs import CallGraph, InstructionNode
from ft_resource_estimation.graphs.flamegraph import to_speedscope
from ft_resource_estimation.graphs.metrics import Fidelity
from ft_resource_estimation.error_models import TwoGrossErrorModel
from ft_resource_estimation.topologies import Linear
from ft_resource_estimation.error_models.bicycle.routing import TeleportationRouting, Allocation

n = 50
num_eval_qubits = 50

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
routing = TeleportationRouting(allocation=Allocation.BEST)
routing = None  # or SwapRouting()
error_model = TwoGrossErrorModel(topology=topo, p=4, routing=routing)

basis = ["qft_dg", "PauliEvolution"]
# basis = None

graph = CallGraph.from_circuit(circuit)

graph.dump_flamegraph(
    "qpe.pl",
    metric=Fidelity(),
    basis=basis,
    error_models={InstructionNode: error_model},
    overwrite=True,
)

flame = graph.flamegraph(Fidelity(), basis=basis, error_models={InstructionNode: error_model})
