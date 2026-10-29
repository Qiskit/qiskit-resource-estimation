# Copyright IBM 2026

from typing import Literal, Any
from qiskit.circuit import QuantumCircuit

def estimate(
    circuit: QuantumCircuit,
    code: Literal["gross", "two_gross"],
    physical_error: Literal["1e-3", "1e-4"],
    epsilon: str,
) -> dict[str, Any]: ...
