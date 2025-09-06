#!/usr/bin/env python3
"""Debug script to understand binding behavior."""

from injectq import InjectQ
from injectq.utils import BindingError


class ServiceA:
    def __init__(self):
        self.value = "Service A"


class ProblematicService:
    def __init__(self, required_param: str):
        self.param = required_param


def test_debug():
    container = InjectQ()

    print("=== Test 1: Binding None without allow_none ===")
    try:
        container.bind(ServiceA, None)  # Should fail
        print("ERROR: This should have failed!")
    except BindingError as e:
        print(f"SUCCESS: Correctly failed - {e}")
    except Exception as e:
        print(f"UNEXPECTED ERROR: {type(e).__name__}: {e}")

    print("\n=== Test 2: Binding problematic class ===")
    try:
        container.bind(ProblematicService, ProblematicService)  # Should fail
        print("ERROR: This should have failed!")
    except BindingError as e:
        print(f"SUCCESS: Correctly failed - {e}")
    except Exception as e:
        print(f"UNEXPECTED ERROR: {type(e).__name__}: {e}")


if __name__ == "__main__":
    test_debug()
