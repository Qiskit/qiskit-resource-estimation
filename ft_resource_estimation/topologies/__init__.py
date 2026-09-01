# Copyright IBM 2025

"""The topologies module."""

from .tour_de_gross import Linear
from .all_to_all import AllToAll

__all__ = ["AllToAll", "Linear"]
