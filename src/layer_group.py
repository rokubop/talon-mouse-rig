"""Layer Group - Container for builders on a single layer

Each layer (base.speed, speed.offset, or user-named) gets a LayerGroup.
Groups manage:
- Active builders (operations in progress)
- Accumulated state (for modifier layers)
- Queue system (sequential execution)
- Lifecycle (for group-level operations like revert)
"""

import time
from typing import Optional, Any, Callable, TYPE_CHECKING
from collections import deque
from .core import Vec2, is_vec2, EPSILON
from .lifecycle import Lifecycle

if TYPE_CHECKING:
    from .builder import ActiveBuilder


class LayerGroup:
    """Container for all builders on a single layer

    Scope examples:
    - Base: base.speed, base.pos, base.direction
    - Auto-modifier: speed.offset, pos.override, direction.scale
    - User-named: "boost", "precision", etc.
    """

    def __init__(
        self,
        layer_name: str,
        property: str,
        mode: Optional[str],
        layer_type: str,
        order: Optional[int] = None,
        is_emit_layer: bool = False,
        source_layer: Optional[str] = None,
        input_type: str = "move"
    ):
        from .contracts import LayerType

        self.layer_name = layer_name
        self.property = property
        self.mode = mode
        self.layer_type = layer_type
        self.is_base = (layer_type == LayerType.BASE)
        self.order = order
        self.creation_time = time.perf_counter()
        self.is_emit_layer = is_emit_layer
        self.source_layer = source_layer
        self.input_type = input_type
        self.builders: list['ActiveBuilder'] = []

        # Accumulated state (for modifier layers - persists after builders complete)
        # For direction.offset, starts as None and gets initialized based on first value type
        if property == "direction" and mode == "offset":
            self.accumulated_value: Any = None
        else:
            self.accumulated_value: Any = self._zero_value()

        # Committed state (for pos.offset only - tracks physical movement that's been baked)
        # All other properties: None (not applicable)
        if property == "pos":
            self.committed_value: Optional[Any] = Vec2(0, 0)
        else:
            self.committed_value: Optional[Any] = None

        # Replace behavior state (for pos.offset only)
        self.replace_target: Optional[Any] = None  # Absolute target for replace operations

        # Cached final target value (what accumulated_value will be after all builders complete)
        self.final_target: Optional[Any] = None

        # Queue system (sequential execution within this layer)
        self.pending_queue: deque[Callable] = deque()
        self.is_queue_active: bool = False

        # Constraints (max/min clamping on layer output)
        self.max_value: Optional[float] = None
        self.min_value: Optional[float] = None

        # Group-level lifecycle (for rig.layer("name").revert() operations)
        self.group_lifecycle: Optional[Lifecycle] = None

    def _zero_value(self) -> Any:
        """Get zero/identity value for this property"""
        if self.property == "pos":
            return Vec2(0, 0)
        elif self.property == "direction":
            return Vec2(1, 0)
        elif self.property == "speed":
            return 0.0
        elif self.property == "vector":
            return Vec2(0, 0)
        else:
            return 0.0

    def _apply_constraints(self, value: Any) -> Any:
        """Apply max/min constraints to a value

        For scalars: direct clamp.
        For Vec2: clamp magnitude (preserving direction).
        """
        if self.max_value is None and self.min_value is None:
            return value

        if isinstance(value, (int, float)):
            if self.max_value is not None:
                value = min(value, self.max_value)
            if self.min_value is not None:
                value = max(value, self.min_value)
            return value

        if is_vec2(value):
            import math
            mag = math.sqrt(value.x * value.x + value.y * value.y)
            if mag < EPSILON:
                return value
            if self.max_value is not None and mag > self.max_value:
                scale = self.max_value / mag
                return Vec2(value.x * scale, value.y * scale)
            if self.min_value is not None and mag < self.min_value:
                scale = self.min_value / mag
                return Vec2(value.x * scale, value.y * scale)
            return value

        return value

    def add_builder(self, builder: 'ActiveBuilder'):
        """Add a builder to this group"""
        self.builders.append(builder)
        builder.group = self  # Back-reference for builder to find its group
        self._recalculate_final_target()

    def remove_builder(self, builder: 'ActiveBuilder'):
        """Remove a builder from this group"""
        if builder in self.builders:
            self.builders.remove(builder)
            self._recalculate_final_target()

    def copy(self, new_name: str) -> 'LayerGroup':
        """Create a copy of this layer group

        Args:
            new_name: Name for the new layer copy

        Returns:
            New LayerGroup with copied state
        """
        copy_group = LayerGroup(
            layer_name=new_name,
            property=self.property,
            mode=self.mode,
            layer_type=self.layer_type,
            order=self.order,
            source_layer=self.layer_name
        )
        copy_group.builders = self.builders.copy()
        copy_group.accumulated_value = self.accumulated_value
        copy_group.committed_value = self.committed_value
        copy_group.replace_target = self.replace_target
        copy_group.final_target = self.final_target
        copy_group.max_value = self.max_value
        copy_group.min_value = self.min_value
        return copy_group

    def clear_builders(self):
        """Remove all active builders (used by replace behavior)"""
        self.builders.clear()
        self._recalculate_final_target()

    def bake_builder(self, builder: 'ActiveBuilder') -> str:
        """Builder completed - bake its value

        Returns:
            "bake_to_base" for base layers (including reverted ones)
            "baked_to_group" for modifier layers
            "reverted" for modifier layers that reverted (clears accumulated value)
        """
        if builder.lifecycle.has_reverted():
            if self.is_base:
                # Base layers need to restore original value when reverting
                return "bake_to_base"
            else:
                # Modifier layers that revert clear their accumulated value
                # Set to zero based on current type, not property default
                if is_vec2(self.accumulated_value):
                    self.accumulated_value = Vec2(0, 0)
                else:
                    self.accumulated_value = 0.0
                return "reverted"

        value = builder.get_interpolated_value()

        if self.is_base:
            # Base layers always bake to global base state
            return "bake_to_base"

        # Modifier layers: accumulate in group
        # Initialize accumulated_value for direction.offset based on first value type
        if self.accumulated_value is None:
            if isinstance(value, (int, float)):
                self.accumulated_value = 0.0
            elif is_vec2(value):
                self.accumulated_value = Vec2(0, 0)
            else:
                self.accumulated_value = value

        self.accumulated_value = self._apply_mode(self.accumulated_value, value, builder.config.mode)
        self.accumulated_value = self._apply_constraints(self.accumulated_value)

        # Handle replace behavior cleanup (pos.offset only)
        if self.replace_target is not None and self.committed_value is not None:
            # Consolidate accumulated into committed (with clamping)
            if is_vec2(self.accumulated_value) and is_vec2(self.committed_value):
                total_x = self.committed_value.x + self.accumulated_value.x
                total_y = self.committed_value.y + self.accumulated_value.y

                # Clamp per axis based on direction
                if is_vec2(self.replace_target):
                    if self.committed_value.x < self.replace_target.x:
                        total_x = min(total_x, self.replace_target.x)
                    elif self.committed_value.x > self.replace_target.x:
                        total_x = max(total_x, self.replace_target.x)
                    else:
                        total_x = self.replace_target.x

                    if self.committed_value.y < self.replace_target.y:
                        total_y = min(total_y, self.replace_target.y)
                    elif self.committed_value.y > self.replace_target.y:
                        total_y = max(total_y, self.replace_target.y)
                    else:
                        total_y = self.replace_target.y

                    self.committed_value = Vec2(total_x, total_y)

            # Reset for next operation
            if is_vec2(self.accumulated_value):
                self.accumulated_value = Vec2(0, 0)
            else:
                self.accumulated_value = 0.0

            self.replace_target = None

        return "baked_to_group"

    def _apply_mode(self, current: Any, incoming: Any, mode: Optional[str]) -> Any:
        """Apply mode operation to combine values within this layer group"""
        if mode == "offset" or mode == "add":
            # Handle None (uninitialized direction.offset) - treat as zero of incoming type
            if current is None:
                return incoming
            # Accumulate values (angles add, vectors add)
            if isinstance(current, (int, float)) and isinstance(incoming, (int, float)):
                return current + incoming
            if is_vec2(current) and is_vec2(incoming):
                return Vec2(current.x + incoming.x, current.y + incoming.y)
            # Type mismatch: if current is scalar but incoming is Vec2, replace with incoming
            if isinstance(current, (int, float)) and is_vec2(incoming):
                return incoming
            if is_vec2(current) and isinstance(incoming, (int, float)):
                # Vec2 + scalar angle: can't mix, keep the Vec2 (or could convert to angle)
                # For now, treat the scalar as negligible and keep the vector
                return current
            # Fallback for unexpected types
            return incoming
        elif mode == "override":
            # Override replaces
            return incoming
        elif mode == "scale" or mode == "mul":
            if is_vec2(current) and isinstance(incoming, (int, float)):
                return Vec2(current.x * incoming, current.y * incoming)
            if isinstance(current, (int, float)) and isinstance(incoming, (int, float)):
                return current * incoming
            # Fallback for unexpected types
            return incoming
        else:
            # Default: additive
            if is_vec2(current) and is_vec2(incoming):
                return Vec2(current.x + incoming.x, current.y + incoming.y)
            if isinstance(current, (int, float)) and isinstance(incoming, (int, float)):
                return current + incoming
            # Type mismatch fallback
            return incoming

    def get_current_value(self) -> Any:
        """Get aggregated value: accumulated + all active builders

        For base layers: Just return the builder's value directly (modes don't apply)
        For modifier layers: Apply modes (offset/override/scale) to accumulated value

        For pos.offset with replace: Clamps output based on replace_target
        """
        # Base layers: ignore accumulated_value (always 0), just use builder value
        if self.is_base:
            if not self.builders:
                return self._apply_constraints(self.accumulated_value)  # Should be 0
            # For base layers, return the LAST builder's value (most recent operation)
            # Multiple builders shouldn't normally exist, but can occur with instant operations
            last_value = self.accumulated_value
            for builder in self.builders:
                builder_value = builder.get_interpolated_value()
                if builder_value is not None:
                    last_value = builder_value
            return self._apply_constraints(last_value)

        # Modifier layers: start with accumulated value and apply modes
        result = self.accumulated_value

        # Initialize if None (for direction.offset that hasn't accumulated yet)
        if result is None:
            # Determine the correct zero value from first builder's type
            if self.builders:
                first_value = self.builders[0].get_interpolated_value()
                if is_vec2(first_value):
                    result = Vec2(0, 0)
                else:
                    result = 0.0
            else:
                result = 0.0

        for builder in self.builders:
            builder_value = builder.get_interpolated_value()
            if builder_value is not None:
                result = self._apply_mode(result, builder_value, builder.config.mode)

        # Apply replace clamping for pos.offset
        if self.replace_target is not None and self.committed_value is not None:
            # Total = committed + accumulated (with active builders)
            if is_vec2(result) and is_vec2(self.committed_value):
                total = Vec2(
                    self.committed_value.x + result.x,
                    self.committed_value.y + result.y
                )

                # Clamp based on approach direction (per axis)
                if is_vec2(self.replace_target):
                    clamped_x = total.x
                    clamped_y = total.y

                    if self.committed_value.x < self.replace_target.x:
                        clamped_x = min(total.x, self.replace_target.x)
                    elif self.committed_value.x > self.replace_target.x:
                        clamped_x = max(total.x, self.replace_target.x)

                    if self.committed_value.y < self.replace_target.y:
                        clamped_y = min(total.y, self.replace_target.y)
                    elif self.committed_value.y > self.replace_target.y:
                        clamped_y = max(total.y, self.replace_target.y)

                    result = Vec2(clamped_x - self.committed_value.x, clamped_y - self.committed_value.y)

        return self._apply_constraints(result)

    def _recalculate_final_target(self):
        """Recalculate cached final target value after all builders complete"""
        if not self.builders:
            self.final_target = None
            return

        # Base layers: return last builder's target (most recent operation)
        if self.is_base:
            self.final_target = self.builders[-1].target_value
            return

        # Modifier layers: compute final accumulated value after all builders complete
        result = self.accumulated_value

        # Initialize if None (for direction.offset)
        if result is None:
            first_target = self.builders[0].target_value
            if is_vec2(first_target):
                result = Vec2(0, 0)
            else:
                result = 0.0

        # Apply all builder targets
        for builder in self.builders:
            target = builder.target_value
            if target is not None:
                result = self._apply_mode(result, target, builder.config.mode)

        self.final_target = result

    @property
    def value(self) -> Any:
        """Current value (accumulated + all active builders)"""
        return self.get_current_value()

    @property
    def target(self) -> Optional[Any]:
        """Final target value after all active builders complete (cached)"""
        return self.final_target

    def should_persist(self) -> bool:
        """Should this group stay alive?

        - Base: Only while it has active builders
        - Modifier: If has non-zero accumulated value OR active builders
        """
        # Any layer persists if it has active builders
        if len(self.builders) > 0:
            return True

        # Base layers with no builders should be removed
        if self.is_base:
            return False

        # Modifier persists if it has accumulated non-zero value
        is_zero = self._is_reverted_to_zero()
        return not is_zero

    def _is_reverted_to_zero(self) -> bool:
        """Check if accumulated value is effectively zero/identity"""
        # Handle None (uninitialized direction.offset)
        if self.accumulated_value is None:
            return True

        if is_vec2(self.accumulated_value):
            return (abs(self.accumulated_value.x) < EPSILON and
                    abs(self.accumulated_value.y) < EPSILON)

        # For scalar values (int, float), check if close to 0.0
        if isinstance(self.accumulated_value, (int, float)):
            return abs(self.accumulated_value) < EPSILON

        # Fallback: unknown type, consider not zero to be safe
        return False

    def enqueue_builder(self, execution_callback: Callable):
        """Add a builder to this group's queue"""
        self.pending_queue.append(execution_callback)

    def start_next_queued(self) -> bool:
        """Start next queued builder if available

        Returns:
            True if a builder was started, False if queue empty
        """
        if len(self.pending_queue) == 0:
            self.is_queue_active = False
            return False

        callback = self.pending_queue.popleft()
        self.is_queue_active = True
        callback()  # Execute the builder
        return True

    def on_builder_complete(self, builder: 'ActiveBuilder'):
        """Called when a builder completes - handle queue progression

        Note: Does NOT remove the builder - caller is responsible for removal
        """
        # Bake the builder
        bake_result = self.bake_builder(builder)

        # Don't remove builder here - let the caller decide when to remove
        # This ensures final position emission happens before removal

        # If there are pending queue items, start next regardless of this builder's behavior
        # This handles cases where builder 1 has no queue behavior, but builder 2 was queued
        if len(self.pending_queue) > 0:
            self.start_next_queued()

        return bake_result

    def advance(self, current_time: float) -> list[tuple['ActiveBuilder', str]]:
        """Advance all builders in this group

        Returns:
            List of (builder, completed_phase) for callbacks
        """
        phase_transitions = []
        builders_to_remove = []

        for builder in self.builders:
            old_phase = builder.lifecycle.phase
            builder.advance(current_time)
            new_phase = builder.lifecycle.phase

            # Track phase transitions for callbacks
            if old_phase != new_phase and old_phase is not None:
                phase_transitions.append((builder, old_phase))

            # Check if builder transitioned to completion (phase becomes None)
            is_complete = builder.lifecycle.is_complete()
            should_gc = builder.lifecycle.should_be_garbage_collected()

            # If builder just completed (transitioned to phase=None), mark for removal
            # Bake NOW before final emission to capture correct value
            if old_phase is not None and new_phase is None:
                builder._marked_for_removal = True
                bake_result = self.on_builder_complete(builder)
                builders_to_remove.append((builder, bake_result))
            elif should_gc:
                # Standard garbage collection for non-completing transitions
                builder._marked_for_removal = True
                bake_result = self.on_builder_complete(builder)
                builders_to_remove.append((builder, bake_result))

        # Don't remove builders here - let _remove_completed_builders handle it
        # after final position emission. This ensures absolute position builders
        # emit their final target position.

        return phase_transitions, builders_to_remove

    def __repr__(self) -> str:
        return f"<LayerGroup '{self.layer_name}' {self.property} mode={self.mode} builders={len(self.builders)} accumulated={self.accumulated_value}>"
