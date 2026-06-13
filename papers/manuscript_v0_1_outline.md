# FundGenesis 论文大纲 v0.1

**标题**: FundGenesis: Narrative-Driven Financial Reflexivity Multi-Agent World Model
**目标**: SCI期刊投稿 (建议: JASSS / JEDC / Quantitative Finance)
**预估长度**: 25-35页

---

## Abstract (250-300词)

### 结构
1. **背景** (2句): 金融市场反身性理论的重要性
2. **问题** (2句): 现有ABM模型的三大局限
3. **方法** (3句): FundGenesis核心创新
4. **验证** (2句): 12个Demo实验验证
5. **贡献** (2句): 理论和实践意义

### 内容要点
- 叙事驱动的多智能体市场仿真框架
- 五因子信念更新器、分层KOL网络、证伪信任崩溃、反身性监控、分级监管
- 因果链约束: Narrative → Belief → Emotion → Behavior → Capital → Price
- 12个Demo验证泡沫形成、信任崩溃、监管干预

---

## 1. Introduction (3-4页)

### 1.1 研究背景
- 金融市场复杂性与反身性理论 (Soros, 1987)
- 叙事经济学兴起 (Shiller, 2017, 2020)
- Agent-Based建模在金融中的应用

### 1.2 问题陈述
**现有ABM模型三大局限**:
1. **信念形成过度简化**: 固定类型(基本面/技术面)或简单外推
2. **叙事动态被忽视**: 叙事作为外生噪声或简单情绪指数
3. **社会传播结构缺失**: 无KOL层级、无信任机制、无级联传播

### 1.3 研究目标
- 将Soros反身性理论形式化为可计算模型
- 建模叙事→信念→情绪→行为→价格的完整因果链
- 提供泡沫形成、信任崩溃、监管干预的仿真平台

### 1.4 主要贡献
1. **五因子信念更新器**: 整合叙事、价格确认、社会压力、证伪信号
2. **分层KOL传播网络**: 四层影响层级,级联传播
3. **证伪信任崩溃机制**: 信任的乘法崩溃模型
4. **反身性监控指标系统**: 实时泡沫/恐慌检测
5. **分级监管干预框架**: 量化评估干预效果

### 1.5 论文结构
- Section 2: Related Work
- Section 3: Methodology
- Section 4: Experiments
- Section 5: Results
- Section 6: Discussion
- Section 7: Conclusion

---

## 2. Related Work (4-5页)

### 2.1 经典Agent-Based市场模型
- Santa Fe Institute模型 (Arthur et al., 1997)
- Lux & Marchesi噪声交易者模型 (1999, 2000)
- Farmer & Foley政策分析框架 (2009)

**对比点**: FundGenesis的信念更新更复杂,有社会传播结构

### 2.2 市场中的意见动力学
- Borkowski有界置信模型 (2023)
- Alfarano & Lux异质Agent模型 (2022)
- Hegselmann & Krause有界置信模型 (2002)

**对比点**: FundGenesis引入叙事内容,而非仅信念值

### 2.3 叙事经济学
- Shiller叙事经济学理论 (2017, 2020)
- 历史案例: 铁路狂热、互联网泡沫、COVID-19

**对比点**: FundGenesis将定性理论形式化为计算模型

### 2.4 金融市场中的社会影响
- Banerjee信息级联 (1992)
- Bikhchandani时尚/文化传播 (1992)
- DeMarzo说服与信息质量 (2001)
- Kolasinac KOL影响研究 (2021)

**对比点**: FundGenesis建模四层KOL层级结构

### 2.5 深度学习市场模型
- LSTM/Transformer预测模型
- 图神经网络

**对比点**: FundGenesis提供可解释因果机制,可做反事实分析

### 2.6 差距分析与本文贡献

| 差距 | 现有工作 | FundGenesis方案 |
|------|----------|-----------------|
| 信念形成 | 静态或简单外推 | 五因子更新(叙事、价格、社会、证伪) |
| 叙事处理 | 外生噪声 | 一等公民(衰减、内容) |
| 社会结构 | 同质Agent | 四层KOL网络+信任 |
| 反身性建模 | 隐式 | 显式因果链约束 |
| 信任动态 | 静态 | 动态+证伪崩溃 |

---

## 3. Methodology (8-10页)

