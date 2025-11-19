"""Tests to ensure contract schemas match actual implementation

These tests prevent drift between validation schemas and actual code.
"""

import inspect
import sys
import os
from unittest.mock import MagicMock

sys.modules['talon'] = MagicMock()
sys.modules['talon.cron'] = MagicMock()
sys.modules['talon.ctrl'] = MagicMock()
sys.modules['talon.fs'] = MagicMock()

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src_v2.contracts import (
    METHOD_SIGNATURES,
    VALID_RIG_METHODS,
    VALID_RIG_PROPERTIES,
    VALID_BUILDER_METHODS,
    VALID_PROPERTIES,
    VALID_OPERATORS,
    VALID_EASINGS,
    VALID_INTERPOLATIONS,
)
from src_v2.builder import RigBuilder
from src_v2 import Rig
from src_v2.core import EASING_FUNCTIONS


def test_method_signatures_match_rigbuilder():
    """Ensure METHOD_SIGNATURES matches actual RigBuilder methods"""

    # Methods that should have schemas
    methods_to_check = ['over', 'revert', 'hold', 'then']

    for method_name in methods_to_check:
        # Get actual method
        actual_method = getattr(RigBuilder, method_name, None)
        assert actual_method is not None, f"RigBuilder.{method_name} doesn't exist"

        # Get schema
        schema = METHOD_SIGNATURES.get(method_name)
        assert schema is not None, f"Missing schema for {method_name}"

        # Extract actual parameters (excluding 'self' and '**kwargs')
        sig = inspect.signature(actual_method)
        actual_params = [
            name for name in sig.parameters.keys()
            if name not in ('self', 'kwargs')
        ]

        # Compare
        expected_params = schema['params']
        assert actual_params == expected_params, (
            f"{method_name} parameter mismatch:\n"
            f"  Actual: {actual_params}\n"
            f"  Schema: {expected_params}"
        )

        print(f"✓ {method_name} signature matches schema")


def test_rig_methods_exist():
    """Ensure all methods in VALID_RIG_METHODS actually exist on Rig"""

    for method_name in VALID_RIG_METHODS:
        assert hasattr(Rig, method_name), f"Rig.{method_name} doesn't exist but is in VALID_RIG_METHODS"
        print(f"✓ Rig.{method_name} exists")


def test_rig_properties_exist():
    """Ensure all properties in VALID_RIG_PROPERTIES actually exist on Rig"""

    for prop_name in VALID_RIG_PROPERTIES:
        # Some are properties, some are methods
        assert hasattr(Rig, prop_name), f"Rig.{prop_name} doesn't exist but is in VALID_RIG_PROPERTIES"
        print(f"✓ Rig.{prop_name} exists")


def test_builder_methods_exist():
    """Ensure all methods in VALID_BUILDER_METHODS exist on RigBuilder"""

    for method_name in VALID_BUILDER_METHODS:
        assert hasattr(RigBuilder, method_name), f"RigBuilder.{method_name} doesn't exist but is in VALID_BUILDER_METHODS"
        print(f"✓ RigBuilder.{method_name} exists")


def test_property_operators_complete():
    """Ensure VALID_OPERATORS covers all VALID_PROPERTIES"""

    from src_v2.builder import PropertyBuilder

    # Valid operators that should exist as methods
    valid_operator_methods = ['to', 'add', 'by', 'sub', 'mul', 'div', 'bake']

    for prop in VALID_PROPERTIES:
        assert prop in VALID_OPERATORS, f"Missing operators definition for property '{prop}'"
        operators = VALID_OPERATORS[prop]
        assert len(operators) > 0, f"No operators defined for property '{prop}'"

        # Verify each operator is a valid method
        for operator in operators:
            assert operator in valid_operator_methods, (
                f"Invalid operator '{operator}' for property '{prop}'. "
                f"Valid operators: {valid_operator_methods}"
            )

            # Verify PropertyBuilder actually has this method
            assert hasattr(PropertyBuilder, operator), (
                f"PropertyBuilder missing method '{operator}' "
                f"(defined in VALID_OPERATORS for '{prop}')"
            )

        print(f"✓ {prop} has valid operators: {operators}")


def test_no_extra_schemas():
    """Ensure we don't have schemas for non-existent methods"""

    for method_name in METHOD_SIGNATURES.keys():
        # Check if it exists on RigBuilder or Rig
        exists_on_builder = hasattr(RigBuilder, method_name)
        exists_on_rig = hasattr(Rig, method_name)

        assert exists_on_builder or exists_on_rig, (
            f"Schema exists for '{method_name}' but method doesn't exist on RigBuilder or Rig"
        )
        print(f"✓ Schema for {method_name} has corresponding method")


def test_easings_are_implemented():
    """Ensure all VALID_EASINGS are actually implemented in EASING_FUNCTIONS"""

    for easing in VALID_EASINGS:
        assert easing in EASING_FUNCTIONS, (
            f"Easing '{easing}' is in VALID_EASINGS but not implemented in EASING_FUNCTIONS.\n"
            f"Available easings: {list(EASING_FUNCTIONS.keys())}"
        )
        print(f"✓ Easing '{easing}' is implemented")


def test_interpolations_are_valid():
    """Ensure VALID_INTERPOLATIONS contains only valid values"""

    # These are the only two interpolation modes supported
    valid_interpolations = {'lerp', 'slerp'}

    for interp in VALID_INTERPOLATIONS:
        assert interp in valid_interpolations, (
            f"Interpolation '{interp}' is in VALID_INTERPOLATIONS but is not a valid mode.\n"
            f"Valid interpolations: {valid_interpolations}"
        )
        print(f"✓ Interpolation '{interp}' is valid")


if __name__ == '__main__':
    print("Running contract validation tests...\n")

    test_method_signatures_match_rigbuilder()
    print()
    test_rig_methods_exist()
    print()
    test_rig_properties_exist()
    print()
    test_builder_methods_exist()
    print()
    test_property_operators_complete()
    print()
    test_no_extra_schemas()
    print()
    test_easings_are_implemented()
    print()
    test_interpolations_are_valid()

    print("\n✅ All contract validation tests passed!")
