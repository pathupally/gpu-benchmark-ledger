PYTHON ?= python3
export PYTHONPATH := src

.PHONY: all build validate test serve clean

all: validate build test

validate:
	$(PYTHON) -m benchmark_ledger validate

build:
	$(PYTHON) -m benchmark_ledger build

test:
	$(PYTHON) -m unittest discover -s tests -v

serve: build
	$(PYTHON) -m benchmark_ledger serve

clean:
	$(PYTHON) -m benchmark_ledger clean

