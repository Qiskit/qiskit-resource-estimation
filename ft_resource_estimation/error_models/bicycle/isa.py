# Copyright IBM 2026.

"""ISA and Gate enums."""

from enum import Enum


class GateType(Enum):
    Pauli = 0
    T = 1
    Clifford = 2
    Rotation = 3
    Measure = 4
    Ignore = 5  # instruction to ignore in the cost model
