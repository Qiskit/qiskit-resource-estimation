# Copyright IBM 2026.

"""Error rates for the bicycle ISA."""

from dataclasses import dataclass
from mpmath import mp

DEFAULT_DPS = 200


@dataclass
class ErrorRates:
    """Physical error rates for the bicycle ISA operations."""

    idle: mp.mpf
    inter_block_measure: mp.mpf
    in_block_measure: mp.mpf
    automorphism: mp.mpf
    inject_t: mp.mpf


def gross_code(p: int, dps: int = DEFAULT_DPS) -> ErrorRates:
    """Return the Gross code error rates for a given physical error exponent.

    Args:
        p: Physical error rate exponent — 3 for 1e-3, 4 for 1e-4.
        dps: Decimal precision for mpmath arithmetic.
    """
    mp.dps = dps
    if p == 3:
        return ErrorRates(
            idle=mp.mpf(0),
            inter_block_measure=mp.mpf(10 ** (-2.7)),
            in_block_measure=mp.mpf(1e-5),
            automorphism=mp.mpf(10 ** (-6.4)),
            inject_t=mp.mpf(10 ** (-5.5)),
        )

    if p == 4:
        return ErrorRates(
            idle=mp.mpf(0),
            inter_block_measure=mp.mpf(10 ** (-7.3)),
            in_block_measure=mp.mpf(1e-9),
            automorphism=mp.mpf(1e-12),
            inject_t=mp.mpf(10 ** (-7.4)),
        )

    raise ValueError(f"Invalid p: {p}")
