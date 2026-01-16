# Copyright IBM 2026.

.PHONY: black ruff

black:
	black ft_resource_estimation examples 

ruff:
	ruff check ft_resource_estimation examples
