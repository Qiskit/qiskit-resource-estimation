# Copyright IBM 2025.

"""An approximate QFT (i.e., with angle cutoff)."""

import numpy as np
from qiskit.circuit import QuantumCircuit, Parameter
from qiskit.circuit.library import HGate, CPhaseGate
from ft_resource_estimation.graphs.dictionary_instruction import DictionaryGate
from ft_resource_estimation.graphs.nodes import Node


class AQFT(DictionaryGate):
    r"""A QFT where small angles are omitted.

    TODO The threshold is :math:`\lceil\log_2(n)\rceil - 1` but I don't understand it.
    """

    def __init__(self, num_qubits: int, threshold: float = None):
        self.threshold = (
            threshold if threshold is not None else int(np.ceil(np.log2(num_qubits))) - 1
        )
        super().__init__(name="AQFT", num_qubits=num_qubits, params=[])

    def operations(self) -> dict[Node, int]:
        """Textbook QFT from Nielsen and Chuang book"""
        n = self.num_qubits
        threshold = self.threshold

        h = HGate()
        cphase = CPhaseGate(Parameter("x"))

        # count the number of cphase gates:
        count = 0
        for i in range(n):
            for _j in range(i + 1, min(n, i + 1 + threshold)):
                count += 1

        operations = {Node(cphase): count, Node(h): n}
        return operations

    def _define(self):
        n = self.num_qubits
        qc = QuantumCircuit(n, name=self.name)
        for i in range(n):
            qc.h(n - 1 - i)
            for j in range(i + 1, min(n, i + 1 + self.threshold)):
                qc.cp(np.pi / 2 ** (j - i), n - 1 - j, n - 1 - i)

        self.definition = qc
