# Copyright IBM 2026

.PHONY: black ruff type check test

all: check test

check: black ruff type

type:
	pyrefly check --summarize-errors

black:
	black ft_resource_estimation examples 

ruff:
	ruff check ft_resource_estimation examples

test:
	python -m unittest discover tests/
