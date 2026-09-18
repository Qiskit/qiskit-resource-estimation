# Copyright IBM 2026

from qiskit.circuit.library import QFTGate, get_standard_gate_name_mapping
from qrisp import QuantumFloat
from qrisp.block_encodings import BlockEncoding
from qrisp.operators import X, Z

from qiskit_resource_estimation.graphs import CallGraph, InstructionNode, Node

NAME_MAP = get_standard_gate_name_mapping()
NAME_MAP["gphase"] = NAME_MAP["global_phase"]


class Block(Node):
    def __init__(self, block: BlockEncoding, var: QuantumFloat):
        super().__init__()
        self.block = block
        self.var = var

    def name(self):
        return "BlockEncoding"

    def num_qubits(self):
        return self.var.num_qubits()

    def __hash__(self):
        return hash(("BlockEncoding", self.num_qubits))

    def operations(self) -> dict[Node, int]:
        resources = self.block.resources(self.var)
        return {
            InstructionNode(NAME_MAP[name]): count
            for name, count in resources["gate counts"].items()
        }


class Qubitization(Node):
    def __init__(self, num_ancillas: int, block: BlockEncoding, var: QuantumFloat) -> None:
        self.block = Block(block, var)
        self.num_ancillas = num_ancillas

    def name(self):
        return "Qubitization"

    def num_qubits(self):
        return self.num_ancillas + self.block.num_qubits

    def __hash__(self):
        return hash(("Qubitization", self.num_ancillas, self.num_block))

    def operations(self) -> dict[Node, int]:
        return {
            InstructionNode(QFTGate(self.num_ancillas)): 1,
            self.block: self.num_ancillas,
        }


hamiltonian = X(0) * X(1) + 0.5 * Z(0) * Z(1)
block = BlockEncoding.from_operator(hamiltonian)
algo = Qubitization(50, block, QuantumFloat(2))

graph = CallGraph(algo)
print(graph.count_basis())
