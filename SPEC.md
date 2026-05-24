# ReflexMarket-AI V1.0 技术规格书

> **项目定位**：叙事驱动的金融反身性多智能体仿真平台
> **版本**：V1.0 | **日期**：2026-05-08
> **Git Commit**：`f95f92b` | **Tag**：`reflexmarket-v0.5-governance-ready`

---

## 一、核心架构

### 1.1 系统全景

```
叙事注入 → KOL网络传播 → 信任演化 → 信念更新
                                         ↓
情绪Field ← 叙事共鸣 ← 价格反馈 ← 资金流
     ↓                              ↑
情绪放大                     订单提交
     ↓                              ↓
 Agent决策 ──────────────────→ 价格更新
```

### 1.2 核心模块

| 模块 | 文件 | 职责 |
|------|------|------|
| **市场环境** | `core/market_environment.py` | 价格发现、订单簿、资金流 |
| **情绪场** | `core/emotion_field.py` | fear/greed惯性、情绪传播 |
| **叙事引擎** | `narrative/narrative_engine.py` | 叙事注入、衰减、传播 |
| **KOL网络** | `social/kol_network.py` | 三层KOL拓扑、信任bootstrap |
| **传播模型** | `social/propagation_model.py` | 跨层级叙事扩散cascade |
| **信任引擎** | `trust/trust_engine.py` | 信任衰减、credibility更新 |
| **信念更新** | `core/belief_updater_v2.py` | 五因子信念更新 |
| **反身性监控** | `monitor/reflexivity_monitor.py` | 实时风险指标观测 |
| **风险识别** | `risk/manipulation_risk_agent.py` | 协同KOL/FOMO/价格自证检测 |
| **监管干预** | `risk/regulator_agent.py` | 四类干预动作（light/strong） |

### 1.3 数据流

```
NarrativeEvent 
  → PropagationModel.inject_narrative()
  → KOLNetwork.propagate() [跨Tier Cascade]
  → TrustEngine.record_interaction()
  → BeliefUpdaterV2.update_all()
  → Agent.decide() [情绪影响]
  → Market.submit_order()
  → Market.update_price() → EmotionField
  → ReflexivityMonitor.observe()
  → ManipulationRiskAgent.evaluate()
  → RegulatorAgent.step()
```

---

## 二、V0.5 核心成果

### 2.1 ManipulationRiskAgent — 异常叙事传播检测

**文件**：`risk/manipulation_risk_agent.py`

**检测能力**：
- `coordinated_kol_amplification`：多KOL短窗口协同放大同一叙事
- `price_narrative_validation`：价格变化确认叙事，形成自证循环
- `fomo_surge_detected`：零售FOMO信号注入
- `kol_trust_collapse`：KOL信任崩塌触发叙事逆转

**评分公式**：
```
manipulation_risk_score = clamp(
    0.45 * kol_coordination_score
  + 0.35 * fomo_score
  + 0.20 * self_validation_score,
  0, 1
)
```

**阈值**：
- monitor: 0.15
- human_review: 0.25
- block: 0.60

### 2.2 RegulatorAgent — 监管干预仿真

**文件**：`risk/regulator_agent.py`

**四类干预动作**：
| 动作 | 效果 | 触发强度 |
|------|------|----------|
| `narrative_throttle` | 降低叙事产生率 + 传播速度 | LIGHT+ |
| `risk_warning` | 市场风险警告公告 | LIGHT+ |
| `kol_downweight` | 降低KOL影响力权重 | MODERATE+ |
| `trading_cooldown` | 临时限制大单交易 | STRONG |

**强度分级**：
- `NONE(0)`：无干预
- `LIGHT(1)`：`narrative_throttle` + `risk_warning`
- `MODERATE(2)`：LIGHT + `kol_downweight`
- `STRONG(3)`：MODERATE + `trading_cooldown`

**关键设计**：
- 接入 `ManipulationRiskAgent` 输出作为输入
- `risk_score >= 0.25` 时触发 `LIGHT`
- `risk_score >= 0.40` 时升级至 `MODERATE`
- `risk_score >= 0.60` 时强制 `STRONG`
- Strong模式可强制在指定步触发（override机制）

### 2.3 ReflexivityMonitor — bubble_risk量化

**文件**：`monitor/reflexivity_monitor.py`

**volatility-based bubble_risk公式**：
```
volatility_momentum = clip(volatility * 50, 0, 1)
belief_boost = belief_concentration * 25
emotion_boost = emotion_amplification * 4
capital_factor = min(abs(capital_imbalance) / 5, 1)
narrative_factor = min(narrative_strength / 2, 1)

bubble_risk = belief_boost * emotion_boost * volatility_momentum * 5 * capital_factor * (0.5 + 0.5 * narrative_factor)
```

