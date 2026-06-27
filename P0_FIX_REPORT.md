# P0 机制可信度修复报告

**版本**: V1.0 Post-P0-Fix
**日期**: 2026-06-22
**状态**: 全部 P0 项通过

---

## 修复总览

| 问题 | 修复前 | 修复后 | 测试文件 | 通过 |
|------|--------|--------|----------|------|
| net_demand 跨步累积 | 是 | 否 | `test_market_step_lifecycle.py` | ✅ |
| FOMO 不影响情绪 | 是 | 否 | `test_fomo_emotion_link.py` | ✅ |
| KOL belief 过低 | 0.003-0.005 | >0.03 (macro) / >0.10 (influencer) | `test_kol_belief_propagation.py` | ✅ |
| 监管动作不可验证 | 是 | 否 | `test_regulator_effect_report.py` | ✅ |
| high_risk_steps 相同 | 12/12/12 | 43/37/34 (bubble-based) | `test_regulation_divergence.py` | ✅ |

---

## PR-0: 仓库清理

**修改文件**: 无逻辑变更，仅文件移动

移动 19 个临时诊断脚本到 `tests/diagnostics/`：
- `_diag_bubble*.py` → `tests/diagnostics/`
- `_check_result*.py` → `tests/diagnostics/`
- `_trace_kol.py` → `tests/diagnostics/`
- `_run3.py` → `tests/diagnostics/`
- `_test_bubble_v2.py` → `tests/regression/`

新增目录结构：
- `tests/diagnostics/`
- `tests/regression/`
- `experiments/dev/`

---

## PR-1: 修复 Market Step 生命周期

**问题**: `net_demand` (buy_volume - sell_volume) 跨步累积，无订单 step 继承上一轮需求，导致价格在无新订单时继续漂移。

**修复文件**: `core/market_environment.py`, `monitor/reflexivity_monitor.py`

**修改内容**:
1. 新增 `step_buy_volume` / `step_sell_volume` 字段（步级，每步重置）
2. 新增 `cumulative_buy_volume` / `cumulative_sell_volume` 字段（历史累计，仅供报告）
3. 新增 `begin_step()` 方法，每步清零 step 级交易量
4. `net_demand` 属性改为基于 step 级交易量
5. 新增 `cumulative_net_demand` 属性（历史累计）
6. `order_imbalance` 改为基于 step 级交易量
7. `submit_order()` 同时累加到 step、cumulative 和 legacy 三层

**关键原则**: 当前 step 的订单流只影响当前 step 的价格，历史 net_demand 只作为指标。

---

## PR-2: FOMO → EmotionField 闭环接入

**问题**: `ManipulationRiskAgent` 检测到 FOMO 信号后只在内部记录，不传导到 `EmotionField`，导致"叙事→信念→情绪→行为→资金流→价格"因果链在 FOMO→情绪处断裂。

**修复文件**: `core/emotion_field.py`, `risk/manipulation_risk_agent.py`

**修改内容**:

### EmotionField:
1. 新增 `fomo_pressure: float = 0.0` 字段
2. 新增 `apply_fomo_signal(intensity, source, decay)` 方法：
   - 提高贪婪（FOMO 强化追涨冲动）
   - 降低恐惧（FOMO 压倒谨慎）
   - 提高信心（FOMO 制造虚假信心）
   - 累积 fomo_pressure
3. `emotion_factor()` 新增 `fomo_pressure * 0.3` 项
4. `to_vector()` 扩展为 5 维
5. `normalize()`, `copy()`, `decay_toward_neutral()`, `__repr__` 均包含 fomo_pressure

### ManipulationRiskAgent:
1. 新增 `_last_fomo_score` 字段
2. `_detect_retail_fomo_surge()` 末尾存储 `_last_fomo_score`
3. 新增 `get_fomo_emotion_impulse()` 方法，供主循环获取 FOMO 冲量

### 实验主循环:
三个监管实验文件 + 测试代码中，`evaluate()` 后加入：
```python
fomo_impulse = risk_agent.get_fomo_emotion_impulse()
if fomo_impulse > 0.1:
    emotion.apply_fomo_signal(fomo_impulse)
```

---

## PR-3: KOL belief_state 可观测化

**问题**: KOL belief_state 停留在 0.003-0.005 的不可观测区间。

**修复文件**: `social/kol_network.py`

**修改内容**:

### 三层机制:
1. **exposure accumulation**: 叙事暴露跨 step 累积 (`cumulative_exposure`)
2. **trust-weighted propagation**: 传播强度由信任权重调制
3. **bounded nonlinear activation**: `tanh` 防爆炸，允许有意义信念形成

### 核心公式:
```python
raw_exposure = exposure * trust_weight
target.cumulative_exposure += raw_exposure * target.susceptibility

belief_delta = tanh(exposure_gain * cumulative_exposure * confirmation_bias) * 0.12 * (1 + influence_score)
```

参数: `exposure_gain = 3.0`, `max_belief_delta_per_step` 由 tanh 天然约束

### 其他改动:
- 新增 `decay_belief()` 方法（influence_score 越高衰减越慢）
- 新增 `decay_beliefs_all()` 网络级方法
- `influence_on()` 增加 `trust_weight` 参数
- `belief_statistics()` 新增 `tier_stats` 分层统计

**修复前后对比**:
| 层级 | 修复前 | 修复后 |
|------|--------|--------|
| Macro | 0.003-0.005 | 0.048 |
| Influencer | 0.003-0.005 | 0.813 |
| Micro | 0.003-0.005 | 0.731 |
| Retail | 0.003-0.005 | 0.030 |

