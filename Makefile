# Copyright IBM 2026

.PHONY: black ruff type headers check test

all: check test

check: black ruff type headers

type:
	pyrefly check --summarize-errors

black:
	black qiskit_resource_estimation examples 

ruff:
	ruff check qiskit_resource_estimation examples

headers:
	./check_headers.sh

test:
	python -m unittest discover tests/