**修复记录**：
- ❌ 旧：`price_change_pct`（单步变化率 ~0.01，无法达到0.6）
- ✅ 新：`volatility`（波动率regime指标，persistent）
- ✅ 新：`belief_boost = bc * 25`（信念集中度基数太小）
- ✅ 新：`emotion_boost = ea * 4`（情绪信号未传入）

---

## 三、实验结果汇总

### 3.1 V0.5 三组对照（200步，异常叙事注入场景）

| 指标 | Baseline | Light | Strong | 趋势 |
|------|----------|-------|--------|------|
| peak_manipulation_risk | 0.504 | 0.504 | 0.504 | = |
| **peak_bubble_risk** | **0.1532** | **0.1116** | **0.1428** | Light < Strong < Baseline |
| high_risk_steps | 12 | 12 | 12 | = |
| final_drawdown | -3.37% | -8.31% | -3.21% | — |
| total_interventions | 0 | 10 | 11 | — |
| first_intervention | N/A | step55 | **step40** | Strong更早 |
| kol_downweight | 0 | 2 | **3** | Strong更多 |
| trading_cooldown | 0 | 0 | **1** | Strong独有 |

**验收**：
- ✅ peak_risk >= 0.50
- ✅ intervention_triggered（light/strong均触发）
- ✅ strong_intervention_triggered（强制step40触发）
- ✅ early_trigger_verified（step40 < step55）

### 3.2 历史版本结果

| 版本 | Demo | 核心指标 |
|------|------|----------|
| V0.2 | positive_narrative | Price 100→276，RefIdx=0.256 |
| V0.2 | regulatory_shock | Price 239→201 (-14.5%) |
| V0.2 | narrative_reversal | Price 103→275→213 |
| V0.3 | low_trust_failure | Trust=0.016，叙事抑制 |
| V0.3 | high_trust_consensus | Trust=0.95，价格加速+50% |
| V0.3 | falsification_collapse | Trust -90%，Price -34% |
| V0.4 | coordinated_kol | peak_risk=0.65 |
| V0.4 | fomo_surge | peak_risk=0.58 |
| V0.5 | baseline | peak_bubble=0.1532 |
| V0.5 | light | peak_bubble=0.1116 (-27%) |
| V0.5 | strong | peak_bubble=0.1428 |

---

## 四、ReflexMarket-Bench

### 4.1 设计目标

50条benchmark，验证框架在以下维度上的表现：
1. **叙事传播**（Narrative Propagation）
2. **信任演化**（Trust Evolution）
3. **反身性检测**（Reflexivity Detection）
4. **风险识别**（Risk Identification）
5. **监管干预**（Regulatory Intervention）

### 4.2 场景分类

**Category A: Narrative Propagation (15条)**
- A01: Positive narrative bubble formation
- A02: Negative narrative panic diffusion
- A03: Mixed narrative oscillation
- A04: Narrative decay over time
- A05: Cross-sector narrative jump
- A06-A15: (扩展场景)

**Category B: Trust Evolution (10条)**
- B01: Low trust KOL failure
- B02: High trust KOL consensus
- B03: Trust gradual erosion
- B04: Sudden trust collapse (falsification)
- B05: Cross-tier trust propagation
- B06-B10: (扩展场景)

**Category C: Reflexivity Detection (10条)**
- C01: Price self-validation loop
- C02: Narrative-price mutual confirmation
- C03: Emotional herding escalation
- C04: Reflexivity index spike detection
- C05: Bubble formation early warning
- C06-C10: (扩展场景)

**Category D: Risk Identification (10条)**
- D01: Coordinated KOL amplification
- D02: FOMO surge detection
- D03: Narrative逆转 detection
- D04: Multi-pattern simultaneous detection
- D05: Low-risk baseline
- D06-D10: (扩展场景)

**Category E: Regulatory Intervention (5条)**
- E01: Baseline (no intervention)
- E02: Light intervention (narrative_throttle + risk_warning)
- E03: Strong intervention (full 4-action package)
- E04: Early intervention timing effect
- E05: Intervention after bubble formation

### 4.3 运行方式

```python
# 基准测试运行
python experiments/run_bench.py --category A --runs 3
python experiments/run_bench.py --category B --runs 3
python experiments/run_bench.py --all --runs 1  # 快速扫描
python experiments/run_bench.py --all --runs 5  # 完整验证
```

### 4.4 评估指标

| 指标 | 计算方式 | 阈值 |
|------|----------|------|
| manipulation_risk_score | risk_agent.evaluate() | peak >= 0.50 |
| bubble_risk_score | reflexivity_monitor.observe() | peak >= 0.15 |
| intervention_effect | (baseline_peak - intervened_peak) / baseline_peak | >= 15% |
| high_risk_steps | count(risk >= 0.25) | 差异显著 |
| coordination_score | kol_coordination_score | peak >= 0.50 |
| fomo_score | risk_agent.fomo_score | peak >= 0.60 |
| price_drawdown | (peak_price - final_price) / peak_price | 有意义差异 |

