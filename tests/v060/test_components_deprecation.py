"""injectq.components is deprecated in 0.6 (removed in 0.7) and loaded lazily."""

from __future__ import annotations

import subprocess
import sys

import pytest

from ._helpers import xf


def _run(code: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        [sys.executable, "-W", "always", "-c", code],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def test_import_injectq_does_not_import_components():
    proc = _run(
        "import sys, injectq\n"
        "print('injectq.components' in sys.modules)\n"
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "False"


def test_import_injectq_emits_no_deprecation_warning():
    proc = _run(
        "import warnings\n"
        "with warnings.catch_warnings(record=True) as w:\n"
        "    warnings.simplefilter('always')\n"
        "    import injectq\n"
        "print([str(x.message) for x in w if issubclass(x.category, DeprecationWarning)])\n"
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "[]"


def test_importing_components_emits_deprecation_warning():
    proc = _run(
        "import warnings\n"
        "with warnings.catch_warnings(record=True) as w:\n"
        "    warnings.simplefilter('always')\n"
        "    import injectq.components\n"
        "print(any(issubclass(x.category, DeprecationWarning) and 'omponent' in str(x.message) for x in w))\n"
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "True"


def test_root_level_component_names_resolve_lazily_with_warning():
    proc = _run(
        "import sys, warnings, injectq\n"
        "assert 'injectq.components' not in sys.modules\n"
        "with warnings.catch_warnings(record=True) as w:\n"
        "    warnings.simplefilter('always')\n"
        "    cls = injectq.ComponentContainer\n"
        "assert cls.__name__ == 'ComponentContainer'\n"
        "print(any(issubclass(x.category, DeprecationWarning) for x in w))\n"
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "True"


def test_using_component_container_warns():
    with pytest.warns(DeprecationWarning):
        from injectq.components import ComponentContainer

        ComponentContainer()
