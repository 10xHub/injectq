"""InjectQ(thread_safe=..., use_async_scopes=...) is deprecated, not removed."""

import warnings

import pytest

from injectq import InjectQ


def test_silent_by_default():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        InjectQ()
        InjectQ(allow_override=False, debug=True)


@pytest.mark.parametrize("name", ["thread_safe", "use_async_scopes"])
@pytest.mark.parametrize("value", [True, False])
def test_warns_when_passed(name, value):
    with pytest.warns(DeprecationWarning, match=f"{name}.*will be removed in 0.7"):
        container = InjectQ(**{name: value})
    container.bind(int, 1)
    assert container.get(int) == 1


def test_warning_points_at_caller():
    with pytest.warns(DeprecationWarning) as rec:
        InjectQ(thread_safe=True)
    assert rec[0].filename == __file__