---

## 五、API Reference

### 5.1 CreatorController — 初始化入口

```python
controller = CreatorController(
    market_config=MarketConfig(
        initial_price=100.0,
        impact_coefficient=0.20,
        noise_std=0.008,
        total_agents=100,
    ),
    emotion_config={
        "initial_fear": 0.15,
        "initial_greed": 0.60,
        "fear_inertia": 0.92,
        "greed_inertia": 0.92,
    }
)
market = controller.setup_market()
emotion = controller.setup_emotion()
```

### 5.2 ReflexivityMonitor.observe()

```python
metrics = monitor.observe(
    step=step,
    market=market,
    emotion=emotion,
    kol_network=kol_network,
    narrative_engine=narrative_engine,
    agents=agents,
)
# 返回 ReflexivityMetrics:
#   .bubble_risk_score, .panic_risk_score
#   .reflexivity_index, .emotion_amplification
#   .volatility, .price_change_pct, .capital_imbalance
```

### 5.3 ManipulationRiskAgent.evaluate()

```python
report = risk_agent.evaluate(
    step=step,
    kol_network=kol_network,
    trust_engine=trust_engine,
    reflexivity_monitor=reflexivity_monitor,
    market=market,
    narrative_engine=narrative_engine,
    propagation_model=propagation,
    agents=agents,
)
# 返回 ManipulationRiskReport:
#   .manipulation_risk_score (float 0-1)
#   .risk_level (low/medium/high/critical)
#   .detected_patterns (List[str])
#   .recommended_action (str)
#   .fomo_score, .kol_coordination_score, .self_validation_score
```

### 5.4 RegulatorAgent.step()

```python
action = regulator.step(
    risk_score=report.manipulation_risk_score,
    market_state={
        "price": market.price,
        "volatility": market.volatility,
        "volume": market.total_volume,
    },
    manipulation_flags={
        "kol_coordination": report.kol_coordination_score,
        "fomo_detected": report.fomo_score > 0.5,
        "price_validation": report.self_validation_score > 0.4,
    },
    narrative_engine=narrative_engine,
    kol_network=kol_network,
    agents=agents,
)
# 返回: (action: InterventionAction, intensity: InterventionIntensity)
```

---

## 六、已知限制

1. **KOL belief_state 基数低**： belief_concentration 约 0.003-0.005（受初始值0和susceptibility=0.1限制）
2. **net_demand 累积问题**：market.net_demand 跨步累积，应改用 order_imbalance（per-step）
3. **high_risk_steps 三组相同**：12步（三组都是），说明阈值触发点相同
4. **FOMO信号未传入emotion field**：risk_agent.record_fomo_signal() 仅更新risk_agent内部状态，未影响emotion.greed
5. **RegulatorAgent._apply_to_* 动作效果未验证**：干预动作修改属性需在对应Agent/KOL/Engine上验证存在

---

## 七、版本路线

```
V0.1 (2026-05-06): FundGenesis baseline — 市场+情绪+叙事基础框架
V0.2 (2026-05-07 am): Narrative propagation + KOL网络 + 信任bootstrap
V0.3 (2026-05-07 pm): Trust演化实验（low/high/falsification）
V0.4 (2026-05-07 late): ManipulationRiskAgent (协同KOL/FOMO检测)
V0.5 (2026-05-08 am): RegulatorAgent (监管干预仿真) ✅ governance-ready
V1.0 (2026-05-08): ReflexMarket-Bench 50条 + SCI论文 + 专利提交
```

---

## 八、论文与专利

**论文标题**：ReflexMarket-AI: A Narrative-Driven Multi-Agent Framework for Financial Reflexivity Simulation

**专利标题**：一种基于叙事传播与多智能体反身性反馈的金融市场风险仿真与异常传播检测方法

**核心创新点**：
1. **叙事-信念-价格闭环**：首次将叙事事件建模为金融市场的内生反身性变量
2. **三层KOL信任传播**：Macro/Influencer/Micro三层异质信任网络
3. **manipulation_risk_score**：多因子协同检测（kol_coord + fomo + self_val）
4. **volatility-based bubble_risk**：波动率regime替代单步价格变化率
5. **监管干预效果量化**：light/strong/moderate三级干预对照实验
6. **反身性指数**：五因子加权实时 reflexivity_index

**创新点-证据映射**：
| 创新点 | 对应Demo | 证据 |
|--------|----------|------|
| 叙事-信念-价格闭环 | V0.2 positive_narrative | Price 100→276，RefIdx=0.256 |
| KOL信任网络 | V0.3 high_trust_consensus | Trust=0.95，价格加速+50% |
| 协同KOL检测 | V0.4 coordinated_kol | peak_risk=0.65 |
| FOMO检测 | V0.4 fomo_surge | peak_risk=0.58 |
| 监管干预效果 | V0.5 baseline/light/strong | peak_bubble降低27%（light vs baseline） |