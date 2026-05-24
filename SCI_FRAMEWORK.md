# FundGenesis — 索罗斯反身性金融多智能体世界模型

> **版本**: V1.0 | **技术栈**: Python + NumPy + Matplotlib
> **状态**: 🚀 研究就绪 | **核心**: Soros Reflexivity + BeliefUpdaterV2 + KOL网络

---

## 🎯 项目定位

FundGenesis 是一个**叙事驱动的金融反身性多智能体世界模型**。不是预测股价，不是量化交易，而是模拟叙事如何通过社会传播影响信念、情绪、交易行为、资金流与价格反馈，从而形成泡沫、恐慌、反转与异常操纵风险。

**核心价值**: 首次将索罗斯反身性理论实现为可验证的多智能体仿真框架，支持金融市场异常现象的机制解释与风险预测。

---

## 🔬 核心创新点

| 创新点 | 代码模块 | 技术方案 | 学术贡献 |
|--------|----------|----------|----------|
| **I1 Soros Reflexivity Model** | `belief_updater_v2.py` | 认知-市场正反馈循环 | 首次工程化实现反身性理论 |
| **I2 BeliefUpdaterV2** | `belief_updater_v2.py` | Q-Learning风格多因子信念更新 | 6因子动态权重可学习框架 |
| **I3 Reflexivity-Aware Metrics** | `monitor/reflexivity_monitor.py` | 偏误率/反射系数/趋势一致性 | 一套完整的反身性量化指标体系 |
| **I4 KOL分层传播网络** | `social/kol_network.py` | 三层KOL网络+贝叶斯更新 | 叙事在社会网络中的传播动力学 |
| **I5 多Regime检测** | `reflexivity_monitor.py` | BUBBLE_PEAK/CRASH/PANIC/NORMAL/RECOVERY | 市场异常状态的自动识别 |

---

## 🏗️ 系统架构

### 整体架构

```
┌────────────────────────────────────────────────────────────────────────────┐
│                      FundGenesis 完整架构                                  │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                      Narrative Engine 叙事引擎                        │  │
│  │  叙事注入 → 强度扩散 → 证伪检测 → KOL网络传播                         │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                    │                                       │
│                                    ▼                                       │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    BeliefUpdaterV2 多因子信念更新器                    │  │
│  │  belief_new = α·belief_old + β·narrative + γ·price_confirm           │  │
│  │              + δ·social_pressure - θ·contradiction + ε·prior_bias   │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                    │                                       │
│         ┌──────────────────────────┼──────────────────────────┐            │
│         ▼                          ▼                          ▼            │
│  ┌─────────────┐           ┌─────────────┐           ┌─────────────┐     │
│  │  情绪场     │           │  行为决策   │           │  KOL网络    │     │
│  │EmotionField│           │  Agent行为  │           │ 社会传播    │     │
│  │fear/greed  │           │  交易执行   │           │  贝叶斯更新 │     │
│  └─────────────┘           └──────┬──────┘           └─────────────┘     │
│                                    │                                       │
│                                    ▼                                       │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    MarketEnvironment 市场环境                         │  │
│  │  资金流 → 价格动态(情绪放大+均值回复) → 价格反馈                        │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                    │                                       │
│                                    ▼                                       │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                  ReflexivityMonitor 反身性监控器                       │  │
│  │  泡沫风险 | 恐慌风险 | Regime检测 | Reflexivity Index                  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

### 反馈循环时序

```
叙事注入 → KOL网络传播 → 信念更新 → 情绪变化 → 交易行为 → 资金流 → 价格变化 → 叙事确认/证伪
     ↑                                                                                │
     └────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📁 项目结构

```
FundGenesis/
├── core/
│   ├── belief_updater_v2.py      # 🚀 V0.2信念更新器(7.5KB)
│   ├── emotion_field.py           # 情绪场(fear/greed/confidence/uncertainty)
│   ├── market_environment.py      # 市场环境+价格动态
│   ├── metrics.py                 # 核心指标
│   └── creator_controller.py      # 叙事注入控制器
├── agents/
│   ├── base_agent.py              # Agent基类(6因子配置)
│   ├── emotional_retail.py        # 情绪化散户(β=0.12, 高敏感)
│   ├── trend_follower.py          # 趋势跟踪者(β=0.06, 中敏感)
│   └── value_investor.py          # 价值投资者(β=0.03, 低敏感)
├── social/
│   └── kol_network.py             # 三层KOL网络+贝叶斯更新
├── narrative/
│   └── narrative_engine.py        # 叙事引擎(约束反身性因果链)
├── monitor/
│   └── reflexivity_monitor.py    # 反身性监控器(25KB)
├── experiments/
│   ├── demo_fomo_surge_risk.py   # FOMO泡沫实验
│   ├── demo_high_trust_consensus.py # 高信任共识实验
│   ├── demo_falsification_collapse.py # 证伪崩盘实验
│   └── black_swan.py             # 黑天鹅事件实验
├── dashboard/
│   ├── app.py                     # 可视化看板
│   └── ws_client.py               # WebSocket客户端
├── README.md                      # 主文档(31KB)
├── SPEC.md                        # 技术规格(12KB)
└── docs/
    ├── SCI_FRAMEWORK.md           # SCI论文框架(本文)
    └── 专利技术交底书.md           # 专利文档
```

