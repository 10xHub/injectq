# Contributing to InjectQ

Bug reports, feature requests, documentation fixes, tests and code are all welcome.

## Reporting issues

Open an issue at [github.com/10xhub/injectq/issues](https://github.com/10xhub/injectq/issues) with:

1. A description of the problem.
2. The smallest code that reproduces it.
3. What you expected and what happened (include the traceback).
4. Python version, InjectQ version, OS, and the framework versions if an integration is involved.

## Development setup

You need Python 3.10 or newer, [uv](https://docs.astral.sh/uv/) and Git.

```bash
git clone https://github.com/<your-account>/injectq.git
cd injectq
uv sync                  # installs the project and the dev dependency group
pre-commit install       # optional: ruff, ruff-format, bandit and other hooks
```

Without uv: `pip install -e ".[dev]"`. The `dev` extra covers tests, mypy and the integration frameworks (FastAPI, Taskiq, FastMCP). The documentation tools (MkDocs and plugins) are in the uv `dev` dependency group only.

### Everyday commands

```bash
uv run pytest                          # all tests
uv run pytest tests/v060/test_scopes.py   # one file
uv run pytest -k override              # by name
uv run ruff check .                    # lint (add --fix to fix)
uv run ruff format .                   # format
uv run mypy injectq                    # type check
```

`pytest` is configured in `pyproject.toml`: it always measures coverage of `injectq` and fails below 73%, and `asyncio_mode = "auto"` means `async def` tests need no marker.

`make test` runs `uv run pytest -v`. Other Makefile targets: `make bench`, `make bench-compare` and `make bench-publish` (see [Benchmarks](benchmarks.md)), `make docs-serve` and `make docs-build`.

## Workflow

1. Branch from `main`: `git checkout -b feature/short-name` (or `fix/short-name`).
2. Make the change. Add or update tests, and update the docs if behaviour changed.
3. Run `uv run pytest`, `uv run ruff check .` and `uv run mypy injectq`.
4. Add an entry to [the changelog](changelog.md) for user-visible changes. A breaking change also needs a note in the [migration guide](migration-0.6.md) (or the guide for the release it ships in).
5. Push and open a pull request against `main`. Describe what changed and why, link related issues, and say how you tested it.

CI must pass and a maintainer must approve before a pull request is merged.

## Code style

- Ruff does linting and formatting (line length 88, isort-style imports). Type hints are required on public APIs and checked with mypy in strict mode.
- Docstrings use the Google style.
- Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`, with an optional scope, for example `fix(container): drop cached singleton on rebind`.

## Tests

Tests live in `tests/`. The 0.6 suite is in `tests/v060/` (scopes, overrides, context, decorators, integrations, codegen, testing helpers). Older files sit directly in `tests/`. Put new tests next to the code they cover.

- Use plain functions or classes named `Test*` with `test_*` methods.
- Create a fresh `InjectQ()` in each test, or use `isolated_container()` / `container_fixture()` from `injectq.testing`, so tests share no bindings.
- Do not import names that start with `test_` or `Test` into a test module: pytest would try to collect them.
- Run the suite with `-W error::DeprecationWarning` to catch use of deprecated names.

```python
from injectq import InjectQ, inject


def test_inject_resolves_by_type():
    container = InjectQ()
    container.bind_instance("greeting", "hello")

    @inject(container=container)
    def handler(greeting: str) -> str:
        return f"{greeting}!"

    assert handler() == "hello!"


async def test_aget_creates_singleton_once():
    container = InjectQ()

    class Client: ...

    async def make() -> Client:
        return Client()

    container.bind_factory(Client, make, scope="singleton")
    assert await container.aget(Client) is await container.aget(Client)
```

## Documentation

Docs are Markdown in `docs/`, built with MkDocs Material (navigation in `mkdocs.yml`).

```bash
uv run mkdocs serve      # or: make docs-serve, at http://127.0.0.1:8000
uv run mkdocs build      # or: make docs-build
```

- Examples must run against the current API. Run them before you commit.
- Use relative links between pages.
- Do not edit the tables between `<!-- BENCH:... -->` markers by hand; they are generated (see [Benchmarks](benchmarks.md)).

## Releases

Maintainers release. The version is `__version__` in `injectq/__init__.py` (read by hatch). A release updates the version and the changelog, builds with `make build` (`uv build`), publishes with `make publish` (checks with `twine`, then uploads), and tags the release on GitHub.

InjectQ follows [Semantic Versioning](https://semver.org/). Deprecated names keep working for one minor release with a `DeprecationWarning` before removal.
