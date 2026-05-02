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
        logger.info(f"💰 Initial Balance Set: ${balance:.2f}")
        logger.info(f"   Max Risk Per Trade: ${balance * MAX_RISK_PER_TRADE:.2f}")
        logger.info(f"   Daily Loss Limit: ${balance * MAX_DAILY_LOSS:.2f}")

    def reset_daily_pnl(self):
        """Reset daily P&L counter (call at start of each day)."""
        self.daily_pnl = 0.0
        logger.info("📅 Daily P&L reset to 0")

    def update_pnl(self, pnl: float):
        """Update daily P&L with trade result."""
        self.daily_pnl += pnl
        loss_pct = (self.daily_pnl / self.initial_balance * 100) if self.initial_balance > 0 else 0
        logger.info(f"📊 Daily P&L Updated: ${self.daily_pnl:.2f} ({loss_pct:.2f}%)")

    def is_daily_loss_exceeded(self) -> bool:
        """Check if daily loss limit has been exceeded."""
        if self.initial_balance <= 0:
            return False
        daily_loss_pct = abs(self.daily_pnl) / self.initial_balance
        if self.daily_pnl < 0 and daily_loss_pct >= MAX_DAILY_LOSS:
            logger.warning(
                f"🛑 DAILY LOSS LIMIT REACHED: {daily_loss_pct*100:.2f}% "
                f"(max {MAX_DAILY_LOSS*100:.1f}%) | Stopping trades for today."
            )
            return True
        return False

    def can_open_position(self, open_positions_count: int) -> bool:
        """Check if we can open more positions."""
        if open_positions_count >= MAX_OPEN_POSITIONS:
            logger.info(f"⚠️ Max positions reached ({MAX_OPEN_POSITIONS}). Skipping new trades.")
            return False
        return True

    def calculate_stop_loss(self, signal: TradeSignal, atr_multiplier: float = 1.5) -> float:
        """
        Calculate stop loss based on ATR.
        SL = Entry ± (ATR * multiplier)
        
        For small capital: ATR multiplier helps ensure SL isn't too tight
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
        
        Formula for $100 capital:
        - Risk per trade = $100 * 2% = $2
        - Position size = Risk / (Entry Price - SL Price) / Leverage
        
        This ensures we only risk MAX_RISK_PER_TRADE of our balance.
        Safety capped at 90% of available margin.
        """
        entry = signal.current_price
        leverage = LEVERAGE_CONFIG.get(signal.symbol, 5)  # Default to 5x for small capital

        # Distance to SL as percentage of entry price
        sl_distance_pct = abs(entry - stop_loss) / entry

        if sl_distance_pct == 0:
            logger.warning(f"⚠️ SL distance is 0 for {signal.symbol}. Skipping position.")
            return 0.0

        # Risk amount in USDT
        risk_amount = balance * MAX_RISK_PER_TRADE

        # Position value (notional) that risks this amount
        position_value = risk_amount / sl_distance_pct

        # With leverage, position size = notional / entry price
        position_size = position_value / entry

        # Cap at available margin with leverage
        # 90% safety margin to avoid liquidation
        max_position_value = balance * leverage * 0.9
        max_position_size = max_position_value / entry

        final_size = min(position_size, max_position_size)

        # Enhanced logging for small capital trading
        logger.info(
            f"📐 Position Sizing for {signal.symbol}:"
        )
        logger.info(
            f"   Entry: ${entry:.4f} | SL: ${stop_loss:.4f} | Distance: {sl_distance_pct*100:.2f}%"
        )
        logger.info(
            f"   Risk Amount: ${risk_amount:.2f} | Leverage: {leverage}x"
        )
        logger.info(
            f"   Position Size: {final_size:.6f} | Max Available: {max_position_size:.6f}"
        )

        return round(final_size, 6)
