# FundGenesis Q2-Level SCI Review

> **Reviewer**: Automated Code Audit
> **Date**: 2026-05-29
> **Scope**: Full codebase (14 core modules, 12 experiment demos, 10 test files)
> **Target Journal Level**: Q2 (e.g., JASSS, Computational Economics, Journal of Economic Dynamics and Control)

---

## 1. Seven-Dimension Scoring

| # | Dimension | Score (0-10) | Summary |
|---|-----------|:------------:|---------|
| D1 | **Novelty & Originality** | 8.0 | First engineering implementation of Soros reflexivity as a multi-agent simulation with KOL network propagation, trust evolution, and regulatory intervention. Combines game theory, social contagion, and emotion dynamics in a way not seen in prior ABM finance literature. |
| D2 | **Technical Soundness** | 7.5 | Core feedback loop is well-designed with clear causal chains. One critical algorithmic bug found and fixed (convergence_rate always zero). BeliefUpdaterV2 formula is incomplete vs. documentation. Agent heterogeneity is properly parameterized. |
| D3 | **Experimental Rigor** | 6.5 | 12+ demo experiments exist but lack statistical significance testing (no confidence intervals, no multiple seeds, no p-values). V0.5 three-way comparison is promising but results show Light outperforming Strong in peak_bubble_risk, which contradicts the intended monotonicity hypothesis. |
| D4 | **Reproducibility** | 7.0 | Deterministic seeding supported via SimulationConfig.seed. All 302 tests pass. Docker + requirements.txt provided. However, no formal benchmark runner output committed; experiments are demo scripts, not automated pipelines. |
| D5 | **Code Quality & Architecture** | 8.0 | Clean modular architecture with 14 well-separated modules. Dataclass-based configuration, ABC for agents, clear docstrings. SimulationRunner orchestrates all components coherently. Minor issues: some modules mix Chinese/English docstrings, no type hints on some return values. |
| D6 | **Significance & Impact** | 7.0 | Addresses a real gap: financial ABM frameworks that model narrative-driven reflexivity with trust dynamics. Applicable to regulatory policy simulation, market abuse detection, and academic study of herding. Limited by lack of real-market calibration or validation. |
| D7 | **Clarity & Presentation** | 6.0 | Extensive documentation (README 31KB, SPEC, SCI_FRAMEWORK) but inconsistent in language (Chinese/English mixed). Mathematical formulas well-documented in SCI_FRAMEWORK.md but not all match the implementation. No formal paper draft provided. |

**Overall Weighted Score: 7.1 / 10**

---

## 2. Top 1 Issue: `convergence_rate` Always Zero (FIXED)

### Location

`core/reflexivity_game.py`, lines 358-366, method `ReflexivityGameModel._compute_convergence_rate()`

### Bug Description

The method intended to compute how fast market beliefs are converging over time. Both `prev` and `current` were read from `self._history[-1]` (the same element), making `(prev - current)` always 0.0.

**Before (buggy)**:
```python
def _compute_convergence_rate(self) -> float:
    if len(self._history) < 2:
        return 0.0
    prev = self._history[-1].belief_dispersion      # BUG: same index
    if prev < 1e-6:
        return 0.0
    current = self._history[-1].belief_dispersion    # BUG: same index
    return float(np.clip((prev - current) / max(prev, 0.01), -1.0, 1.0))
```

### Impact

- `convergence_rate` was always 0.0 in all simulation outputs.
- `GameEquilibrium.convergence_rate` field was meaningless dead data.
- Any downstream analysis relying on convergence dynamics (e.g., regime classification refinement, convergence speed comparison across scenarios) was broken.
- The `summary()` method's regime analysis was unaffected (it does not use convergence_rate).

### Fix Applied

```python
def _compute_convergence_rate(self) -> float:
    if len(self._history) < 2:
        return 0.0
    prev = self._history[-2].belief_dispersion      # FIXED: previous step
    if prev < 1e-6:
        return 0.0
    current = self._history[-1].belief_dispersion    # current step
    return float(np.clip((prev - current) / max(prev, 0.01), -1.0, 1.0))
```

**Verification**: All 302 tests pass after the fix.

---

## 3. Additional Issues (Ranked by Severity)

### 3.1 [HIGH] BeliefUpdaterV2 Missing `prior_bias` Term

**File**: `core/belief_updater_v2.py`, `_update_single()` (line 99-132)

**Problem**: The docstring (line 8-16) documents a 6-factor formula including `+ epsilon * prior_bias`, but the implementation only has 5 terms. The `prior_bias` term is completely absent.

**SCI Impact**: The formula in any paper must exactly match the code. Reviewers will check this.

**Recommendation**: Either add the prior_bias computation or update the documentation to reflect the actual 5-factor formula.

### 3.2 [MEDIUM] V0.5 Experimental Monotonicity Violation

**File**: `SPEC.md` (experiment results table)

**Problem**: The three-way comparison shows `peak_bubble_risk`: Baseline=0.1532, Light=0.1116, Strong=0.1428. The Strong intervention produces HIGHER bubble risk than Light, violating the expected monotonic relationship (Strong should suppress more than Light).

**Root Cause**: The `RegulatorAgent._apply_deescalation()` method may prematurely reduce intervention intensity. The `trading_cooldown` action in Strong mode adds `investor_fear_factor` which can paradoxically increase emotion_amplification via the emotion feedback loop.

**SCI Impact**: A reviewer will flag this as either (a) a design flaw or (b) an interesting emergent finding that needs explanation. Currently neither is provided.

