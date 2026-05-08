# Copyright IBM 2026.

"""Tests for get_gate_type angle classification across all rotation gate classes."""

import unittest
import numpy as np
from itertools import product
from ddt import ddt, data, unpack
from qiskit.circuit.library import (
    RZGate,
    RYGate,
    PhaseGate,
    RZZGate,
    RXXGate,
    RYYGate,
    RZXGate,
    PauliEvolutionGate,
    PauliProductRotationGate,
)
from qiskit.quantum_info import Pauli, SparsePauliOp

from ft_resource_estimation.error_models.bicycle.compiler import get_gate_type
from ft_resource_estimation.error_models.bicycle.isa import GateType


ROTATION_GATES = [RZGate, RYGate, PhaseGate, RZZGate, RXXGate, RYYGate, RZXGate]


@ddt
class TestRotationGateExactAngles(unittest.TestCase):
    """All standard rotation gate classes share the same angle convention."""

    @data(*ROTATION_GATES)
    def test_pauli_exact(self, gate_cls):
        self.assertEqual(get_gate_type(gate_cls(0)), GateType.Pauli)
        self.assertEqual(get_gate_type(gate_cls(np.pi)), GateType.Pauli)
        self.assertEqual(get_gate_type(gate_cls(2 * np.pi)), GateType.Pauli)

    @data(*ROTATION_GATES)
    def test_clifford_exact(self, gate_cls):
        self.assertEqual(get_gate_type(gate_cls(np.pi / 2)), GateType.Clifford)
        self.assertEqual(get_gate_type(gate_cls(3 * np.pi / 2)), GateType.Clifford)

    @data(*ROTATION_GATES)
    def test_t_exact(self, gate_cls):
        self.assertEqual(get_gate_type(gate_cls(np.pi / 4)), GateType.T)
        self.assertEqual(get_gate_type(gate_cls(3 * np.pi / 4)), GateType.T)

    @data(*ROTATION_GATES)
    def test_rotation(self, gate_cls):
        self.assertEqual(get_gate_type(gate_cls(np.pi / 8)), GateType.Rotation)
        self.assertEqual(get_gate_type(gate_cls(np.pi / 5)), GateType.Rotation)


@ddt
class TestRotationGatePerturbedAngles(unittest.TestCase):
    """Small perturbations around canonical angles should still classify correctly."""

    def setUp(self):
        super().setUp()
        self.eps = 1e-9  # within np.isclose's default atol of 1e-8

    @data(*ROTATION_GATES)
    def test_pauli_perturbed(self, gate_cls):
        eps = self.eps
        self.assertEqual(get_gate_type(gate_cls(np.pi + eps)), GateType.Pauli)
        self.assertEqual(get_gate_type(gate_cls(np.pi - eps)), GateType.Pauli)
        self.assertEqual(get_gate_type(gate_cls(-np.pi + eps)), GateType.Pauli)
        self.assertEqual(get_gate_type(gate_cls(6 * np.pi - eps)), GateType.Pauli)

    @data(*ROTATION_GATES)
    def test_clifford_perturbed(self, gate_cls):
        eps = self.eps
        self.assertEqual(get_gate_type(gate_cls(np.pi / 2 + eps)), GateType.Clifford)
        self.assertEqual(get_gate_type(gate_cls(np.pi / 2 - eps)), GateType.Clifford)
        self.assertEqual(get_gate_type(gate_cls(-7 * np.pi / 2 - eps)), GateType.Clifford)
        self.assertEqual(get_gate_type(gate_cls(-3 * np.pi / 2 + eps)), GateType.Clifford)

    @data(*ROTATION_GATES)
    def test_t_perturbed(self, gate_cls):
        eps = self.eps
        self.assertEqual(get_gate_type(gate_cls(np.pi / 4 + eps)), GateType.T)
        self.assertEqual(get_gate_type(gate_cls(np.pi / 4 - eps)), GateType.T)
        self.assertEqual(get_gate_type(gate_cls(7 * np.pi / 4 + eps)), GateType.T)
        self.assertEqual(get_gate_type(gate_cls(-23 * np.pi / 4 + eps)), GateType.T)

    @data(*ROTATION_GATES)
    def test_large_perturbation_gives_rotation(self, gate_cls):
        self.assertEqual(get_gate_type(gate_cls(np.pi / 4 + 1e-5)), GateType.Rotation)
        self.assertEqual(get_gate_type(gate_cls(np.pi / 2 + 1e-5)), GateType.Rotation)


