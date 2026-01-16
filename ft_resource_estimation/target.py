# Copyright IBM 2025.

"""The compile target."""

from collections.abc import Sequence
import numpy as np

from qiskit.circuit import QuantumCircuit, ParameterExpression
from qiskit.quantum_info import get_clifford_gate_names
from qiskit.compiler import transpile
from qiskit.transpiler.passes import CommutativeOptimization

from .graphs.nodes import Node
from .transformations import PBCTransformation
from .topologies.topology import BaseTopology
from .error_models.error_model import BicycleErrorModel, GateType


CLIFFORD_GATES = get_clifford_gate_names()
BASIS_GATES = CLIFFORD_GATES + ["rz", "rzz"]


class Target:
    """The compile target."""

    def __init__(self, topology: BaseTopology, error_model: BicycleErrorModel):
        """
        Args:
            topology: The topology of the compile target.
            error_model: The error model of the compile target.
        """
        self._topology = topology
        self._errors = error_model

    def compile(self, node: Node, location: Sequence[int]) -> float:
        """Return the fidelity of a single node on a location."""
        if node.num_qubits() != len(location):
            raise ValueError(
                f"Location (length {len(location)}) does not "
                f"match number of qubits ({node.num_qubits()}))."
            )

        # transpile the node to the location into clifford + rz + rzz, and cancel out commutations
        # append the instruction to a circuit
        num_qubits = node.num_qubits()
        circuit = QuantumCircuit(num_qubits)
        circuit.append(node._inst, range(num_qubits))
        # transpile to clifford + rzz, rz, p and cp
        tqc = transpile(circuit, optimization_level=2, basis_gates=BASIS_GATES + ["p", "cp"])
        # merge/optimize rotations that commute
        copt = CommutativeOptimization()
        opt_qc = copt(tqc)
        # transpile back to clifford + rz + rzz
        node_transpiled = transpile(
            opt_qc,
            optimization_level=2,
            basis_gates=BASIS_GATES,
            initial_layout=location,
            coupling_map=self._topology.coupling_map(),
        )

        # compile to pbc
        pbc = PBCTransformation()
        node_pbc = pbc(node_transpiled)

        # last commutative optimization pass
        node_transpiled = copt(node_pbc)

        # compute the fidelity from the resulting circuit
        node_fidelity = 1
        indices = {qubit: index for index, qubit in enumerate(node_transpiled.qubits)}
        # iterate through the circuit instructions
        for instruction in node_transpiled.data:
            qubits = [indices[q] for q in instruction.qubits]
            locality = self._topology.locality(qubits)
            if len(qubits) == 1:
                num_blocks = 0
            else:
                num_blocks = self._topology.block_distance(*qubits)
            total_span = num_blocks
            # get the gate type (T, Pauli, Clifford, Rotation, Measure)
            gate_type = get_gate_type(instruction)

            # for non-clifford gates the total span should take into account the distance to the
            # nearest factory
            if gate_type in {GateType.T, GateType.Rotation}:
                total_span += self._topology.magic_distance(*qubits)

            # finally add the errors arising from the inter block measurments
            node_fidelity *= self._errors.gate_fidelity(total_span, locality, gate_type)

        return node_fidelity

    def estimate_fidelity(self, counts: dict[Node, int]) -> float:
        """Accumulate the fidelity in a counts dictionary.

        Args:
            counts: A dict with ``{node: count}`` pairs.

        Returns:
            The product of all errors, to the power of the counts.
        """
        fidelity = 1.0
        for node, count in counts.items():
            location = self._topology.allocate(node)  # allocate to the average location
            cost = self.compile(node, location)
            overhead = self.average_routing_overhead(node.num_qubits())

            fidelity *= (cost * overhead) ** count

        return fidelity

    # TODO Enable this once we want to look at specific routing overheads.
    # def route(self, origin: Sequence[int], dest: Sequence[int]) -> float:
    #     """Return the routing overhead (in terms of error) from ``origin`` to ``dest``."""
    #     raise NotImplementedError

    def average_routing_overhead(self, num_qubits: int) -> float:
        """Return the average routing overhead for an operation of size ``num_qubits``."""
        total_span = self._topology.average_routing_overhead(num_qubits)

        # The cost of a SWAP gate is (XX + YY + ZZ) pi/4 rotations. The cost is then that of 3
        # two-local clifford gates
        swap_fidelity = self._errors.gate_fidelity(2, 2, True) ** (3 * total_span)

        # in total there are `num_qubit` SWAPS
        return swap_fidelity**num_qubits


def get_gate_type(inst) -> GateType:
    """Works for circuits containing measurements, Cliffords, P/RX/RY/RZ and PauliEvolutionGates."""
    name = inst.name

    if name == "measure":
        return GateType.Measure

    # julien: hotpatch p to rz
    if name == "p":
        name = "rz"

    if name in {"rx", "ry", "rz", "PauliEvolution"}:
        angle = inst.params[0]
        if isinstance(angle, ParameterExpression):
            # for parameterized angles, we cannot assume they are clifford
            return GateType.Rotation
        # The angle in PauliEvolutions is defined without the /2 factor
        if name != "PauliEvolution":
            angle *= 2

        # under this definition of `angle`, the gate implements cos(angle)I - isin(angle)P
        # therefore pauli gates are multiples of pi / 2
        if np.isclose(angle % np.pi / 2, 0):
            return GateType.Pauli
        # multiples of pi / 4 are cliffords (I + iP) / sqrt(2)
        elif np.isclose(angle % np.pi / 4, 0):
            return GateType.Clifford
        # multiples of pi / 8 are T gates
        elif np.isclose(angle % np.pi / 8, 0):
            return GateType.T
        # otherwise it's an arbitrary rotation
        else:
            return GateType.Rotation
    # the following cases shouldn't be reachable under the current workflow because we convert
    # to PBC before this method is called. Added for completeness
    elif name in {"x", "y", "z"}:
        return GateType.Pauli
    elif name == "t":
        return GateType.T
    elif name in CLIFFORD_GATES:
        return GateType.Clifford
    else:
        return GateType.Rotation
