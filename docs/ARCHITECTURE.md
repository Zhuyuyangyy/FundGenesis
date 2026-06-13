# FundGenesis Architecture

## System Overview

FundGenesis is a multi-agent simulation framework that implements George Soros's theory of financial reflexivity. The system models how narratives propagate through social networks, shift agent beliefs, drive trading behavior, move capital flows, and feed back into prices.

---

## Core Design Principles

### 1. Enforced Causal Chain

The simulation enforces a strict causal pathway:

```
Narrative --> Belief Shift --> Emotion Update --> Behavior Change --> Capital Flow --> Price Change
    ^                                                                              |
    └──────────────────────────────────────────────────────────────────────────────┘
```

Narratives never directly modify prices. Every signal must traverse the full causal pathway, ensuring that emergent phenomena arise from agent interactions.

### 2. Heterogeneous Agents

Three agent archetypes with distinct behavioral parameters model real-world investor diversity:

| Agent Type | Narrative Sensitivity | Herding Coefficient | Emotional Sensitivity |
|---|---|---|---|
| Value Investor | 0.03 | 0.1 | 0.2 |
| Trend Follower | 0.06 | 0.4 | 0.4 |
| Emotional Retail | 0.12 | 0.7 | 0.8 |

### 3. Trust-Weighted Propagation

Narrative propagation strength depends on the trustworthiness of the source:

```
effective_trust = trust_level × credibility^α × social_proof^β × price_validation^γ
```

---

## Module Architecture

```
FundGenesis/
│
├── core/                          Core simulation engine
│   ├── belief_updater_v2.py       5-factor belief update model
│   ├── emotion_field.py           4-dimensional emotion state
│   ├── market_environment.py      Price dynamics and order matching
│   ├── metrics.py                 Market-level indicators
│   ├── simulation_runner.py       Experiment orchestration
│   ├── creator_controller.py      Parameter control and shock injection
│   ├── reflexivity_game.py        Game-theoretic reflexivity model
│   └── risk_propagation.py        Risk cascade dynamics
│
├── agents/                        Agent decision modules
│   ├── base_agent.py              Abstract base class
│   ├── value_investor.py          Fundamental-value strategy
│   ├── trend_follower.py          Momentum strategy
│   └── emotional_retail.py        Emotion-driven retail strategy
│
├── narrative/                     Narrative engine
│   ├── narrative_engine.py        Narrative injection and impact
│   └── narrative_event.py         Event types and decay models
│
├── social/                        KOL social network
│   ├── kol_network.py             4-tier network topology
│   ├── propagation_model.py       Cascade diffusion (V1)
│   └── propagation_model_v2.py    Trust-aware propagation (V2)
│
├── trust/                         Dynamic trust system
│   ├── trust_engine.py            Trust tracking and evolution
│   ├── trust_bootstrapper.py      Initial trust calibration
│   ├── trust_decay_model.py       Falsification-triggered decay
│   └── credibility_updater.py     Source credibility evolution
│
├── monitor/                       Reflexivity monitoring
│   └── reflexivity_monitor.py     Bubble/panic/regime detection
│
├── risk/                          Risk detection and governance
│   ├── manipulation_risk_agent.py Coordinated KOL/FOMO detection
│   └── regulator_agent.py         Tiered regulatory intervention
│
├── dashboard/                     REST API + WebSocket server
│   ├── app.py                     FastAPI application
│   └── ws_client.py               WebSocket client
│
└── experiments/                   Demonstration scripts
```

---

## Data Flow

### Simulation Step

Each simulation step follows this sequence:

1. **Narrative Injection**
   - External events are injected into the NarrativeEngine
   - Events have strength, credibility, polarity, and duration

2. **Social Propagation**
   - Narratives propagate through the KOL network
   - Propagation strength = influence × susceptibility × trust × narrative_strength

3. **Belief Update**
   ```
   belief_new = α·belief_old
              + β·narrative_shift
              + γ·price_confirmation
              + δ·social_pressure
              - θ·contradiction_signal
   ```

4. **Emotion Update**
   - Fear, greed, confidence, uncertainty evolve based on price changes and narratives
   - Emotions decay toward neutral over time