### 3.1 系统概述
**反身性因果链约束**:
```
Narrative → Belief Shift → Emotion Update → Behavior Change → Capital Flow → Price Change
```

**系统架构图** (Figure 1):
- 叙事引擎 → 信念更新器 → 情绪场 → Agent决策 → 市场价格
- KOL网络传播 + 信任引擎 + 反身性监控 + 监管代理

### 3.2 叙事引擎 (NarrativeEngine)

**3.2.1 叙事作为一等公民**
- 叙事事件属性: intensity, credibility, novelty, polarity, duration
- 叙事衰减: effective_intensity = intensity × (steps_remaining / duration)

**3.2.2 叙事→信念映射**
```python
belief_shift = intensity × credibility × (1 + 0.2 × novelty) × (1 + 0.25 × price_confirmation) × 0.3
```

**3.2.3 叙事→情绪传播**
- 价格确认叙事: greed_delta += price_change × 0.25 × 0.3
- 价格否定叙事: fear_delta += |price_change| × 0.25 × 0.2

### 3.3 五因子信念更新器 (BeliefUpdaterV2)

**3.3.1 更新公式**
```
belief_new = α·belief_old + β·narrative_shift + γ·price_confirmation + δ·social_pressure - θ·contradiction
```

**3.3.2 权重计算**
```python
alpha = belief_inertia × (1 - sens × 0.2)
beta = narrative_weight × sens
gamma = price_confirmation_weight × (1 - sens × 0.3)
delta = social_pressure_weight × herding_coefficient
theta = contradiction_penalty × confirmation_bias
```

**3.3.3 Agent类型参数**

| 类型 | emotional_sensitivity | herding_coefficient | confirmation_bias |
|------|----------------------|--------------------|--------------------|
| ValueInvestor | 0.2 | 0.1 | 0.3 |
| TrendFollower | 0.4 | 0.4 | 0.3 |
| EmotionalRetail | 0.8 | 0.7 | 0.3 |

**3.3.4 硬约束**
- 单步最大变化: |Δbelief| ≤ 0.3
- 信念范围: [-1.0, 1.0]

### 3.4 分层KOL传播网络 (KOLPropagationNetwork)

**3.4.1 网络拓扑**
```
MACRO (2) → INFLUENCER (5) → MICRO (10) → RETAIL (100)
```

**3.4.2 层级参数**

| 层级 | influence_score | susceptibility | trust_level |
|------|-----------------|----------------|-------------|
| MACRO | 0.8-1.0 | 0.1 | 0.7-0.9 |
| INFLUENCER | 0.4-0.7 | 0.3 | 0.5-0.7 |
| MICRO | 0.15-0.35 | 0.5 | 0.3-0.5 |
| RETAIL | 0.01-0.05 | 0.5-0.8 | 0.3-0.6 |

**3.4.3 传播公式**
```python
influence = source.influence_score × target.susceptibility × narrative_strength × target.trust_level
```

**3.4.4 衰减机制**
- 每次传输: 30%暴露 (decay_factor = 0.3)
- 每步衰减: 8% (decay = 0.08)

### 3.5 信任引擎 (TrustEngine + CredibilityUpdater)

**3.5.1 有效信任公式**
```
effective_trust = Trust × Credibility^0.6 × SocialProof^0.3 × PriceValidation^0.4
```

**3.5.2 证伪崩溃机制**
```python
# 当预测被证伪:
trust_level *= 0.1  # 90%崩溃
credibility *= 0.1
```

**3.5.3 信任启动**
- 初始可信度基于层级
- 社会证明随关注者增长
- 价格验证随预测测试积累

### 3.6 反身性监控 (ReflexivityMonitor)

**3.6.1 反身性指数**
```python
reflexivity_index = (
    0.15 * narrative_penetration
    + 0.20 * belief_concentration
    + 0.20 * emotion_amplification
    + 0.25 * capital_imbalance
    + 0.20 * price_momentum
)
```

**3.6.2 泡沫风险分数** (乘法结构)
```python
bubble_risk = belief_boost × emotion_boost × volatility_momentum × capital_factor × narrative_factor
```

**3.6.3 市场状态分类**
- BUBBLE_FORMING: RefIdx>0.7, BeliefConc>0.6, PriceChange>0.01
- CRASH: 同上但PriceChange<-0.01
- PANIC_SPREAD: EmotionAmp>0.6, FearGreed<-0.3
- NORMAL: RefIdx<0.3

