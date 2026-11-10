# Copyright IBM 2026

import unittest

from qiskit.circuit import QuantumCircuit
from qiskit.circuit.library import PauliEvolutionGate
from qiskit.quantum_info import SparseObservable

from qiskit_resource_estimation import CallGraph
from qiskit_resource_estimation.error_models.tdg import (
    TdGErrorModel,
    TotalError,
    Automorphisms,
    JointMeasurements,
    Measurements,
)


class TestTdGErrorModel(unittest.TestCase):
    """Test the TdG error model."""

    def test_integration(self):
        """Build a circuit to compile to Gross code ISA."""
        num_qubits = 100
        obs = SparseObservable.from_sparse_list(
            [("Z", [i], 0.5) for i in range(num_qubits)]
            + [
                (inter, [i, i + 1], -1)
                for i in range(num_qubits - 1)
                for inter in ("XX", "YY", "ZZ")
            ],
            num_qubits=num_qubits,
        )

        reps = 100
        evo = PauliEvolutionGate(obs, time=1 / reps)

        circuit = QuantumCircuit(num_qubits, num_qubits)
        for _ in range(reps):
            circuit.append(evo, circuit.qubits)

        for i, _ in enumerate(circuit.qubits):
            circuit.measure(i, i)

        model = TdGErrorModel("two_gross", "1e-3")
        graph = CallGraph.from_circuit(circuit)
        data = graph.estimate(basis=["PauliEvolution"], error_models=[model])

        self.assertGreater(data[TotalError()], 0.0)
        self.assertGreater(data[Automorphisms()], 0)
        self.assertGreater(data[Measurements()], 0)
        self.assertGreater(data[JointMeasurements()], 0)
