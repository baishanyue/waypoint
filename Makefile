.PHONY: test demo bench lint

test:
	python3 -m pytest -q

demo:
	python3 -m waypoint run --goal "research hybrid retrieval"

bench:
	python3 benchmarks/bench.py

lint:
	python3 -m compileall -q src
