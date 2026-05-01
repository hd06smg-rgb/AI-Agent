import pandas as pd
from dataclasses import dataclass, field
from core.indicators import TechnicalIndicators
from core.ai_model import OpenRouterAI
from config.settings import MIN_SIGNAL_SCORE, MIN_RISK_REWARD_RATIO, AI_ENABLED
from utils.logger import logger


@dataclass
class TradeSignal:
    """Represents a trading signal from the AI strategy."""
    symbol: str
    direction: str          # "LONG" or "SHORT"
    score: int              # Confluence score (0-3)
    rsi_signal: int         # 1, -1, or 0
    macd_signal: int        # 1, -1, or 0
    supertrend_signal: int  # 1 or -1
    rsi_value: float
    current_price: float
    atr: float
    is_valid: bool          # Whether trade meets minimum criteria
    reason: str             # Why valid or rejected
    ai_approved: bool = True
    ai_confidence: float = 0.0
    ai_reasoning: str = ""
    ai_suggestion: str = ""


class AIStrategy:
    """
    AI Strategy Engine.
    Evaluates confluence of RSI, MACD, SuperTrend indicators.
    Uses OpenRouter AI model for final trade validation.
    Decides if a trade setup is valid based on signal agreement + R:R ratio + AI approval.
    """

    def __init__(self):
        self.indicators = TechnicalIndicators()
        self.ai_model = OpenRouterAI() if AI_ENABLED else None

    def analyze(self, df: pd.DataFrame, symbol: str) -> TradeSignal | None:
        """
        Analyze market data and generate a trade signal.
        Returns TradeSignal or None if insufficient data.
        """
        if df.empty or len(df) < 30:
            logger.warning(f"Insufficient data for {symbol}")
            return None

        # Calculate indicators
        rsi = self.indicators.calculate_rsi(df)
        macd_line, signal_line, histogram = self.indicators.calculate_macd(df)
        supertrend, direction = self.indicators.calculate_supertrend(df)
        atr = self.indicators.calculate_atr(df)

        # Get current values
        current_rsi = rsi.iloc[-1]
        current_price = df["close"].iloc[-1]
        current_atr = atr.iloc[-1]

        # Get individual signals
        rsi_sig = self.indicators.get_rsi_signal(current_rsi)
        macd_sig = self.indicators.get_macd_signal(macd_line, signal_line)
        st_sig = self.indicators.get_supertrend_signal(direction)

        # Calculate confluence score
        signals = [rsi_sig, macd_sig, st_sig]
        long_score = sum(1 for s in signals if s == 1)
        short_score = sum(1 for s in signals if s == -1)

        # Determine dominant direction
        if long_score >= short_score:
            trade_direction = "LONG"
            score = long_score
        else:
            trade_direction = "SHORT"
            score = short_score

        # Indicator confluence validation
        indicator_valid = score >= MIN_SIGNAL_SCORE

        # AI Model validation (only if indicators pass)
        ai_approved = True
        ai_confidence = 0.0
        ai_reasoning = ""
        ai_suggestion = ""

        if indicator_valid and self.ai_model:
            ai_result = self._get_ai_decision(
                df, symbol, trade_direction, current_price,
                current_rsi, rsi_sig, macd_sig, st_sig,
                score, current_atr
            )
            ai_approved = ai_result["approved"]
            ai_confidence = ai_result["confidence"]
            ai_reasoning = ai_result["reasoning"]
            ai_suggestion = ai_result["suggestion"]

        # Final validity: indicators + AI must both approve
        is_valid = indicator_valid and ai_approved

        reason = self._build_reason(
            trade_direction, score, rsi_sig, macd_sig, st_sig,
            current_rsi, ai_approved, ai_reasoning
        )

        signal = TradeSignal(
            symbol=symbol,
            direction=trade_direction,
            score=score,
            rsi_signal=rsi_sig,
            macd_signal=macd_sig,
            supertrend_signal=st_sig,
            rsi_value=current_rsi,
            current_price=current_price,
            atr=current_atr,
            is_valid=is_valid,
            reason=reason,
            ai_approved=ai_approved,
            ai_confidence=ai_confidence,
            ai_reasoning=ai_reasoning,
            ai_suggestion=ai_suggestion
        )

        if is_valid:
            logger.info(
                f"🎯 {symbol} | Signal: {trade_direction} | Score: {score}/3 | "
                f"RSI: {current_rsi:.1f} | Price: {current_price} | "
                f"AI: ✅ ({ai_confidence:.0%})"
            )
        elif indicator_valid and not ai_approved:
            logger.info(
                f"🧠 {symbol} | AI REJECTED {trade_direction} | Score: {score}/3 | "
                f"Reason: {ai_reasoning[:60]}"
            )
        else:
            logger.debug(
                f"⏸️ {symbol} | No valid setup | Score: {score}/3 | "
                f"RSI: {current_rsi:.1f}"
            )

        return signal

    def _get_ai_decision(self, df: pd.DataFrame, symbol: str, direction: str,
                         price: float, rsi: float, rsi_sig: int, macd_sig: int,
                         st_sig: int, score: int, atr: float) -> dict:
        """Get AI model decision on the trade setup."""
        # Prepare recent candles for context
        recent_candles = []
        for i in range(-5, 0):
            if abs(i) <= len(df):
                row = df.iloc[i]
                recent_candles.append({
                    "open": row["open"],
                    "high": row["high"],
                    "low": row["low"],
                    "close": row["close"]
                })

        # Calculate SL/TP distances for AI context
        sl_distance = atr * 1.5
        tp_distance = sl_distance * MIN_RISK_REWARD_RATIO
        sl_pct = (sl_distance / price) * 100
        tp_pct = (tp_distance / price) * 100

        market_data = {
            "symbol": symbol,
            "direction": direction,
            "price": price,
            "rsi": rsi,
            "rsi_signal": rsi_sig,
            "macd_signal": macd_sig,
            "supertrend_signal": st_sig,
            "score": score,
            "atr": atr,
            "recent_candles": recent_candles,
            "sl_distance_pct": sl_pct,
            "tp_distance_pct": tp_pct,
            "rr_ratio": MIN_RISK_REWARD_RATIO
        }

        return self.ai_model.analyze_trade(market_data)

    def _build_reason(self, direction: str, score: int,
                      rsi_sig: int, macd_sig: int, st_sig: int,
                      rsi_value: float, ai_approved: bool = True,
                      ai_reasoning: str = "") -> str:
        """Build human-readable reason for trade decision."""
        parts = []

        if score >= MIN_SIGNAL_SCORE:
            parts.append(f"✅ Valid {direction} setup (score {score}/3)")
        else:
            parts.append(f"❌ Insufficient confluence (score {score}/3, need {MIN_SIGNAL_SCORE})")

        sig_map = {1: "LONG ✅", -1: "SHORT ✅", 0: "NEUTRAL ⚪"}
        parts.append(f"RSI({rsi_value:.1f}): {sig_map[rsi_sig]}")
        parts.append(f"MACD: {sig_map[macd_sig]}")
        parts.append(f"SuperTrend: {sig_map[st_sig]}")

        # AI decision
        if ai_approved:
            parts.append("🧠 AI: APPROVED")
        else:
            parts.append(f"🧠 AI: REJECTED - {ai_reasoning[:50]}")

        return " | ".join(parts)

    def evaluate_risk_reward(self, signal: TradeSignal, entry_price: float,
                              stop_loss: float, take_profit: float) -> bool:
        """
        Evaluate if the Risk:Reward ratio meets minimum requirements.
        Returns True if R:R >= MIN_RISK_REWARD_RATIO.
        """
        if signal.direction == "LONG":
            risk = entry_price - stop_loss
            reward = take_profit - entry_price
        else:  # SHORT
            risk = stop_loss - entry_price
            reward = entry_price - take_profit

        if risk <= 0:
            logger.warning(f"Invalid risk calculation for {signal.symbol}")
            return False

        rr_ratio = reward / risk

        if rr_ratio >= MIN_RISK_REWARD_RATIO:
            logger.info(f"📊 {signal.symbol} R:R = 1:{rr_ratio:.2f} ✅ (min 1:{MIN_RISK_REWARD_RATIO})")
            return True
        else:
            logger.info(f"📊 {signal.symbol} R:R = 1:{rr_ratio:.2f} ❌ (below min 1:{MIN_RISK_REWARD_RATIO})")
            return False
