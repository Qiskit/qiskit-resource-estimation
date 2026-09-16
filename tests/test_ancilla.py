# Copyright IBM 2026

"""Tests for ancilla qubit support in topology and compiler."""

import unittest
from ddt import ddt, data
from qiskit.circuit import QuantumCircuit
from qiskit.circuit.library import MCXGate
from qiskit import transpile, generate_preset_pass_manager
from qiskit.transpiler import AnalysisPass
from qiskit.transpiler.passes import CommutativeOptimization, ConvertToPauliRotations
from qiskit.quantum_info import get_clifford_gate_names

from qiskit_resource_estimation.graphs.nodes import InstructionNode
from qiskit_resource_estimation.graphs.callgraph import CallGraph
from qiskit_resource_estimation.graphs.metrics import Fidelity
from qiskit_resource_estimation.error_models import GrossErrorModel
from qiskit_resource_estimation.topologies import Linear


class TrackOps(AnalysisPass):
    def run(self, dag):
        self.property_set["op_count"] = dag.count_ops()
        # print(dag.count_ops())


@ddt
class TestAncillaAllocation(unittest.TestCase):
    """Test ancilla allocations."""

    def test_ancilla_indices_are_at_end(self):
        """allocate_ancilla() returns the last num_ancillas available indices."""
        topo = Linear(num_modules=2, num_ancillas=3)
        # 2 modules × 11 data qubits = [1..11, 13..23]; last 3 are [21, 22, 23]
        self.assertEqual(topo.allocate_ancilla(), [21, 22, 23])

    def test_num_ancilla_qubits(self):
        self.assertEqual(Linear(num_modules=2, num_ancillas=5).num_ancilla_qubits(), 5)

    def test_no_ancillas_by_default(self):
        topo = Linear(num_modules=2)
        self.assertEqual(topo.num_ancilla_qubits(), 0)
        self.assertEqual(topo.allocate_ancilla(), [])

    def test_logical_allocation_raises_when_ancillas_exhaust_space(self):
        """Allocating more logical qubits than the non-ancilla budget should raise."""
        # 1 module = 11 data qubits, 5 reserved as ancillas → only 6 usable for logic
        topo = Linear(num_modules=1, num_ancillas=5)
        node = InstructionNode(MCXGate(6))  # 7-qubit node — exceeds the 6-qubit budget
        with self.assertRaises(ValueError):
            topo.allocate(node)

    def test_ancilla_improves_mcx_fidelity(self):
        """MCX should achieve higher fidelity with ancilla qubits available."""
        n_controls = 5
        # gate = MCXGate(n_controls)  # (n_controls + 1)-qubit gate
        num_qubits = n_controls + 1
        num_modules = num_qubits // 11 + 1
        circuit = QuantumCircuit(num_qubits)
        circuit.x(0)
        circuit.mcx(list(range(n_controls)), n_controls)

        topo_no_ancilla = Linear(num_modules=num_modules)
        topo_with_ancilla = Linear(num_modules=num_modules + 1, num_ancillas=11)

        em_no_ancilla = GrossErrorModel(topology=topo_no_ancilla, p=3)
        em_with_ancilla = GrossErrorModel(topology=topo_with_ancilla, p=3)

        # node = InstructionNode(gate)
        graph = CallGraph.from_circuit(circuit)
        fidelity_no_ancilla = graph.estimate(
            basis=["mcx"], error_models={InstructionNode: em_no_ancilla}
        )[Fidelity()]

        fidelity_with_ancilla = graph.estimate(
            basis=["mcx"], error_models={InstructionNode: em_with_ancilla}
        )[Fidelity()]

        self.assertGreater(fidelity_with_ancilla, fidelity_no_ancilla)

    @data(0, 1, 2, 5, 10)
    def test_ancilla_decomposition(self, num_ancillas):
        """Test the circuit decomposition with ancillas."""
        # We build an MCX circuit with 5 controls and Hadamards on all controls.
        # The resource estimation tool will compile the MCX instruction only and compare
        # it to Qiskit's transpiler with clean input qubits (the controls are flagged as dirty
        # due to the Hadamards) and we compare the final counts
        n_controls = 5
        num_qubits = n_controls + 1
        circuit = QuantumCircuit(num_qubits)
        circuit.h(range(n_controls))
        circuit.mcx(list(range(n_controls)), n_controls)
        basis_gates = get_clifford_gate_names() + ["rz"]
        staged_pm = generate_preset_pass_manager(
            2, basis_gates=basis_gates, qubits_initially_zero=False
        )
        # add a custom operation tracker
        staged_pm.optimization.append(TrackOps())  # type: ignore[attr-defined]

        # Set the bicycle topology, including the ancillas
        num_modules = (num_qubits + num_ancillas) // 11 + 1
        topo = Linear(num_modules=num_modules + 1, num_ancillas=num_ancillas)
        em = GrossErrorModel(topology=topo, p=3, pass_manager=staged_pm)

        # Run the estimation, triggering the pass
        graph = CallGraph.from_circuit(circuit)
        _ = graph.estimate(basis=["mcx"], error_models={InstructionNode: em})

        # Get the reference count
        reference = QuantumCircuit(num_qubits + num_ancillas)
        reference.compose(circuit, list(range(num_qubits)), inplace=True)
        ref_transpiled = transpile(
            reference,
            basis_gates=basis_gates,
            coupling_map=topo.coupling_map(),
            qubits_initially_zero=True,
        )

        # Compare the two (remember to deduct the Hadamards)
        counts = staged_pm.property_set["op_count"]
        for op, ref_count in ref_transpiled.count_ops().items():
            if op == "h":
                self.assertEqual(ref_count - n_controls, counts.get(op, 0))
            else:
                self.assertEqual(ref_count, counts.get(op, 0))


if __name__ == "__main__":
    unittest.main()
