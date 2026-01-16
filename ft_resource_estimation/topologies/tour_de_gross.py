# Copyright IBM 2025.

"""Tour de Gross topology -- linear module connectivity with a single T factory at the beginning."""

from functools import partial
import numpy as np

from ft_resource_estimation.graphs.nodes import BaseNode
from .topology import BaseTopology


class Linear(BaseTopology):
    """Tour de Gross topology -- linear module connectivity with a single T factory at 0."""

    def __init__(self, num_modules: int):
        """
        Args:
            num_modules: The number of modules ("donuts") in the topology.
        """
        default_allocator = partial(linear_allocator, num_modules=num_modules)
        super().__init__(default_allocator)

        self._num_modules = num_modules
        self._qubits_per_module = 11

    def num_qubits(self) -> int:
        return self._num_modules * self._qubits_per_module

    def coupling_map(self) -> list[list[int]]:
        coupling_map = []
        # for the coupling map we take into account the pivot qubit
        qubits_per_module = self._qubits_per_module + 1

        # Intra module connections (all-to-all)
        for m in range(self._num_modules):
            for i in range(qubits_per_module):
                for j in range(i + 1, qubits_per_module):
                    coupling_map.append([m * qubits_per_module + i, m * qubits_per_module + j])
                    coupling_map.append([m * qubits_per_module + j, m * qubits_per_module + i])

        # Inter module connections (adjacent modules connected via qubits 0 and 6)
        special_indices = [0, 6]  # qubits that connect across modules
        for m in range(self._num_modules - 1):
            for q1 in special_indices:
                for q2 in special_indices:
                    coupling_map.append(
                        [m * qubits_per_module + q1, (m + 1) * qubits_per_module + q2]
                    )
                    coupling_map.append(
                        [(m + 1) * qubits_per_module + q2, m * qubits_per_module + q1]
                    )

        return coupling_map

    def magic_distance(self, index1, index2=None):
        """If adjacent to a factory, it returns 1."""
        if index2 is not None:
            index = min(index1, index2)
        else:
            index = index1
        return 1 + index // self._qubits_per_module

    def block_distance(self, index1, index2):
        """Block distance between the two indices, if they lay within the same module, it returns 0."""
        return np.abs(index2 // self._qubits_per_module - index1 // self._qubits_per_module)

    def locality(self, indices):
        """Return the number of different blocks the given indices lay in.

        This corresponds to the number of blocks with non-identity operations."""
        locality = len({index // self._qubits_per_module for index in indices})
        return locality

    def average_routing_overhead(self, num_qubits: int):
        """Return the average number of blocks between the optimal and average location given a
        node with `num_qubits` qubits.
        """
        available_qubits = self.num_qubits()
        if num_qubits > available_qubits:
            raise ValueError(
                "Cannot compute the average location, too many qubits "
                f"({num_qubits} > {available_qubits})"
            )
        mid_chip_idx = available_qubits // 2
        half_qubits = num_qubits // 2
        average_q0_idx = mid_chip_idx - half_qubits

        # the optimal location starts at block 0, so the average displacement is
        return average_q0_idx // self._qubits_per_module


class AllToAll(BaseTopology):
    """All to all module connectivity.

    It assumes T gate factories next to
    each module and that each module is connected to every other module.
    """

    def __init__(self, num_modules: int):
        """
        Args:
            num_modules: The number of modules ("donuts") in the topology.
        """
        default_allocator = partial(linear_allocator, num_modules=num_modules)
        super().__init__(default_allocator)

        self._num_modules = num_modules
        self._qubits_per_module = 11

    def num_qubits(self) -> int:
        return self._num_modules * self._qubits_per_module

    def coupling_map(self) -> list[list[int]]:
        return None

    def magic_distance(self, index1, index2=None):
        """If adjacent to a factory, it returns 1."""
        return 1

    def block_distance(self, index1, index2):
        """Block distance between the two indices, if they lay within the same module, it returns 0."""
        return np.abs(index2 // self._qubits_per_module - index1 // self._qubits_per_module)

    def locality(self, indices):
        """Return the number of different blocks the given indices lay in. This corresponds to the
        number of blocks with non-identity operations.
        """
        locality = len({index // self._qubits_per_module for index in indices})
        return locality

    def average_routing_overhead(self, num_qubits: int):
        """In the all-to-all connectivity we assume no overhead."""
        return 0


def linear_allocator(num_modules: int, node: BaseNode) -> list[int]:
    """An allocator for a linear topology.

    Just returns the first ``node.num_qubits()`` indices, which are associated to the ones
    next to the T factory.

    Returns the optimal location for the given node as a list of qubit indices.

    Args:
        num_modules: The number of modules in the topology.
        node: The node to allocate.

    Raises:
        ValueError: If ``node.num_qubits()`` is too large for the topology.
    """
    qubits_per_module = 11
    available_qubits = num_modules * qubits_per_module
    num_qubits = node.num_qubits()
    if num_qubits > available_qubits:
        raise ValueError(
            f"Node {node.name()} has too many qubits ({num_qubits} > {available_qubits})"
        )

    # TODO build this list once and store as a variable?
    # The first qubit per module is a pivot qubit, which cannot be used for data. The available
    # indices are the remaining 11 qubits below we build a list with indices [1-11], [13-21], etc.
    available_indices = np.concatenate(
        [
            np.arange((qubits_per_module + 1) * k + 1, (qubits_per_module + 1) * (k + 1))
            for k in range(num_modules)
        ]
    )

    return available_indices[:num_qubits]
