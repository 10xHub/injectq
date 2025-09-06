#!/usr/bin/env python3
"""Debug script to understand binding parameter passing."""

import inspect
from injectq import InjectQ


class ServiceA:
    def __init__(self):
        self.value = "Service A"


def test_parameter_passing():
    print("=== Testing parameter passing ===")

    container = InjectQ()

    # Test case 1: bind(ServiceA) - implementation defaults to None
    print("Case 1: container.bind(ServiceA)")
    try:
        # This is calling bind(service_type=ServiceA, implementation=None, ...)
        container.bind(ServiceA)
        print("SUCCESS: bind(ServiceA) worked")
    except Exception as e:
        print(f"FAILED: bind(ServiceA) failed with {e}")

    # Test case 2: bind(ServiceA, None) - explicit None
    print("\nCase 2: container.bind(ServiceA, None)")
    try:
        container.bind(ServiceA, None)
        print("ERROR: This should have failed!")
    except Exception as e:
        print(f"SUCCESS: bind(ServiceA, None) correctly failed with {e}")

    # Test case 3: bind(ServiceA, None, allow_none=True) - explicit None with flag
    print("\nCase 3: container.bind(ServiceA, None, allow_none=True)")
    try:
        container.bind(ServiceA, None, allow_none=True)
        print("SUCCESS: bind(ServiceA, None, allow_none=True) worked")
    except Exception as e:
        print(f"FAILED: bind(ServiceA, None, allow_none=True) failed with {e}")


def debug_bind_signature():
    print("\n=== Analyzing bind method signature ===")
    sig = inspect.signature(InjectQ.bind)
    print(f"Bind method signature: {sig}")

    for name, param in sig.parameters.items():
        print(f"  {name}: default={param.default}, kind={param.kind}")


if __name__ == "__main__":
    debug_bind_signature()
    test_parameter_passing()
