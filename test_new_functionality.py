#!/usr/bin/env python3
"""Test script for the updated null binding functionality."""

from injectq import InjectQ


def test_new_functionality():
    """Test the new allow_none functionality."""
    print("=== Testing Updated InjectQ Functionality ===")

    # Create a fresh container
    container = InjectQ()

    class A:
        def __init__(self):
            self.value = "Service A"

    # Test 1: Binding None without allow_none should fail
    print("\n1. Testing bind(A, None) without allow_none...")
    try:
        container.bind(A, None)
        print("ERROR: Should have failed!")
    except Exception as e:
        print(f"SUCCESS: Correctly failed - {e}")

    # Test 2: Binding None with allow_none=True should work
    print("\n2. Testing bind(A, None, allow_none=True)...")
    try:
        container.bind(A, None, allow_none=True)
        result = container.get(A)
        print(f"SUCCESS: Got result - {result}")
        assert result is None
    except Exception as e:
        print(f"FAILED: {e}")

    # Test 3: Auto-binding should still work
    print("\n3. Testing auto-binding...")
    try:
        container2 = InjectQ()
        container2.bind(A)  # Should auto-bind to A
        result = container2.get(A)
        print(f"SUCCESS: Auto-binding works - {result}")
        assert isinstance(result, A)
        print(f"Result value: {result.value}")
    except Exception as e:
        print(f"FAILED: {e}")

    # Test 4: Dict-style binding with None
    print("\n4. Testing dict-style binding...")
    try:
        container3 = InjectQ()
        container3[A] = None  # Should auto-detect allow_none
        result = container3.get(A)
        print(f"SUCCESS: Dict-style None binding works - {result}")
        assert result is None
    except Exception as e:
        print(f"FAILED: {e}")


if __name__ == "__main__":
    test_new_functionality()
