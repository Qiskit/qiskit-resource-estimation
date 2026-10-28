# Copyright IBM 2026

import unittest

from qiskit.circuit import QuantumCircuit, Parameter
from qiskit.circuit.library import PauliEvolutionGate
from qiskit.transpiler import generate_preset_pbc_pass_manager
from qiskit.quantum_info import SparseObservable

from qiskit_resource_estimation._bicycle import estimate


class TestCustomPassManager(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.pm = generate_preset_pbc_pass_manager()

    def test_estimate(self):
        bell = QuantumCircuit(2)
        bell.h(0)
        bell.cx(0, 1)

        err = estimate(self.pm.run(bell), "gross", "1e-3", "1e-10")
        print(err)
        self.assertGreater(err, 0.0)

    def test_parameterized_circuit(self):
        qc = QuantumCircuit(1)
        qc.h(0)
        qc.p(Parameter("i do not belong here"), 0)
        qc.x(0)

        pbc = self.pm.run(qc)
        with self.assertRaises(TypeError):
            estimate(pbc, "gross", "1e-3", "1e-10")

    def test_non_pbc_circuit(self):
        bell = QuantumCircuit(2)
        bell.h(0)
        bell.cx(0, 1)

        with self.assertRaises(TypeError):
            estimate(bell, "gross", "1e-3", "1e-10")

    def test_empty(self):
        err = estimate(QuantumCircuit(), "gross", "1e-3", "1e-10")
        self.assertEqual(err, 0.0)

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
        evo = PauliEvolutionGate(obs, time=1 / reps).definition

        circuit = QuantumCircuit(num_qubits, num_qubits)
        for _ in range(reps):
            circuit.compose(evo, circuit.qubits, inplace=True)

        for i, _ in enumerate(circuit.qubits):
            circuit.measure(i, i)

        pbc = self.pm.run(circuit)

        errs = {
            "gross3": estimate(pbc, "gross", "1e-3", "1e-10"),
            "gross4": estimate(pbc, "gross", "1e-4", "1e-10"),
            "twogross3": estimate(pbc, "two_gross", "1e-3", "1e-10"),
            "twogross4": estimate(pbc, "two_gross", "1e-4", "1e-10"),
        }

        self.assertGreater(errs["twogross4"], 0)
        self.assertGreater(errs["twogross3"], errs["twogross4"])
        self.assertGreater(errs["gross4"], errs["twogross3"])
        self.assertGreater(errs["gross3"], errs["gross4"])