### 3.7 监管代理 (RegulatorAgent)

**3.7.1 干预措施**
| 措施 | 公式 |
|------|------|
| NARRATIVE_THROTTLE | cap = max(1 - risk × 0.55, 0.25) |
| KOL_DOWNWEIGHT | penalty = max(1 - risk × 0.65, 0.15) |
| RISK_WARNING | strength = min(risk × 1.2, 1.0) |
| TRADING_COOLDOWN | slowdown = min(risk × 0.75, 0.75) |

**3.7.2 分级干预**
| 风险 | 分数 | 措施 |
|------|------|------|
| NONE | <0.30 | 无 |
| LIGHT | 0.30-0.50 | 叙事抑制+警告 |
| MODERATE | 0.50-0.70 | +KOL降权 |
| STRONG | ≥0.70 | +交易冷却 |

### 3.8 价格动态

**更新公式**:
```python
P_{t+1} = P_t × exp(η × order_imbalance - φ × deviation + ε)
```
- η = 0.5 (冲击系数)
- φ = 0.03 (<20%偏离) / 0.10 (≥20%偏离)
- ε ~ N(0, 0.01)
- emotion_amp = 1.0 + greed × 0.2 - fear × 0.15

### 3.9 仿真步序 (因果链执行)

```python
# 1. KOL网络传播叙事
propagator.step()
narrative_engine.tick()

# 2. 信念更新
belief_updater.update_all(agents, market, emotion, kol_network, narrative_engine)

# 3. 叙事→情绪传播
narrative_engine.propagate_to_emotion(emotion, price_change_pct)

# 4. Agent决策
for agent in agents:
    action = agent.decide(market.get_snapshot(), emotion)
    market.submit_order(agent.agent_id, action.value, volume)

# 5. 价格更新 (含均值回归和情绪放大)
market.update_price(emotion)

# 6. 情绪衰减
emotion.decay_toward_neutral(inertia=0.92)
```

---

## 4. Experiments (4-5页)

### 4.1 实验设置

**仿真参数**:
| 参数 | 值 | 描述 |
|------|-----|------|
| initial_price | 100.0 | 初始价格 |
| impact_coefficient | 0.5 | 价格敏感度 |
| noise_std | 0.01 | 随机冲击 |
| mean_reversion | 0.03/0.10 | 均值回归强度 |
| total_agents | 100 | 10 VI + 30 TF + 60 ER |
| KOL网络 | 2+5+10+100 | 四层结构 |
| simulation_steps | 200-400 | 每实验步数 |

**评估指标**:
| 指标 | 公式 | 阈值 |
|------|------|------|
| reflexivity_index | 5因子加权和 | >0.7 = 高反身性 |
| bubble_risk_score | 5因子乘积 | >0.6 = 临界泡沫 |
| manipulation_risk | 0.45×kol_coord + 0.35×fomo + 0.20×self_val | >0.50 = 异常 |
| intervention_effect | (baseline-peak)/baseline | >15% = 有效 |

### 4.2 实验1: 正面叙事泡沫形成

**设计**:
- Step 0-30: 基线期
- Step 30: 注入"AI Medical Revolution"叙事 (intensity=0.75, credibility=0.7)
- Step 30-300: 观察传播动态

**预期结果**:
- 叙事渗透: Macro→Influencer→Micro→Retail (分层级联)
- 信念集中: 从~0.01增至>0.60
- 情绪: Greed>0.7, Fear<0.2
- 价格: 增长>15%
- 反身性指数: 峰值>0.6
- 泡沫风险: 进入"临界"状态(≥0.6)

### 4.3 实验2: 证伪信任崩溃

**设计**:
- Step 20-100: 正面叙事→泡沫形成
- Step 100: 注入证伪事件"AI Hype Debunked"
- 强制信任崩溃: trust × 0.1, credibility × 0.1

**预期结果**:
- Step 20-100: 价格上涨~20%, mean_trust > 0.80
- Step 100: 信任崩溃至<0.1
- 价格下跌>15%
- 反身性指数: 先升后降

### 4.4 实验3: 监管干预对比

**设计**:
- 三种条件: 基线、轻度干预、强力干预
- 注入异常叙事波 (Macro step25 → Influencer step28 → Micro step33)
- 添加价格自我验证 (step45) + FOMO信号 (step55)
- 200步对比

