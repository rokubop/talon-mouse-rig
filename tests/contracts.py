"""Contract validation tests - ensure schemas match actual implementation

These tests prevent drift between validation schemas and actual code.
"""

from talon import actions
import inspect


def test_method_signatures_match_rigbuilder(on_success, on_failure):
    """Test: METHOD_SIGNATURES matches actual RigBuilder methods"""
    try:
        from ..src.contracts import METHOD_SIGNATURES
        from ..src.builder import RigBuilder

        # Methods that should have schemas
        methods_to_check = ['over', 'revert', 'hold', 'then']

        for method_name in methods_to_check:
            # Get actual method
            actual_method = getattr(RigBuilder, method_name, None)
            if actual_method is None:
                on_failure(f"RigBuilder.{method_name} doesn't exist")
                return

            # Get schema
            schema = METHOD_SIGNATURES.get(method_name)
            if schema is None:
                on_failure(f"Missing schema for {method_name}")
                return

            # Extract actual parameters (excluding 'self' and '**kwargs')
            sig = inspect.signature(actual_method)
            actual_params = [
                name for name in sig.parameters.keys()
                if name not in ('self', 'kwargs')
            ]

            # Compare
            expected_params = schema['params']
            if actual_params != expected_params:
                on_failure(
                    f"{method_name} parameter mismatch:\n"
                    f"  Actual: {actual_params}\n"
                    f"  Schema: {expected_params}"
                )
                return

        on_success()
    except Exception as e:
        print(f"  Error message: {e}")
        on_failure(f"Unexpected error: {e}")


def test_rig_methods_exist(on_success, on_failure):
    """Test: All methods in VALID_RIG_METHODS exist on Rig"""
    try:
        from ..src.contracts import VALID_RIG_METHODS
        from ..src import Rig

        for method_name in VALID_RIG_METHODS:
            if not hasattr(Rig, method_name):
                on_failure(f"Rig.{method_name} doesn't exist but is in VALID_RIG_METHODS")
                return

        on_success()
    except Exception as e:
        print(f"  Error message: {e}")
        on_failure(f"Unexpected error: {e}")


def test_rig_properties_exist(on_success, on_failure):
    """Test: All properties in VALID_RIG_PROPERTIES exist on Rig"""
    try:
        from ..src.contracts import VALID_RIG_PROPERTIES
        from ..src import Rig

        for prop_name in VALID_RIG_PROPERTIES:
            if not hasattr(Rig, prop_name):
                on_failure(f"Rig.{prop_name} doesn't exist but is in VALID_RIG_PROPERTIES")
                return

        on_success()
    except Exception as e:
        print(f"  Error message: {e}")
        on_failure(f"Unexpected error: {e}")


def test_builder_methods_exist(on_success, on_failure):
    """Test: All methods in VALID_BUILDER_METHODS exist on RigBuilder"""
    try:
        from ..src.contracts import VALID_BUILDER_METHODS
        from ..src.builder import RigBuilder

        for method_name in VALID_BUILDER_METHODS:
            if not hasattr(RigBuilder, method_name):
                on_failure(f"RigBuilder.{method_name} doesn't exist but is in VALID_BUILDER_METHODS")
                return

        on_success()
    except Exception as e:
        print(f"  Error message: {e}")
        on_failure(f"Unexpected error: {e}")


def test_property_operators_complete(on_success, on_failure):
    """Test: VALID_OPERATORS covers all VALID_PROPERTIES"""
    try:
        from ..src.contracts import VALID_OPERATORS, VALID_PROPERTIES
        from ..src.builder import PropertyBuilder

        # Valid operators that should exist as methods
        valid_operator_methods = ['to', 'add', 'by', 'sub', 'mul', 'div', 'bake']

        for prop in VALID_PROPERTIES:
            if prop not in VALID_OPERATORS:
                on_failure(f"Missing operators definition for property '{prop}'")
                return

            operators = VALID_OPERATORS[prop]
            if len(operators) == 0:
                on_failure(f"No operators defined for property '{prop}'")
                return

            # Verify each operator is a valid method
            for operator in operators:
                if operator not in valid_operator_methods:
                    on_failure(
                        f"Invalid operator '{operator}' for property '{prop}'. "
                        f"Valid operators: {valid_operator_methods}"
                    )
                    return

                # Verify PropertyBuilder actually has this method
                if not hasattr(PropertyBuilder, operator):
                    on_failure(
                        f"PropertyBuilder missing method '{operator}' "
                        f"(defined in VALID_OPERATORS for '{prop}')"
                    )
                    return

        on_success()
    except Exception as e:
        print(f"  Error message: {e}")
        on_failure(f"Unexpected error: {e}")


def test_no_extra_schemas(on_success, on_failure):
    """Test: No schemas for non-existent methods"""
    try:
        from ..src.contracts import METHOD_SIGNATURES
        from ..src.builder import RigBuilder
        from ..src import Rig

        for method_name in METHOD_SIGNATURES.keys():
            # Check if it exists on RigBuilder or Rig
            exists_on_builder = hasattr(RigBuilder, method_name)
            exists_on_rig = hasattr(Rig, method_name)

            if not (exists_on_builder or exists_on_rig):
                on_failure(
                    f"Schema exists for '{method_name}' but method doesn't exist on RigBuilder or Rig"
                )
                return

        on_success()
    except Exception as e:
        print(f"  Error message: {e}")
        on_failure(f"Unexpected error: {e}")


def test_easings_are_implemented(on_success, on_failure):
    """Test: All VALID_EASINGS are implemented in EASING_FUNCTIONS"""
    try:
        from ..src.contracts import VALID_EASINGS
        from ..src.core import EASING_FUNCTIONS

        for easing in VALID_EASINGS:
            if easing not in EASING_FUNCTIONS:
                on_failure(
                    f"Easing '{easing}' is in VALID_EASINGS but not implemented in EASING_FUNCTIONS.\n"
                    f"Available easings: {list(EASING_FUNCTIONS.keys())}"
                )
                return

        on_success()
    except Exception as e:
        print(f"  Error message: {e}")
        on_failure(f"Unexpected error: {e}")


def test_interpolations_are_valid(on_success, on_failure):
    """Test: VALID_INTERPOLATIONS contains only valid values"""
    try:
        from ..src.contracts import VALID_INTERPOLATIONS

        # These are the only two interpolation modes supported
        valid_interpolations = {'lerp', 'slerp', 'linear'}

        for interp in VALID_INTERPOLATIONS:
            if interp not in valid_interpolations:
                on_failure(
                    f"Interpolation '{interp}' is in VALID_INTERPOLATIONS but is not a valid mode.\n"
                    f"Valid interpolations: {valid_interpolations}"
                )
                return

        on_success()
    except Exception as e:
        print(f"  Error message: {e}")
        on_failure(f"Unexpected error: {e}")


# ============================================================================
# TEST REGISTRY
# ============================================================================

CONTRACTS_TESTS = [
    ("method signatures match", test_method_signatures_match_rigbuilder),
    ("rig methods exist", test_rig_methods_exist),
    ("rig properties exist", test_rig_properties_exist),
    ("builder methods exist", test_builder_methods_exist),
    ("property operators complete", test_property_operators_complete),
    ("no extra schemas", test_no_extra_schemas),
    ("easings implemented", test_easings_are_implemented),
    ("interpolations valid", test_interpolations_are_valid),
]
