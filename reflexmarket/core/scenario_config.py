"""
reflexmarket/core/scenario_config.py
======================================
YAML-driven scenario configuration.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import yaml


@dataclass
class ScenarioConfig:
    id: str
    name: str
    seed: int
    steps: int
    category: str = "uncategorized"
    market: dict[str, Any] = field(default_factory=dict)
    emotion: dict[str, Any] = field(default_factory=dict)
    regulation: dict[str, Any] = field(default_factory=dict)
    scheduled_events: list[dict[str, Any]] = field(default_factory=list)
    agents: dict[str, Any] = field(default_factory=dict)
    narratives: dict[str, Any] = field(default_factory=dict)
    expected: dict[str, Any] = field(default_factory=dict)
    ablation: dict[str, Any] = field(default_factory=dict)
    failure_modes: list[str] = field(default_factory=list)

    @classmethod
    def from_yaml(cls, path: str | Path) -> ScenarioConfig:
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Scenario file not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls(
            id=data.get("id", path.stem),
            name=data.get("name", path.stem),
            seed=data.get("seed", 42),
            steps=data.get("steps", 200),
            category=data.get("category", "uncategorized"),
            market=data.get("market", {}),
            emotion=data.get("emotion", {}),
            regulation=data.get("regulation", {}),
            scheduled_events=data.get("scheduled_events", []),
            agents=data.get("agents", {}),
            narratives=data.get("narratives", {}),
            expected=data.get("expected", {}),
            ablation=data.get("ablation", {}),
            failure_modes=data.get("failure_modes", []),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id, "name": self.name, "seed": self.seed,
            "steps": self.steps, "category": self.category,
            "market": self.market, "emotion": self.emotion,
            "regulation": self.regulation,
            "scheduled_events": self.scheduled_events,
            "agents": self.agents, "narratives": self.narratives,
            "expected": self.expected, "ablation": self.ablation,
            "failure_modes": self.failure_modes,
        }
