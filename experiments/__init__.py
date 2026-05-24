"""
experiments/__init__.py
======================
ReflexMarket-AI V0.3 Trust Bootstrapping Demos
"""
from .demo_low_trust_failure import run_demo_low_trust_failure
from .demo_high_trust_consensus import run_demo_high_trust_consensus
from .demo_falsification_collapse import run_demo_falsification_collapse

__all__ = [
    "run_demo_low_trust_failure",
    "run_demo_high_trust_consensus",
    "run_demo_falsification_collapse",
]
