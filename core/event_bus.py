"""
core/event_bus.py
==================
P1.2: 事件总线。

所有模块变化变成事件，每个事件带：
  step, source, target, payload, before_state, after_state

支撑后续的 provenance audit（P7 溯源系统）。
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from enum import Enum
import time


class EventType(Enum):
    """事件类型"""
    NARRATIVE_INJECTED = "narrative_injected"
    NARRATIVE_PROPAGATED = "narrative_propagated"
    TRUST_UPDATED = "trust_updated"
    BELIEF_UPDATED = "belief_updated"
    EMOTION_UPDATED = "emotion_updated"
    ORDER_SUBMITTED = "order_submitted"
    PRICE_UPDATED = "price_updated"
    RISK_DETECTED = "risk_detected"
    INTERVENTION_APPLIED = "intervention_applied"
    REGIME_CHANGED = "regime_changed"
    STEP_STARTED = "step_started"
    STEP_COMPLETED = "step_completed"


@dataclass
class Event:
    """
    单个事件。

    Attributes:
        event_type: 事件类型
        step: 发生步数
        source: 事件来源模块
        target: 事件目标（可选）
        payload: 事件数据
        before_state: 变化前状态（可选）
        after_state: 变化后状态（可选）
        timestamp: 事件时间戳
    """
    event_type: EventType
    step: int
    source: str
    target: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    before_state: Optional[Dict[str, Any]] = None
    after_state: Optional[Dict[str, Any]] = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type.value,
            "step": self.step,
            "source": self.source,
            "target": self.target,
            "payload": self.payload,
            "before_state": self.before_state,
            "after_state": self.after_state,
            "timestamp": self.timestamp,
        }


class EventBus:
    """
    P1.2: 事件总线。

    收集所有模块产生的事件，支持：
      - 事件记录
      - 事件查询
      - 事件订阅（回调）
      - 事件回放

    用法：
        bus = EventBus()
        bus.emit(Event(EventType.PRICE_UPDATED, step=10, source="market",
                       payload={"price": 105.2, "change": 0.05}))
        events = bus.query(event_type=EventType.PRICE_UPDATED, step=10)
    """

    def __init__(self, max_events: int = 100000):
        self._events: List[Event] = []
        self._subscribers: Dict[EventType, List[Callable]] = {}
        self._max_events = max_events

    def emit(self, event: Event):
        """发射事件"""
        self._events.append(event)
        # 防止内存溢出
        if len(self._events) > self._max_events:
            self._events = self._events[-self._max_events:]
        # 通知订阅者
        if event.event_type in self._subscribers:
            for callback in self._subscribers[event.event_type]:
                callback(event)

    def subscribe(self, event_type: EventType, callback: Callable[[Event], None]):
        """订阅特定类型的事件"""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)

    def query(
        self,
        event_type: Optional[EventType] = None,
        step: Optional[int] = None,
        source: Optional[str] = None,
        target: Optional[str] = None,
    ) -> List[Event]:
        """查询事件"""
        results = self._events
        if event_type is not None:
            results = [e for e in results if e.event_type == event_type]
        if step is not None:
            results = [e for e in results if e.step == step]
        if source is not None:
            results = [e for e in results if e.source == source]
        if target is not None:
            results = [e for e in results if e.target == target]
        return results

    def get_step_events(self, step: int) -> List[Event]:
        """获取某一步的所有事件"""
        return [e for e in self._events if e.step == step]

    def get_timeline(self, start_step: int = 0, end_step: Optional[int] = None) -> List[Dict]:
        """获取事件时间线（序列化）"""
        if end_step is None:
            end_step = max((e.step for e in self._events), default=0)
        return [
            e.to_dict() for e in self._events
            if start_step <= e.step <= end_step
        ]

    def clear(self):
        """清空所有事件"""
        self._events.clear()

    @property
    def event_count(self) -> int:
        return len(self._events)

    @property
    def events(self) -> List[Event]:
        return list(self._events)
