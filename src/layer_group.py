"""Mouse LayerGroup - extends BaseLayerGroup with mouse-specific fields

Mouse adds: input_type, committed_value, replace_target, copy() override,
and pos.offset clamping in get_current_value/bake_builder.
(is_emit_layer and source_layer are inherited from BaseLayerGroup in rig-core.)
"""

from typing import Optional, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .builder import ActiveBuilder

# Set by _build_classes
LayerGroup = None


def _build_classes(core):
    global LayerGroup

    Vec2 = core.Vec2
    is_vec2 = core.is_vec2
    EPSILON = core.EPSILON

    class _MouseLayerGroup(core.BaseLayerGroup):
        """Extends BaseLayerGroup with mouse-specific tracking"""

        def __init__(
            self,
            layer_name: str,
            property: str,
            property_kind,
            mode: Optional[str],
            layer_type: str,
            order: Optional[int] = None,
            input_type: str = "move",
        ):
            super().__init__(layer_name, property, property_kind, mode, layer_type, order)
            self.input_type = input_type

            # Committed state (for pos.offset only - tracks physical movement that's been baked)
            if property == "pos":
                self.committed_value: Optional[Any] = Vec2(0, 0)
            else:
                self.committed_value: Optional[Any] = None

            # Replace behavior state (for pos.offset only)
            self.replace_target: Optional[Any] = None

        def copy(self, new_name: str) -> '_MouseLayerGroup':
            """Create a copy of this layer group"""
            copy_group = _MouseLayerGroup(
                layer_name=new_name,
                property=self.property,
                property_kind=self.property_kind,
                mode=self.mode,
                layer_type=self.layer_type,
                order=self.order,
                input_type=self.input_type,
            )
            copy_group.source_layer = self.layer_name
            copy_group.builders = self.builders.copy()
            if is_vec2(self.accumulated_value):
                copy_group.accumulated_value = Vec2(self.accumulated_value.x, self.accumulated_value.y)
            elif isinstance(self.accumulated_value, (int, float)):
                copy_group.accumulated_value = self.accumulated_value
            else:
                copy_group.accumulated_value = self.accumulated_value
            copy_group.committed_value = self.committed_value
            copy_group.replace_target = self.replace_target
            copy_group.final_target = self.final_target
            copy_group.max_value = self.max_value
            copy_group.min_value = self.min_value
            return copy_group

        def bake_builder(self, builder) -> str:
            """Override to handle committed_value + replace_target cleanup for pos.offset"""
            if builder.lifecycle.has_reverted():
                if self.is_base:
                    return "bake_to_base"
                else:
                    if is_vec2(self.accumulated_value):
                        self.accumulated_value = Vec2(0, 0)
                    else:
                        self.accumulated_value = 0.0
                    return "reverted"

            value = builder.get_interpolated_value()

            if self.is_base:
                return "bake_to_base"

            # Modifier layers: accumulate in group
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
                if is_vec2(self.accumulated_value) and is_vec2(self.committed_value):
                    total_x = self.committed_value.x + self.accumulated_value.x
                    total_y = self.committed_value.y + self.accumulated_value.y

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

        def get_current_value(self) -> Any:
            """Override to handle committed_value and replace_target clamping for pos.offset"""
            # Base layers: use parent impl
            if self.is_base:
                return super().get_current_value()

            # Modifier layers: start with accumulated value and apply modes
            result = self.accumulated_value

            if result is None:
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
                if is_vec2(result) and is_vec2(self.committed_value):
                    total = Vec2(
                        self.committed_value.x + result.x,
                        self.committed_value.y + result.y
                    )

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

        def __repr__(self) -> str:
            return f"<MouseLayerGroup '{self.layer_name}' {self.property} mode={self.mode} builders={len(self.builders)} accumulated={self.accumulated_value}>"

    LayerGroup = _MouseLayerGroup
