# Copyright IBM 2025.

"""Rewrite a circuit into PBC."""

from __future__ import annotations
from numpy import pi

from qiskit.circuit.library import PauliEvolutionGate
from qiskit.dagcircuit import DAGCircuit
from qiskit.quantum_info import SparseObservable
from qiskit.transpiler.basepasses import TransformationPass


class PBCTransformation(TransformationPass):
    """Write a QuantumCircuit in Pauli Rotations."""

    def __init__(self):
        super().__init__()
        # map gates to the list of equivalent Pauli rotations. Each element of the list is of the form
        # (Pauli string, phase rescale factor, global phase update, [qubit indices]). For gates that
        # didn't have a phase (e.g. X) the phase rescale factor is simply the phase of the rotation
        # gate. The convention is
        # `original_gate = PauliEvolutionGate(pauli, phase) * e^{i global_phase_update}`
        self._gate_to_pbc = {
            "x": [("X", pi / 2, pi / 2, [0])],
            "y": [("Y", pi / 2, pi / 2, [0])],
            "z": [("Z", pi / 2, pi / 2, [0])],
            "h": [
                ("Z", pi / 4, pi / 6, [0]),
                ("X", pi / 4, pi / 6, [0]),
                ("Z", pi / 4, pi / 6, [0]),
            ],
            "s": [("Z", pi / 4, pi / 4, [0])],
            "sx": [("X", pi / 4, pi / 4, [0])],
            "sdg": [("Z", -pi / 4, -pi / 4, [0])],
            "cx": [
                ("XZ", pi / 4, -pi / 12, [0, 1]),
                ("Z", -pi / 4, -pi / 12, [0]),
                ("X", -pi / 4, -pi / 12, [1]),
            ],
            "cz": [
                ("ZZ", pi / 4, -pi / 12, [0, 1]),
                ("Z", -pi / 4, -pi / 12, [0]),
                ("Z", -pi / 4, -pi / 12, [1]),
            ],
            "cy": [
                ("YZ", pi / 4, -pi / 12, [0, 1]),
                ("Z", -pi / 4, -pi / 12, [0]),
                ("Y", -pi / 4, -pi / 12, [1]),
            ],
            "swap": [
                ("XX", pi / 4, pi / 12, [0, 1]),
                ("YY", pi / 4, pi / 12, [0, 1]),
                ("ZZ", pi / 4, pi / 12, [0, 1]),
            ],
            "iswap": [("XX", -pi / 4, 0, [0, 1]), ("YY", -pi / 4, 0, [0, 1])],
            "dcx": [
                ("XZ", pi / 4, -pi / 12, [0, 1]),
                ("Z", -pi / 4, -pi / 12, [0]),
                ("X", -pi / 4, -pi / 12, [1]),
                ("ZX", pi / 4, -pi / 12, [0, 1]),
                ("Z", -pi / 4, -pi / 12, [1]),
                ("X", -pi / 4, -pi / 12, [0]),
            ],
            "rz": [("Z", 1 / 2, 0, [0])],
            "rzz": [("ZZ", 1 / 2, 0, [0, 1])],
        }

    def run(self, dag: DAGCircuit):
        """
        Run the PBCTransformation pass on `dag`.

        Args:
            dag: the directed acyclic graph to run on.

        Returns:
            DAGCircuit: Transformed DAG.
        """
        out = dag.copy_empty_like()
        global_phase_update = 0
        for node in dag.topological_op_nodes():
            # map node to PBC. A single gate can result in more than one Pauli rotation
            pauli_rotation_list = self._gate_to_pbc.get(node.op.name)
            # check that the node can be mapped to rotations
            if pauli_rotation_list is not None:
                for pauli, phase, phase_update, qubit_indices in pauli_rotation_list:
                    global_phase_update += phase_update
                    # check if the node was a rotation
                    if len(node.params) != 0:
                        phase *= node.params[0]
                    pauli_gate = PauliEvolutionGate(SparseObservable(pauli), phase)
                    # update the qargs
                    qargs = tuple(node.qargs[idx] for idx in qubit_indices)
                    # append instruction
                    out.apply_operation_back(pauli_gate, qargs, node.cargs)
            # append special instructions without transformation
            elif node.op.name in ["measure", "reset", "delay", "barrier"]:
                out.apply_operation_back(node.op, node.qargs, node.cargs)
            else:
                raise ValueError(f"Unsuported operation: {node.op.name}")

        if global_phase_update != 0:
            out.global_phase += phase_update

        return out
