# Copyright IBM 2025.

"""A dictionary-based instruction, possible without definition."""

from __future__ import annotations
import typing
from abc import ABC, abstractmethod
from qiskit.circuit import Instruction, Gate

if typing.TYPE_CHECKING:
    from .nodes import Node  # pylint: disable=cyclic-import


class DictionaryMixin(ABC):
    """A dictionary-based instruction, possible without definition."""

    @abstractmethod
    def operations(self) -> dict[Node, int]:
        """Get the operation counts."""
        raise NotImplementedError


class DictionaryInstruction(Instruction, DictionaryMixin):
    """A dictionary-based instruction, possible without definition."""


class DictionaryGate(Gate, DictionaryMixin):
    """A dictionary-based gate, possible without definition."""