PAULI_OPS = ["Z", "XX", "YIZYZXXYZ"]


@ddt
class TestPauliGateClassification(unittest.TestCase):
    """Covers PauliProductRotationGate and PauliEvolutionGate across multiple Pauli operators.

    All test angles follow the RZ convention. _gate multiplies by 2 for "evo" to account
    for PauliEvolutionGate's halved-angle convention.
    """

    def _gate(self, label, angle, kind):
        if kind == "ppr":
            return PauliProductRotationGate(Pauli(label), angle)

        return PauliEvolutionGate(SparsePauliOp(label), time=2 * angle)

    @data(*product(PAULI_OPS, ("ppr", "evo")))
    @unpack
    def test_pauli_exact(self, label, kind):
        self.assertEqual(get_gate_type(self._gate(label, 0, kind)), GateType.Pauli)
        self.assertEqual(get_gate_type(self._gate(label, np.pi, kind)), GateType.Pauli)
        self.assertEqual(get_gate_type(self._gate(label, 2 * np.pi, kind)), GateType.Pauli)

    @data(*product(PAULI_OPS, ("ppr", "evo")))
    @unpack
    def test_clifford_exact(self, label, kind):
        self.assertEqual(get_gate_type(self._gate(label, np.pi / 2, kind)), GateType.Clifford)
        self.assertEqual(get_gate_type(self._gate(label, 3 * np.pi / 2, kind)), GateType.Clifford)

    @data(*product(PAULI_OPS, ("ppr", "evo")))
    @unpack
    def test_t_exact(self, label, kind):
        self.assertEqual(get_gate_type(self._gate(label, np.pi / 4, kind)), GateType.T)
        self.assertEqual(get_gate_type(self._gate(label, 3 * np.pi / 4, kind)), GateType.T)

    @data(*product(PAULI_OPS, ("ppr", "evo")))
    @unpack
    def test_rotation(self, label, kind):
        self.assertEqual(get_gate_type(self._gate(label, np.pi / 8, kind)), GateType.Rotation)
        self.assertEqual(get_gate_type(self._gate(label, np.pi / 5, kind)), GateType.Rotation)

    @data(*product(PAULI_OPS, ("ppr", "evo")))
    @unpack
    def test_pauli_perturbed(self, label, kind):
        eps = 1e-9
        self.assertEqual(get_gate_type(self._gate(label, np.pi + eps, kind)), GateType.Pauli)
        self.assertEqual(get_gate_type(self._gate(label, np.pi - eps, kind)), GateType.Pauli)

    @data(*product(PAULI_OPS, ("ppr", "evo")))
    @unpack
    def test_clifford_perturbed(self, label, kind):
        eps = 1e-9
        self.assertEqual(get_gate_type(self._gate(label, np.pi / 2 + eps, kind)), GateType.Clifford)
        self.assertEqual(get_gate_type(self._gate(label, np.pi / 2 - eps, kind)), GateType.Clifford)

    @data(*product(PAULI_OPS, ("ppr", "evo")))
    @unpack
    def test_t_perturbed(self, label, kind):
        eps = 1e-9
        self.assertEqual(get_gate_type(self._gate(label, np.pi / 4 + eps, kind)), GateType.T)
        self.assertEqual(get_gate_type(self._gate(label, np.pi / 4 - eps, kind)), GateType.T)

    @data(*product(PAULI_OPS, ("ppr", "evo")))
    @unpack
    def test_large_perturbation_gives_rotation(self, label, kind):
        self.assertEqual(
            get_gate_type(self._gate(label, np.pi / 4 + 1e-5, kind)), GateType.Rotation
        )
        self.assertEqual(
            get_gate_type(self._gate(label, np.pi / 2 + 1e-5, kind)), GateType.Rotation
        )


if __name__ == "__main__":
    unittest.main()