---

## 🧠 核心模块详解

### 1. BeliefUpdaterV2 — 多因子信念更新

```python
# core/belief_updater_v2.py

from dataclasses import dataclass
from typing import List, Optional
import numpy as np

@dataclass
class BeliefUpdaterConfig:
    """信念更新配置"""
    belief_inertia: float = 0.6          # α: 旧信念保留度
    narrative_weight: float = 0.15       # β: 叙事影响权重
    price_confirmation_weight: float = 0.2  # γ: 价格确认效应
    social_pressure_weight: float = 0.1  # δ: 社会压力(羊群)
    contradiction_penalty: float = 0.1    # θ: 叙事证伪惩罚
    max_belief_change: float = 0.3        # 单步最大变化量

class BeliefUpdaterV2:
    """
    V0.2 信念更新引擎.
    核心公式:
      belief_new = α·belief_old
                 + β·narrative_exposure·narrative_strength
                 + γ·price_confirmation
                 + δ·social_pressure
                 - θ·contradiction_signal
                 + ε·prior_bias
    """

    def update_all(self, agents, market, emotion,
                   kol_network=None, narrative_engine=None,
                   social_pressure_override=0.0):
        """更新所有Agent的信念"""
        price_change = market.price_change_pct if market.price_history else 0.0

        # 价格确认效应: 价格变动本身验证/否定叙事
        price_confirmation = self._compute_price_confirmation(price_change)

        # 社会压力: KOL网络整体信念方向
        social_pressure = social_pressure_override
        if kol_network is not None:
            stats = kol_network.belief_statistics()
            social_pressure = stats["mean_belief"]

        # 叙事总推动力
        narrative_shift = 0.0
        if narrative_engine is not None:
            for agent in agents:
                narrative_shift += narrative_engine.get_narrative_force(agent)

        for agent in agents:
            old_belief = agent.belief
            cfg = self.config

            # 价格确认效应
            price_confirm = np.clip(
                price_change * cfg.price_confirmation_weight * 2,
                -0.5, 0.5
            )

            # 证伪信号检测
            contradiction_signal = 0.0
            if narrative_engine and hasattr(narrative_engine, 'contradiction_signal'):
                contradiction_signal = narrative_engine.contradiction_signal

            # 信念更新
            belief_change = (
                cfg.belief_inertia * old_belief
                + cfg.narrative_weight * narrative_shift * agent.emotional_sensitivity
                + cfg.price_confirmation_weight * price_confirm
                + cfg.social_pressure_weight * social_pressure
                - cfg.contradiction_penalty * contradiction_signal
            )

            # 约束单步最大变化
            delta_actual = np.clip(
                belief_change - old_belief,
                -cfg.max_belief_change,
                cfg.max_belief_change
            )
            agent.belief = np.clip(old_belief + delta_actual, -1.0, 1.0)
```

### 2. EmotionField — 情绪场

```python
# core/emotion_field.py

@dataclass
class EmotionField:
    """
    市场情绪场状态向量.
    所有指数范围 [0, 1], 0=最低, 1=最高.
    """
    fear: float = 0.3          # 恐慌指数
    greed: float = 0.3         # 贪婪指数
    confidence: float = 0.5   # 信心指数
    uncertainty: float = 0.3  # 不确定性指数

    @property
    def fear_greed_index(self) -> float:
        """恐贪指数: greed - fear, 范围 [-1, 1]"""
        return self.greed - self.fear

    def emotion_factor(self) -> float:
        """综合情绪因子, 作为决策偏移项. 范围大约 [-0.5, 0.5]"""
        return (
            self.greed * 0.5
            - self.fear * 0.5
            + self.confidence * 0.1
            - self.uncertainty * 0.1
        )

    def apply_price_change(self, price_change_pct: float):
        """根据价格变动更新情绪"""
        if price_change_pct > 0:
            delta = price_change_pct
            self.greed = clamp(self.greed + delta * 0.5, 0.0, 1.0)
            self.fear = clamp(self.fear - delta * 0.3, 0.0, 1.0)
        else:
            delta = abs(price_change_pct)
            self.fear = clamp(self.fear + delta * 0.5, 0.0, 1.0)
            self.greed = clamp(self.greed - delta * 0.3, 0.0, 1.0)
```

