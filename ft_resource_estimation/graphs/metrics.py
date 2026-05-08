# Copyright IBM 2026

"""Base for metrics."""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any

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

    def __hash__(self):
        return hash(type(self))

    def __eq__(self, other):
        return type(self) is type(other)


class Fidelity(Metric):
    """Multiplicative fidelity metric."""

    def combine(self, a: Value, b: Value) -> Value:
        return a * b

    def repeat(self, value: Value, count: int) -> Value:
        return value**count

    def identity(self) -> Value:
        return 1


class TCount(Metric):
    """Additive T-gate count metric."""

    def combine(self, a: Value, b: Value) -> Value:
        return a + b

    def repeat(self, value: Value, count: int) -> Value:
        return value * count

    def identity(self) -> Value:
        return 0


class InFidelity(Fidelity): ...


class InterFidelity(Fidelity): ...


class TFidelity(Fidelity): ...


class RoutingFidelity(Fidelity): ...
