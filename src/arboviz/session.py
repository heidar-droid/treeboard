from __future__ import annotations

import time


class AgentSession:
    """In-memory state for the current agent task."""

    def __init__(self):
        self.reset()

    def reset(self) -> None:
        """Reset all in-memory state. Used by /api/reset in test mode and
        called from __init__ to keep both paths in sync."""
        self.state: str = "idle"  # idle | scanning | editing | frozen
        self.current_task: dict = self._empty_task()
        self.tasks: list[dict] = []

    def _empty_task(self) -> dict:
        return {
            "label": "",
            "started_at": 0,
            "footprint": {"read": [], "edited": [], "created": [], "deleted": []},
            "snapshot_before": {"files": [], "timestamp": 0},
        }

    def handle(self, event_type: str, file: str | None, label: str | None) -> None:
        if event_type == "snapshot":
            self.state = "scanning"
            self.current_task = self._empty_task()
            self.current_task["started_at"] = int(time.time())
            self.current_task["snapshot_before"]["timestamp"] = int(time.time())

        elif event_type == "read" and file:
            if file not in self.current_task["footprint"]["read"]:
                self.current_task["footprint"]["read"].append(file)

        elif event_type == "edit" and file:
            self.state = "editing"
            fp = self.current_task["footprint"]
            if file not in fp["edited"]:
                fp["edited"].append(file)

        elif event_type == "create" and file:
            self.state = "editing"
            fp = self.current_task["footprint"]
            if file not in fp["created"]:
                fp["created"].append(file)

        elif event_type == "delete" and file:
            self.state = "editing"
            fp = self.current_task["footprint"]
            if file not in fp["deleted"]:
                fp["deleted"].append(file)

        elif event_type == "task-end":
            self.state = "frozen"
            self.current_task["label"] = label or f"task {len(self.tasks) + 1}"
            self.current_task["duration_s"] = (
                int(time.time()) - self.current_task["started_at"]
            )
            self.tasks.append(dict(self.current_task))
            # Reset so a stray event without a preceding snapshot (Claude
            # restart, manual `arboviz edit`, etc.) does NOT accumulate into
            # the previous task's footprint.
            self.current_task = self._empty_task()
