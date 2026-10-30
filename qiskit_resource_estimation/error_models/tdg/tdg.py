# Copyright IBM 2026

from typing import Literal

from qiskit.circuit import QuantumCircuit
from qiskit.transpiler import PassManager, generate_preset_pbc_pass_manager

from qiskit_resource_estimation.error_models.tdg.bicycle_architecture import estimate

from ...graphs.nodes import Node, InstructionNode
from ...graphs.metrics import Metric, Value, AdditiveMetric
from ..error_model import ErrorModel


class TotalError(AdditiveMetric): ...


class Automorphisms(AdditiveMetric): ...


class JointMeasurements(AdditiveMetric): ...


class Measurements(AdditiveMetric): ...


class TdGErrorModel(ErrorModel[InstructionNode]):
    """Tour de Gross error model based on ``bicycle-architecture-compiler`` [1].

    Args:
        code: The bicycle code variant ("gross" or "two_gross").
        physical_error: Physical error rate ("1e-3" or "1e-4").
        accuracy: The RZ synthesis accuracy for gridsynth.
        pbc_pass_manager: A pass manager compiling the input circuits into PBC format.
            Per default, this uses ``qiskit.transpiler.generate_preset_pbc_pass_manager()``.

    References:

    [1] https://github.com/qiskit-community/bicycle-architecture-compiler
    """

    def __init__(
        self,
        code: Literal["gross", "two_gross"],
        physical_error: Literal["1e-3", "1e-4"],
        epsilon: str = "1e-10",
        pbc_pass_manager: PassManager | None = None,
    ):
        super().__init__()
        self._code = code
        self._p = physical_error
        self._epsilon = epsilon
        if pbc_pass_manager is None:
            pbc_pass_manager = generate_preset_pbc_pass_manager()

        self._pm = pbc_pass_manager

    def supports(self, node: Node) -> bool:
        return isinstance(node, InstructionNode)

    def evaluate(self, node: InstructionNode) -> dict[Metric, Value]:
        circuit = QuantumCircuit(node.num_qubits(), node.num_clbits())
        circuit.append(node.instruction, circuit.qubits, circuit.clbits)
        pbc = self._pm.run(circuit)

        data = estimate(pbc, self._code, self._p, self._epsilon)
        return {
            TotalError(): data["total_error"],
            Automorphisms(): data["counts"].get("automorphisms", 0),
            JointMeasurements(): data["counts"].get("joint_measurements", 0),
            Measurements(): data["counts"].get("measurements", 0),
        }
