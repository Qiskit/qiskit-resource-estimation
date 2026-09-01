# Copyright IBM 2025

"""All-to-all connectivity."""

from functools import partial
import numpy as np
from .topology import BaseTopology
from .tour_de_gross import linear_allocator


class AllToAll(BaseTopology):
    """All to all module connectivity.

    It assumes T gate factories next to
    each module and that each module is connected to every other module.
    """

    def __init__(self, num_modules: int, num_ancillas: int = 0):
        """
        Args:
            num_modules: The number of modules ("donuts") in the topology.
            num_ancillas: Number of ancilla qubits reserved at the far end of the chain.
        """
        default_allocator = partial(
            linear_allocator, num_modules=num_modules, num_ancillas=num_ancillas
        )
        super().__init__(default_allocator)

        self._num_modules = num_modules
        self._qubits_per_module = 11
        available = np.concatenate(
            [
                np.arange(
                    (self._qubits_per_module + 1) * k + 1, (self._qubits_per_module + 1) * (k + 1)
                )
                for k in range(num_modules)
            ]
        )
        self._ancilla_indices = available[-num_ancillas:].tolist() if num_ancillas > 0 else []

    def num_qubits(self):
        return self._num_modules * self._qubits_per_module

    def num_ancilla_qubits(self):
        return len(self._ancilla_indices)

    def allocate_ancilla(self):
        return self._ancilla_indices

    def coupling_map(self):
        return None

    def magic_distance(self, index1: int, index2=None):  # noqa: ARG002
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

    def average_routing_overhead(self, num_qubits):
        """In the all-to-all connectivity we assume no overhead."""
        return 0
