from dataclasses import dataclass, field
from datetime import datetime
from core.exchange import OKXExchange
from core.ai_strategy import TradeSignal
from utils.logger import logger


@dataclass
class TradeRecord:
    """Record of an executed trade."""
    symbol: str
    direction: str
    entry_price: float
    stop_loss: float
    take_profit: float
    amount: float
    leverage: int
    risk_reward: float
    entry_time: datetime = field(default_factory=datetime.now)
    exit_price: float = 0.0
    exit_time: datetime = None
    pnl: float = 0.0
    pnl_pct: float = 0.0
    status: str = "OPEN"  # OPEN, CLOSED, STOPPED


class OrderManager:
    """Manages order execution and trade tracking."""

    def __init__(self, exchange: OKXExchange):
        self.exchange = exchange
        self.active_trades: dict[str, TradeRecord] = {}
        self.trade_history: list[TradeRecord] = []

    def has_open_position(self, symbol: str) -> bool:
        """Check if there's an active trade for symbol."""
        return symbol in self.active_trades

    def execute_trade(self, signal: TradeSignal, amount: float,
                      stop_loss: float, take_profit: float, leverage: int) -> TradeRecord | None:
        """Execute a new trade based on signal."""
        if self.has_open_position(signal.symbol):
            logger.warning(f"Already have position for {signal.symbol}, skipping")
            return None

        # Determine order side
        side = "buy" if signal.direction == "LONG" else "sell"

        # Place order
        order = self.exchange.place_market_order(
            symbol=signal.symbol,
            side=side,
            amount=amount,
            stop_loss=stop_loss,
            take_profit=take_profit
        )

        if not order:
            return None

        # Calculate R:R
        if signal.direction == "LONG":
            risk = signal.current_price - stop_loss
            reward = take_profit - signal.current_price
        else:
            risk = stop_loss - signal.current_price
            reward = signal.current_price - take_profit

        rr_ratio = reward / risk if risk > 0 else 0

        # Create trade record
        trade = TradeRecord(
            symbol=signal.symbol,
            direction=signal.direction,
            entry_price=signal.current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            amount=amount,
            leverage=leverage,
            risk_reward=rr_ratio
        )

        self.active_trades[signal.symbol] = trade
        logger.info(
            f"📝 Trade recorded: {signal.direction} {signal.symbol} @ {signal.current_price} | "
            f"SL: {stop_loss} | TP: {take_profit} | R:R 1:{rr_ratio:.2f}"
        )

        return trade

    def check_and_close_positions(self) -> list[TradeRecord]:
        """Check positions and close if SL/TP hit. Returns list of closed trades."""
        closed_trades = []

        for symbol in list(self.active_trades.keys()):
            trade = self.active_trades[symbol]
            current_price = self.exchange.get_ticker_price(symbol)

            if current_price == 0:
                continue

            should_close = False
            close_reason = ""

            if trade.direction == "LONG":
                if current_price <= trade.stop_loss:
                    should_close = True
                    close_reason = "STOP_LOSS"
                elif current_price >= trade.take_profit:
                    should_close = True
                    close_reason = "TAKE_PROFIT"
            else:  # SHORT
                if current_price >= trade.stop_loss:
                    should_close = True
                    close_reason = "STOP_LOSS"
                elif current_price <= trade.take_profit:
                    should_close = True
                    close_reason = "TAKE_PROFIT"

            if should_close:
                closed_trade = self._close_trade(symbol, current_price, close_reason)
                if closed_trade:
                    closed_trades.append(closed_trade)

        return closed_trades

    def _close_trade(self, symbol: str, exit_price: float, reason: str) -> TradeRecord | None:
        """Close a trade and record results."""
        if symbol not in self.active_trades:
            return None

        trade = self.active_trades[symbol]
        side = "buy" if trade.direction == "LONG" else "sell"

        # Close via exchange
        order = self.exchange.close_position(symbol, side, trade.amount)

        # Calculate P&L
        if trade.direction == "LONG":
            pnl_pct = ((exit_price - trade.entry_price) / trade.entry_price) * trade.leverage
        else:
            pnl_pct = ((trade.entry_price - exit_price) / trade.entry_price) * trade.leverage

        pnl_amount = trade.amount * trade.entry_price * (pnl_pct / 100) if pnl_pct != 0 else 0

        # Update trade record
        trade.exit_price = exit_price
        trade.exit_time = datetime.now()
        trade.pnl = pnl_amount
        trade.pnl_pct = pnl_pct * 100  # Convert to percentage
        trade.status = reason

        # Move to history
        self.trade_history.append(trade)
        del self.active_trades[symbol]

        emoji = "🟢" if pnl_pct > 0 else "🔴"
        logger.info(
            f"{emoji} Trade closed: {trade.direction} {symbol} | "
            f"Entry: {trade.entry_price} → Exit: {exit_price} | "
            f"P&L: {pnl_pct*100:.2f}% | Reason: {reason}"
        )

        return trade

    def get_active_trades_count(self) -> int:
        """Get number of active trades."""
        return len(self.active_trades)

    def get_daily_stats(self) -> dict:
        """Get daily trading statistics."""
        if not self.trade_history:
            return {"trades": 0, "wins": 0, "losses": 0, "win_rate": 0, "total_pnl": 0}

        today = datetime.now().date()
        today_trades = [
            t for t in self.trade_history
            if t.exit_time and t.exit_time.date() == today
        ]

        wins = sum(1 for t in today_trades if t.pnl > 0)
        losses = sum(1 for t in today_trades if t.pnl <= 0)
        total_pnl = sum(t.pnl for t in today_trades)
        win_rate = (wins / len(today_trades) * 100) if today_trades else 0

        return {
            "trades": len(today_trades),
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
            "total_pnl": total_pnl
        }
