# Makefile for PyAgenity packaging, publishing, and docs

.PHONY: build publish testpublish clean test test-cov docs-serve docs-build docs-deploy

# Build and upload with uv-managed tools, so the result doesn't depend on
# whichever virtualenv (and twine version) happens to be active.
build:
	rm -rf dist
	uv build

publish: build
	uvx twine check dist/*
	uvx twine upload dist/*

testpublish: build
	uvx twine check dist/*
	uvx twine upload --repository testpypi dist/*

clean:
	rm -rf dist build *.egg-info site

test:
	uv run pytest -v

test-cov:
	uv run pytest --cov=pyagenity --cov-report=html --cov-report=term-missing --cov-report=xml -v

# ---------- Docs Section ----------
docs-serve:
	@echo "Serving docs at http://127.0.0.1:8000"
	mkdocs serve -a 127.0.0.1:8000

docs-build:
	# Build docs without strict mode to avoid aborting on warnings
	mkdocs build

# Deploy to GitHub Pages
docs-deploy: docs-build
	uv pip install mkdocs ghp-import
	ghp-import -n -p -f site
	@echo "✅ Docs deployed to GitHub Pages"
