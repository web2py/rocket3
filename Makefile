.PHONY: venv test build deploy
venv:
	python3 -m venv venv
test: venv
	venv/bin/pip install -U requests
	venv/bin/pip install -U pytest
	venv/bin/python -m pytest
build:
	python3 -m pip install --upgrade build
	python3 -m pip install --upgrade twine
	python3 -m build
deploy: build
	python3 -m twine upload dist/*
