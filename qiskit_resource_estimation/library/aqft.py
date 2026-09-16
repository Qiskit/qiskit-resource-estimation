# Copyright IBM 2025

"""An approximate QFT (i.e., with angle cutoff)."""

import numpy as np
from qiskit.circuit import QuantumCircuit
from qiskit.circuit.library import HGate, CPhaseGate

from qiskit_resource_estimation.graphs.nodes import InstructionNode, Node


class AQFT(InstructionNode):
    r"""A QFT where small angles are omitted.

    TODO The threshold is :math:`\lceil\log_2(n)\rceil - 1` but I don't understand it.
    """

    def __init__(self, num_qubits: int, threshold: int | None = None):
        super().__init__()
        self._num_qubits = num_qubits
        if threshold is None:
            threshold = int(np.ceil(np.log2(num_qubits))) - 1
            if threshold < 0:
                raise ValueError("num_qubits too small, getting negative threshold")

        self.threshold = threshold

    def name(self):
        return "AQFT"

    def num_qubits(self):
        return self._num_qubits

    def __hash__(self):
        return hash(("AQFT", self._num_qubits, self.threshold))

    def operations(self) -> dict[Node, int]:
        """Textbook QFT from Nielsen and Chuang book"""
        n = self._num_qubits
        threshold = self.threshold

        h = HGate()
        cphase = CPhaseGate(1.0)

        count = 0
        for i in range(n):
            for _j in range(i + 1, min(n, i + 1 + threshold)):
                count += 1

        return {InstructionNode(cphase): count, InstructionNode(h): n}

    def definition(self) -> QuantumCircuit:
        """Return the Qiskit circuit definition."""
        n = self._num_qubits
        qc = QuantumCircuit(n, name=self.name())
        for i in range(n):
            qc.h(n - 1 - i)
            for j in range(i + 1, min(n, i + 1 + self.threshold)):
                qc.cp(np.pi / 2 ** (j - i), n - 1 - j, n - 1 - i)
        return qc
