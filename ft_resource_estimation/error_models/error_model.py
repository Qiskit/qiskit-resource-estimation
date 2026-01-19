# Copyright IBM 2025.

"""The error model base class."""

from abc import ABC, abstractmethod
from enum import Enum
from mpmath import mp

DEFAULT_DPS = 200


# pylint: disable=invalid-name
class BicycleISA(Enum):
    """The bicycle ISA."""

    Idle = 0
    Automorphism = 1
    InBlockMeasure = 2
    InterBlockMeasure = 3
    InjectT = 4


class GateType(Enum):
    Pauli = 0
    T = 1
    Clifford = 2
    Rotation = 3
    Measure = 4


class BicycleErrorModel(ABC):
    """The error model base class."""

    def __init__(self, errors: dict[BicycleISA, mp.mpf]):
        self._errors = errors
        self._t_threshold = 200

    def query(self, operation: BicycleISA) -> float:
        """Query the error for an operation."""
        return self._errors[operation]

    @abstractmethod
    def gate_fidelity(self, total_span: int, locality: int, gate_type: GateType) -> float:
        """Returns the fidelity of a given its defining parameters.

        Args:
            total_span: The number of modules the gate spans.
            locality: The number of modules that need to implement non-identity Pauli operations.
            gate_type: The type of gate.

        Returns:
            A float representing the fidelity of the gate.
        """
        raise NotImplementedError


class GrossErrorModel(BicycleErrorModel):
    """Gross code error model."""

    def __init__(self, p: int, dps: int = DEFAULT_DPS):
        """
        Args:
            p: Indicate the physical error; 3 for 1e-3 and 4 for 1e-4.
        """
        errors = None
        mp.dps = dps
        if p == 3:
            errors = {
                BicycleISA.Idle: 0,
                BicycleISA.InterBlockMeasure: mp.mpf(10 ** (-2.7)),
                BicycleISA.InBlockMeasure: mp.mpf(1e-5),
                BicycleISA.Automorphism: mp.mpf(10 ** (-6.4)),
                BicycleISA.InjectT: mp.mpf(10 ** (-5.5)),
            }
        elif p == 4:
            errors = {
                BicycleISA.Idle: 0,
                BicycleISA.InterBlockMeasure: mp.mpf(10 ** (-7.3)),
                BicycleISA.InBlockMeasure: mp.mpf(1e-9),
                BicycleISA.Automorphism: mp.mpf(1e-12),
                BicycleISA.InjectT: mp.mpf(10 ** (-7.4)),
            }
        else:
            raise ValueError(f"Invalid p: {p}")

        super().__init__(errors)

    def gate_fidelity(self, total_span: int, locality: int, gate_type: GateType):
        """By convention `total_span` counts the number of edges between modules rather
        than the total number of modules. This is because the error formulas always involve
        total number of modules minus one.
        """
        # Pauli gates are for free
        if gate_type == GateType.Pauli:
            return 1

        # get BycycleISA fidelities
        in_meas_fid = 1 - self.query(BicycleISA.InBlockMeasure)
        aut_fid = 1 - self.query(BicycleISA.Automorphism)

        if gate_type == GateType.Measure:
            return in_meas_fid * (aut_fid**2)

        # get the remaining BycycleISA fidelities
        inter_meas_fid = 1 - self.query(BicycleISA.InterBlockMeasure)
        t_fid = 1 - self.query(BicycleISA.InjectT)

        # Compute the fidelity of the gate
        fidelity = 1

        # update fidelity with the comb
        fidelity *= ((aut_fid**2) * (in_meas_fid)) ** (19 + locality)
        fidelity *= aut_fid**2
        # in module measurements cost
        fidelity *= in_meas_fid**total_span
        # check whether the gate is non clifford and update error arising from T gates
        if gate_type == GateType.T:
            fidelity *= t_fid
        elif gate_type == GateType.Rotation:
            fidelity *= t_fid**self._t_threshold
        # finally add the errors arising from the inter block measurments
        fidelity *= inter_meas_fid**total_span

        return fidelity
