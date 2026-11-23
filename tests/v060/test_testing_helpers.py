"""injectq.testing regressions (plan 1.2 'Testing helpers')."""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
import warnings
from pathlib import Path

import pytest

from injectq import ContainerContext, InjectQ


REPO_ROOT = Path(__file__).resolve().parents[2]


class Dep:
    pass


# --- renamed helpers ---------------------------------------------------------


def test_renamed_helpers_are_exported():
    import injectq.testing as t

    for name in ("container_fixture", "isolated_container", "MockModule"):
        assert hasattr(t, name), name
        assert name in t.__all__, name
    # none of the new names may look like a pytest-collectable / hook name
    assert not t.container_fixture.__name__.startswith(("pytest_", "test"))
    assert not t.isolated_container.__name__.startswith("test")
    assert not t.MockModule.__name__.startswith("Test")


def test_isolated_container_yields_container():
    from injectq.testing import isolated_container

    with isolated_container() as c:
        c.bind(Dep, Dep)
        assert isinstance(c.get(Dep), Dep)


def test_mock_module_binds_mocks_and_values():
    from injectq.testing import MockModule

    c = InjectQ()
    c.install_module(MockModule().mock(Dep).bind_value("k", 1))
    assert c.get("k") == 1
    assert c.get(Dep) is not None


def test_old_test_container_warns():
    from injectq.testing import test_container

    with pytest.warns(DeprecationWarning), test_container():
        pass


def test_old_test_module_warns():
    from injectq.testing import TestModule

    with pytest.warns(DeprecationWarning):
        TestModule()


def test_old_pytest_container_fixture_warns():
    from injectq.testing import pytest_container_fixture

    with pytest.warns(DeprecationWarning):
        pytest_container_fixture()


def test_old_names_still_importable():
    """Guard: deprecated aliases stay importable until 0.7."""
    from injectq.testing import (  # noqa: F401
        TestModule,
        pytest_container_fixture,
        test_container,
    )


# --- container visibility ----------------------------------------------------


def test_test_container_visible_while_context_active():
    from injectq.testing import test_container

    outer = InjectQ()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        with ContainerContext.use(outer), test_container() as t:
            assert InjectQ.get_instance() is t


def test_override_dependency_on_factory_key():
    from injectq.testing import override_dependency

    c = InjectQ()
    c.bind_factory("k", lambda: "real")
    with override_dependency("k", "fake", container=c):
        assert c.get("k") == "fake"


# --- pytest plumbing (run in a clean subprocess) -------------------------------


def _run_pytest(tmp_path: Path, conftest: str, test: str):
    (tmp_path / "conftest.py").write_text(textwrap.dedent(conftest))
    (tmp_path / "test_sample.py").write_text(textwrap.dedent(test))
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    env.pop("PYTEST_ADDOPTS", None)
    return subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            "-W",
            "ignore::DeprecationWarning",
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def test_container_fixture_in_conftest_works(tmp_path):
    proc = _run_pytest(
        tmp_path,
        """
        from injectq.testing import container_fixture

        container = container_fixture()
        """,
        """
        def test_uses_fixture(container):
            container.bind("k", 1)
            assert container.get("k") == 1
        """,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_renamed_helpers_not_collected_as_tests(tmp_path):
    proc = _run_pytest(
        tmp_path,
        "",
        """
        from injectq.testing import isolated_container, MockModule

        def test_real():
            assert True
        """,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "1 passed" in proc.stdout
    assert "warning" not in proc.stdout.lower()


def test_mock_factory_caches_per_type_and_kwargs():
    from injectq.testing import MockFactory

    f = MockFactory()
    a = f.create_mock(Dep, name="a")
    assert f.create_mock(Dep, name="a") is a
    b = f.create_mock(Dep, name="b")
    assert b is not a
    assert b.name == "b"
    assert type(a).__name__ == "MockDep"


def test_isolated_container_restores_global_and_context():
    from injectq.testing import isolated_container

    glob = InjectQ.get_instance()
    with isolated_container() as outer, isolated_container() as inner:
        assert InjectQ.get_instance() is inner
        assert inner is not outer
    assert InjectQ.get_instance() is glob
    assert ContainerContext.get_current() is None


def test_deprecated_aliases_are_not_collectable():
    import injectq.testing as t

    assert t.test_container.__test__ is False
    assert t.TestModule.__test__ is False
    assert issubclass(t.TestModule, t.MockModule)
    for name in ("test_container", "TestModule", "pytest_container_fixture"):
        assert name not in t.__all__
        assert name not in vars(t)
