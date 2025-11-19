"""Queue system for behavior modes

Handles queuing of builders when behavior is set to 'queue'.
Each tag has its own queue.
"""

from typing import Optional, Callable
from collections import deque


class BuilderQueue:
    """Queue for a specific tag"""

    def __init__(self):
        self.queue: deque = deque()
        self.current: Optional[Callable] = None

    def enqueue(self, execution_callback: Callable):
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
        """Check if queue has no pending items"""
        return len(self.queue) == 0

    def clear(self):
        """Clear all queued items"""
        self.queue.clear()
        self.current = None


class QueueManager:
    """Manages all builder queues"""

    def __init__(self):
        self.queues: dict[str, BuilderQueue] = {}

    def get_queue(self, tag: str) -> BuilderQueue:
        """Get or create a queue for a tag"""
        if tag not in self.queues:
            self.queues[tag] = BuilderQueue()
        return self.queues[tag]

    def enqueue(self, tag: str, execution_callback: Callable):
        """Enqueue a builder for a tag"""
        queue = self.get_queue(tag)
        queue.enqueue(execution_callback)

    def on_builder_complete(self, tag: str):
        """Called when a builder completes, starts next in queue"""
        if tag in self.queues:
            queue = self.queues[tag]
            if not queue.start_next():
                # Queue is empty, can remove it
                del self.queues[tag]

    def clear_queue(self, tag: str):
        """Clear all queued items for a tag"""
        if tag in self.queues:
            self.queues[tag].clear()
            del self.queues[tag]

    def is_active(self, tag: str) -> bool:
        """Check if a tag has an active builder or queued items"""
        return tag in self.queues and not self.queues[tag].is_empty()
