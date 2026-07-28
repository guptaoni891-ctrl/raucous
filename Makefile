.PHONY: install format lint typecheck test build bundle check clean

install:
	python -m pip install -e ".[dev]"

format:
	ruff format src tests

lint:
	ruff check src tests

typecheck:
	mypy src/vinylpulse/config.py src/vinylpulse/pulse_audio.py src/vinylpulse/soundcard_audio.py src/vinylpulse/spectrum.py src/vinylpulse/spotify_parser.py

test:
	pytest

build:
	python -m build

bundle:
	pyinstaller --noconfirm --clean vinylpulse.spec

check: lint typecheck test build

clean:
	rm -rf build dist .pytest_cache .mypy_cache .ruff_cache src/*.egg-info
