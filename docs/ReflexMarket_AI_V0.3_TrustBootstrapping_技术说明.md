# ReflexMarket-AI V0.3 技术说明
## Trust Bootstrapping — 信任引导机制

**版本：** V0.3  
**日期：** 2026-05-07  
**Git Tag：** `reflexmarket-v0.3-trust-ready`  
**Commit：** `731da63`  

---

## 1. 核心定位

V0.3 在 V0.2「叙事传播 → 价格反身性」基础上，新增**信任动力学**层：

```
叙事 → 信任 → 信念 → 情绪 → 行为 → 资金 → 价格 → 反馈
```

**核心问题：** 同样的叙事，为什么有些能引爆市场共识，有些不能？

**答案：** 信任决定了叙事能否有效传播并转化为市场行为。

---

## 2. 架构变更

### 2.1 新增模块

| 文件 | 职责 |
|------|------|
| `trust/trust_engine.py` | 信任状态机（per-KOL effective_trust 计算） |
| `trust/trust_bootstrapper.py` | 初始信任锚定（bootstrap credibility/social_proof） |
| `trust/trust_decay_model.py` | 信任衰减（随时间/沉默/曝光衰减） |
| `trust/credibility_updater.py` | 历史准确率驱动的可信度更新 |

### 2.2 修改模块

| 文件 | 变更 |
|------|------|
| `social/propagation_model.py` | 传播计算引入 trust_weight 加权（解决循环导入） |
| `social/kol_network.py` | KOL 持有 TrustState 引用，追踪 per-KOL effective_trust |

### 2.3 关键设计决策：Lazy Import 解决循环依赖

循环依赖路径：
```
social/__init__.py → PropagationModel
→ narrative.narrative_event → NarrativeEngine
→ core.emotion_field → core.belief_updater_v2
→ narrative.narrative_engine (循环!)
```

解决方案：在 `social/__init__.py` 和 `core/__init__.py` 中使用 `__getattr__` 延迟导入：

```python
# social/__init__.py
def __getattr__(name):
    if name == "PropagationModel":
        from social.propagation_model import PropagationModel
        globals()["PropagationModel"] = PropagationModel
        return PropagationModel
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
```

---

## 3. 核心算法

### 3.1 Effective Trust 计算

```
effective_trust = TrustLevel × Credibility^α × SocialProof^β × PriceValidation^γ

其中：
  α = 2.0 (credibility_alpha)
  β = 1.0 (social_proof_beta)  
  γ = 0.5 (price_validation_gamma)
  min_effective_trust = 0.01
```

### 3.2 信任引导（Bootstrap）

初始信任来源三元组：
- **Credibility（可信度）：** 基于历史预测准确率
- **Social Proof（社会证明）：** 基于粉丝量级（Macro/Influencer/Micro）
- **Price Validation（价格验证）：** 基于过去 5 步价格变动方向与叙事方向的一致性

### 3.3 信任衰减

```python
decayed = current_trust * (1 - decay_rate) ^ steps_since_update
decay_rate = base_rate * exposure_gap_penalty * sentiment_penalty
```

### 3.4 叙事证伪触发信任崩塌

```python
if narrative.polarity == Polarity.NEGATIVE and target_kol.confirmed:
    penalty = 2.0 * base_penalty  # 证伪惩罚翻倍
    trust_level *= (1 - penalty)   # 信任直接崩塌
```

---

## 4. V0.3 新增实验证据

| Demo | 核心论点 | 结果 | 关键数字 |
|------|---------|------|---------|
| Demo 4 | 低信任 → 叙事无法传播 | ✅ 部分抑制 | trust=0.016，曝光率 0.009 |
| Demo 5 | 高信任 → 共识加速引爆 | ✅ 确认 | 峰值 step 75 vs baseline step 100 |
| Demo 6 | 证伪 → 信任崩塌 → 泡沫破裂 | ✅ 确认 | trust -90%，价格 259→184 |

---

## 5. 与 V0.2 的关系

V0.3 **不是**替代 V0.2，而是叠加信任机制增强解释力：

| 能力 | V0.2 | V0.3 |
|------|------|------|
| 叙事传播 | ✅ | ✅ |
| 价格反身性 | ✅ | ✅ |
| KOL 层级传播 | ✅ | ✅ |
| **信任感知传播** | ❌ | ✅ |
| **per-KOL 信任追踪** | ❌ | ✅ |
| **证伪触发信任崩塌** | ❌ | ✅ |
| **信任加速/抑制共识** | ❌ | ✅ |

---

## 6. 技术约束与已知局限

1. **传播抑制不完全：** Demo 4 显示即使 trust=0.016（极低），泡沫仍未完全阻止（103→263，+156.4% vs baseline +176%）。说明 trust 机制提供 damping 效果但非完全门控。
2. **Bulk 阈值保守：** `shadow/database/scorer.py` 中 bulk_operation 阈值 100 行较严格，production 需调参。
3. **价格验证延迟：** PriceValidation 仅看过去 5 步，对短期叙事可能响应不足。

---

## 7. 下一阶段（V0.4）

V0.4 将新增 **ManipulationRiskAgent**，在 trust 机制基础上识别异常传播路径：

```
异常 KOL 协同传播检测
FOMO 聚集异常检测
价格—叙事自我验证检测
情绪单边化检测
manipulation_risk_score 输出
```

---

*本文件为 ReflexMarket-AI V0.3 封版技术说明，与 demo_evidence_v0.3/ 和 Phase2_TrustBootstrapping_实验结论摘要.md 共同构成完整证据链。*
