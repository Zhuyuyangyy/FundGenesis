# FundGenesis

> A Narrative-Driven Financial Reflexivity Multi-Agent World Model

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status: V1.0](https://img.shields.io/badge/status-V1.0-orange.svg)](#)

FundGenesis is an academic research framework that implements George Soros's theory of financial reflexivity as a multi-agent simulation. It models how narratives propagate through social networks, shift agent beliefs, drive trading behavior, move capital flows, and feed back into prices -- forming bubbles, panics, reversals, and manipulation risks.

This is not a quantitative trading system and does not claim real-market predictive capability. It is a controlled simulation environment for studying reflexivity mechanisms.

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Core Modules](#core-modules)
- [Experimental Results](#experimental-results)
- [Research](#research)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

Financial markets exhibit reflexive dynamics: participants' beliefs influence prices, and distorted prices in turn reinforce or undermine those beliefs. FundGenesis formalizes this feedback loop as a computational multi-agent system.

The framework enforces a strict causal chain:

```
Narrative --> Belief Shift --> Emotion Update --> Behavior Change --> Capital Flow --> Price Change
    ^                                                                              |
    └──────────────────────────────────────────────────────────────────────────────┘
```

Narratives never directly modify prices. Every signal must traverse the full causal pathway, ensuring that emergent phenomena (bubbles, crashes, herding) arise from the interaction of heterogeneous agents rather than from hard-coded rules.

### Research Questions Addressed

1. How do narratives propagate through layered social networks and shape investor beliefs?
2. What distinguishes value investors, trend followers, and retail speculators in their response to market narratives?
3. How do trust dynamics and falsification signals trigger belief collapse and market reversals?
4. Can coordinated KOL activity and FOMO surges be detected through reflexivity-aware metrics?
5. How effective are tiered regulatory interventions at dampening bubble formation?

---

## Key Features

### Multi-Agent Simulation with Heterogeneous Investors

Three agent archetypes with distinct behavioral parameters:

| Agent Type | Narrative Sensitivity | Herding Coefficient | Emotional Sensitivity |
|---|---|---|---|
| Value Investor | 0.03 | 0.1 | 0.2 |
| Trend Follower | 0.06 | 0.4 | 0.4 |
| Emotional Retail | 0.12 | 0.7 | 0.8 |

Emotional retail investors are 4x more sensitive to narrative shifts than value investors, capturing empirically observed behavioral differences.

### BeliefUpdaterV2: Multi-Factor Belief Update

A Q-learning-inspired belief update rule that integrates five signal sources:

```
belief_new = alpha * belief_old
           + beta * narrative_shift
           + gamma * price_confirmation
           + delta * social_pressure
           - theta * contradiction_signal
```

Each coefficient is modulated by agent-specific traits (emotional sensitivity, herding coefficient, confirmation bias), producing differentiated responses to identical market conditions.

### Four-Tier KOL Social Network

A hierarchical social propagation model with four node types:

| Tier | Influence Score | Susceptibility | Role |
|---|---|---|---|
| Macro KOL | 0.8 - 1.0 | 0.1 | Top media, institutional voices |
| Influencer | 0.4 - 0.7 | 0.3 | Mid-tier KOLs and opinion leaders |
| Micro KOL | 0.15 - 0.35 | 0.5 | Community leaders, small-group anchors |
| Retail | 0.01 - 0.05 | 0.5 - 0.8 | Individual investors |

Narrative propagation follows a cascade model with per-step decay (0.3 per hop, 0.08 per-step exposure decay), ensuring realistic diffusion dynamics.

### Reflexivity-Aware Metrics

A multi-layer metric system for real-time market state assessment:

- **Reflexivity Index** (0-1): Weighted composite of narrative penetration, belief concentration, emotion amplification, capital imbalance, and price momentum.
- **Bubble Risk Score** (0-1): Multiplicative combination of belief concentration, emotion amplification, volatility regime, capital factor, and narrative strength.
- **Market Regime Detection**: Classifies states as Normal, Bubble Peak, Crash, Panic Spread, or Recovery based on threshold conditions on the reflexivity metrics.

### Dynamic Trust Engine

Trust evolves through a bootstrapping mechanism where successful predictions strengthen trust and falsification signals trigger trust collapse. This enables modeling of trust-dependent narrative propagation and credibility erosion.

### Manipulation Risk Detection

Detection of coordinated KOL amplification and FOMO surges through a multi-factor `manipulation_risk_score` that combines coordination metrics, FOMO signals, and self-validation patterns.

### Tiered Regulatory Intervention

Three intervention levels (light, moderate, strong) with quantified effects on bubble formation. Experimental results show light intervention reduces peak bubble risk by approximately 27% compared to baseline.

---

## Architecture

```
FundGenesis
+-- core/                    Core simulation engine
|   +-- belief_updater_v2    Multi-factor belief update (alpha/beta/gamma/delta/theta)
|   +-- emotion_field        Four-dimensional emotion state (fear/greed/confidence/uncertainty)
|   +-- market_environment   Price dynamics with mean-reversion and emotion amplification
|   +-- metrics              Market-level indicator computation
|   +-- simulation_runner    Experiment orchestration
|
+-- agents/                  Heterogeneous agent decision logic
|   +-- base_agent           Agent base class with configurable traits
|   +-- value_investor       Fundamental-valuation-driven, contrarian
|   +-- trend_follower       Momentum-driven, emotion-amplified
|   +-- emotional_retail     FOMO/panic-driven, high information lag
|
+-- narrative/               Narrative engine
|   +-- narrative_engine     Narrative injection, propagation, and decay
|   +-- narrative_event      Event types with strength, credibility, direction
|
+-- social/                  KOL social network
|   +-- kol_network          Four-tier topology (Macro/Influencer/Micro/Retail)
|   +-- propagation_model    Cascade diffusion with decay
|
+-- trust/                   Dynamic trust system
|   +-- trust_engine         Trust tracking per agent pair
|   +-- trust_bootstrapper   Initial trust calibration
|   +-- trust_decay_model    Trust erosion on falsification
|   +-- credibility_updater  Source credibility evolution
|
+-- monitor/                 Reflexivity monitoring
|   +-- reflexivity_monitor  Bubble/panic/regime detection
|
+-- risk/                    Risk detection and governance
|   +-- manipulation_risk_agent   Coordinated KOL and FOMO detection
|   +-- regulator_agent           Tiered intervention strategies
|
+-- experiments/             Demonstration scripts and benchmarks
+-- dashboard/               REST API + WebSocket visualization server
+-- tests/                   Pytest test suite
```

### Core Causal Chain

The simulation enforces Soros's reflexivity loop. At each timestep:

1. **Narrative Injection**: External events are injected into the narrative engine with strength, credibility, and directional bias.
2. **Social Propagation**: Narratives propagate through the KOL network, with influence modulated by trust levels and node susceptibility.
3. **Belief Update**: Each agent's belief is updated via BeliefUpdaterV2, incorporating narrative exposure, price confirmation, social pressure, and contradiction signals.
4. **Emotion Update**: The EmotionField evolves based on price changes and narrative direction (four-dimensional: fear, greed, confidence, uncertainty).
5. **Behavior Decision**: Agents generate BUY/SELL/HOLD signals based on their archetype-specific decision logic.
6. **Capital Flow and Price Update**: Aggregated orders drive price changes through an impact coefficient modulated by the emotion field.

---

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3.10+ |
| Core Computation | NumPy |
| API Server | FastAPI + Uvicorn |
| Data Validation | Pydantic |
| Visualization | Matplotlib |
| Testing | Pytest |
| Linting | Ruff |
| Containerization | Docker (multi-stage build) |

---

## Quick Start

### Prerequisites

- Python 3.10 or later
- pip

### Installation

```bash
git clone <repo-url>
cd FundGenesis
pip install -r requirements.txt
```

### Run Classic Experiments

```bash
# Positive narrative bubble formation
python main.py --demo 1

# Regulatory shock and panic propagation
python main.py --demo 2

# Narrative reversal and bubble burst
python main.py --demo 3

# Run all V0.2 demos sequentially
python main.py --v02

# Run all experiments (V0.1 + V0.2)
python main.py --all
```

### Run the Dashboard Server

```bash
python dashboard/app.py --port 8765
# API docs at http://localhost:8765/docs
```

### Docker

```bash
docker build -t fundgenesis .
docker run -p 8765:8765 fundgenesis
```

### Run Tests

```bash
pytest tests/ -v
```

---

## Project Structure

```
FundGenesis/
├── core/                            Core simulation engine
│   ├── belief_updater_v2.py         Multi-factor belief update engine
│   ├── emotion_field.py             Four-dimensional emotion state
│   ├── market_environment.py        Price dynamics and order matching
│   ├── metrics.py                   Market-level indicators
│   ├── simulation_runner.py         Experiment orchestration
│   ├── reflexivity_game.py          Game-theoretic reflexivity model
│   ├── risk_propagation.py          Risk cascade dynamics
│   └── creator_controller.py        Simulation parameter control
│
├── agents/                          Agent decision modules
│   ├── base_agent.py                Base class with AgentConfig
│   ├── value_investor.py            Fundamental-value-driven strategy
│   ├── trend_follower.py            Momentum-driven strategy
│   └── emotional_retail.py          Emotion-driven retail strategy
│
├── narrative/                       Narrative engine
│   ├── narrative_engine.py          Narrative injection and mapping
│   └── narrative_event.py           Event types and decay models
│
├── social/                          KOL social network
│   ├── kol_network.py               Four-tier network topology
│   ├── propagation_model.py         Cascade diffusion model (V1)
│   └── propagation_model_v2.py      Enhanced propagation (V2)
│
├── trust/                           Dynamic trust system
│   ├── trust_engine.py              Trust tracking and evolution
│   ├── trust_bootstrapper.py        Initial trust calibration
│   ├── trust_decay_model.py         Falsification-triggered decay
│   └── credibility_updater.py       Source credibility evolution
│
├── monitor/                         Reflexivity monitoring
│   └── reflexivity_monitor.py       Bubble, panic, and regime detection
│
├── risk/                            Risk detection and governance
│   ├── manipulation_risk_agent.py   Coordinated KOL / FOMO detection
│   └── regulator_agent.py           Tiered regulatory intervention
│
├── dashboard/                       Visualization and API
│   ├── app.py                       FastAPI server (port 8765)
│   └── ws_client.py                 WebSocket client
│
├── experiments/                     Demonstration and benchmark scripts
│   ├── demo_positive_narrative.py   Demo 1: Positive narrative bubble
│   ├── demo_regulatory_shock.py     Demo 2: Regulatory panic
│   ├── demo_narrative_reversal.py   Demo 3: Reversal and collapse
│   ├── demo_coordinated_kol_risk.py Coordinated KOL amplification
│   ├── demo_fomo_surge_risk.py      FOMO surge detection
│   ├── demo_regulation_*.py         Tiered regulation experiments
│   ├── demo_*_trust*.py             Trust evolution experiments
│   ├── black_swan.py                Black swan stress test
│   ├── herding_ablation.py          Herding effect ablation
│   ├── ablation_experiment.py       Mechanism ablation study
│   └── reflexivity_bench.py         Reflexivity benchmark suite
│
├── tests/                           Pytest test suite
│   ├── test_agents.py               Agent decision logic tests
│   ├── test_api.py                  API endpoint tests
│   ├── test_models.py               Data model tests
│   ├── test_smoke.py                Integration smoke tests
│   └── ...
│
├── config/                          Configuration files
├── docs/                            Documentation
├── main.py                          CLI entry point
├── Dockerfile                       Multi-stage production build
├── requirements.txt                 Python dependencies
├── pyproject.toml                   Project metadata
└── pytest.ini                       Pytest configuration
```

---

## Core Modules

### BeliefUpdaterV2

The belief update engine implements a five-factor model where each agent's belief (a scalar in [-1, 1]) evolves based on:

| Factor | Symbol | Default Weight | Meaning |
|---|---|---|---|
| Belief Inertia | alpha | 0.6 | Retention of prior belief |
| Narrative Influence | beta | 0.15 | Sensitivity to narrative exposure |
| Price Confirmation | gamma | 0.2 | Price movement validates/invalidates narrative |
| Social Pressure | delta | 0.1 | Herding effect from peer behavior |
| Contradiction Penalty | theta | 0.1 | Penalty when price contradicts narrative |

Single-step belief change is clipped to [-0.3, 0.3] to prevent runaway dynamics. Belief is bounded in [-1.0, 1.0].

### EmotionField

A four-dimensional emotion state vector:

| Dimension | Range | Update Rule |
|---|---|---|
| Fear | [0, 1] | Increases on price drops, decreases on gains |
| Greed | [0, 1] | Increases on price gains, decreases on drops |
| Confidence | [0, 1] | Updated by narrative credibility |
| Uncertainty | [0, 1] | Increased by contradictory signals |

The fear-greed index is `greed - fear` in [-1, 1]. The composite emotion factor modulates price impact coefficients.

### Market Environment

Price dynamics follow:

```
P(t+1) = P(t) * exp(eta * order_imbalance + phi * deviation + epsilon)
```

where `eta` is the impact coefficient (0.5) modulated by the emotion field, `phi` is a mean-reversion term, and `epsilon` is stochastic noise. Realized volatility is computed over configurable rolling windows (10, 50, 200 steps).

### Reflexivity Monitor

Real-time computation of reflexivity metrics:

- **Reflexivity Index**: Weighted sum of narrative penetration (0.15), belief concentration (0.20), emotion amplification (0.20), capital imbalance (0.25), and price momentum (0.20).
- **Bubble Risk Score**: Multiplicative product of belief boost, emotion boost, volatility momentum, capital factor, and narrative factor.
- **Market Regime**: Classification into Normal (reflexivity_index < 0.3), Bubble Peak (reflexivity > 0.7, sustained), Crash (reflexivity > 0.7, negative price change), Panic Spread (emotion amplification > 0.6, fear-greed < -0.3), or Recovery.

---

## Experimental Results

All experiments produce output charts saved to `outputs/`.

### Demo 1: Positive Narrative Bubble

- **Scenario**: "AI Healthcare Revolution" narrative injected at step 30 (strength 0.75, credibility 0.7, positive direction)
- **Observation**: Price trajectory 100 -> 276 -> 259; Reflexivity Index peaks at 0.256
- **Mechanism**: Narrative -> belief concentration -> capital inflow -> price bubble formation

### Demo 2: Regulatory Shock and Panic

- **Scenario**: Regulatory policy change triggers panic propagation
- **Observation**: Price decline from 239 to 201 (-14.5%); Panic score reaches 0.008
- **Mechanism**: Negative narrative -> fear amplification -> herd selling -> price decline -> panic cascade

### Demo 3: Narrative Reversal and Collapse

- **Scenario**: Narrative direction reverses from positive to negative
- **Observation**: Price trajectory 103 -> 275 -> 213; Reflexivity Index 0.261
- **Mechanism**: Contradiction signal -> trust collapse -> belief reversal -> selling pressure -> bubble burst

### Additional Experiments

| Experiment | Key Finding |
|---|---|
| Coordinated KOL Risk | Peak manipulation risk score reaches 0.65 |
| FOMO Surge Detection | Peak manipulation risk score reaches 0.58 |
| Regulation Baseline vs. Light | Light intervention reduces peak bubble by ~27% |
| Trust Evolution | High-trust environments accelerate narrative adoption |
| Black Swan Stress Test | Extreme shock propagation under rare-event scenarios |

---

## Research

### Academic Contributions

This framework makes the following contributions to the computational finance and agent-based modeling literature:

1. **Executable Reflexivity Theory**: First implementation of Soros's reflexivity theory as a verifiable multi-agent simulation with enforced causal chains.
2. **Multi-Factor Belief Dynamics**: A Q-learning-inspired belief update rule integrating narrative, price confirmation, social pressure, and falsification signals.
3. **Reflexivity-Aware Metrics**: Novel composite metrics (reflexivity index, bubble risk score) that capture feedback-loop intensity rather than relying solely on price-based indicators.
4. **Tiered Governance Simulation**: Quantified evaluation of regulatory intervention effectiveness across multiple intervention levels.

### Associated Publications

- **Paper**: "ReflexMarket-AI: A Narrative-Driven Multi-Agent Framework for Financial Reflexivity Simulation"
- **Patent**: "A Narrative Diffusion and Belief Update Based Financial Reflexivity Multi-Agent Market Simulation Method" (Chinese patent filing)

### Version History

| Module | V0.1 | V0.2 | V0.3 | V0.4 | V0.5 | V1.0 |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| Market Simulation Core | Y | Y | Y | Y | Y | Y |
| Emotion Layer | Y | Y | Y | Y | Y | Y |
| Behavior Layer | Y | Y | Y | Y | Y | Y |
| Capital / Price Engine | Y | Y | Y | Y | Y | Y |
| Narrative Engine | - | Y | Y | Y | Y | Y |
| KOL Social Contagion | - | Y | Y | Y | Y | Y |
| Belief Update V2 | - | Y | Y | Y | Y | Y |
| Reflexivity Monitor | - | Y | Y | Y | Y | Y |
| Trust Bootstrapping | - | - | Y | Y | Y | Y |
| ManipulationRiskAgent | - | - | - | Y | Y | Y |
| RegulatorAgent | - | - | - | - | Y | Y |
| ReflexMarket-Bench | - | - | - | - | - | Y |

---

## Roadmap

| Phase | Version | Status | Description |
|---|---|---|---|
| 0 | V0.2 | Complete | Narrative propagation + KOL network + trust bootstrapping |
| 1 | V0.3 | Complete | Trust-weighted propagation, falsification-triggered collapse |
| 2 | V0.4 | Complete | ManipulationRiskAgent for abnormal narrative detection |
| 3 | V0.5 | Complete | RegulatorAgent for governance intervention simulation |
| 4 | V1.0 | Complete | Benchmark suite (50 scenarios) + SCI paper + patent filing |
| 5 | V1.1 | Planned | Real-time dashboard with interactive parameter tuning |
| 6 | V2.0 | Planned | Multi-asset cross-market reflexivity simulation |

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code guidelines, and submission process.

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

## Disclaimer

This system is for academic research purposes only. It does not constitute investment advice. Financial markets carry inherent risks.
