# Copyright IBM 2026

"""Test the flamegraph."""

import unittest
import tempfile

from qiskit import QuantumCircuit
from qiskit.transpiler import generate_preset_clifford_t_pass_manager
from qiskit_resource_estimation.graphs import CallGraph, InstructionNode
from qiskit_resource_estimation.error_models import ErrorModel
from qiskit_resource_estimation.graphs.metrics import TCount


class TCounts(ErrorModel[InstructionNode]):
    def __init__(self):
        super().__init__()
        self.pm = generate_preset_clifford_t_pass_manager()

    def supports(self, node):
        return isinstance(node, InstructionNode)

    def evaluate(self, node):
        circuit = QuantumCircuit(node.num_qubits())
        circuit.append(node.instruction, circuit.qubits)

        cliff_t = self.pm.run(circuit)

        counts = cliff_t.count_ops()
        return {TCount(): counts.get("t", 0) + counts.get("tdg", 0)}


class TestFlamegraph(unittest.TestCase):
    """Flamegraph test."""

    def test_tcount(self):
        # single block with 2 T
        block1 = QuantumCircuit(1, name="block1")
        block1.t(0)
        block1.t(0)

        # nested block with 5 T
        block2 = QuantumCircuit(2, name="block2")
        block2.append(block1.to_instruction(), [0])
        block2.append(block1.to_instruction(), [1])
        block2.tdg(0)

        circuit = QuantumCircuit(3, name="root")
        circuit.t(0)
        circuit.h(0)
        circuit.ccx(0, 1, 2)
        circuit.append(block1.to_instruction(), [0])
        circuit.append(block2.to_instruction(), [1, 2])

        f = tempfile.NamedTemporaryFile("w+")
        graph = CallGraph.from_circuit(circuit)
        graph.dump_flamegraph(
            f.name,
            TCount(),
            error_models=[TCounts()],
            overwrite=True,
            basis=["ccx", "t", "tdg", "h"],
        )

        expected = {
            "root(1x); h(1x) 0",
            "root(1x); t(1x) 1",
            "root(1x); ccx(1x) 7",
            "root(1x); block1(1x); t(2x) 2",
            "root(1x); block2(1x); block1(2x); t(2x) 4",
            "root(1x); block2(1x); tdg(1x) 1",
        }

        actual = set(line.strip() for line in f.readlines())
        self.assertEqual(expected, actual)


if __name__ == "__main__":
    unittest.main()
