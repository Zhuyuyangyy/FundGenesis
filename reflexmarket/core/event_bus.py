"""
reflexmarket/core/event_bus.py
================================
Append-only event log for simulation tracing.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


@dataclass
class SimulationEvent:
    event_id: str
    step: int
    event_type: str
    source: str
    target: str | None
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "step": self.step,
            "event_type": self.event_type,
            "source": self.source,
            "target": self.target,
            "payload": self.payload,
        }


@dataclass
class EventBus:
    events: list[SimulationEvent] = field(default_factory=list)

    def emit(self, step: int, event_type: str, source: str,
             target: str | None = None, **payload: Any) -> SimulationEvent:
        event = SimulationEvent(
            event_id=str(uuid4())[:8], step=step, event_type=event_type,
            source=source, target=target, payload=payload,
        )
        self.events.append(event)
        return event

    def events_at(self, step: int) -> list[SimulationEvent]:
        return [e for e in self.events if e.step == step]

    def events_of(self, event_type: str) -> list[SimulationEvent]:
        return [e for e in self.events if e.event_type == event_type]

    def to_jsonl(self) -> str:
        import json
        return "\n".join(json.dumps(e.to_dict()) for e in self.events)

    def clear(self) -> None:
        self.events.clear()