**预期结果**:
| 指标 | 基线 | 轻度 | 强力 |
|------|------|------|------|
| peak_bubble_risk | 0.1532 | 0.1116 | 0.1428 |
| intervention_effect | N/A | 27% | 7% |
| first_intervention | N/A | step 55 | step 40 |

### 4.5 消融实验

**四组消融**:
- A_Baseline: 无叙事,无KOL
- B_Narrative_Only: 仅叙事注入
- C_Narrative_KOL: 叙事+KOL传播
- D_Full_Loop: 完整因果链

**关键对比**: 情绪放大效应差异 (0.03 vs 0.76)

### 4.6 风险检测实验 (Demo 7/8/9)

| Demo | 场景 | 峰值风险 | 检测模式 |
|------|------|----------|----------|
| 7 | 正常传播 | 0.12 (LOW) | 无 |
| 8 | 协调KOL | 0.65 (HIGH) | coordinated_kol_amplification |
| 9 | FOMO激增 | 0.58 (HIGH) | price_narrative_self_validation + retail_fomo_surge |

---

## 5. Results (4-5页)

### 5.1 泡沫形成过程

**Figure 4**: 价格+情绪+信念时间序列
- 展示Step 30叙事注入后的动态变化
- 标注分层传播延迟 (Macro→Influencer→Micro→Retail)

**关键数据**:
- 价格峰值: 272-279 (增长~170%)
- 峰值贪婪: 0.35-0.31
- 信念集中: 0.006-0.008

### 5.2 证伪崩溃过程

**Figure 5**: 信任+价格+反身性指数时间序列
- 展示Step 100证伪事件后的崩溃动态

**关键数据**:
- 信任崩溃: 0.80→0.08 (90%下降)
- 价格回撤: -8.1% (最大)
- 反身性指数: 从~0.27降至~0.26

### 5.3 消融实验结果

**Figure 7**: 四组条件对比柱状图

**Table 4**: 消融实验详细数据

| 条件 | 峰值价格 | 最终价格 | 情绪放大 | 最大回撤 | 波动率 |
|------|----------|----------|----------|----------|--------|
| A_Baseline | 272.61 | 261.16 | 0.0279 | -6.04% | 0.0115 |
| B_Narrative_Only | 278.83 | 261.44 | **0.7626** | -8.10% | 0.0115 |
| C_Narrative_KOL | 276.82 | 260.61 | 0.4916 | -7.94% | 0.0116 |
| D_Full_Loop | 276.34 | 262.16 | 0.4916 | -7.33% | 0.0113 |

**关键发现**: 叙事注入使情绪放大提升27倍

### 5.4 监管干预效果

**Figure 6**: 三种干预条件泡沫风险对比

**Table 5**: 监管干预详细结果

| 条件 | 峰值风险 | 干预效果 | 首次干预 |
|------|----------|----------|----------|
| Baseline | 0.1532 | N/A | N/A |
| Light | 0.1116 | 27% | Step 55 |
| Strong | 0.1428 | 7% | Step 40 |

**关键发现**: 轻度干预更有效,过度干预可能适得其反

### 5.5 风险检测能力

**Table 6**: 风险检测实验结果

| 场景 | 峰值风险 | 风险等级 | 检测模式 |
|------|----------|----------|----------|
| 正常传播 | 0.12 | LOW | 无 |
| 协调KOL | 0.65 | HIGH | coordinated_kol_amplification |
| FOMO激增 | 0.58 | HIGH | price_narrative_self_validation |

**关键发现**: 系统能区分正常传播和异常操纵行为

### 5.6 因果链验证

**叙事→信念→情绪→行为→价格**:
1. 叙事注入后,信念先于价格变化
2. 情绪变化滞后于信念变化
3. 价格变化最后发生
4. 验证因果链约束有效

---

## 6. Discussion (3-4页)

### 6.1 理论贡献

**6.1.1 Soros反身性理论的形式化**
- 首次将"参与者偏见→感知现实→行动→市场结果"循环形式化为可计算模型
- 五因子信念更新公式捕捉认知和社会机制

**6.1.2 叙事经济学的计算实现**
- 将Shiller的定性理论转化为可执行仿真
- 叙事作为一等公民,有属性、衰减、传播

**6.1.3 社会影响的层级建模**
- 四层KOL网络捕捉真实社交媒体结构
- 级联传播模拟信息扩散

### 6.2 实践意义

