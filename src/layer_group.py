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
from .core import Vec2, EPSILON
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
        order: Optional[int] = None
    ):
        from .contracts import LayerType

        self.layer_name = layer_name
        self.property = property
        self.mode = mode
        self.layer_type = layer_type
        self.is_base = (layer_type == LayerType.BASE)
        self.order = order
        self.creation_time = time.perf_counter()

        # Active builders in this group
        self.builders: list['ActiveBuilder'] = []

        # Accumulated state (for modifier layers - persists after builders complete)
        # For direction.offset, starts as None and gets initialized based on first value type
        if property == "direction" and mode == "offset":
            self.accumulated_value: Any = None
        else:
            self.accumulated_value: Any = self._zero_value()

        # Cached final target value (what accumulated_value will be after all builders complete)
        self.final_target: Optional[Any] = None

        # Queue system (sequential execution within this layer)
        self.pending_queue: deque[Callable] = deque()
        self.is_queue_active: bool = False

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
                if isinstance(self.accumulated_value, Vec2):
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
            elif isinstance(value, Vec2):
                self.accumulated_value = Vec2(0, 0)
            else:
                self.accumulated_value = value

        self.accumulated_value = self._apply_mode(self.accumulated_value, value, builder.config.mode)
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
            if isinstance(current, Vec2) and isinstance(incoming, Vec2):
                return Vec2(current.x + incoming.x, current.y + incoming.y)
            # Type mismatch: if current is scalar but incoming is Vec2, replace with incoming
            if isinstance(current, (int, float)) and isinstance(incoming, Vec2):
                return incoming
            if isinstance(current, Vec2) and isinstance(incoming, (int, float)):
                # Vec2 + scalar angle: can't mix, keep the Vec2 (or could convert to angle)
                # For now, treat the scalar as negligible and keep the vector
                return current
            # Fallback for unexpected types
            return incoming
        elif mode == "override":
            # Override replaces
            return incoming
        elif mode == "scale" or mode == "mul":
            if isinstance(current, Vec2) and isinstance(incoming, (int, float)):
                return Vec2(current.x * incoming, current.y * incoming)
            if isinstance(current, (int, float)) and isinstance(incoming, (int, float)):
                return current * incoming
            # Fallback for unexpected types
            return incoming
        else:
            # Default: additive
            if isinstance(current, Vec2) and isinstance(incoming, Vec2):
                return Vec2(current.x + incoming.x, current.y + incoming.y)
            if isinstance(current, (int, float)) and isinstance(incoming, (int, float)):
                return current + incoming
            # Type mismatch fallback
            return incoming

    def get_current_value(self) -> Any:
        """Get aggregated value: accumulated + all active builders

        For base layers: Just return the builder's value directly (modes don't apply)
        For modifier layers: Apply modes (offset/override/scale) to accumulated value
        """
        print(f"[DEBUG LayerGroup.get_current_value] Layer '{self.layer_name}': is_base={self.is_base}, accumulated_value={self.accumulated_value}, {len(self.builders)} builders")

        # Base layers: ignore accumulated_value (always 0), just use builder value
        if self.is_base:
            if not self.builders:
                return self.accumulated_value  # Should be 0
            # For base layers, return the LAST builder's value (most recent operation)
            # Multiple builders shouldn't normally exist, but can occur with instant operations
            last_value = self.accumulated_value
            for builder in self.builders:
                builder_value = builder.get_interpolated_value()
                print(f"[DEBUG LayerGroup.get_current_value]   Base builder: value={builder_value}")
                if builder_value is not None:
                    last_value = builder_value
            print(f"[DEBUG LayerGroup.get_current_value] Final result (base): {last_value}")
            return last_value

        # Modifier layers: start with accumulated value and apply modes
        result = self.accumulated_value

        # Initialize if None (for direction.offset that hasn't accumulated yet)
        if result is None:
            # Determine the correct zero value from first builder's type
            if self.builders:
                first_value = self.builders[0].get_interpolated_value()
                if isinstance(first_value, Vec2):
                    result = Vec2(0, 0)
                else:
                    result = 0.0
            else:
                result = 0.0

        for builder in self.builders:
            builder_value = builder.get_interpolated_value()
            print(f"[DEBUG LayerGroup.get_current_value]   Modifier builder: value={builder_value}, mode={builder.config.mode}")
            if builder_value is not None:
                result = self._apply_mode(result, builder_value, builder.config.mode)

        print(f"[DEBUG LayerGroup.get_current_value] Final result (modifier): {result}")
        return result

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
            if isinstance(first_target, Vec2):
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
            print(f"[DEBUG should_persist] {self.layer_name}: YES - has {len(self.builders)} active builders")
            return True

        # Base layers with no builders should be removed
        if self.is_base:
            print(f"[DEBUG should_persist] {self.layer_name}: NO - base layer with no builders")
            return False

        # Modifier persists if it has accumulated non-zero value
        is_zero = self._is_reverted_to_zero()
        print(f"[DEBUG should_persist] {self.layer_name}: {'NO' if is_zero else 'YES'} - modifier layer, accumulated_value={self.accumulated_value}, is_zero={is_zero}")
        return not is_zero

    def _is_reverted_to_zero(self) -> bool:
        """Check if accumulated value is effectively zero/identity"""
        # Handle None (uninitialized direction.offset)
        if self.accumulated_value is None:
            return True

        if isinstance(self.accumulated_value, Vec2):
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
        print(f"[DEBUG LayerGroup.start_next_queued] Layer '{self.layer_name}': pending_queue_len={len(self.pending_queue)}")

        if len(self.pending_queue) == 0:
            print(f"[DEBUG LayerGroup.start_next_queued] Queue empty, marking queue as inactive")
            self.is_queue_active = False
            return False

        print(f"[DEBUG LayerGroup.start_next_queued] Starting next queued builder")
        callback = self.pending_queue.popleft()
        self.is_queue_active = True
        callback()  # Execute the builder
        return True

    def on_builder_complete(self, builder: 'ActiveBuilder'):
        """Called when a builder completes - handle queue progression

        Note: Does NOT remove the builder - caller is responsible for removal
        """
        print(f"[DEBUG LayerGroup.on_builder_complete] Layer '{self.layer_name}': builder behavior={builder.config.behavior}, pending_queue_len={len(self.pending_queue)}")

        # Bake the builder
        bake_result = self.bake_builder(builder)

        # Don't remove builder here - let the caller decide when to remove
        # This ensures final position emission happens before removal

        # If there are pending queue items, start next regardless of this builder's behavior
        # This handles cases where builder 1 has no queue behavior, but builder 2 was queued
        if len(self.pending_queue) > 0:
            print(f"[DEBUG LayerGroup.on_builder_complete] Pending queue items found, starting next queued builder")
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

            if builder.config.behavior == "queue":
                print(f"[DEBUG LayerGroup.advance] Queue builder: phase={new_phase}, old_phase={old_phase}, is_complete={is_complete}, should_gc={should_gc}")

            # If builder just completed (transitioned to phase=None), mark for removal
            # Bake NOW before final emission to capture correct value
            if old_phase is not None and new_phase is None:
                print(f"[DEBUG LayerGroup.advance] Builder completed (phase transition to None), marking for removal, behavior={builder.config.behavior}")
                builder._marked_for_removal = True
                bake_result = self.on_builder_complete(builder)
                builders_to_remove.append((builder, bake_result))
            elif should_gc:
                # Standard garbage collection for non-completing transitions
                print(f"[DEBUG LayerGroup.advance] Builder should_gc=True, marking for removal, behavior={builder.config.behavior}")
                builder._marked_for_removal = True
                bake_result = self.on_builder_complete(builder)
                builders_to_remove.append((builder, bake_result))

        # Don't remove builders here - let _remove_completed_builders handle it
        # after final position emission. This ensures absolute position builders
        # emit their final target position.

        return phase_transitions, builders_to_remove

    def __repr__(self) -> str:
        return f"<LayerGroup '{self.layer_name}' {self.property} mode={self.mode} builders={len(self.builders)} accumulated={self.accumulated_value}>"
