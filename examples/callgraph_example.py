# Copyright IBM 2025.

"""An example on how to use the callgraph with Qiskit ``Instruction``s."""

from qiskit.circuit import QuantumCircuit
from qiskit.circuit.library import QFTGate, MCXGate
from ft_resource_estimation.graphs import CallGraph
from ft_resource_estimation.error_models import GrossErrorModel
from ft_resource_estimation.topologies import Linear
from ft_resource_estimation.target import Target
from ft_resource_estimation.library import Add


def build_circuit(num_qubits):
    qft = QFTGate(num_qubits)
    mcx = MCXGate(num_qubits - 1)

    circuit = QuantumCircuit(num_qubits)
    for _ in range(4):
        circuit.append(qft, circuit.qubits)
    circuit.append(mcx, circuit.qubits)

    # note this will currently use the default definitions of the gates
    graph = CallGraph(circuit)

    base_count = graph.count_basis()  # count final leafs
    for node, count in base_count.items():
        print(node.name(), count)

    # show off some other functionality..
    high_count = graph.count_basis(["cp", "h", "swap"])  # dont unroll CP/H/SWAP
    for node, count in high_count.items():
        print(node.name(), count)

    cxcount = graph.count("cx")  # count CX gates
    print("cx:", cxcount)

    return base_count


# define the Target we compile to
num_qubits = 20
error_model = GrossErrorModel(p=3)
topo = Linear(num_modules=num_qubits // 11 + 1)
target = Target(topo, error_model)

# first we build a call graph from a circuit
base_count = build_circuit(num_qubits)
base_fid = target.estimate_fidelity(base_count)
print("\nCircuit example:")
print("Estimated fidelity:", base_fid)

# but we can also use the library and defined instructions there
add = Add(num_qubits, apply_qft=True)
graph = CallGraph(add)
base_count = graph.count_basis()
base_fid = target.estimate_fidelity(base_count)
print("\nGate example:")
print("Estimated fidelity:", base_fid)
