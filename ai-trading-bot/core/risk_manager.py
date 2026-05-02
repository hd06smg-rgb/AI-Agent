from core.ai_strategy import TradeSignal
from config.settings import (
    MAX_RISK_PER_TRADE, MIN_RISK_REWARD_RATIO,
    MAX_DAILY_LOSS, MAX_OPEN_POSITIONS, LEVERAGE_CONFIG
)
from utils.logger import logger


class RiskManager:
    """Manages risk: position sizing, SL/TP, daily loss tracking.
    
    OPTIMIZED FOR SMALL CAPITAL ($100):
    - Per-trade risk: 2% ($2)
    - Leverage: 5x
    - Max positions: 2
    - Daily loss limit: 10%
    """

    def __init__(self):
        self.daily_pnl = 0.0
        self.initial_balance = 0.0

    def set_initial_balance(self, balance: float):
        """Set initial balance for daily loss tracking."""
        self.initial_balance = balance
        logger.info(f"💰 Initial Balance Set: ${balance:.2f}")

    def reset_daily_pnl(self):
        """Reset daily P&L counter (call at start of each day)."""
        self.daily_pnl = 0.0
        logger.info("📅 Daily P&L reset to 0")

    def update_pnl(self, pnl: float):
        """Update daily P&L with trade result."""
        self.daily_pnl += pnl
        logger.info(f"📊 Daily P&L updated: ${self.daily_pnl:.2f}")

    def is_daily_loss_exceeded(self) -> bool:
        """Check if daily loss limit has been exceeded."""
        if self.initial_balance <= 0:
            return False
        daily_loss_pct = abs(self.daily_pnl) / self.initial_balance
        if self.daily_pnl < 0 and daily_loss_pct >= MAX_DAILY_LOSS:
            logger.warning(
                f"🛑 DAILY LOSS LIMIT REACHED: {daily_loss_pct*100:.2f}% "
                f"(limit: {MAX_DAILY_LOSS*100:.1f}%) | "
                f"Loss: ${abs(self.daily_pnl):.2f} | "
                f"Stopping all trades for today"
            )
            return True
        return False

    def can_open_position(self, open_positions_count: int) -> bool:
        """Check if we can open more positions."""
        if open_positions_count >= MAX_OPEN_POSITIONS:
            logger.info(f"⚠️ Max positions reached ({MAX_OPEN_POSITIONS}). Waiting for trade closure.")
            return False
        return True

    def calculate_stop_loss(self, signal: TradeSignal, atr_multiplier: float = 1.5) -> float:
        """
        Calculate stop loss based on ATR.
        SL = Entry ± (ATR * multiplier)
        
        For small capital: tighter SL is better (lower risk per trade)
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
        
        MIN_RISK_REWARD_RATIO = 2.0 means we need 2:1 reward:risk
        Example: If we risk $2, we target $4 profit
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
        
        For $100 capital with 2% risk per trade ($2):
        - If stop loss is 2% away → position size = $100 risk amount / 2% distance
        - With 5x leverage → can control larger notional value
        
        Formula:
        risk_amount = balance * MAX_RISK_PER_TRADE = $100 * 0.02 = $2
        sl_distance = |entry - stop_loss| / entry (as percentage)
        position_size = risk_amount / sl_distance / entry
        """
        entry = signal.current_price
        leverage = LEVERAGE_CONFIG.get(signal.symbol, 5)  # Default 5x for small capital

        # Distance to SL as percentage
        sl_distance_pct = abs(entry - stop_loss) / entry

        if sl_distance_pct == 0:
            logger.warning(f"❌ SL distance is 0 for {signal.symbol}")
            return 0.0

        # Risk amount in USDT ($2 for $100 balance)
        risk_amount = balance * MAX_RISK_PER_TRADE

        # Position value (notional) that risks this amount
        # Example: $2 risk / 2% SL distance = $100 notional value
        position_value = risk_amount / sl_distance_pct

        # With leverage, actual position size = notional / entry price
        position_size = position_value / entry

        # Cap at available margin (safety margin = 10% buffer)
        # Max position value = $100 * 5x leverage * 0.9 = $450
        max_position_value = balance * leverage * 0.9
        max_position_size = max_position_value / entry

        # Use smaller of calculated size or max size
        final_size = min(position_size, max_position_size)

        logger.info(
            f"📐 {signal.symbol} Position Sizing:\n"
            f"   Entry: ${entry:.2f}\n"
            f"   Stop Loss: ${stop_loss:.2f} ({sl_distance_pct*100:.2f}% away)\n"
            f"   Position Size: {final_size:.6f} contracts\n"
            f"   Notional Value: ${final_size * entry:.2f}\n"
            f"   Risk Amount: ${risk_amount:.2f} (2% of ${balance:.2f})\n"
            f"   Leverage: {leverage}x\n"
            f"   Margin Required: ${(final_size * entry / leverage):.2f}"
        )

        return round(final_size, 6)
