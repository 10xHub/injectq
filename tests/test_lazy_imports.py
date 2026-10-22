"""Test that the decorator exports survive Python 3.15 lazy imports (PEP 810).

A submodule named like a function it exports (``decorators/inject.py`` exporting
``inject``) breaks under lazy imports: loading the submodule for a sibling name
such as ``Inject`` rebinds the package attribute ``inject`` to the module.
"""

import subprocess
import sys
import textwrap

import pytest


# Make only injectq's own imports lazy. Global ``PYTHON_LAZY_IMPORTS=all`` is
# not usable here because pytest itself fails to start under it.
LAZY_PRELUDE = """
import sys
sys.set_lazy_imports_filter(
    lambda importer, name, fromlist: (importer or "").startswith("injectq")
    or name.startswith("injectq")
)
sys.set_lazy_imports("all")
"""

requires_lazy_imports = pytest.mark.skipif(
    not hasattr(sys, "set_lazy_imports"),
    reason="lazy imports need Python 3.15+",
)


def run_python(code: str, *, lazy: bool) -> str:
    source = (LAZY_PRELUDE if lazy else "") + textwrap.dedent(code)
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-c", source],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


# Each case touches a sibling name first, then reads the clashing name.
SIBLING_FIRST = {
    "inject": "injectq.Inject",
    "singleton": "injectq.transient",
    "resource": "injectq.managed_resource",
}


@requires_lazy_imports
@pytest.mark.parametrize(("name", "sibling"), SIBLING_FIRST.items())
def test_export_is_function_under_lazy_imports(name: str, sibling: str) -> None:
    code = f"""
    import injectq
    {sibling}
    print(type(injectq.{name}).__name__)
    """
    assert run_python(code, lazy=True) == "function"


@requires_lazy_imports
def test_inject_decorator_usable_under_lazy_imports() -> None:
    code = """
    from injectq import Inject, inject
    marker = Inject

    @inject
    def handler() -> str:
        return "ok"

    print(handler())
    """
    assert run_python(code, lazy=True) == "ok"


@pytest.mark.parametrize("lazy", [False, True], ids=["eager", "lazy"])
def test_old_submodule_paths_still_import(lazy: bool) -> None:
    if lazy and not hasattr(sys, "set_lazy_imports"):
        pytest.skip("lazy imports need Python 3.15+")
    code = """
    import injectq.decorators as decorators
    from injectq.decorators.inject import Inject, inject
    from injectq.decorators.resource import ResourceError, resource
    from injectq.decorators.singleton import singleton, transient

    assert inject is decorators.inject
    assert resource is decorators.resource
    assert singleton is decorators.singleton
    print(type(decorators.inject).__name__, ResourceError.__name__)
    """
    assert run_python(code, lazy=lazy) == "function ResourceError"
