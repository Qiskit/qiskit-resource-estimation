# Copyright IBM 2025.

"""Base topology."""

from __future__ import annotations
from abc import ABC, abstractmethod
from collections.abc import Callable
from enum import Enum

from ft_resource_estimation.graphs.nodes import Node


class Allocation(Enum):
    BEST = 0
    AVG = 1
    WORST = 2


class BaseTopology(ABC):
    """Base topology."""

    def __init__(self, default_allocator: Callable[[Node, Allocation], list[int]]):
        """
        Args:
            default_allocator: A topology needs a default allocator for nodes.
        """
        self._allocator = default_allocator

    def set_allocator(self, allocator: Callable[[Node, Allocation], list[int]]):
        """Set a new allocator to use."""
        self._allocator = allocator

    def allocate(self, node: Node, allocation: Allocation = Allocation.BEST) -> list[int]:
        """Get the location of a node."""
        return self._allocator(node, allocation)

    def num_ancilla_qubits(self) -> int:
        """The number of ancilla qubits available for compilation."""
        return 0

    def allocate_ancilla(self) -> list[int]:
        """Return topology indices reserved for ancilla qubits."""
        return []

    @abstractmethod
    def num_qubits(self) -> int:
        """The number of qubits."""
        raise NotImplementedError

    @abstractmethod
    def coupling_map(self) -> list[list[int]] | None:
        """The coupling map of the topology"""
        raise NotImplementedError

    @abstractmethod
    def magic_distance(self, index1: int, index2: int | None = None) -> int:
        """Return the distance to the magic factory, counted in blocks.

        The neighboring block of the magic factory would have distance 1.

        Args:
            index: The qubit index (not the block index).

        Returns:
            The block distance to the magic factory.
        """
        raise NotImplementedError

    @abstractmethod
    def block_distance(self, index1: int, index2: int) -> int:
        """Return the distance, counted in blocks, in between two qubits.

        Two qubits inside the same block would have distance 0.

        Args:
            index1: The first qubit index.
            index2: The other qubit index.

        Returns:
            The block distance of the qubits.
        """
        raise NotImplementedError

    @abstractmethod
    def locality(self, indices: list[int]) -> int:
        """The locality of an operation is the number of different blocks in which
        non-identity operations are applied.

        Args:
            indices: A list of qubit indices where non-identity operations are applied.

        Returns:
            The number of different blocks involved in the list of indices.
        """
        raise NotImplementedError

    @abstractmethod
    def average_routing_overhead(self, num_qubits: int) -> int:
        """Return the average number of blocks between the optimal and average location
        given a node with `num_qubits` qubits.

        Args:
            num_qubits: The number of qubits.

        Returns:
            The number of blocks the swaps will span.
        """
        raise NotImplementedError