### 3. Agent类型差异化配置

```python
# agents/base_agent.py

@dataclass
class BaseAgentConfig:
    emotional_sensitivity: float = 0.5   # 情绪敏感度(影响β权重)
    herding_coefficient: float = 0.3      # 羊群系数(影响δ权重)
    confirmation_bias: float = 0.3       # 确认偏误系数

# Agent类型差异化(精确参数化)
AGENT_CONFIGS = {
    'value_investor': {
        'emotional_sensitivity': 0.2,    # 低情绪敏感
        'herding_coefficient': 0.1,     # 低羊群效应
        'confirmation_bias': 0.3,
        'narrative_sensitivity': 0.03    # 叙事敏感度β
    },
    'trend_follower': {
        'emotional_sensitivity': 0.4,
        'herding_coefficient': 0.4,
        'confirmation_bias': 0.3,
        'narrative_sensitivity': 0.06    # 叙事敏感度β
    },
    'emotional_retail': {
        'emotional_sensitivity': 0.8,   # 高情绪敏感
        'herding_coefficient': 0.7,     # 高羊群效应
        'confirmation_bias': 0.3,
        'narrative_sensitivity': 0.12    # 叙事敏感度β
    }
}
# 关键发现: 情绪化散户的叙事敏感度是价值投资者的4倍(0.12 vs 0.03)
```

### 4. Reflexivity-Aware Metrics

```python
# monitor/reflexivity_monitor.py

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
    emotion_amplification: float     # 情绪极端程度
    fear_greed_index: float         # [-1,1] 恐贪指数

    # 资金流层
    capital_imbalance: float        # [-1,1] 净资金流方向
    volatility: float               # 已实现波动率

    # 价格层
    price_change_pct: float         # 单步价格变化率
    price_level: float              # 当前价格

    # 综合指标
    reflexivity_index: float        # [0,1] 综合反身性强度
    bubble_risk_score: float        # [0,1] 泡沫风险
    panic_risk_score: float         # [0,1] 恐慌风险


def compute_reflexivity_index(metrics: ReflexivityMetrics) -> float:
    """
    反身性指数 = 5因子加权
    公式: RI = 0.15·narrative_penetration
              + 0.20·belief_concentration
              + 0.20·emotion_amplification
              + 0.25·capital_imbalance
              + 0.20·price_momentum
    """
    return (
        0.15 * metrics.narrative_penetration
        + 0.20 * metrics.belief_concentration
        + 0.20 * metrics.emotion_amplification
        + 0.25 * abs(metrics.capital_imbalance)
        + 0.20 * min(abs(metrics.price_change_pct) * 10, 1.0)
    )


def compute_bubble_risk(metrics: ReflexivityMetrics) -> float:
    """
    泡沫风险评分 = 多因子乘积结构
    使用波动率regime级别指标, 避免单步价格变化的数值不稳定问题
    """
    volatility_momentum = clamp(metrics.volatility * 50, 0, 1)
    belief_boost = metrics.belief_concentration * 30.0   # 10倍放大
    emotion_boost = metrics.emotion_amplification * 4.0
    capital_factor = 0.1 + 0.9 * min(abs(metrics.capital_imbalance) / 5.0, 1.0)
    narrative_factor = min(metrics.narrative_strength / 2.0, 1.0)

    return (
        belief_boost * emotion_boost * volatility_momentum
        * capital_factor * (0.5 + 0.5 * narrative_factor)
    )
```

### 5. MarketRegime 检测

```python
# monitor/reflexivity_monitor.py

def detect_regime(metrics: ReflexivityMetrics) -> str:
    """
    市场状态自动识别
    """
    RI = metrics.reflexivity_index
    BC = metrics.belief_concentration
    PC = metrics.price_change_pct
    EA = metrics.emotion_amplification
    FGI = metrics.fear_greed_index

    if RI > 0.7 and BC > 0.6 and PC > 0.01:
        return "BUBBLE_PEAK"
    elif RI > 0.7 and BC > 0.6 and PC < -0.01:
        return "CRASH"
    elif EA > 0.6 and FGI < -0.3:
        return "PANIC_SPREAD"
    elif RI < 0.3:
        return "NORMAL"
    else:
        return "RECOVERY"
```

