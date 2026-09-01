# Copyright IBM 2025

"""An example on how to use the callgraph with Qiskit ``Instruction``s."""

from qiskit.circuit import QuantumCircuit
from qiskit.circuit.library import QFTGate, MCXGate

from ft_resource_estimation.graphs import CallGraph, InstructionNode
from ft_resource_estimation.graphs.metrics import Fidelity
from ft_resource_estimation.error_models import GrossErrorModel
from ft_resource_estimation.topologies import Linear
from ft_resource_estimation.library import Add


def build_circuit(num_qubits):
    qft = QFTGate(num_qubits)
    mcx = MCXGate(num_qubits - 1)

    circuit = QuantumCircuit(num_qubits)
    for _ in range(4):
        circuit.append(qft, circuit.qubits)
    circuit.append(mcx, circuit.qubits)

    graph = CallGraph.from_circuit(circuit)

    base_count = graph.count_basis()  # count final leafs
    for node, count in base_count.items():
        print(node.name(), count)

    # show off some other functionality..
    high_count = graph.count_basis(["cp", "h", "swap"])  # dont unroll CP/H/SWAP
    for node, count in high_count.items():
        print(node.name(), count)

    cxcount = graph.count("cx")  # count CX gates
    print("cx:", cxcount)

    return graph


num_qubits = 20
topo = Linear(num_modules=num_qubits // 11 + 1)
error_model = GrossErrorModel(topology=topo, p=3)

# build a call graph from a circuit and estimate metrics
graph = build_circuit(num_qubits)
metrics = graph.estimate(error_models={InstructionNode: error_model})
print("\nCircuit example:")
print("Estimated fidelity:", metrics[Fidelity()])

# library nodes (Add) are InstructionNode subclasses — same error model applies
add = Add(num_qubits, apply_qft=True)
graph = CallGraph(add)
metrics = graph.estimate(error_models={InstructionNode: error_model})
print("\nGate example:")
print("Estimated fidelity:", metrics[Fidelity()])
