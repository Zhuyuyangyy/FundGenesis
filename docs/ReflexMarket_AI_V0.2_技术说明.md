# ReflexMarket-AI V0.2 技术说明

## 核心定位

ReflexMarket-AI V0.2 将 FundGenesis 从普通市场仿真系统升级为叙事驱动的金融反身性世界模型。系统新增叙事引擎与 KOL 社会传播网络，形成「叙事注入—社会传播—信念更新—情绪变化—交易行为—资金流动—价格反馈—叙事强化/崩塌」的闭环。

## English Pitch

ReflexMarket-AI V0.2 extends FundGenesis from a market simulation system into a narrative-driven reflexive financial world model. The system introduces a Narrative Engine and KOL-based social contagion network, enabling the closed-loop path: narrative injection \xe2\x86\x92 social propagation \xe2\x86\x92 belief update \xe2\x86\x92 emotion shift \xe2\x86\x92 trading behavior \xe2\x86\x92 capital flow \xe2\x86\x92 price movement \xe2\x86\x92 narrative reinforcement or collapse.

## V0.2 成果

| # | 模块 | 说明 |
|---|------|------|
| 1 | **Narrative Engine** | 支持正向叙事、负向叙事、叙事反转（NarrativeReversal）三种注入模式，polarity=intensity\xd7direction，强度0\xe2\x88\xb50.8 |
| 2 | **KOL Graph / Social Contagion** | KOL 节点网络，叙事通过社会网络扩散而非瞬时全局生效；支持影响力加权的叙事传播 |
| 3 | **Belief Updater V2** | 将 narrative_exposure、price_confirmation、social_pressure、prior_bias、contradiction_signal 五维因子纳入信念变化 |
| 4 | **Reflexivity Monitor** | 输出 reflexivity_index、bubble_risk、panic_risk、regime_distribution 等指标 |
| 5 | **三个 Demo 验证** | 正向叙事泡沫 / 监管恐慌扩散 / 叙事反转崩塌 |

## Demo 结果

### Demo 1: 正向叙事泡沫
- **初始价格:** 100 \xe2\x86\x92 **峰值: 276.48** \xe2\x86\x92 终值: 258.69
- **注入:** AI\xc2\xb0\xc2\xb0\xc2\xb0\xc2\xb0\xc2\xb0\xc2\xb0\xc2\xb0\xc2\xb0\xc2\xb0\xc2\xb0\xc2\xb0\xc2\xb0\xc2\xb0\xc2\xb0\xc2\xb0\xc2\xb0 (正向, intensity=0.75)
- ** reflexivity_index: 0.2562 / Bubble Risk: 0.0**

### Demo 2: 监管恐慌扩散
- **冲击前价格:** 234.67 \xe2\x86\x92 **终值: 200.54** (\xe2\x88\x9214.5%)
- **注入:** \xc2\xb0\xc2\xb0\xc2\xb0\xc2\xb0\xc2\xb0\xc2\xb0\xc2\xb0\xc2\xb0\xc2\xb0\xc2\xb0\xc2\xb0\xc2\xb0\xc2\xb0\xc2\xb0\xc2\xb0\xc2\xb0 (负向, intensity=0.8)
- ** reflexivity_index: 0.2552 / Panic Risk: 0.0077**

### Demo 3: 叙事反转崩塌
- **初始: 102.53 \xe2\x86\x92 正向泡沫峰值: 274.72 (Step 80) \xe2\x86\x92 反转后: 213.13 (Step 280)**
- **注入:** Step 60 正向 \xe2\x86\x92 Step 200 叙事反转
- ** reflexivity_index: 0.2605 / Panic Risk (peak): 0.0085**

## 架构

`
NarrativeEngine
    \xe2\x86\x92 inject(positive/negative/reversal)
    \xe2\x86\x92 Narrative: polarity, intensity, events[], reversal_signaled

KOLNetwork
    \xe2\x86\x92 Node: kol_id, influence, polarity
    \xe2\x86\x92 propagate(narrative, agents) \xe2\x86\x92 信念\xe4\xb8\xbb\xe5\x8a\xa8\xe4\xbc\xa0\xe7\xbb\x9f\xe5\x88\x86\xe5\xb8\x83

BeliefUpdaterV2
    \xe2\x86\x92 belief_new = \xce\xb1\xc2\xb7belief_old + \xce\xb2\xc2\xb7narrative_exposure + \xce\xb3\xc2\xb7price_conf + \xce\xb4\xc2\xb7social_pressure \xe2\x88\x92 \xce\xb8\xc2\xb7contradiction + \xce\xb5\xc2\xb7prior_bias

EmotionField
    \xe2\x86\x92 emotion = 0.6\xc2\xb7fear \xe2\x88\x92 0.4\xc2\xb7greed

TradingEngine
    \xe2\x86\x92 emotion \xe2\x86\x92 position_delta \xe2\x86\x92 market_price

MarketEnvironment
    \xe2\x86\x92 price = f(position_delta, momentum, volatility)
`

## 关键参数

| 参数 | 值 | 说明 |
|------|---|------|
| belief_inertia (\xce\xb1) | 0.6 | 旧信念保留度 |
| narrative_influence (\xce\xb2) | 0.15 | 叙事曝光影响力 |
| price_confirmation (\xce\xb3) | 0.15 | 价格确认权重 |
| social_pressure (\xce\xb4) | 0.05 | 社会传播压力 |
| contradiction_penalty (\xce\xb8) | 0.1 | 叙事证伪惩罚 |
| max_belief_change | 0.3 | 单步最大信念变化 |
| T | 300 | 模拟总步数 |

## 相对于 V0.1 的核心升级

1. **叙事不再是外生噪声**：Narrative Engine 使叙事成为一等公民，可注入、可衰减、可反转
2. **社会传播取代全局瞬时**：KOL Network 使叙事通过影响力网络扩散，有速度差
3. **信念更新五维化**：V0.1 只有 emotion + price，V0.2 纳入了 social + prior + contradiction
4. **Narrative Reversal 机制**：首次实现了叙事反转对泡沫的触发

## 下一步（V0.3 规划）

- [ ] 多叙事竞争与叠加
- [ ] 媒体置信度与叙事可信度衰减
- [ ] 散户情绪与机构情绪的分离建模
- [ ] 真实市场数据回测接口（AKShare）
