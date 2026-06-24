"""
risk/manipulation_risk_agent.py
================================
ManipulationRiskAgent — 异常叙事传播风险识别

V0.4 核心模块

输入：
  - KOL Network（social/kol_network.py）
  - Trust Engine（trust/trust_engine.py）
  - Propagation Model（social/propagation_model.py）
  - Reflexivity Monitor（monitor/reflexivity_monitor.py）
  - Market Environment（core/market_environment.py）

输出：
  {
    "manipulation_risk_score": 0.0-1.0,
    "risk_level": "low"|"medium"|"high"|"critical",
    "detected_patterns": ["coordinated_kol_amplification", ...],
    "recommended_action": "allow"|"monitor"|"human_review"|"block",
    "confidence": 0.0-1.0,
    "details": {...}
  }

检测的四类异常模式：
  1. coordinated_kol_amplification    — 多 KOL 协同放大同一叙事
  2. price_narrative_self_validation  — 价格变动成为叙事自我验证
  3. retail_fomo_surge                — 散户 FOMO 异常涌入
  4. abnormal_trust_building          — KOL 信任建立速度异常
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from enum import Enum
import numpy as np


class RiskLevel(Enum):
    LOW = "low"           # 无需干预
    MEDIUM = "medium"     # 持续监控
    HIGH = "high"         # 人工复核
    CRITICAL = "critical" # 立即干预


class PatternType(Enum):
    COORDINATED_KOL_AMPLIFICATION = "coordinated_kol_amplification"
    PRICE_NARRATIVE_SELF_VALIDATION = "price_narrative_self_validation"
    RETAIL_FOMO_SURGE = "retail_fomo_surge"
    ABNORMAL_TRUST_BUILDING = "abnormal_trust_building"


@dataclass
class PatternDetection:
    """单模式检测结果"""
    pattern: PatternType
    score: float                    # 0.0-1.0
    evidence: List[str]             # 具体证据
    confidence: float                # 检测置信度
    step: int                       # 检测步


@dataclass
class ManipulationRiskReport:
    """综合风险报告"""
    step: int

    # 总体评分
    manipulation_risk_score: float          # [0, 1]
    risk_level: RiskLevel

    # 模式检测结果
    detected_patterns: List[PatternDetection]

    # 推荐的处置动作
    recommended_action: str                  # "allow"|"monitor"|"human_review"|"block"

    # 置信度
    confidence: float                        # 报告整体置信度

    # 各维度细节
    kol_coordination_score: float            # KOL 协同程度
    self_validation_score: float             # 自我验证程度
    fomo_score: float                       # FOMO 程度
    trust_build_score: float                # 异常信任建立程度

    # 历史参考
    previous_risk_score: Optional[float] = None
    risk_acceleration: Optional[float] = None  # 风险上升速度

    def as_dict(self) -> dict:
        return {
            "step": self.step,
            "manipulation_risk_score": round(self.manipulation_risk_score, 4),
            "risk_level": self.risk_level.value,
            "detected_patterns": [
                {
                    "pattern": p.pattern.value,
                    "score": round(p.score, 4),
                    "evidence": p.evidence,
                    "confidence": round(p.confidence, 4),
                    "step": p.step,
                }
                for p in self.detected_patterns
            ],
            "recommended_action": self.recommended_action,
            "confidence": round(self.confidence, 4),
            "details": {
                "kol_coordination_score": round(self.kol_coordination_score, 4),
                "self_validation_score": round(self.self_validation_score, 4),
                "fomo_score": round(self.fomo_score, 4),
                "trust_build_score": round(self.trust_build_score, 4),
            },
            "previous_risk_score": (
                round(self.previous_risk_score, 4)
                if self.previous_risk_score is not None else None
            ),
            "risk_acceleration": (
                round(self.risk_acceleration, 4)
                if self.risk_acceleration is not None else None
            ),
        }


class ManipulationRiskAgent:
    """
    异常叙事传播风险识别 Agent。

    使用方法：
        # 生产模式（默认阈值）
        agent = ManipulationRiskAgent()

        # Demo 敏感模式（宽松阈值，用于受控实验验证检测能力）
        agent = ManipulationRiskAgent(
            action_thresholds={
                "monitor": 0.15,
                "human_review": 0.25,
                "block": 0.60,
            }
        )

        for step in range(1000):
            report = agent.evaluate(
                step=step,
                kol_network=kol_network,
                trust_engine=trust_engine,
                reflexivity_monitor=reflexivity_monitor,
                market=market,
                narrative_engine=narrative_engine,
                propagation_model=propagation_model,
            )
            if report.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
                trigger_human_review(report)
    """

    # 各模式权重（用于综合评分）
    # 协同放大是高风险信号，给更高权重使其能单独触发 HIGH
    PATTERN_WEIGHTS = {
        PatternType.COORDINATED_KOL_AMPLIFICATION: 0.60,
        PatternType.PRICE_NARRATIVE_SELF_VALIDATION: 0.35,
        PatternType.RETAIL_FOMO_SURGE: 0.25,
        PatternType.ABNORMAL_TRUST_BUILDING: 0.20,
    }

    # 默认阈值（生产模式）
    DEFAULT_ACTION_THRESHOLDS = {
        "monitor": 0.20,
        "human_review": 0.50,
        "block": 0.80,
    }

    def __init__(self, action_thresholds: dict = None):
        """
        初始化风险 Agent。

        Args:
            action_thresholds: 可选的自定义动作阈值字典。
                例如 {"monitor": 0.15, "human_review": 0.25, "block": 0.60}
                用于受控 Demo 场景验证检测能力，不应直接修改默认阈值。
                不传入时使用 DEFAULT_ACTION_THRESHOLDS（生产模式）。
        """
        self._action_thresholds = (
            action_thresholds
            if action_thresholds is not None
            else self.DEFAULT_ACTION_THRESHOLDS.copy()
        )

        # 历史风险评分（用于计算加速度）
        self._risk_history: List[float] = []

        # KOL 协同追踪：{narrative_id: [spreading_kol_ids]}
        self._kol_spread_map: Dict[str, List[str]] = {}

        # 历史 trust 变化追踪：{kol_id: [(step, trust_level), ...]}
        self._trust_history: Dict[str, List[tuple]] = {}

        # 自我验证追踪：{narrative_id: [(step, price_at_validation)]}
        self._price_validation_history: Dict[str, List[tuple]] = {}

        # 手动注入的价格验证事件（用于 Demo / 测试）
        self._injected_price_events: List[dict] = []

        # 手动注入的 FOMO 信号（用于 Demo / 测试）
        self._injected_fomo_signals: List[dict] = []

        # 手动注入的 trust 建立事件（用于 Demo / 测试）
        self._injected_trust_events: List[dict] = []

    def evaluate(
        self,
        step: int,
        kol_network,           # KOLNetwork
        trust_engine,           # TrustEngine
        reflexivity_monitor,   # ReflexivityMonitor
        market,                # MarketEnvironment
        narrative_engine,      # NarrativeEngine
        propagation_model=None,  # PropagationModel (optional)
        agents=None,           # BaseAgent list (optional)
    ) -> ManipulationRiskReport:
        """
        执行一次风险评估。
        """

        # ── 1. 检测各模式 ──────────────────────────────────

        coordinated = self._detect_coordinated_kol_amplification(
            step, kol_network, narrative_engine
        )

        self_validation = self._detect_price_narrative_self_validation(
            step, kol_network, narrative_engine, market
        )

        fomo = self._detect_retail_fomo_surge(
            step, kol_network, market, reflexivity_monitor
        )

        trust_abnormal = self._detect_abnormal_trust_building(
            step, kol_network, trust_engine
        )

        patterns = [coordinated, self_validation, fomo, trust_abnormal]
        active_patterns = [p for p in patterns if p.score > 0.3]

        # ── 2. 综合评分 ────────────────────────────────────
        total_score = sum(
            self.PATTERN_WEIGHTS[p.pattern] * p.score
            for p in patterns
        )

        # P0.6 修复 A：让风险分读取干预修改的字段
        # 干预修改的字段 → 风险公式应感知的变化：
        #   narrative_throttle → narrative_strength_multiplier ↓ → 叙事传播减弱 → 风险↓
        #   kol_downweight → kol.influence_score ↓ → KOL 协同放大减弱 → 风险↓
        #   trading_cooldown → agent.trade_frequency ↓ → FOMO 买入压力减弱 → 风险↓
        #   risk_warning → agent.fomo_sensitivity ↓ → FOMO 情绪减弱 → 风险↓
        intervention_factor = 1.0  # 1.0 = 无干预效果，<1.0 = 干预降低风险

        if narrative_engine is not None:
            # narrative_throttle 将 narrative_strength_multiplier 从 1.0 压到 0.6-0.72
            nsm = getattr(narrative_engine, 'narrative_strength_multiplier', 1.0)
            intervention_factor *= (0.5 + 0.5 * nsm)  # nsm=1.0→1.0, nsm=0.6→0.8

        if kol_network is not None:
            # kol_downweight 降低了 KOL influence_score，降低协同放大风险
            kols = kol_network.get_kols()
            if kols:
                avg_influence = sum(k.influence_score for k in kols) / len(kols)
                # 正常 avg_influence ~0.3-0.5；干预后下降
                # 用 influence 衰减 coordinated 和 fomo 的贡献
                influence_ratio = min(1.0, avg_influence / 0.3)  # 0.3 为基准
                intervention_factor *= (0.6 + 0.4 * influence_ratio)

        if agents is not None and len(agents) > 0:
            # trading_cooldown + risk_warning 降低了 agent 活跃度
            trade_freqs = [getattr(a, 'trade_frequency', 1.0) for a in agents]
            fomo_senss = [getattr(a, 'fomo_sensitivity', 1.0) for a in agents]
            avg_tf = sum(trade_freqs) / len(trade_freqs)
            avg_fs = sum(fomo_senss) / len(fomo_senss)
            # 正常 avg_tf ~1.0, avg_fs ~1.0；干预后下降
            agent_factor = (0.7 + 0.3 * avg_tf) * (0.8 + 0.2 * avg_fs)
            intervention_factor *= agent_factor

        total_score *= intervention_factor

        # 加速度惩罚：如果风险在短时间内快速上升
        if len(self._risk_history) >= 3:
            recent = self._risk_history[-3:]
            acceleration = (recent[-1] - recent[0]) / max(recent[0], 0.01)
            if acceleration > 0.5:
                total_score = min(1.0, total_score * 1.2)  # 加速上涨时放大风险

        manipulation_risk_score = float(np.clip(total_score, 0.0, 1.0))

        # ── 3. 风险等级 ───────────────────────────────────
        risk_level = self._score_to_risk_level(manipulation_risk_score)

        # ── 4. 推荐动作 ────────────────────────────────────
        recommended_action = self._score_to_action(manipulation_risk_score)

        # ── 5. 置信度 ────────────────────────────────────
        confidences = [p.confidence for p in patterns if p.score > 0.2]
        confidence = float(np.mean(confidences)) if confidences else 0.0

        # ── 6. 历史记录 ──────────────────────────────────
        prev_risk = self._risk_history[-1] if self._risk_history else None
        risk_acc = None
        if prev_risk is not None and len(self._risk_history) >= 2:
            risk_acc = manipulation_risk_score - prev_risk

        self._risk_history.append(manipulation_risk_score)

        return ManipulationRiskReport(
            step=step,
            manipulation_risk_score=manipulation_risk_score,
            risk_level=risk_level,
            detected_patterns=active_patterns,
            recommended_action=recommended_action,
            confidence=confidence,
            kol_coordination_score=coordinated.score,
            self_validation_score=self_validation.score,
            fomo_score=fomo.score,
            trust_build_score=trust_abnormal.score,
            previous_risk_score=prev_risk,
            risk_acceleration=risk_acc,
        )

    def _detect_coordinated_kol_amplification(
        self,
        step: int,
        kol_network,
        narrative_engine,
    ) -> PatternDetection:
        """
        检测：多 KOL 协同放大同一叙事

        信号：
          - 同一叙事在短时间窗口内被多个 KOL 传播
          - 涉及的 KOL 分属不同层级（Macro/Influencer/Micro 同时转发）
          - 传播时间间隔极短（< 5 步）
        """
        evidence = []
        score = 0.0

        if narrative_engine is None or kol_network is None:
            return PatternDetection(
                pattern=PatternType.COORDINATED_KOL_AMPLIFICATION,
                score=0.0,
                evidence=["narrative_engine or kol_network not available"],
                confidence=0.0,
                step=step,
            )

        # 获取最近活跃叙事
        active_narratives = list(narrative_engine.registry.active)[:5]

        for narrative in active_narratives:
            # P0.6 修复 C：使用 narrative._id 而非 id(narrative)，与 record_kol_spread 的键一致
            nid = narrative._id
            if nid not in self._kol_spread_map:
                self._kol_spread_map[nid] = []

            # 查找过去 10 步内转发此叙事的 KOL
            recent_spreads = self._kol_spread_map[nid]
            kol_ids = [k.node_id for k in kol_network.get_kols()]

            # 检查是否有多个 KOL 在短时间内传播同一叙事
            spread_count = len(recent_spreads)
            if spread_count >= 3:
                tiers = set()
                for kid in recent_spreads:
                    kol = next((k for k in kol_network.get_kols() if k.node_id == kid), None)
                    if kol:
                        tiers.add(kol.tier)

                # 跨层级协同（Macro + Micro 同时转发）= 高可疑
                if len(tiers) >= 2 and spread_count >= 4:
                    score = max(score, 0.85)
                    evidence.append(
                        f"Cross-tier coordinated spread: {spread_count} KOLs, tiers={tiers}"
                    )
                elif spread_count >= 3:
                    score = max(score, 0.60)
                    evidence.append(
                        f"Multi-KOL same-narrative spread: {spread_count} KOLs"
                    )

        # 更新传播映射（如果有新的传播事件）
        # 注意：这里只能检测已经在kol_network中记录的传播
        return PatternDetection(
            pattern=PatternType.COORDINATED_KOL_AMPLIFICATION,
            score=min(score, 1.0),
            evidence=evidence if evidence else ["No coordinated amplification detected"],
            confidence=0.80,
            step=step,
        )

    def _detect_price_narrative_self_validation(
        self,
        step: int,
        kol_network,
        narrative_engine,
        market,
    ) -> PatternDetection:
        """
        检测：价格—叙事自我验证

        信号：
          - 叙事强度与价格变动方向一致（正反馈）
          - 价格成为叙事的"证据"：价格涨 → 相信叙事的人更多 → 继续买入
          - 具体：连续 5+ 步 price_change 和 narrative_direction 同向
        """
        evidence = []
        score = 0.0

        if narrative_engine is None or market is None:
            return PatternDetection(
                pattern=PatternType.PRICE_NARRATIVE_SELF_VALIDATION,
                score=0.0,
                evidence=["narrative_engine or market not available"],
                confidence=0.0,
                step=step,
            )

        # 获取最近 5 步价格变动方向
        price_history = getattr(market, 'price_history', [])[-10:]
        if len(price_history) < 3:
            return PatternDetection(
                pattern=PatternType.PRICE_NARRATIVE_SELF_VALIDATION,
                score=0.0,
                evidence=["Insufficient price history"],
                confidence=0.0,
                step=step,
            )

        # 计算最近 N 步价格动量
        price_changes = [
            price_history[i] - price_history[i-1]
            for i in range(1, len(price_history))
        ]
        price_direction = [1 if c > 0 else -1 for c in price_changes[-5:]]

        # 获取最近活跃叙事的方向
        active_narratives = list(narrative_engine.registry.active)
        if not active_narratives:
            return PatternDetection(
                pattern=PatternType.PRICE_NARRATIVE_SELF_VALIDATION,
                score=0.0,
                evidence=["No active narratives"],
                confidence=0.0,
                step=step,
            )

        # 检查价格方向是否与叙事方向一致
        aligned_steps = 0
        for narrative in active_narratives[:3]:
            polarity = narrative.polarity.value if hasattr(narrative.polarity, 'value') else str(narrative.polarity)
            narr_direction = 1 if polarity == "POSITIVE" else -1

            # 检查最近 5 步中有多少步方向一致
            aligned = sum(1 for pd in price_direction if pd == narr_direction)
            if aligned >= 4:
                aligned_steps += 1

        if aligned_steps >= 2:
            score = 0.75
            evidence.append(
                f"Price-narrative alignment: {aligned_steps} narratives with "
                f"{len(price_direction)}-step consistent direction"
            )
        elif aligned_steps == 1:
            score = 0.40
            evidence.append(f"Partial price-narrative alignment detected")

        # 检查 reflexivity_index 是否同时偏高（泡沫特征）
        reflexivity = getattr(market, 'reflexivity_index', 0.0) if hasattr(market, 'reflexivity_index') else 0.0
        if reflexivity > 0.6 and score > 0.3:
            score = min(1.0, score * 1.1)
            evidence.append(f"High reflexivity ({reflexivity:.2f}) amplifies self-validation risk")

        # 考虑手动注入的价格自我验证事件（用于 Demo / 测试）
        for event in self._injected_price_events:
            if event["confirmation_strength"] >= 0.6:
                score = max(score, 0.70)
                evidence.append(
                    f"Injected price-narrative validation: "
                    f"confirmation_strength={event['confirmation_strength']:.2f} at step {event['step']}"
                )
            elif event["confirmation_strength"] >= 0.4:
                score = max(score, 0.45)
                evidence.append(
                    f"Partial injected validation: confirmation_strength={event['confirmation_strength']:.2f}"
                )

        return PatternDetection(
            pattern=PatternType.PRICE_NARRATIVE_SELF_VALIDATION,
            score=min(score, 1.0),
            evidence=evidence if evidence else ["No self-validation pattern detected"],
            confidence=0.75,
            step=step,
        )

    def _detect_retail_fomo_surge(
        self,
        step: int,
        kol_network,
        market,
        reflexivity_monitor,
    ) -> PatternDetection:
        """
        检测：散户 FOMO 异常涌入

        信号：
          - 散户 agent 持仓量或买入频率异常上升
          - 同时叙事强度偏高（FOMO 叙事环境）
          - 市场买卖不平衡加剧
        """
        evidence = []
        score = 0.0

        if market is None:
            return PatternDetection(
                pattern=PatternType.RETAIL_FOMO_SURGE,
                score=0.0,
                evidence=["market not available"],
                confidence=0.0,
                step=step,
            )

        # 1. 价格上涨速度（FOMO 特征：快速上涨）
        price_history = getattr(market, 'price_history', [])
        if len(price_history) >= 5:
            recent_change = (price_history[-1] - price_history[-5]) / max(price_history[-5], 1.0)
            if recent_change > 0.15:  # 5 步内涨 15%+
                score = max(score, 0.60)
                evidence.append(f"Rapid price surge: {recent_change*100:.1f}% in 5 steps")
            elif recent_change > 0.08:
                score = max(score, 0.35)
                evidence.append(f"Moderate price surge: {recent_change*100:.1f}% in 5 steps")

        # 2. 贪婪指数极端化（FOMO 环境）
        greed = getattr(market, 'greed', 0.0) if hasattr(market, 'greed') else 0.0
        fear = getattr(market, 'fear', 0.0) if hasattr(market, 'fear') else 0.0
        if greed > 0.75 and fear < 0.25:
            score = max(score, 0.65)
            evidence.append(f"Greed extreme: {greed:.2f} vs fear {fear:.2f}")

        # 3. Reflexivity Monitor 历史检查（如果有）
        if reflexivity_monitor is not None and reflexivity_monitor.history:
            recent = reflexivity_monitor.history[-5:]
            bubble_scores = [m.bubble_risk_score for m in recent]
            if any(b > 0.5 for b in bubble_scores):
                score = max(score, 0.55)
                evidence.append(f"Elevated bubble risk in recent steps: max={max(bubble_scores):.2f}")

        # 4. KOL 网络平均曝光率异常（散户跟随 KOL 的信号）
        if kol_network is not None:
            all_kols = kol_network.get_kols()
            if all_kols:
                avg_exposure = sum(k.narrative_exposure for k in all_kols) / len(all_kols)
                if avg_exposure > 0.3 and score > 0.3:
                    score = min(1.0, score * 1.1)
                    evidence.append(f"High KOL avg_exposure ({avg_exposure:.2f}) with FOMO signals")

        # 5. 手动注入的 FOMO 信号（用于 Demo / 测试）
        for signal in self._injected_fomo_signals:
            if signal["greed_level"] > 0.75 and signal["retail_buy_ratio"] > 0.70:
                score = max(score, 0.70)
                evidence.append(
                    f"Injected FOMO signal: greed={signal['greed_level']:.2f}, "
                    f"retail_buy_ratio={signal['retail_buy_ratio']:.2f} at step {signal['step']}"
                )

        return PatternDetection(
            pattern=PatternType.RETAIL_FOMO_SURGE,
            score=min(score, 1.0),
            evidence=evidence if evidence else ["No FOMO surge detected"],
            confidence=0.70,
            step=step,
        )

    def _detect_abnormal_trust_building(
        self,
        step: int,
        kol_network,
        trust_engine,
    ) -> PatternDetection:
        """
        检测：KOL 信任建立速度异常

        信号：
          - 单一 KOL 在短时间内（< 10 步）trust_level 上升 > 50%
          - 没有对应的价格验证或准确率支撑
          - 属于全新 KOL（冷启动）
        """
        evidence = []
        score = 0.0

        if kol_network is None or trust_engine is None:
            return PatternDetection(
                pattern=PatternType.ABNORMAL_TRUST_BUILDING,
                score=0.0,
                evidence=["kol_network or trust_engine not available"],
                confidence=0.0,
                step=step,
            )

        # 获取当前 trust states（遍历 KOL nodes）
        all_effective = trust_engine.get_all_effective_trusts()

        for kol_id, effective_trust in all_effective.items():
            # 追踪历史
            if kol_id not in self._trust_history:
                self._trust_history[kol_id] = []
            self._trust_history[kol_id].append((step, effective_trust))

            # 需要至少 10 步历史
            history = self._trust_history[kol_id]
            if len(history) < 10:
                continue

            # 计算最近 10 步 vs 更早的 trust 变化
            recent_trust = history[-1][1]
            earlier_trust = history[-10][1]

            if earlier_trust < 0.1:
                continue  # 从极低开始建立，正常

            trust_growth = (recent_trust - earlier_trust) / max(earlier_trust, 0.01)

            if trust_growth > 1.5:  # 10 步内 trust 涨了 150%+
                score = max(score, 0.80)
                evidence.append(
                    f"KOL {kol_id[:8]}: trust +{trust_growth*100:.0f}% "
                    f"in 10 steps ({earlier_trust:.3f} -> {recent_trust:.3f})"
                )
            elif trust_growth > 0.8:  # 80%+
                score = max(score, 0.50)
                evidence.append(
                    f"KOL {kol_id[:8]}: abnormal trust growth +{trust_growth*100:.0f}%"
                )

        # 处理手动注入的 trust 建立事件（用于 Demo / 测试）
        for event in self._injected_trust_events:
            if event["trust_growth_rate"] > 1.5:
                score = max(score, 0.80)
                evidence.append(
                    f"Injected abnormal trust: kol_id={event['kol_id'][:8]}, "
                    f"growth_rate={event['trust_growth_rate']:.2f}x from {event['source']}"
                )
            elif event["trust_growth_rate"] > 0.8:
                score = max(score, 0.50)
                evidence.append(
                    f"Injected partial trust growth: rate={event['trust_growth_rate']:.2f}x"
                )

        return PatternDetection(
            pattern=PatternType.ABNORMAL_TRUST_BUILDING,
            score=min(score, 1.0),
            evidence=evidence if evidence else ["No abnormal trust building detected"],
            confidence=0.75,
            step=step,
        )

    def _score_to_risk_level(self, score: float) -> RiskLevel:
        if score >= 0.75:
            return RiskLevel.CRITICAL
        elif score >= 0.50:
            return RiskLevel.HIGH
        elif score >= 0.30:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    def _score_to_action(self, score: float) -> str:
        if score >= self._action_thresholds["block"]:
            return "block"
        elif score >= self._action_thresholds["human_review"]:
            return "human_review"
        elif score >= self._action_thresholds["monitor"]:
            return "monitor"
        else:
            return "allow"

    @property
    def risk_history(self) -> List[float]:
        return list(self._risk_history)

    def reset(self):
        """重置状态（用于新的模拟实验）"""
        self._risk_history.clear()
        self._kol_spread_map.clear()
        self._trust_history.clear()
        self._price_validation_history.clear()
        self._injected_price_events.clear()
        self._injected_fomo_signals.clear()
        self._injected_trust_events.clear()

    @property
    def action_thresholds(self) -> dict:
        """返回当前生效的动作阈值配置"""
        return dict(self._action_thresholds)

    def record_kol_spread(self, narrative_id: int, kol_id: str):
        """
        记录 KOL 对某叙事的传播事件（供 Demo / 测试用）。

        注意：这是测试钩子，用于向风险检测器注入观测到的 KOL 传播轨迹。
        不是人为制造结果，而是模拟"系统观测到多个 KOL 传播同一叙事"的实际情况。
        """
        if narrative_id not in self._kol_spread_map:
            self._kol_spread_map[narrative_id] = []
        if kol_id not in self._kol_spread_map[narrative_id]:
            self._kol_spread_map[narrative_id].append(kol_id)

    def record_price_feedback(
        self,
        narrative_id: int,
        price_change: float,
        confirmation_strength: float = 0.5,
        step: int = 0,
    ):
        """
        记录价格-叙事验证事件（供 Demo / 测试用）。

        当价格变动方向与叙事方向一致时调用。
        confirmation_strength: 0.0-1.0，价格变动对叙事的确认程度。
        """
        self._injected_price_events.append({
            "narrative_id": narrative_id,
            "price_change": price_change,
            "confirmation_strength": confirmation_strength,
            "step": step,
        })

    def record_fomo_signal(
        self,
        retail_buy_ratio: float,
        greed_level: float,
        belief_concentration: float = 0.5,
        step: int = 0,
    ):
        """
        记录散户 FOMO 信号（供 Demo / 测试用）。

        当观察到散户买入比例异常上升时调用。
        """
        self._injected_fomo_signals.append({
            "retail_buy_ratio": retail_buy_ratio,
            "greed_level": greed_level,
            "belief_concentration": belief_concentration,
            "step": step,
        })

    def record_trust_bootstrap(
        self,
        kol_id: str,
        trust_growth_rate: float,
        source: str = "price_confirmation",
        step: int = 0,
    ):
        """
        记录异常 trust 建立事件（供 Demo / 测试用）。

        当 KOL trust 在短时间内异常上升时调用。
        """
        self._injected_trust_events.append({
            "kol_id": kol_id,
            "trust_growth_rate": trust_growth_rate,
            "source": source,
            "step": step,
        })
