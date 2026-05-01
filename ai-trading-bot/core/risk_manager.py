from core.ai_strategy import TradeSignal
from config.settings import (
    MAX_RISK_PER_TRADE, MIN_RISK_REWARD_RATIO,
    MAX_DAILY_LOSS, MAX_OPEN_POSITIONS, LEVERAGE_CONFIG
)
from utils.logger import logger


class RiskManager:
    """Manages risk: position sizing, SL/TP, daily loss tracking."""

    def __init__(self):
        self.daily_pnl = 0.0
        self.initial_balance = 0.0

    def set_initial_balance(self, balance: float):
        """Set initial balance for daily loss tracking."""
        self.initial_balance = balance

    def reset_daily_pnl(self):
        """Reset daily P&L counter (call at start of each day)."""
        self.daily_pnl = 0.0
        logger.info("📅 Daily P&L reset to 0")

    def update_pnl(self, pnl: float):
        """Update daily P&L with trade result."""
        self.daily_pnl += pnl

    def is_daily_loss_exceeded(self) -> bool:
        """Check if daily loss limit has been exceeded."""
        if self.initial_balance <= 0:
            return False
        daily_loss_pct = abs(self.daily_pnl) / self.initial_balance
        if self.daily_pnl < 0 and daily_loss_pct >= MAX_DAILY_LOSS:
            logger.warning(
                f"🛑 Daily loss limit reached: {daily_loss_pct*100:.2f}% "
                f"(max {MAX_DAILY_LOSS*100:.1f}%)"
            )
            return True
        return False

    def can_open_position(self, open_positions_count: int) -> bool:
        """Check if we can open more positions."""
        if open_positions_count >= MAX_OPEN_POSITIONS:
            logger.info(f"⚠️ Max positions reached ({MAX_OPEN_POSITIONS})")
            return False
        return True

    def calculate_stop_loss(self, signal: TradeSignal, atr_multiplier: float = 1.5) -> float:
        """
        Calculate stop loss based on ATR.
        SL = Entry ± (ATR * multiplier)
        """
        atr_distance = signal.atr * atr_multiplier

        if signal.direction == "LONG":
            stop_loss = signal.current_price - atr_distance
        else:  # SHORT
            stop_loss = signal.current_price + atr_distance

        return round(stop_loss, 6)

    def calculate_take_profit(self, signal: TradeSignal, stop_loss: float,
                               rr_ratio: float = None) -> float:
        """
        Calculate take profit based on R:R ratio.
        TP = Entry + (risk * rr_ratio) for LONG
        TP = Entry - (risk * rr_ratio) for SHORT
        """
        rr = rr_ratio or MIN_RISK_REWARD_RATIO

        if signal.direction == "LONG":
            risk = signal.current_price - stop_loss
            take_profit = signal.current_price + (risk * rr)
        else:  # SHORT
            risk = stop_loss - signal.current_price
            take_profit = signal.current_price - (risk * rr)

        return round(take_profit, 6)

    def calculate_position_size(self, signal: TradeSignal, balance: float,
                                 stop_loss: float) -> float:
        """
        Calculate position size based on max risk per trade.
        Position size = (Balance * Risk%) / (|Entry - SL| / Entry) / Leverage
        
        This ensures we only risk MAX_RISK_PER_TRADE of our balance.
        """
        entry = signal.current_price
        leverage = LEVERAGE_CONFIG.get(signal.symbol, 10)

        # Distance to SL as percentage
        sl_distance_pct = abs(entry - stop_loss) / entry

        if sl_distance_pct == 0:
            logger.warning(f"SL distance is 0 for {signal.symbol}")
            return 0.0

        # Risk amount in USDT
        risk_amount = balance * MAX_RISK_PER_TRADE

        # Position value (notional) that risks this amount
        position_value = risk_amount / sl_distance_pct

        # With leverage, margin needed = position_value / leverage
        # But we want position size in base currency
        position_size = position_value / entry

        # Cap at available margin with leverage
        max_position_value = balance * leverage * 0.9  # 90% safety margin
        max_position_size = max_position_value / entry

        final_size = min(position_size, max_position_size)

        logger.info(
            f"📐 {signal.symbol} | Size: {final_size:.6f} | "
            f"Risk: ${risk_amount:.2f} | Leverage: {leverage}x"
        )

        return round(final_size, 6)