5. **Behavior Decision**
   - Each agent generates BUY/SELL/HOLD based on archetype-specific logic

6. **Capital Flow and Price Update**
   ```
   P(t+1) = P(t) × exp(η·order_imbalance + φ·deviation + ε)
   ```

7. **Risk Assessment**
   - ManipulationRiskAgent evaluates for abnormal patterns
   - RegulatorAgent intervenes if risk exceeds thresholds

---

## Key Algorithms

### BeliefUpdaterV2

Five-factor belief update with agent-specific modulation:

```python
# Agent-specific weights
alpha = belief_inertia × (1 - sensitivity × 0.2)
beta = narrative_weight × sensitivity
gamma = price_confirmation × (1 - sensitivity × 0.3)
delta = social_pressure × herding_coefficient
theta = contradiction_penalty × confirmation_bias

# Update with clipping
belief_change = alpha·old + beta·narrative + gamma·price + delta·social - theta·contradiction
belief_new = clip(old + clip(belief_change - old, -0.3, 0.3), -1, 1)
```

### EmotionField

Four-dimensional emotion state with natural decay:

| Dimension | Range | Update Rule |
|---|---|---|
| Fear | [0, 1] | Increases on price drops |
| Greed | [0, 1] | Increases on price gains |
| Confidence | [0, 1] | Updated by narrative credibility |
| Uncertainty | [0, 1] | Increased by contradictory signals |

### Market Price Dynamics

```
P(t+1) = P(t) × exp(η·OI + φ·deviation + ε)

where:
  η = impact_coefficient × emotion_amplification
  OI = order_imbalance ∈ [-1, 1]
  φ = mean_reversion_strength (0.03 normal, 0.10 deep deviation)
  deviation = (price - fundamental) / fundamental
  ε ~ N(0, noise_std)
```

### Reflexivity Index

Weighted composite of five market dimensions:

```python
reflexivity_index = (
    0.15 × narrative_penetration
  + 0.20 × belief_concentration
  + 0.20 × emotion_amplification
  + 0.25 × capital_imbalance
  + 0.20 × price_momentum
)
```

### Bubble Risk Score

Multiplicative combination:

```python
bubble_risk = (
    belief_boost × emotion_boost × volatility_momentum
  × capital_factor × (0.5 + 0.5 × narrative_factor)
)
```

---

## Trust System

### Trust State

Each KOL has four trust dimensions:

| Dimension | Description |
|---|---|
| trust_level | Base trust from bootstrapping |
| credibility_score | Historical prediction accuracy |
| social_proof | Follower count normalized |
| price_validation | Recent price-narrative alignment |

### Effective Trust

```
effective_trust = trust_level × credibility^0.6 × social_proof^0.3 × price_validation^0.4
```

### Trust Evolution

- **Time Decay**: Natural erosion over time
- **Validation Boost**: Price confirms narrative → trust increases
- **Falsification Penalty**: Price contradicts narrative → trust collapses

---

## Risk Detection

### ManipulationRiskAgent

Detects four abnormal patterns:

1. **Coordinated KOL Amplification**: Multiple KOLs spreading same narrative in short window
2. **Price-Narrative Self-Validation**: Price movement becomes "evidence" for narrative
3. **Retail FOMO Surge**: Abnormal retail buying activity
4. **Abnormal Trust Building**: Trust rising without price validation

### RegulatorAgent

Four intervention levels:

| Level | Threshold | Actions |
|---|---|---|
| NONE | risk < 0.30 | No action |
| LIGHT | 0.30-0.50 | Narrative throttle + risk warning |
| MODERATE | 0.50-0.70 | + KOL downweight |
| STRONG | >= 0.70 | + trading cooldown |

---

## Technology Stack

| Component | Technology | Purpose |
|---|---|---|
| Language | Python 3.10+ | Core implementation |
| Core Computation | NumPy | Numerical operations |
| API Server | FastAPI + Uvicorn | REST API + WebSocket |
| Data Validation | Pydantic | Request/response validation |
| Visualization | Matplotlib | Chart generation |
| Testing | Pytest | Test framework |
| Linting | Ruff | Code quality |
| Containerization | Docker | Deployment |
| CI/CD | GitHub Actions | Automated pipeline |