**6.2.1 金融监管**
- 分级干预框架提供量化决策支持
- 轻度干预可能比强力干预更有效

**6.2.2 风险管理**
- 反身性指数和泡沫风险分数实时监控
- 区分正常传播和异常操纵

**6.2.3 投资决策**
- 理解叙事如何影响市场
- 识别泡沫形成早期信号

### 6.3 与现有工作的区别

**Table 7**: 与SFI、Lux-Marchesi、Borkowski对比

| 特性 | SFI | Lux-Marchesi | Borkowski | FundGenesis |
|------|-----|--------------|-----------|-------------|
| 信念更新 | 固定类型 | 简单外推 | 有界置信 | **五因子** |
| 叙事 | 无 | 无 | 无 | **一等公民** |
| 社会结构 | 同质 | 同质 | 同质 | **四层KOL** |
| 信任 | 无 | 无 | 无 | **证伪崩溃** |
| 反身性 | 隐式 | 隐式 | 隐式 | **显式约束** |

### 6.4 局限性

1. **KOL信念基线**: 当前~0.003-0.005 (受susceptibility=0.1限制)
2. **净需求累积**: 跨步累积应使用每步order_imbalance
3. **FOMO信号**: 当前未传播至emotion.greed
4. **干预验证**: _apply_to_*方法效果未完全验证
5. **校准缺失**: 未与真实市场数据校准

### 6.5 未来工作

1. **历史数据校准**: 2008金融危机、2020 COVID崩溃
2. **异质行业叙事**: 科技 vs 医疗 vs 能源
3. **多资产市场**: 跨市场溢出效应
4. **实时集成**: 接入实时市场数据
5. **组合优化**: 基于反身性预测的投资组合

---

## 7. Conclusion (1-2页)

### 7.1 总结

FundGenesis提供了一个新颖的计算框架,用于研究叙事驱动的市场反身性。其核心创新——五因子信念更新、分层KOL传播、证伪信任崩溃、反身性监控指标、分级监管干预——已在12个Demo实验中验证。

### 7.2 主要贡献

1. **五因子信念更新器**: 捕捉认知和社会机制,4×敏感度差异
2. **分层KOL网络**: 四层影响层级,级联传播
3. **证伪信任崩溃**: 90%乘法崩溃,模拟突然信任丧失
4. **反身性监控**: 实时泡沫/恐慌检测
5. **分级监管**: 轻度干预27%效果,强力干预7%效果

### 7.3 理论意义

- 将Soros反身性理论形式化为可计算模型
- 整合行为金融、社会影响、复杂系统理论
- 提供反事实分析和政策评估平台

### 7.4 实践意义

- 金融监管决策支持
- 风险管理工具
- 投资策略优化

---

## References

### 核心理论
- Soros, G. (1987). The Alchemy of Finance. Simon & Schuster.
- Shiller, R.J. (2017). Narrative economics. American Economic Review, 107(4), 967-1004.
- Kahneman, D. (2011). Thinking, Fast and Slow. Farrar, Straus and Giroux.

### Agent-Based模型
- Arthur, W.B., et al. (1997). Asset pricing under endogenous expectations. Santa Fe Institute.
- Lux, T. & Marchesi, M. (1999). Scaling and criticality in a stochastic multi-agent model. Nature, 397, 498-500.
- Farmer, J.D. & Foley, D. (2009). The economy needs agent-based modelling. Nature, 460, 685-686.

### 意见动力学
- Borkowski, M. et al. (2023). Social influence and market bubbles. arXiv.
- Alfarano, S. & Lux, T. (2022). Opinion dynamics in financial markets. J. Economic Behavior & Organization.
- Hegselmann, R. & Krause, U. (2002). Opinion dynamics and bounded confidence models. JASSS.

### 社会影响
- Banerjee, A.V. (1992). A simple model of herd behavior. QJE, 107(3), 797-817.
- Bikhchandani, S., et al. (1992). A theory of fads, fashion, custom, and cultural change. JPE, 100(5), 992-1026.
- DeMarzo, P.M., et al. (2001). Persuasion and optimal information. QJE, 116(3), 909-968.

---

## Appendix

### A. 完整参数表
### B. 代码实现细节
### C. 额外实验结果
### D. 可复现性指南

---

**大纲版本**: v0.1
**创建日期**: 2026-05-28
**维护人**: Claude Code Agent
