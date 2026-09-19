# Copyright IBM 2026

"""Base for metrics."""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any
import numpy as np

Value = Any


class Metric(ABC):
    """A metric that can be accumulated across call graph nodes.

    Subclass this to define custom metrics (e.g. fidelity, T-gate count).
    Instances of the same subclass are considered equal as dict keys.
    """

    @abstractmethod
    def combine(self, a: Value, b: Value) -> Value:
        """Combine two metric values (e.g. multiply for fidelity, add for counts)."""
        ...

    @abstractmethod
    def repeat(self, value: Value, count: int) -> Value:
        """Scale a value by a repetition count (e.g. power for fidelity, multiply for counts)."""
        ...

    @abstractmethod
    def identity(self) -> Value:
        """The identity element for combine (e.g. 1.0 for fidelity, 0 for counts)."""
        ...

    def values_to_samples(self, values: list[Value], num_samples: int) -> list[int]:
        """Convert a set of leaf values to samples for a flamegraph representation.

        Args:
            value: The values to convert to samples.
            num_samples: The suggested number of samples. This is only an indicator, and
                the argument is not guaranteed to be used (e.g. if the values are counts already)
                or that the samples exactly sum up to this.

        This is not marked as abstractmethod on purpose, since users might not need to
        construct a flamegraph for their custom nodes and metrics.
        """
        raise NotImplementedError(f"{type(self)} does not support flamegraph width.")

    def __hash__(self):
        return hash(type(self))

    def __eq__(self, other):
        return type(self) is type(other)


class MultiplicativeMetric(Metric):
    """A generic multiplicative metric."""

    def combine(self, a: Value, b: Value) -> Value:
        return a * b

    def repeat(self, value: Value, count: int) -> Value:
        return value**count

    def identity(self) -> Value:
        return 1

    def values_to_samples(self, values, num_samples):
        """Fidelities are multiplicative, but samples are additive in nature.

        To provide an intuition nevertheless, we convert fidelities ``[f_i]_i`` into errors,
        ``e_i = 1 - f_i`` and base samples based on the relation of ``e_i`` to
        ``e_tot = sum(e_i)``.

        Importantly, this does **not** correctly reflect the value of the total fidelity
        ``f_tot = prod(f_i)``, but only provides a visual aid.
        """
        errors = np.array([1 - fid for fid in values])
        total_error = sum(errors)
        # we finally cast the mp.mpf into floats
        samples = [int(np.round(float(v))) for v in num_samples * errors / total_error]
        return samples


class AdditiveMetric(Metric):
    """A generic additive metric."""

    def combine(self, a: Value, b: Value) -> Value:
        return a + b

    def repeat(self, value: Value, count: int) -> Value:
        return value * count

    def identity(self) -> Value:
        return 0

    def values_to_samples(self, values, num_samples):
        # disregard samples, not required here
        return list(map(int, values))


class Fidelity(MultiplicativeMetric):
    """Multiplicative fidelity metric."""

    ...


class TCount(AdditiveMetric):
    """Additive T-gate count metric."""

    ...


class InFidelity(Fidelity): ...


class InterFidelity(Fidelity): ...


class TFidelity(Fidelity): ...


class RoutingFidelity(Fidelity): ...
