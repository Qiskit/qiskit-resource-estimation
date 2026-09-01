# Copyright IBM 2026

"""Tests for BicycleErrorModel / GrossErrorModel behaviour."""

import unittest
from qiskit.circuit import QuantumCircuit

from ft_resource_estimation.graphs.callgraph import CallGraph
from ft_resource_estimation.graphs.nodes import InstructionNode
from ft_resource_estimation.graphs.metrics import Fidelity
from ft_resource_estimation.error_models import GrossErrorModel
from ft_resource_estimation.topologies import Linear


class TestGrossErrorModel(unittest.TestCase):
    def setUp(self):
        self.topo = Linear(num_modules=1)
        self.model = GrossErrorModel(topology=self.topo, p=3)

    def fidelity(self, circuit: QuantumCircuit) -> float:
        graph = CallGraph.from_circuit(circuit)
        result = graph.estimate(error_models={InstructionNode: self.model})
        return float(result[Fidelity()])

    def test_pauli_and_reset_circuit_has_fidelity_one(self):
        """Circuits containing only Pauli gates and resets carry no error."""
        qc = QuantumCircuit(2)
        qc.reset(0)
        qc.x(0)
        qc.y(1)
        qc.z(0)
        qc.reset(1)
        qc.x(1)

        self.assertAlmostEqual(self.fidelity(qc), 1.0)


if __name__ == "__main__":
    unittest.main()
