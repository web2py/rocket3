.PHONY: uv check format test lock build publish

# Keep the virtualenv out of the (Dropbox-synced) source tree
export UV_PROJECT_ENVIRONMENT := $(HOME)/.venvs$(CURDIR)/venv

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
