.PHONY: uv check format test lock build publish

uv:
	which uv || curl -LsSf https://astral.sh/uv/install.sh | sh
check: uv
	uv tool run ruff check
format: uv
	uv tool run ruff format
test: check
	uv run --with pytest --with requests -m pytest
build: test
	rm -rf dist/* build/*
	uv build
publish: build
	uv run --with twine -m twine upload dist/*
