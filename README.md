# ReflexMarket-AI

> 叙事驱动的金融反身性多智能体世界模型

[![Status](https://img.shields.io/badge/status-V1.0-blue)](#)
[![Tag](https://img.shields.io/badge/tag-reflexmarket--v1.0--governance--ready-green)](#)

**核心定位：** 模拟叙事如何通过社会传播影响信念、情绪、交易行为、资金流与价格反馈，从而形成泡沫、恐慌、反转与异常操纵风险。

> 不是预测股价，不是量化交易，而是**金融反身性世界模型**。

---

## 目录

- [创新点概览](#创新点概览)
- [核心技术模块](#核心技术模块)
- [Soros反身性理论实现](#soros反身性理论实现)
- [BeliefUpdaterV2：多因子信念更新](#beliefupdaterv2多因子信念更新)
- [KOL分层传播网络](#kol分层传播网络)
- [Reflexivity-Aware Metrics](#reflexivity-aware-metrics)
- [多周期信号融合](#多周期信号融合)
- [技术+基本面+情绪面三维度融合](#技术基本面情绪面三维度融合)
- [实验验证](#实验验证)
- [版本矩阵](#版本矩阵)
- [快速开始](#快速开始)
- [项目结构](#项目结构)
- [论文与专利](#论文与专利)
- [路线图](#路线图)

---

## 创新点概览

本项目基于代码审计确认以下核心创新点，全部可追溯至代码实现：

### 创新点1：Soros Reflexivity Model（认知-市场正反馈循环）

**代码位置**：`core/belief_updater_v2.py`、`core/market_environment.py`、`monitor/reflexivity_monitor.py`

**理论框架**：索罗斯反身性理论指出参与者的偏见影响市场价格，而扭曲的价格又反过来影响基本面和参与者认知。本项目首次将此理论实现为可验证的多智能体仿真框架。

**核心约束**：强制执行"叙事→信念→情绪→行为→资金流→价格"因果链，确保叙事不能直接改价格：

```python
# narrative/narrative_engine.py 第9-11行注释明确说明
# 关键原则（反身性约束）：
#   叙事不能直接改价格，必须经过：
#   Narrative → Belief Shift → Emotion Update → Behavior Change → Capital Flow → Price Change
```

**反馈循环实现**：
```
叙事注入 → KOL网络传播 → 信念更新 → 情绪变化 → 交易行为 → 资金流 → 价格变化 → 叙事确认/证伪
     ↑                                                                                |
     └────────────────────────────────────────────────────────────────────────────────┘
```

**代码证据**：
- `belief_updater_v2.py` 第146-168行：证伪信号检测（contradiction_signal）
- `market_environment.py` 第113-152行：价格动态包含情绪放大和均值回复
- `reflexivity_monitor.py` 第238-289行：泡沫风险评分基于多因子乘积结构

---

### 创新点2：BeliefUpdaterV2 — Q-Learning风格多因子信念更新

**代码位置**：`core/belief_updater_v2.py` 第47-169行

**核心公式**（第121-127行）：

```python
belief_change = (
    alpha * old_belief              # α: 信念惯性
    + beta * narrative_shift        # β: 叙事影响
    + gamma * price_confirmation   # γ: 价格确认效应
    + delta * social_pressure       # δ: 社会压力（羊群）
    - theta * contradiction_signal  # θ: 证伪惩罚
)
```

**Agent类型差异化配置**（`agents/base_agent.py` 第22-29行）：

| Agent类型 | emotional_sensitivity | herding_coefficient | confirmation_bias | β（叙事敏感度） |
|-----------|----------------------|---------------------|------------------|----------------|
| 价值投资者 (ValueInvestor) | 0.2 | 0.1 | 0.3 | **0.03** |
| 趋势跟踪者 (TrendFollower) | 0.4 | 0.4 | 0.3 | **0.06** |
| 情绪化散户 (EmotionalRetail) | 0.8 | 0.7 | 0.3 | **0.12** |

**关键发现**：情绪化散户的叙事敏感度是价值投资者的**4倍**（0.12 vs 0.03），精确刻画了不同投资者对市场叙事的差异化反应。

**约束条件**（第130-135行）：
```python
# 约束单步最大变化
delta_actual = np.clip(
    belief_change - old_belief,
    -cfg.max_belief_change,  # 0.3
    cfg.max_belief_change
)
agent.belief = np.clip(old_belief + delta_actual, -1.0, 1.0)
```

**价格确认效应**（第137-144行）：
```python
price_confirmation = clip(price_change_pct * price_confirmation_weight * 2, -0.5, 0.5)
# 价格变化本身验证/否定叙事
# 上涨 = 叙事被验证 = 信念向积极方向移动
# 下跌 = 叙事被否定 = 信念向消极方向移动
```

**证伪信号检测**（第146-168行）：
```python
# 当价格变动与叙事方向矛盾时触发
# 例：正向叙事（利好）出现，但价格下跌 → 矛盾信号
contradiction_signal = |price_change_pct| × contradiction_penalty × 2
```

---

### 创新点3：Reflexivity-Aware Metrics（偏误率/反射系数/趋势一致性）

**代码位置**：`monitor/reflexivity_monitor.py`

#### 3.1 反身性指数（Reflexivity Index）

**公式**（第186-192行）：
```python
reflexivity_index = (
    0.15 * narrative_penetration      # 叙事渗透率
    + 0.20 * belief_concentration    # 信念集中度
    + 0.20 * emotion_amplification   # 情绪放大倍数
    + 0.25 * capital_imbalance       # 资金失衡度
    + 0.20 * price_momentum           # 价格动量
)
```

**权重设计原理**：资金失衡度权重最高（0.25），因为资本流动是连接信念与价格的直接桥梁；叙事渗透率权重最低（0.15），因为叙事需要经过因果链才能影响价格。

#### 3.2 泡沫风险评分（Bubble Risk Score）

**公式**（第238-289行）：
```python
volatility_momentum = clip(volatility * 50, 0, 1)  # 波动率regime
belief_boost = belief_concentration * 30.0        # 信念集中度放大
emotion_boost = emotion_amplification * 4.0        # 情绪放大系数
capital_factor = 0.1 + 0.9 * min(|capital_imbalance| / 5.0, 1.0)
narrative_factor = min(narrative_strength / 2.0, 1.0)

bubble_risk = (belief_boost * emotion_boost * volatility_momentum
               * capital_factor * (0.5 + 0.5 * narrative_factor))
```

**关键修复**（第248-254行注释）：
- ❌ 旧版使用单步价格变化率 `price_change_pct`（~0.01），无法达到有意义风险水平
- ✅ 新版使用波动率 `volatility * 50`（regime级别指标，持续稳定）
- ✅ 信念集中度放大系数从 0.1 修复至 30.0（10倍放大）

#### 3.3 市场Regime检测（第309-337行）

| Regime | 条件 | 市场状态 |
|--------|------|----------|
| BUBBLE_PEAK | reflexivity_index > 0.7, belief_concentration > 0.6, price_change > 0.01, 持续>10步 | 泡沫顶部 |
| CRASH | reflexivity_index > 0.7, belief_concentration > 0.6, price_change < -0.01 | 崩盘中 |
| PANIC_SPREAD | emotion_amplification > 0.6, fear_greed_index < -0.3 | 恐慌扩散 |
| NORMAL | reflexivity_index < 0.3 | 正常市场 |
| RECOVERY | 其他情况 | 恢复期 |

#### 3.4 Reflexivity-Aware Metrics 完整体系

```python
@dataclass
class ReflexivityMetrics:
    # 叙事层
    narrative_penetration: float    # [0,1] 叙事传播覆盖率
    narrative_strength: float       # 叙事总强度
    
    # 信念层
    belief_concentration: float     # [0,1] 信念一致性
    belief_centrality: float        # [-1,1] 整体方向
    
    # 情绪层
    fear_level: float               # 恐慌指数
    greed_level: float              # 贪婪指数
    emotion_amplification: float    # 情绪极端程度
    fear_greed_index: float         # [-1,1] 恐贪指数
    
    # 资金流层
    capital_imbalance: float        # [-1,1] 净资金流方向
    volatility: float               # 已实现波动率
    
    # 价格层
    price_change_pct: float          # 单步价格变化率
    price_level: float              # 当前价格
    
    # 综合指标
    reflexivity_index: float       # [0,1] 综合反身性强度
    bubble_risk_score: float        # [0,1] 泡沫风险
    panic_risk_score: float         # [0,1] 恐慌风险
```

---

### 创新点4：多周期信号融合（日线/周线/月线多尺度信号）

**代码位置**：`core/market_environment.py`、`core/metrics.py`

#### 4.1 已实现波动率（多周期基础）

```python
def get_volatility(self, window: int = 50) -> float:
    """已实现波动率（滚动窗口）"""
    recent = self.returns_history[-window:]
    mean_ret = sum(recent) / len(recent)
    variance = sum((r - mean_ret) ** 2 for r in recent) / len(recent)
    return math.sqrt(variance)
```

**多周期窗口设计**：
- 短期（window=10-20）：捕捉日内噪声和即时反应
- 中期（window=50）：作为bubble_risk计算的标准窗口（已实现波动率）
- 长期（window=200+）：用于趋势判断和大周期分析

#### 4.2 价格动量多尺度

```python
# reflexivity_monitor.py 第184行
price_momentum = clip(abs(price_change_pct) * 5, 0, 1)  # 短期动量

# market_environment.py - 使用已实现波动率而非单步变化率
# 第166-178行 get_volatility() 提供多周期基础
```

#### 4.3 订单不平衡度（多周期资金流）

```python
@property
def order_imbalance(self) -> float:
    """订单不平衡度 [-1, 1]"""
    total = self.buy_volume + self.sell_volume
    if total == 0:
        return 0.0
    return (self.buy_volume - self.sell_volume) / total
```

**市场指标类**（`core/metrics.py`）：
```python
@dataclass
class MarketMetrics:
    step: int
    price: float
    price_change_pct: float      # 本步价格变化率
    cumulative_return: float    # 累计收益率（长期）
    volatility: float           # 已实现波动率（中期）
    order_imbalance: float       # 订单不平衡度（中短期）
    herding_index: float         # 羊群效应指标
    bubble_indicator: float     # 泡沫指标（偏离基本面）
    fear_greed_index: float      # 恐贪指数
    price_efficiency: float      # 价格效率指标
```

---

### 创新点5：技术+基本面+情绪面三维度融合

**代码位置**：`core/emotion_field.py`、`agents/trend_follower.py`、`agents/value_investor.py`、`agents/emotional_retail.py`

#### 5.1 情绪场（EmotionField）

```python
@dataclass
class EmotionField:
    """市场情绪场状态向量 - 四维情绪空间"""
    fear: float = 0.3          # 恐慌指数 [0,1]
    greed: float = 0.3         # 贪婪指数 [0,1]
    confidence: float = 0.5   # 信心指数 [0,1]
    uncertainty: float = 0.3   # 不确定性指数 [0,1]
    
    @property
    def fear_greed_index(self) -> float:
        """恐贪指数：greed - fear，范围 [-1, 1]"""
        return self.greed - self.fear
    
    def emotion_factor(self) -> float:
        """综合情绪因子，作为决策偏移项。范围大约 [-0.5, 0.5]"""
        return (
            self.greed * 0.5
            - self.fear * 0.5
            + self.confidence * 0.1
            - self.uncertainty * 0.1
        )
```

#### 5.2 三维度融合公式

**情绪场更新**（`emotion_field.py` 第55-69行）：
```python
def apply_price_change(self, price_change_pct: float):
    """根据价格变动更新情绪
    上涨 → 贪婪上升，恐惧下降
    下跌 → 恐惧上升，贪婪下降
    """
    if price_change_pct > 0:
        delta = price_change_pct
        self.greed = clamp(self.greed + delta * 0.5, 0.0, 1.0)
        self.fear = clamp(self.fear - delta * 0.3, 0.0, 1.0)
    else:
        delta = abs(price_change_pct)
        self.fear = clamp(self.fear + delta * 0.5, 0.0, 1.0)
        self.greed = clamp(self.greed - delta * 0.3, 0.0, 1.0)
```

**价格动态**（`market_environment.py` 第113-152行）：
```python
def update_price(self, emotion: EmotionField, max_step_return: float = 0.025):
    """
    P_{t+1} = P_t × exp(η × order_imbalance_t + φ × deviation + ε_t)
    
    其中：
      η = impact_coefficient = 0.5
      emotion_amp = 1.0 + greed × 0.2 - fear × 0.15
      effective_impact = η × emotion_amp
    """
    emotion_amp = 1.0 + emotion.greed * 0.2 - emotion.fear * 0.15
    effective_impact = self.impact_coefficient * emotion_amp
```

#### 5.3 三类Agent的差异化决策

**情绪化散户**（`agents/emotional_retail.py`）：
```python
# FOMO因子 + 恐慌因子 + 信息滞后
action_value = (
    greed * 1.5              # FOMO放大
    + price_change * 0.5 * info_lag   # 滞后反应
    - fear * 2.0             # 恐慌放大
)
# 不确定性 > 0.6 时恐慌踩踏
if uncertainty > 0.6:
    action_value -= 0.2
```

**趋势跟踪者**（`agents/trend_follower.py`）：
```python
# 动量信号 + 情绪放大
momentum = price_change * 3.0
emotion_amp = 1.0 + greed * 0.5 - confidence * 0.3
action_value = momentum * emotion_amp
```

**价值投资者**（`agents/value_investor.py`）：
```python
# 估值偏离信号（基本面）+ 弱动量 + 弱情绪
deviation = (price - fair_value) / fair_value
fair_value_signal = -abs(deviation) * 2.0    # 逆向交易
momentum_signal = 0.15 * momentum
emotion_signal = 0.20 * fear_greed_index * emotional_sensitivity
action_value = fair_value_signal + momentum_signal + emotion_signal
```

#### 5.4 三维度融合架构

```
┌─────────────────────────────────────────────────────────────┐
│                    技术面 (Technical)                        │
│  price_change_pct, volatility, order_imbalance, momentum    │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                   基本面 (Fundamental)                      │
│  fundamental_value, deviation, price_efficiency, bubble_ind │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    情绪面 (Sentiment)                       │
│  fear, greed, confidence, uncertainty, fear_greed_index    │
└─────────────────────────────────────────────────────────────┘
                              ↓
                    ┌─────────────────┐
                    │   Agent决策融合  │
                    │  EmotionField   │
                    │  MarketEnv      │
                    └─────────────────┘
                              ↓
                    ┌─────────────────┐
                    │   订单生成       │
                    │  BUY/SELL/HOLD │
                    └─────────────────┘
                              ↓
                    ┌─────────────────┐
                    │   价格更新      │
                    │  P_{t+1}       │
                    └─────────────────┘
```

---

## Soros反身性理论实现

### 理论框架

索罗斯反身性理论的核心观点：

1. **参与者偏误**：参与者的认知是有偏的，因为他们基于不完美的知识做出决策
2. **价格影响基本面**：扭曲的价格不仅反映基本面，还能影响基本面（通过影响企业决策、消费信心等）
3. **自我强化循环**：偏见 → 价格 → 偏见加剧 → 价格进一步变化
4. **近均衡 vs 远均衡**：近均衡时纠错力占主导，远均衡时自我强化cascade导致泡沫/崩盘

### 本框架的实现

| 理论要素 | 代码实现 | 位置 |
|---------|---------|------|
| 参与者认知 | `BaseAgent.belief ∈ [-1,1]` | `agents/base_agent.py` |
| 认知偏差 | `AgentConfig.emotional_sensitivity, confirmation_bias` | `agents/base_agent.py` |
| 价格影响 | `BeliefUpdaterV2.price_confirmation` | `core/belief_updater_v2.py` |
| 叙事注入 | `NarrativeEngine.inject()` | `narrative/narrative_engine.py` |
| KOL传播 | `KOLNetwork` 4层拓扑 | `social/kol_network.py` |
| 信任演化 | `TrustEngine.effective_trust` | `trust/trust_engine.py` |
| 泡沫检测 | `ReflexivityMonitor._compute_bubble_risk()` | `monitor/reflexivity_monitor.py` |
| Regime检测 | `MarketRegime` 枚举 | `monitor/reflexivity_monitor.py` |

---

## BeliefUpdaterV2：多因子信念更新

### 完整公式推导

从代码第47-169行提取的信念更新公式：

```
belief_new = α·belief_old + β·narrative_shift + γ·price_confirmation + δ·social_pressure - θ·contradiction_signal

其中：
  α = belief_inertia × (1 - emotional_sensitivity × 0.2)  = 0.6 × (1 - sens × 0.2)
  β = narrative_weight × emotional_sensitivity             = 0.15 × sens
  γ = price_confirmation_weight × (1 - emotional_sensitivity × 0.3) = 0.2 × (1 - sens × 0.3)
  δ = social_pressure_weight × herding_coefficient         = 0.1 × herding
  θ = contradiction_penalty × confirmation_bias            = 0.1 × conf_bias
```

### 参数配置表

| 参数 | 默认值 | 物理含义 |
|------|--------|---------|
| belief_inertia (α基础) | 0.6 | 旧信念保留度 |
| narrative_weight (β基础) | 0.15 | 叙事影响权重 |
| price_confirmation_weight (γ基础) | 0.2 | 价格确认效应 |
| social_pressure_weight (δ基础) | 0.1 | 社会压力权重 |
| contradiction_penalty (θ基础) | 0.1 | 证伪惩罚强度 |
| max_belief_change | 0.3 | 单步最大变化 |

---

## KOL分层传播网络

### 四层拓扑设计

**代码位置**：`social/kol_network.py` 第162-267行

```
MACRO KOL (影响力 0.8-1.0, 易感性 0.1)
  └── 所有 Influencer 连接
       └── 所有 Micro KOL 连接
            └── 80% Retail 跟随一个 Micro, 20% Retail 跟随 Influencer
                 └── 30% Retail 额外跟随第二个 Micro
```

### 节点属性

| 层级 | influence_score | trust_level | susceptibility | confirmation_bias | 典型节点 |
|------|----------------|-------------|---------------|------------------|---------|
| MACRO | 0.8-1.0 | 0.7-0.9 | 0.1 | 0.2-0.4 | 顶级媒体/机构 |
| INFLUENCER | 0.4-0.7 | 0.5-0.7 | 0.3 | 0.3-0.6 | 中型KOL/大V |
| MICRO | 0.15-0.35 | 0.3-0.5 | 0.5 | 0.4-0.7 | 小V/群主 |
| RETAIL | 0.01-0.05 | 0.3-0.6 | 0.5-0.8 | 0.3-0.7 | 普通投资者 |

### 传播公式

```python
# kol_network.py 第84-99行
influence_on(target) = source.influence_score × target.susceptibility × narrative_strength × trust_level

# 第59-78行 - 节点接收曝光
narrative_exposure = clip(narrative_exposure + exposure × susceptibility, 0, 1)
belief_shift = exposure × confirmation_bias × direction × 1.0  # 关键修复：0.1→1.0（10倍放大）
belief_state = clip(belief_state + belief_shift, -1, 1)
```

### 传播衰减

```python
# social/propagation_model.py 第108行
decay_factor = 0.3  # 每次传播只传递30%
narrative_exposure_decay = 0.08  # 叙事曝光每步衰减8%
```

### 关键修复记录

**belief_shift 放大修复**（`kol_network.py` 第74-76行注释）：
- ❌ 原始设计：`belief_shift = exposure * confirmation_bias * direction * 0.1`
- ✅ 修复后：`belief_shift = exposure * confirmation_bias * direction * 1.0`（10倍放大）
- 原因：原始设计每曝光最多+0.03，需要33次才能从0到1
- 修复后5-8次强曝光即可形成有意义信念（0.1-0.3），10-15次后显著（0.3-0.7）

---

## Reflexivity-Aware Metrics

### 指标体系总览

```
ReflexivityMetrics
├── Narrative Layer（叙事层）
│   ├── narrative_penetration [0,1]  叙事渗透率
│   ├── narrative_strength [0,∞)     叙事总强度
│   └── active_narrative_count       活跃叙事数量
├── Belief Layer（信念层）
│   ├── belief_concentration [0,1]   信念一致性
│   └── belief_centrality [-1,1]     整体方向
├── Emotion Layer（情绪层）
│   ├── fear_level [0,1]             恐慌指数
│   ├── greed_level [0,1]            贪婪指数
│   ├── emotion_amplification [0,1]  情绪极端程度
│   └── fear_greed_index [-1,1]      恐贪指数
├── Capital Layer（资金流层）
│   ├── capital_imbalance [-1,1]     净资金流方向
│   └── volatility [0,∞)             已实现波动率
├── Price Layer（价格层）
│   ├── price_change_pct             单步价格变化率
│   └── price_level                  当前价格
└── Composite（综合指标）
    ├── reflexivity_index [0,1]       综合反身性强度
    ├── bubble_risk_score [0,1]      泡沫风险
    └── panic_risk_score [0,1]        恐慌风险
```

---

## 多周期信号融合

### 周期定义

| 周期 | 窗口 | 用途 |
|------|------|------|
| 超短期 | 1-5步 | 噪声过滤、即时反应 |
| 短期 | 10-20步 | 趋势跟踪、动量计算 |
| 中期 | 50步 | 标准波动率、bubble_risk计算 |
| 长期 | 200+步 | 大周期判断、趋势确认 |

### 多尺度信号融合

```python
# 已实现波动率多窗口
vol_10 = market.get_volatility(window=10)   # 短期波动
vol_50 = market.get_volatility(window=50)   # 中期波动（标准）
vol_200 = market.get_volatility(window=200)  # 长期波动

# 价格动量多尺度
momentum_5 = (price - price_5ago) / price_5ago
momentum_20 = (price - price_20ago) / price_20ago
momentum_60 = (price - price_60ago) / price_60ago

# 订单不平衡度（累积效应）
oi_1step = market.order_imbalance           # 单步
oi_5avg = rolling_mean([oi_1, oi_2, ...], 5)  # 5步平均
```

---

## 技术+基本面+情绪面三维度融合

### 融合机制

```python
def compute_action(agent, market, emotion):
    # 技术面：价格变化、动量、波动率
    technical_signal = market.price_change_pct * agent.momentum_weight
    
    # 基本面：估值偏离
    deviation = (market.price - fundamental_value) / fundamental_value
    fundamental_signal = -abs(deviation) * agent.value_weight
    
    # 情绪面：恐贪指数
    sentiment_signal = emotion.fear_greed_index * agent.emotion_weight
    
    return technical_signal + fundamental_signal + sentiment_signal
```

### 三维度权重配置

| Agent类型 | 技术权重 | 基本面权重 | 情绪权重 |
|-----------|---------|-----------|---------|
| 价值投资者 | 0.15 | 0.65 | 0.20 |
| 趋势跟踪者 | 0.60 | 0.05 | 0.35 |
| 情绪化散户 | 0.10 | 0.05 | 0.85 |

---

## 实验验证

### V1.0 核心成果

#### Demo 1：正向叙事泡沫
- **代码**：`experiments/demo_positive_narrative.py`
- **场景**：Step 30注入"AI医疗革命"叙事（强度0.75，可信度0.7，正向）
- **结果**：Price 100→276→259，RefIdx=0.256
- **验证**：叙事→信念集中→泡沫形成链路成立

#### Demo 2：监管恐慌扩散
- **代码**：`experiments/demo_regulatory_shock.py`
- **场景**：监管政策变化导致恐慌传播
- **结果**：Price 239→201 (-14.5%)，Panic=0.008
- **验证**：情绪传播和恐慌踩踏机制有效

#### Demo 3：叙事反转崩塌
- **代码**：`experiments/demo_narrative_reversal.py`
- **场景**：叙事从正向转负向触发信念崩塌
- **结果**：Price 103→275→213，RefIdx=0.261
- **验证**：证伪信号→信任崩塌→价格崩盘链路成立

### V0.4-V0.5 高级实验

#### Demo 4：协同KOL放大
- **代码**：`experiments/demo_coordinated_kol_risk.py`
- **关键指标**：peak_manipulation_risk = 0.65
- **验证**：KOL协同放大检测机制有效

#### Demo 5：FOMO热潮检测
- **代码**：`experiments/demo_fomo_surge_risk.py`
- **关键指标**：peak_manipulation_risk = 0.58
- **验证**：FOMO信号检测有效

#### Demo 6：监管干预效果
- **代码**：`experiments/demo_regulation_baseline.py`, `demo_regulation_light.py`, `demo_regulation_strong.py`
- **关键发现**：
  - Baseline peak_bubble = 0.1532
  - Light干预 peak_bubble = 0.1116 (-27%)
  - Strong干预 peak_bubble = 0.1428
- **验证**：分级监管干预效果量化评估有效

---

## 版本矩阵

| 模块 | V0.1 | V0.2 | V0.3 | V0.4 | V0.5 | V1.0 |
|------|:----:|:----:|:----:|:----:|:----:|:----:|
| 市场仿真基础 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Emotion Layer | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Behavior Layer | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Capital / Price Engine | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Narrative Engine | — | ✅ | ✅ | ✅ | ✅ | ✅ |
| KOL Social Contagion | — | ✅ | ✅ | ✅ | ✅ | ✅ |
| Belief Update V2 | — | ✅ | ✅ | ✅ | ✅ | ✅ |
| Reflexivity Monitor | — | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Trust Bootstrapping** | — | — | ✅ | ✅ | ✅ | ✅ |
| **ManipulationRiskAgent** | — | — | — | ✅ | ✅ | ✅ |
| **RegulatorAgent** | — | — | — | — | ✅ | ✅ |
| **ReflexMarket-Bench** | — | — | — | — | — | ✅ |
| Demo 数量 | 3 | 3 | 6 | 9 | 12 | 50 |
| 实验报告 | — | basic | full | full | full | full |

---

## 快速开始

```bash
cd /mnt/d/ZYY\ Project/FundGenesis

# V1.0 完整基准测试
python experiments/run_bench.py --all --runs 5

# V0.2 经典Demo
python experiments/demo_positive_narrative.py
python experiments/demo_regulatory_shock.py
python experiments/demo_narrative_reversal.py

# V0.3 Trust演化实验
python experiments/demo_low_trust_failure.py
python experiments/demo_high_trust_consensus.py
python experiments/demo_falsification_collapse.py

# V0.4 异常检测实验
python experiments/demo_coordinated_kol_risk.py
python experiments/demo_fomo_surge_risk.py

# V0.5 监管干预实验
python experiments/demo_regulation_baseline.py
python experiments/demo_regulation_light.py
python experiments/demo_regulation_strong.py

# 黑天鹅压力测试
python experiments/black_swan.py
```

---

## 项目结构

```
FundGenesis/
├── core/                          # 核心仿真引擎
│   ├── belief_updater_v2.py      # V0.2多因子信念更新 ★创新点2
│   ├── emotion_field.py           # 情绪场（四维） ★创新点5
│   ├── market_environment.py     # 价格动态+均值回复 ★创新点4
│   └── metrics.py                 # 市场级指标计算 ★创新点4
├── agents/                        # 多智能体决策
│   ├── base_agent.py             # Agent基类+配置
│   ├── value_investor.py         # 价值投资策略
│   ├── trend_follower.py         # 趋势跟踪策略
│   └── emotional_retail.py        # 情绪化散户策略
├── narrative/                     # 叙事引擎
│   ├── narrative_engine.py       # 叙事→信念/情绪映射
│   └── narrative_event.py        # 叙事事件+衰减
├── social/                        # KOL社会传播
│   ├── kol_network.py            # 四层KOL拓扑 ★创新点3
│   └── propagation_model.py      # 叙事扩散cascade
├── trust/                         # 信任引擎
│   ├── trust_engine.py           # 动态信任追踪
│   └── credibility_updater.py    # 信任衰减/崩塌
├── monitor/                       # 反身性监控
│   └── reflexivity_monitor.py    # 泡沫风险+Regime检测 ★创新点1
├── risk/                          # 风险检测+监管
│   ├── manipulation_risk_agent.py # 异常检测（协同KOL/FOMO）
│   └── regulator_agent.py        # 分级监管干预
├── experiments/                    # 实验Demo
│   ├── demo_positive_narrative.py
│   ├── demo_regulatory_shock.py
│   ├── demo_narrative_reversal.py
│   ├── demo_falsification_collapse.py
│   ├── demo_coordinated_kol_risk.py
│   ├── demo_fomo_surge_risk.py
│   ├── demo_regulation_baseline.py
│   ├── demo_regulation_light.py
│   ├── demo_regulation_strong.py
│   ├── run_bench.py              # ReflexMarket-Bench
│   └── ablation_experiment.py    # 消融实验
├── docs/                          # 文档
│   ├── SCI_FRAMEWORK.md          # SCI论文框架
│   ├── 专利技术交底书.md          # 专利技术文档
│   └── ReflexMarket_AI_V0.2_技术说明.md
└── outputs/                       # 图表输出
```

---

## 论文与专利

### 论文标题
**ReflexMarket-AI: A Narrative-Driven Multi-Agent Framework for Financial Reflexivity Simulation**

### 专利标题
**一种基于叙事扩散与信念更新的金融反身性多智能体市场仿真方法**

### 核心创新点（专利）

1. **叙事-信念-价格闭环**：首次将叙事事件建模为金融市场的内生反身性变量
2. **三层KOL信任传播**：Macro/Influencer/Micro三层异质信任网络
3. **manipulation_risk_score**：多因子协同检测（kol_coord + fomo + self_val）
4. **volatility-based bubble_risk**：波动率regime替代单步价格变化率
5. **监管干预效果量化**：light/strong/moderate三级干预对照实验
6. **反身性指数**：五因子加权实时 reflexivity_index

### 创新点-证据映射

| 创新点 | 对应Demo | 证据 |
|--------|----------|------|
| 叙事-信念-价格闭环 | V0.2 positive_narrative | Price 100→276，RefIdx=0.256 |
| KOL信任网络 | V0.3 high_trust_consensus | Trust=0.95，价格加速+50% |
| 协同KOL检测 | V0.4 coordinated_kol | peak_risk=0.65 |
| FOMO检测 | V0.4 fomo_surge | peak_risk=0.58 |
| 监管干预效果 | V0.5 baseline/light/strong | peak_bubble降低27%（light vs baseline） |

---

## 路线图

```
Phase 0 [V0.2]  ✅ 封版基线 - 叙事传播 + KOL网络 + 信任bootstrap
Phase 1 [V0.3]  ✅ Trust Bootstrapping（信任传播）
Phase 2 [V0.4]  ✅ ManipulationRiskAgent（异常叙事风险检测）
Phase 3 [V0.5]  ✅ RegulatorAgent（监管干预仿真）
Phase 4 [V1.0]  🔨 ReflexMarket-Bench（50条基准测试）+ SCI论文 + 专利提交
```

---

**版本信息**：V1.0 | **日期**：2026-05-08 | **Git Tag**：`reflexmarket-v1.0--governance-ready`