**Recommendation**: Either fix the monotonicity (ensure Strong >= Light in bubble suppression) OR explicitly frame it as a non-trivial emergent result with theoretical explanation.

### 3.3 [MEDIUM] No Statistical Significance in Experiments

**Files**: All `experiments/demo_*.py`

**Problem**: All experiments run a single seed with no confidence intervals. A Q2 journal requires at minimum:
- 30+ independent runs with different seeds
- Mean +/- standard deviation for key metrics
- Statistical test (e.g., Mann-Whitney U) for intervention effect significance

**Recommendation**: Add a `run_experiment_suite(experiment_fn, n_seeds=30)` utility that collects statistics.

### 3.4 [MEDIUM] Agent Positions Not Tracked

**File**: `agents/base_agent.py`

**Problem**: `get_trade_volume()` always returns 0.1 regardless of actual portfolio state. Agents have `cash` and `position` fields but they are never updated by trade execution. The market's `buy_volume`/`sell_volume` are aggregate counters reset each step, with no connection to individual agent positions.

**SCI Impact**: This means the model cannot capture wealth effects, margin calls, or portfolio rebalancing -- limiting its applicability to more realistic market scenarios.

### 3.5 [LOW] Mixed Language Documentation

**Files**: Multiple `.py` files, `README.md`, `SPEC.md`

**Problem**: Docstrings and comments alternate between Chinese and English. A Q2 international journal requires consistent English throughout.

**Recommendation**: Standardize all public API docstrings to English. Internal comments can remain Chinese if the paper is in Chinese.

### 3.6 [LOW] NumPy RuntimeWarning in Tests

**File**: `tests/test_monitor.py`

**Problem**: `RuntimeWarning: Mean of empty slice` and `RuntimeWarning: invalid value encountered in scalar divide` during `test_observe_with_narrative_engine`. Caused by `np.mean([])` in `belief_statistics()` when KOL network has no beliefs yet.

**Recommendation**: Add guard in `belief_statistics()` to return 0.0 when beliefs list is empty before calling `np.mean`.

---

## 4. Strengths for Q2 Submission

1. **Novel contribution**: First ABM framework combining Soros reflexivity + KOL social propagation + trust evolution + regulatory intervention. This is a genuine gap in the literature.

2. **Clean architecture**: 14 modules with clear separation of concerns. The SimulationRunner orchestrates 14 components in a coherent pipeline -- impressive engineering.

3. **Test coverage**: 302 tests covering all core modules. This is above average for academic code.

4. **Mathematical rigor**: Core formulas (BeliefUpdaterV2, Reflexivity Index, Bubble Risk) are well-documented with LaTeX notation.

5. **Extensibility**: The component toggle system (enable_reflexivity_game, enable_risk_propagation, etc.) allows clean ablation studies.

---

## 5. Recommended Actions for Q2 Readiness

| Priority | Action | Effort |
|----------|--------|--------|
| P0 | Fix convergence_rate bug (DONE) | 5 min |
| P1 | Add prior_bias to BeliefUpdaterV2 or fix docs | 1 hour |
| P2 | Run 30-seed experiments with CI for all demos | 1 day |
| P3 | Fix Strong vs Light monotonicity or explain it | 2 hours |
| P4 | Standardize all docstrings to English | 2 hours |
| P5 | Add position tracking to agents | 1 day |
| P6 | Write formal paper draft with BibTeX references | 1 week |

---

## 6. Code Module Inventory

| Module | Lines | Status | Notes |
|--------|------:|--------|-------|
| `core/emotion_field.py` | 104 | OK | Clean, well-tested |
| `core/market_environment.py` | 211 | OK | Solid price dynamics |
| `core/metrics.py` | 64 | OK | Simple, correct |
| `core/belief_updater_v2.py` | 203 | WARN | Missing prior_bias |
| `core/reflexivity_game.py` | 420 | FIXED | convergence_rate bug fixed |
| `core/risk_propagation.py` | 442 | OK | Well-structured contagion model |
| `core/simulation_runner.py` | 580 | OK | Orchestrates 14 components |
| `core/creator_controller.py` | 141 | OK | Clean config layer |
| `agents/base_agent.py` | 76 | WARN | No position tracking |
| `agents/emotional_retail.py` | 70 | OK | Good FOMO/panic model |
| `agents/trend_follower.py` | 56 | OK | Clean momentum model |
| `agents/value_investor.py` | 64 | OK | Proper contrarian logic |
| `social/kol_network.py` | 268 | OK | 3-tier network, well-tested |
| `social/propagation_model.py` | 163 | OK | Layer-by-layer diffusion |
| `narrative/narrative_engine.py` | 189 | OK | Reflexivity constraint enforced |
| `narrative/narrative_event.py` | 168 | OK | Good event lifecycle |
| `trust/trust_engine.py` | 170 | OK | Effective trust formula |
| `monitor/reflexivity_monitor.py` | 360 | OK | 5-factor index, 6 regimes |
| `risk/manipulation_risk_agent.py` | 736 | OK | 4-pattern detection |
| `risk/regulator_agent.py` | 334 | WARN | De-escalation may cause monotonicity issue |

---

## 7. Verdict

**Q2 Readiness**: 75% ready. The core innovation is strong and the architecture is clean. The main blockers are: (1) the fixed convergence_rate bug must be verified in experiment outputs, (2) experimental rigor needs 30-seed statistical validation, and (3) the Strong vs Light monotonicity issue needs resolution or theoretical justification.

**Top 1 Fix Applied**: `convergence_rate` in `core/reflexivity_game.py` -- changed `self._history[-1]` to `self._history[-2]` for `prev` variable. All 302 tests pass.
