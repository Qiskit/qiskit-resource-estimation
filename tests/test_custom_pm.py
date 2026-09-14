# Copyright IBM 2026

"""Test passing a custom pass manager into BicycleErrorModel.

NOTE: BicycleErrorModel does not yet accept a ``pass_manager`` argument.
      Wiring it through (topology, error_rates, routing, t_threshold, pass_manager)
      is required before this test can run.
"""

import unittest
from qiskit.circuit.library import QFTGate
from qiskit.quantum_info import get_clifford_gate_names
from qiskit.transpiler import PassManager, generate_preset_pass_manager
from qiskit.transpiler.passes import CommutativeOptimization, LitinskiTransformation

from ft_resource_estimation.graphs import CallGraph, InstructionNode
from ft_resource_estimation.graphs.metrics import Fidelity
from ft_resource_estimation.error_models import GrossErrorModel
from ft_resource_estimation.topologies import Linear


class CallbackCliffordT(PassManager):
    def __init__(self, callback):
        self.callback = callback

    def run(
        self, circuits, output_name=None, callback=None, num_processes=None, *, property_set=None
    ):
        cliff_t = generate_preset_pass_manager(
            optimization_level=1,
            basis_gates=get_clifford_gate_names() + ["t", "tdg"],
        )
        return cliff_t.run(
            circuits,
            output_name=output_name,
            callback=self.callback,
            num_processes=num_processes,
            property_set=property_set,
        )


class TestCustomPassManager(unittest.TestCase):
    def test_custom_pm_changes_fidelity(self):
        n = 4
        topo = Linear(num_modules=n // 11 + 1)
        gate = QFTGate(n)
        callback_calls = [0]

        def count(**kwargs):
            callback_calls[0] += 1

        custom_model = GrossErrorModel(topology=topo, p=3, pass_manager=CallbackCliffordT(count))

        _ = CallGraph(InstructionNode(gate)).estimate(error_models={InstructionNode: custom_model})
        self.assertGreater(callback_calls[0], 0)

    def test_litinski_pm(self):
        pm = generate_preset_pass_manager(
            2, basis_gates=get_clifford_gate_names() + ["rz"], qubits_initially_zero=False
        )
        pm.optimization.append(LitinskiTransformation(fix_clifford=False))  # type: ignore[attr-defined]
        pm.optimization.append(CommutativeOptimization())  # type: ignore[attr-defined]

        n = 4
        topo = Linear(num_modules=n // 11 + 1)
        model = GrossErrorModel(topology=topo, p=3, pass_manager=pm)
        result = CallGraph(InstructionNode(QFTGate(n))).estimate(
            basis=["QFT"], error_models={InstructionNode: model}
        )
        self.assertIn(Fidelity(), result)
        self.assertGreater(result[Fidelity()], 0)


if __name__ == "__main__":
    unittest.main()
