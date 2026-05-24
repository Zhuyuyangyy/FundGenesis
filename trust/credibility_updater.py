from __future__ import annotations

"""
trust/credibility_updater.py
============================
V0.3：信誉分更新器（Credibility Updater）。

核心问题：
  KOL 发了叙事之后，市场价格是否验证了该叙事？
  → 如果验证 → 信誉分上升 → 有效信任上升 → 叙事传播力更强
  → 如果证伪 → 信誉分下降 → 信任崩塌

机制设计：
1. 每条叙事有 polarity（正向/负向/中性）和初始强度
2. 仿真结束后，检查：叙事期间价格是否按 KOL 预测的方向变动？
3. 如果是 → credibility_score × (1 + accuracy_reward)
   如果否 → credibility_score × (1 - accuracy_penalty)
   如果基本不变 → 基本不变（噪声太多，不做判断）

4. 价格验证系数 V_kol 也同步更新：
   - 叙事期内有 3 步以上同向价格变动 → V_kol = 0.9
   - 叙事期内有反向价格变动 → V_kol = 0.2
   - 无明显价格变动 → V_kol = 0.5

Demo 6 关键：证伪触发信任崩塌（Penalty 乘数放大）

使用时机：
  - 每条叙事结束时（即 NarrativeEvent 被标记为 expired 时）
  - 或在每步手动调用 check_and_update
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import numpy as np

from narrative.narrative_event import NarrativeEvent, Polarity
from trust.trust_engine import TrustEngine


@dataclass
class CredibilityConfig:
    """信誉更新配置"""
    # 预测正确时的奖励乘数
    accuracy_reward: float = 0.08     # 每次验证正确，信誉分 +0.08
    # 预测错误时的惩罚乘数
    accuracy_penalty: float = 0.15    # 每次证伪，信誉分 -0.15
    # 价格验证系数更新
    validation_confirm: float = 0.90  # 价格同向验证
    validation_reject: float = 0.20   # 价格反向证伪
    validation_neutral: float = 0.50  # 价格无明显变化
    # 检验阈值（价格变动超过多少才认为有信号）
    price_signal_threshold: float = 0.005  # 0.5% 以上才算有效信号
    # 最低信誉分（不会衰减到 0）
    min_credibility: float = 0.05


@dataclass
class NarrativePrediction:
    """单条叙事的预测记录"""
    narrative_id: str
    kol_id: str
    polarity: Polarity
    initial_strength: float
    injected_step: int
    verified_step: Optional[int] = None
    price_direction: Optional[str] = None  # "confirm" / "reject" / "neutral"
    accuracy_score: Optional[float] = None


class CredibilityUpdater:
    """
    信誉分更新器。

    使用方法：
        updater = CredibilityUpdater(config)
        updater.attach_engine(trust_engine)

        # 叙事注入时记录
        updater.record_prediction(kol_id, narrative_event, step)

        # 叙事结束后检验并更新信誉
        updater.verify_and_update(network, market_history, current_step)
    """

    def __init__(self, config: Optional[CredibilityConfig] = None):
        self.config = config or CredibilityConfig()
        self._engine: Optional[TrustEngine] = None

        # 记录所有未验证的叙事预测
        self._pending_predictions: Dict[str, NarrativePrediction] = {}

        # 已验证的叙事记录（用于 Debug 和分析）
        self._verified_predictions: List[NarrativePrediction] = []

        # 历史信誉分（用于计算趋势）
        self._credibility_history: Dict[str, List[float]] = {}

    def attach_engine(self, engine: TrustEngine) -> None:
        """绑定信任引擎"""
        self._engine = engine

    def record_prediction(self,
                          kol_id: str,
                          narrative: NarrativeEvent,
                          step: int) -> NarrativePrediction:
        """记录一条 KOL 发出的叙事预测"""
        pred = NarrativePrediction(
            narrative_id=narrative._id,
            kol_id=kol_id,
            polarity=narrative.polarity,
            initial_strength=narrative.intensity,
            injected_step=step,
        )
        self._pending_predictions[narrative._id] = pred

        # 初始化信誉历史
        if kol_id not in self._credibility_history:
            self._credibility_history[kol_id] = []

        return pred

    def verify_and_update(self,
                          network: KOLNetwork,
                          market_price_history: List[float],
                          current_step: int) -> List[NarrativePrediction]:
        """
        检验所有待验证的叙事，更新对应 KOL 的信誉分。

        检验逻辑：
        1. 找到叙事注入后的价格序列
        2. 判断净价格方向（均值斜率）
        3. 对比叙事 polarity
           - 正向叙事 + 价格上涨 → confirm
           - 正向叙事 + 价格下跌 → reject
           - 负向叙事 + 价格下跌 → confirm
           - 负向叙事 + 价格上涨 → reject
        4. 更新 credibility_score 和 price_validation
        """
        if self._engine is None:
            return []

        verified = []

        # 价格方向计算窗口（叙事注入后多少步内算验证期）
        VERIFICATION_WINDOW = 8  # 步

        for nid, pred in list(self._pending_predictions.items()):
            # 判断是否到了验证窗口
            steps_since_injection = current_step - pred.injected_step
            if steps_since_injection < 3:
                # 太短，不验证
                continue

            # 取叙事注入后 VERIFICATION_WINDOW 步的价格序列
            start_idx = max(0, pred.injected_step)
            end_idx = min(len(market_price_history), start_idx + VERIFICATION_WINDOW)

            if end_idx - start_idx < 2:
                # 价格数据不足
                del self._pending_predictions[nid]
                continue

            price_window = market_price_history[start_idx:end_idx]
            price_direction = self._classify_price_direction(price_window, pred.polarity)

            pred.price_direction = price_direction
            pred.verified_step = current_step

            kol_state = self._engine.get_state(pred.kol_id)
            if kol_state:
                old_cred = kol_state.credibility_score

                if price_direction == "confirm":
                    new_cred = min(1.0, old_cred + self.config.accuracy_reward)
                    new_val = self.config.validation_confirm
                    pred.accuracy_score = 1.0

                elif price_direction == "reject":
                    new_cred = max(
                        self.config.min_credibility,
                        old_cred - self.config.accuracy_penalty
                    )
                    new_val = self.config.validation_reject
                    pred.accuracy_score = 0.0

                else:  # neutral
                    new_cred = old_cred * 0.98  # 轻微自然衰减
                    new_val = self.config.validation_neutral
                    pred.accuracy_score = 0.5

                self._engine.set_credibility_score(pred.kol_id, new_cred)
                self._engine.set_price_validation(pred.kol_id, new_val)

                # 记录历史
                self._credibility_history[pred.kol_id].append(new_cred)
                # 只保留最近 20 条
                if len(self._credibility_history[pred.kol_id]) > 20:
                    self._credibility_history[pred.kol_id] = \
                        self._credibility_history[pred.kol_id][-20:]

            verified.append(pred)
            del self._pending_predictions[nid]
            self._verified_predictions.append(pred)

        return verified

    def force_verify_all(self,
                         network: KOLNetwork,
                         market_price_history: List[float],
                         current_step: int) -> List[NarrativePrediction]:
        """强制验证所有待验证叙事（用于 Demo 6 证伪崩塌）"""
        # 先扩展验证窗口以确保全部可验证
        for nid, pred in list(self._pending_predictions.items()):
            steps_since_injection = current_step - pred.injected_step
            if steps_since_injection < 1:
                del self._pending_predictions[nid]
        return self.verify_and_update(network, market_price_history, current_step)

    def _classify_price_direction(self,
                                   price_window: List[float],
                                   polarity: Polarity) -> str:
        """
        判断价格方向与叙事 polarity 的关系。

        使用价格窗口均值的变化斜率：
        - slope > threshold → 上涨
        - slope < -threshold → 下跌
        - 否则 → 中性
        """
        if len(price_window) < 2:
            return "neutral"

        # 简单线性回归斜率
        x = np.arange(len(price_window))
        y = np.array(price_window)
        slope = float(np.polyfit(x, y, 1)[0])

        # 归一化（相对于窗口均值）
        mean_price = np.mean(y)
        if mean_price > 0:
            normalized_slope = slope / mean_price
        else:
            normalized_slope = 0.0

        if normalized_slope > self.config.price_signal_threshold:
            direction = "up"
        elif normalized_slope < -self.config.price_signal_threshold:
            direction = "down"
        else:
            return "neutral"

        # 判断是否与 polarity 一致
        if polarity == Polarity.POSITIVE:
            return "confirm" if direction == "up" else "reject"
        elif polarity == Polarity.NEGATIVE:
            return "confirm" if direction == "down" else "reject"
        else:
            return "neutral"

    def get_credibility_trend(self, kol_id: str) -> Optional[float]:
        """获取某 KOL 的信誉趋势（最近 N 次变化的均值）"""
        if kol_id not in self._credibility_history:
            return None
        history = self._credibility_history[kol_id]
        if len(history) < 2:
            return None
        return float(np.mean(np.diff(history)))

    def get_verification_summary(self) -> dict:
        """验证摘要"""
        if not self._verified_predictions:
            return {"total": 0, "confirm_rate": 0.0}

        confirms = sum(1 for p in self._verified_predictions if p.price_direction == "confirm")
        rejects = sum(1 for p in self._verified_predictions if p.price_direction == "reject")
        return {
            "total": len(self._verified_predictions),
            "confirm": confirms,
            "reject": rejects,
            "neutral": len(self._verified_predictions) - confirms - rejects,
            "confirm_rate": confirms / len(self._verified_predictions),
        }

    def get_pending_count(self) -> int:
        return len(self._pending_predictions)
