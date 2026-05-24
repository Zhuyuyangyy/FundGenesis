# SCI Outline — ReflexMarket-AI V0.2

**Draft version：** 2026-05-07  
**Framework：** Multi-Agent Financial Reflexivity Simulation  
**Status：** Structure draft, content TBD

---

## Proposed Title

**ReflexMarket-AI: A Narrative-Driven Multi-Agent Framework for Financial Reflexivity Simulation**

---

## 1. Introduction (~800 words)

- Background: financial markets are not purely rational; narratives shape investor belief and behavior
- Problem: existing market simulation models lack structured narrative propagation mechanisms
- Gap: no computational framework that models narrative-KOL belief-capital-price reflexive loops
- Contribution: we propose ReflexMarket-AI, a multi-agent framework that simulates narrative-driven market reflexivity with quantitative metrics

**Key contributions (bullet list):**
1. Narrative event model with polarity, intensity, credibility, and decay
2. KOL-based social contagion network for non-uniform narrative diffusion
3. Three-factor belief update combining narrative exposure, social proof, and price confirmation
4. Reflexivity index as a quantitative market abnormal signal
5. Ablation experiments validating Narrative / KOL / Price Feedback contributions

---

## 2. Related Work (~1000 words)

### 2.1 Market Simulation and Multi-Agent Systems
- Agent-based market models (Alpine etc.)
- Limit order book simulation
- Retail vs institutional investor modeling

### 2.2 Narrative Economics
- Robert Shiller\'s narrative economics concept
- Narrative-driven market anomalies
- Social media and market sentiment

### 2.3 Social Contagion and KOL Networks
- Information cascade models
- KOL influence in social networks
- Herding behavior in financial markets

### 2.4 Financial Reflexivity
- George Soros\' reflexivity theory
- Self-reinforcing feedback loops in markets
- Price belief loops in behavioral finance

### 2.5 Research Gap
- No existing framework combines narrative events + KOL networks + belief updating + reflexivity monitoring in one simulation
- Our work addresses this gap

---

## 3. Method (~1500 words)

### 3.1 Narrative Event Modeling
- NarrativeEvent class: polarity, intensity, credibility, novelty, duration, target_sector
- NarrativeEngine: injection, propagation, decay
- Emotion field integration

### 3.2 KOL-based Social Contagion Network
- Three-tier KOL topology: Macro-KOL (2) / Influencer-KOL (5) / Micro-KOL (10) / Retail (100)
- PropagationModel: cascade probability, exposure update
- Social proof calculation per agent

### 3.3 Belief and Emotion Updating
- BeliefUpdaterV2: five-factor model (narrative, social, momentum, value, price_confirm)
- EmotionField: fear/inertia, greed/inertia, uncertainty
- Agent types: ValueInvestor / TrendFollower / EmotionalRetail

### 3.4 Capital Flow and Price Feedback
- CreatorController: market making, impact coefficient, noise
- Order submission and price update logic
- Capital flow imbalance tracking

### 3.5 Reflexivity Index
- Definition: weighted combination of emotion_divergence, belief_concentration, capital_imbalance, narrative_penetration
- Real-time computation per simulation step
- Bubble risk score derivation

### 3.6 System Architecture
- Figure: ReflexMarket-AI architecture diagram
- Data flow: Narrative → KOL → Belief → Emotion → Action → Capital → Price → Narrative

---

## 4. Experiments (~1200 words)

### 4.1 Demo Scenarios
- Demo 1: Positive narrative bubble formation (healthcare AI innovation)
- Demo 2: Regulatory shock and panic diffusion
- Demo 3: Narrative reversal and bubble burst
- Results: price trajectories, emotion dynamics, reflexivity index

### 4.2 Ablation Settings
- Group A: Baseline (no narrative, no KOL, no price feedback)
- Group B: Narrative Only
- Group C: Narrative + KOL
- Group D: Full Reflexive Loop
- 5 repeats per group, 300 steps per run, injection at step 30

### 4.3 Metrics
- emotion_amplification (primary)
- avg_reflexivity_index
- peak_bubble_risk_score
- narrative_penetration
- belief_concentration
- price_change_pct, volatility, max_drawdown

### 4.4 Results
- Table: key metrics across 4 groups (mean +- std)
- Figure 1: emotion_amplification bar chart (4 groups)
- Figure 2: avg_reflexivity_index bar chart
- Figure 3: peak_bubble_risk bar chart
- Statistical significance discussion

### 4.5 Discussion
- Narrative is the dominant emotion amplifier (27x)
- KOL has heterogeneous调节 effect: reduces extreme emotions (-35%) but increases belief_concentration (+10%)
- Price feedback triggers marginal bubble risk signal
- Reflexivity loop validated: narrative → emotion → belief → behavior → price → narrative

---

## 5. Limitations (~400 words)

1. Bubble risk signals are weak under current parameters
2. capital_imbalance is zero across all groups
3. Single market environment; no cross-market comparison
4. Fixed injection timing; narrative timing sensitivity unexplored
5. Agent types are simplified; real investor heterogeneity not fully modeled
6. No real-market data validation (pure simulation)

---

## 6. Conclusion (~300 words)

- Summary of contributions
- ReflexMarket-AI as a general framework for narrative-driven market reflexivity
- Future work: Trust Bootstrapping (V0.3), ManipulationRiskAgent (V0.4), RegulatorAgent (V0.5), ReflexMarket-Bench

---

## References (~20 items)

1. Soros, G. (1987). The Alchemy of Finance
2. Shiller, R.J. (2017). Narrative Economics
3. Bikhchandani, S. et al. (1992). Herd Behavior in Financial Markets
4. Kirilenko, A. et al. (2017). The Flash Crash
5. [Additional agent-based models, social contagion papers]

---

## Appendix: Demo Metrics Table

| Scenario | Start Price | Peak Price | Final Price | RefIdx | Panic |
|----------|------------|------------|------------|--------|-------|
| Positive Narrative Bubble | 100 | 276 | 259 | 0.256 | — |
| Regulatory Shock | 239 | 234 | 201 | — | 0.008 |
| Narrative Reversal Burst | 103 | 275 | 213 | 0.261 | — |

---

## Notes for Authors

- **Target venue:** Finance AI / Agent-based modeling / Computational social science venues
- **Novelty claim:** First computational framework to model narrative-KOL-reflexivity loop with quantitative ablation validation
- **Ethics:** No real market data used; purely synthetic simulation
- **Reproducibility:** All code and experiment outputs are publicly available (GitHub)