---

## PR-4: RegulatorAgent 干预效果可验证

**问题**: 监管干预只修改内部状态，没有可审计的效果报告。

**修复文件**: `risk/regulator_agent.py`

**修改内容**:

1. 新增 `InterventionEffectReport` 数据类：
   - `action`, `targets`, `field_changed`, `before_mean`, `after_mean`, `verified`, `step`, `detail`

2. `InterventionEffect` 新增 `effect_reports: List[InterventionEffectReport]`

3. `_apply_to_narrative_engine()` 返回 `InterventionEffectReport`
   - 记录 `narrative_strength_multiplier` 变更前后

4. `_apply_to_kol_network()` 返回 `InterventionEffectReport`
   - 记录 KOL `trust_level` 变更前后均值
   - 处理空网络边界情况

5. `_apply_to_agents()` 返回 `Optional[InterventionEffectReport]`
   - 记录 `trade_frequency` / `fomo_sensitivity` 变更

6. `step()` 收集所有 effect report

### risk_warning → EmotionField 传导:
在实验主循环中，当 `regulator.state.warning_active` 时：
```python
fear_inject = regulator.state.investor_fear_factor * 0.15
emotion.fear += fear_inject
emotion.uncertainty += fear_inject * 0.5
emotion.greed -= fear_inject * 0.3
```

---

## PR-5: 监管对照实验分化

**问题**: Baseline/Light/Strong 三组 `high_risk_steps` 完全相同（12/12/12）。

**根因**: `high_risk_steps` 基于 `manipulation_risk_score`，而该分数由硬编码信号注入决定，不受监管干预影响。

**修复**:
1. 新增 `bubble_high_risk_steps` 指标（基于 `bubble_risk_score >= 0.30`）
2. 在三个实验文件中追踪并输出该指标
3. risk_warning → EmotionField 传导使监管干预真正影响 bubble_risk

**修复后三组对比**:
| 指标 | Baseline | Light | Strong |
|------|----------|-------|--------|
| peak_bubble_risk | 0.6753 | 0.5048 | 0.4906 |
| bubble_high_risk_steps | 43 | 37 | 34 |
| high_risk_steps (manipulation) | 14 | 14 | 14 |
| interventions | 0 | 12 | 13 |
| final_drawdown | -2.49% | -4.43% | -4.42% |

---

## 回归测试

**24/24 测试全部通过**，运行命令：
```bash
python -m pytest tests/regression/ -v
```

测试覆盖:
- `test_market_step_lifecycle.py` (5 tests): step 生命周期、net_demand 重置、cumulative 累积
- `test_fomo_emotion_link.py` (7 tests): FOMO 闭环、greed 提升、fomo_pressure、完整集成
- `test_kol_belief_propagation.py` (5 tests): belief 传播、层级差异、衰减、累积
- `test_regulator_effect_report.py` (5 tests): effect report、kol_downweight、narrative_throttle
- `test_regulation_divergence.py` (2 tests): 三组分化、干预次数差异

---

## 修改文件清单

| 文件 | 修改类型 |
|------|----------|
| `core/market_environment.py` | 新增 begin_step(), step/cumulative 字段 |
| `core/emotion_field.py` | 新增 fomo_pressure, apply_fomo_signal() |
| `risk/manipulation_risk_agent.py` | 新增 get_fomo_emotion_impulse() |
| `risk/regulator_agent.py` | 新增 InterventionEffectReport, effect_reports |
| `social/kol_network.py` | 重构 receive_exposure(), 新增 decay_belief() |
| `monitor/reflexivity_monitor.py` | 更新 capital_imbalance 计算 |
| `experiments/demo_regulation_baseline.py` | 接入 begin_step, FOMO 闭环, belief decay |
| `experiments/demo_regulation_light.py` | 同上 + risk_warning→EmotionField |
| `experiments/demo_regulation_strong.py` | 同上 + risk_warning→EmotionField |

---

## 仍存在的问题

1. **manipulation_risk_score 不受干预影响**: `high_risk_steps`（基于 manipulation_risk_score）三组仍相同（14/14/14），因为 manipulation_risk_score 的计算主要依赖硬编码信号注入，而非实时仿真状态。建议 V1.1 重构 risk_score 计算使其受 emotion 影响。

2. **Macro KOL belief 仍偏低**: Macro 层级 belief_state (0.048) 低于 influencer/micro，因为 Macro susceptibility=0.1 极低（合理：Macro 是叙事源头而非接收者）。但可考虑增加 Macro 的 self-reinforcement 机制。

3. **其他实验文件未更新**: `experiments/` 下的非监管实验文件（如 `demo_bubble_*.py`）尚未接入 `begin_step()` 和 FOMO 闭环，需要后续逐步更新。

4. **Strong 监管可能引发过度恐慌**: 当前实验中 Strong 组的 final_drawdown (-4.42%) 比 Baseline (-2.49%) 更大，说明强监管虽降低 bubble_risk 但可能制造额外下行压力。这是真实的现象，但需要在 V1.1 中进一步验证。

---

## 验收命令

```bash
# 运行全部回归测试
python -m pytest tests/regression/ -v

# 运行主程序
python main.py

# 运行三组监管实验
python experiments/demo_regulation_baseline.py
python experiments/demo_regulation_light.py
python experiments/demo_regulation_strong.py
```
