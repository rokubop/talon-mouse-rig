"""Queue system for behavior modes

Handles queuing of builders when behavior is set to 'queue'.
Each layer has its own queue with accumulated state tracking.

Key concepts:
- Each queue has a 'current' callback representing the actively executing builder
- Queues track 'accumulated_state' per property for sequential chaining
- When a builder completes, its final value is saved and the next item starts
"""

from typing import Optional, Callable, Any
from collections import deque


class BuilderQueue:
    """Queue for a specific layer

    Manages sequential execution of builders on the same layer/property.

    Attributes:
        queue: Deque of execution callbacks waiting to execute
        current: Currently executing callback (None if queue is idle)
        accumulated_state: Dict of property -> final_value for chaining queue items
    """

    def __init__(self):
        self.queue: deque = deque()
        self.current: Optional[Callable] = None
        self.accumulated_state: dict[str, Any] = {}

    def enqueue(self, execution_callback: Callable) -> None:
        """Add a builder execution callback to the queue"""
        self.queue.append(execution_callback)

    def start_next(self) -> bool:
        """Start the next queued builder if available.

        Returns:
            True if a builder was started, False if queue is empty
        """
        if len(self.queue) == 0:
            self.current = None
            return False

        self.current = self.queue.popleft()
        self.current()  # Execute the builder
        return True

    def is_empty(self) -> bool:
        return len(self.queue) == 0

    def clear(self) -> None:
        """Clear all pending queue items and reset current"""
        self.queue.clear()
        self.current = None


class QueueManager:
    """Manages all builder queues across all layers

    Single source of truth for queue state. Queues are created on-demand
    and automatically cleaned up when empty.
    """

    def __init__(self):
        self.queues: dict[str, BuilderQueue] = {}

    def get_queue(self, layer: str) -> BuilderQueue:
        if layer not in self.queues:
            self.queues[layer] = BuilderQueue()
        return self.queues[layer]

    def enqueue(self, layer: str, execution_callback: Callable) -> None:
        """Add a builder to the specified queue"""
        queue = self.get_queue(layer)
        queue.enqueue(execution_callback)

    def on_builder_complete(self, layer: str, property: str, final_value):
        """Handle builder completion and start next queued item

        Args:
            layer: Queue key (layer name or anonymous key)
            property: Property name to save accumulated state for
            final_value: Final value to accumulate for next queue item
        """
        if layer in self.queues:
            queue = self.queues[layer]
            # Save the accumulated state for this property
            queue.accumulated_state[property] = final_value

            if not queue.start_next():
                # Queue is empty, clean up
                del self.queues[layer]

    def clear_queue(self, layer: str) -> None:
        """Clear and remove the queue for a specific layer"""
        if layer in self.queues:
            self.queues[layer].clear()
            del self.queues[layer]

    def clear_all(self) -> None:
        """Clear all queues"""
        for queue in self.queues.values():
            queue.clear()
        self.queues.clear()

    def is_active(self, layer: str) -> bool:
        """Check if a queue exists and has items"""
        return layer in self.queues and not self.queues[layer].is_empty()
