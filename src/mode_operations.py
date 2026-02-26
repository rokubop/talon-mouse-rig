"""Mouse mode operations - imports from rig-core

All mode operation functions are identical between mouse and other rigs.
This module re-exports them from rig-core for backward compatibility.
"""

# Set by _build_classes
calculate_scalar_target = None
apply_scalar_mode = None
calculate_direction_target = None
apply_direction_mode = None
calculate_position_target = None
apply_position_mode = None
calculate_vector_target = None
apply_vector_mode = None


def _build_classes(core):
    global calculate_scalar_target, apply_scalar_mode
    global calculate_direction_target, apply_direction_mode
    global calculate_position_target, apply_position_mode
    global calculate_vector_target, apply_vector_mode

    calculate_scalar_target = core.mode_operations.calculate_scalar_target
    apply_scalar_mode = core.mode_operations.apply_scalar_mode
    calculate_direction_target = core.mode_operations.calculate_direction_target
    apply_direction_mode = core.mode_operations.apply_direction_mode
    calculate_position_target = core.mode_operations.calculate_position_target
    apply_position_mode = core.mode_operations.apply_position_mode
    calculate_vector_target = core.mode_operations.calculate_vector_target
    apply_vector_mode = core.mode_operations.apply_vector_mode
