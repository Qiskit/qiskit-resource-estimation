# Copyright IBM 2026

"""Compiler for the bicycle code architecture."""

from __future__ import annotations

from mpmath import mp

from qiskit.circuit import AncillaRegister, QuantumCircuit, ParameterExpression
from qiskit.transpiler import PassManager, generate_preset_pass_manager
from qiskit.transpiler.passes import CommutativeOptimization, ConvertToPauliRotations
from qiskit.quantum_info import get_clifford_gate_names

from .error_rates import ErrorRates
from .isa import GateType
from ...graphs.nodes import AngleClass, InstructionNode, angle_class
from ...topologies.topology import BaseTopology

CLIFFORD_GATES = get_clifford_gate_names()
BASIS_GATES = CLIFFORD_GATES + ["rz", "rzz"]

ANGLE_CLASS_TO_GATE_TYPE = {
    AngleClass.PAULI: GateType.Pauli,
    AngleClass.CLIFFORD: GateType.Clifford,
    AngleClass.T: GateType.T,
    AngleClass.ROTATION: GateType.Rotation,
}


def get_gate_type(inst) -> GateType:
    """Classify a circuit instruction into a GateType.

    Works for measurements, Cliffords, P/RX/RY/RZ, and PauliEvolutionGates.
    """
    name = inst.name

    if name == "measure":
        return GateType.Measure

    if name == "reset":
        return GateType.Ignore

    # hotpatch p to rz
    if name == "p":
        name = "rz"

    if name in {
        "rx",
        "ry",
        "rz",
        "rzz",
        "ryy",
        "rxx",
        "rzx",
        "PauliEvolution",
        "pauli_product_rotation",
    }:
        angle = inst.params[0]
        if isinstance(angle, ParameterExpression):
            return GateType.Rotation
        # The angle in PauliEvolutions is defined without the /2 factor
        if name == "PauliEvolution":
            angle /= 2

        return ANGLE_CLASS_TO_GATE_TYPE[angle_class(angle)]
    elif name in {"x", "y", "z"}:
        return GateType.Pauli
    elif name == "t":
        return GateType.T
    elif name in CLIFFORD_GATES:
        return GateType.Clifford
    else:
        return GateType.Rotation


def gate_fidelity(
    total_span: int,
    locality: int,
    gate_type: GateType,
    error_rates: ErrorRates,
    t_threshold: int = 200,
) -> tuple[mp.mpf, mp.mpf, mp.mpf, mp.mpf]:
    """Return the fidelity of a gate given its defining parameters.

    By convention ``total_span`` counts the number of edges between modules rather than
    the total number of modules, because the error formulas always involve total modules
    minus one.

    Args:
        total_span: The number of module edges the gate spans.
        locality: The number of modules with non-identity Pauli operations.
        gate_type: The type of gate.
        error_rates: The physical error rates for the bicycle ISA.
        t_threshold: Number of T gates used to synthesise an arbitrary rotation.
    """
    er = error_rates

    if gate_type in [GateType.Pauli, GateType.Ignore]:
        return mp.mpf(1), mp.mpf(1), mp.mpf(1), mp.mpf(1)

    in_meas_fid = 1 - er.in_block_measure
    aut_fid = 1 - er.automorphism

    if gate_type == GateType.Measure:
        fidelity = in_meas_fid * (aut_fid**2)
        return fidelity, fidelity, mp.mpf(1), mp.mpf(1)

    inter_meas_fid = 1 - er.inter_block_measure
    t_fid = 1 - er.inject_t

    in_fidelity = ((aut_fid**2) * in_meas_fid) ** (19 + locality)
    in_fidelity *= aut_fid**2
    in_fidelity *= in_meas_fid**total_span

    t_fidelity = mp.mpf(1)
    if gate_type == GateType.T:
        t_fidelity *= t_fid
    elif gate_type == GateType.Rotation:
        t_fidelity *= t_fid**t_threshold

    inter_fidelity = inter_meas_fid**total_span

    fidelity = in_fidelity * t_fidelity * inter_fidelity

    return fidelity, in_fidelity, t_fidelity, inter_fidelity


def default_pm():
    staged_pm = generate_preset_pass_manager(
        2, basis_gates=BASIS_GATES, qubits_initially_zero=False
    )
    # run additional commutative optimization, to PBC, and commutative optimization again
    staged_pm.optimization.append(CommutativeOptimization())  # type: ignore[attr-defined]
    staged_pm.optimization.append(ConvertToPauliRotations())  # type: ignore[attr-defined]
    staged_pm.optimization.append(CommutativeOptimization())  # type: ignore[attr-defined]

    return staged_pm


def compile(
    node: InstructionNode,
    location: list[int],
    topology: BaseTopology,
    error_rates: ErrorRates,
    t_threshold: int = 200,
    pass_manager: PassManager | None = None,
) -> tuple[mp.mpf, mp.mpf, mp.mpf, mp.mpf]:
    """Transpile a node to the bicycle ISA at the given location and return its fidelity.

    Args:
        node: The node to compile.
        location: Qubit indices on the topology to compile to.
        topology: The hardware topology.
        error_rates: The physical error rates for the bicycle ISA.
        t_threshold: Number of T gates used to synthesise an arbitrary rotation.
    """
    if node.num_qubits() != len(location):
        raise ValueError(
            f"Location (length {len(location)}) does not "
            f"match number of qubits ({node.num_qubits()})."
        )

    num_qubits = node.num_qubits()
    num_ancilla = topology.num_ancilla_qubits()
    circuit = QuantumCircuit(num_qubits)

    if num_ancilla > 0:
        ancilla_register = AncillaRegister(num_ancilla)
        circuit.add_register(ancilla_register)
        # For now we assume the ancillas are all in state 0
        circuit.reset(ancilla_register)
        circuit.barrier()

    if (inst := node.instruction) is not None:
        circuit.append(inst, range(num_qubits))
    else:
        raise ValueError(f"Cannot compile node {node}: no circuit representation available.")

    if pass_manager is None:
        pass_manager = default_pm()

    # transpile to clifford + rzz + rz, optimise commutations
    node_transpiled = pass_manager.run(circuit)

    # accumulate per-gate fidelity
    fidelity = mp.mpf(1)
    in_fidelity = mp.mpf(1)
    t_fidelity = mp.mpf(1)
    inter_fidelity = mp.mpf(1)

    ancilla_location = topology.allocate_ancilla() if num_ancilla > 0 else []
    all_locations = list(location) + ancilla_location
    indices = {qubit: all_locations[i] for i, qubit in enumerate(node_transpiled.qubits)}
    for instruction in node_transpiled.data:
        qubits = [indices[q] for q in instruction.qubits]
        locality = topology.locality(qubits)
        num_blocks = 0 if len(qubits) == 1 else topology.block_distance(min(qubits), max(qubits))
        total_span = num_blocks
        g_type = get_gate_type(instruction)

        if g_type in {GateType.T, GateType.Rotation}:
            total_span += topology.magic_distance(max(qubits))

        fid, in_fid, t_fid, inter_fid = gate_fidelity(
            total_span, locality, g_type, error_rates, t_threshold
        )
        fidelity *= fid
        in_fidelity *= in_fid
        t_fidelity *= t_fid
        inter_fidelity *= inter_fid

    return fidelity, in_fidelity, t_fidelity, inter_fidelity