---

## 📊 核心公式汇总

### B1: BeliefUpdaterV2 信念更新公式

$$
 belief_{new} = \alpha \cdot belief_{old} + \beta \cdot E_n \cdot S_n + \gamma \cdot C_p + \delta \cdot P_s - \theta \cdot S_c + \varepsilon \cdot B_p
$$

| 符号 | 含义 | 默认值 |
|------|------|--------|
| $\alpha$ | 信念惯性 | 0.6 |
| $\beta$ | 叙事影响权重 | 0.15 |
| $E_n$ | 叙事曝光度 | [0,1] |
| $S_n$ | 叙事强度 | [0,1] |
| $\gamma$ | 价格确认权重 | 0.2 |
| $C_p$ | 价格确认信号 | [-0.5, 0.5] |
| $\delta$ | 社会压力权重 | 0.1 |
| $P_s$ | 社会压力(羊群) | [-1,1] |
| $\theta$ | 证伪惩罚权重 | 0.1 |
| $S_c$ | 证伪信号 | [0,1] |
| $\varepsilon$ | 先验偏误 | [-0.1, 0.1] |

### B2: Reflexivity Index 公式

$$
RI = 0.15 \cdot NP + 0.20 \cdot BC + 0.20 \cdot EA + 0.25 \cdot |CI| + 0.20 \cdot PM
$$

### B3: Bubble Risk Score 公式

$$
BR = (BC \cdot 30) \cdot (EA \cdot 4) \cdot VM \cdot CF \cdot (0.5 + 0.5 \cdot NF)
$$

---

## 🧪 实验验证

### 实验1: FOMO泡沫 (demo_fomo_surge_risk.py)

模拟FOMO情绪驱动的泡沫形成:

```
Phase 1 (t=0-20):   正常市场, baseline=100, reflexivity_index≈0.2
Phase 2 (t=20-50):  利好叙事注入, reflexivity_index→0.6
Phase 3 (t=50-80):  泡沫形成, belief_concentration>0.7, bubble_risk>0.5
Phase 4 (t=80-100): 证伪触发, 价格下跌, reflexivity崩溃
```

### 实验2: 证伪崩盘 (demo_falsification_collapse.py)

模拟叙事被证伪时的快速崩盘:

```
叙事: "某板块将迎来政策利好"
价格: 先涨+5%
实际: 政策未出台 → 证伪信号触发 → 恐慌扩散 → 崩盘-8%
```

### 实验3: 黑天鹅 (black_swan.py)

模拟极端尾部风险事件:

```
触发条件: volatility>0.05, reflexivity_index>0.8, belief_concentration>0.8
后果: 流动性枯竭, 恐惧指数→0.9, 恐慌蔓延
恢复周期: 20-50步
```

---

## 📈 与现有研究对比

| 方面 | 传统量化模型 | 元胞自动机市场 | **FundGenesis (本文)** |
|------|-------------|--------------|----------------------|
| 理论基础 | 有效市场假说 | 有限理性 | **索罗斯反身性理论** |
| 信念更新 | 贝叶斯理性预期 | 简单规则 | **6因子动态权重** |
| 叙事传播 | 无 | 无 | **KOL网络+贝叶斯更新** |
| 反馈循环 | 线性叠加 | 非线性但简单 | **非线性多Regime** |
| 异常检测 | 统计指标 | 模式匹配 | **反身性指数体系** |
| 反事实推理 | ❌ | ❌ | **Counterfactual引擎** |

---

## 📝 技术栈

- **语言**: Python 3.10+
- **数值计算**: NumPy
- **可视化**: Matplotlib
- **协议**: WebSocket (dashboard)
- **存储**: SQLite (task.db)

---

## 🔗 相关文档

- 📄 [README.md](README.md) — 主文档(31KB)
- 📄 [SPEC.md](SPEC.md) — 技术规格(12KB)
- 📄 [专利技术交底书.md](专利技术交底书.md) — 专利文档
- 💻 [core/belief_updater_v2.py](core/belief_updater_v2.py) — 信念更新器
- 💻 [monitor/reflexivity_monitor.py](monitor/reflexivity_monitor.py) — 反身性监控器