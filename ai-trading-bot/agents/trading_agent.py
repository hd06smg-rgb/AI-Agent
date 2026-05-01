import time
import traceback
from datetime import datetime, date
from core.exchange import OKXExchange
from core.data_fetcher import DataFetcher
from core.ai_strategy import AIStrategy
from core.risk_manager import RiskManager
from core.order_manager import OrderManager
from notifications.telegram_bot import TelegramNotifier
from config.settings import (
    TRADING_PAIRS, LEVERAGE_CONFIG, LOOP_INTERVAL_SECONDS,
    HEARTBEAT_INTERVAL
)
from utils.logger import logger


class TradingAgent:
    """
    Main autonomous trading agent.
    Runs 24/7, analyzing markets and executing trades based on AI strategy.
    """

    def __init__(self):
        logger.info("🤖 Initializing Trading Agent...")

        # Initialize components
        self.exchange = OKXExchange()
        self.data_fetcher = DataFetcher(self.exchange)
        self.strategy = AIStrategy()
        self.risk_manager = RiskManager()
        self.order_manager = OrderManager(self.exchange)
        self.telegram = TelegramNotifier()

        # State
        self.is_running = False
        self.current_date = date.today()
        self.last_heartbeat = time.time()

        # Set initial balance
        balance = self.exchange.get_balance()
        self.risk_manager.set_initial_balance(balance)
        logger.info(f"💰 Initial balance: ${balance:.2f}")

    def start(self):
        """Start the trading agent main loop."""
        self.is_running = True
        self.telegram.notify_bot_started()
        logger.info("🚀 Trading Agent started")

        try:
            while self.is_running:
                self._main_loop()
                time.sleep(LOOP_INTERVAL_SECONDS)
        except KeyboardInterrupt:
            logger.info("⏹️ Bot stopped by user (KeyboardInterrupt)")
            self.stop("User interrupt")
        except Exception as e:
            error_msg = f"Fatal error: {str(e)}\n{traceback.format_exc()}"
            logger.critical(error_msg)
            self.telegram.notify_error(error_msg)
            self.stop(f"Fatal error: {str(e)}")

    def stop(self, reason: str = "Manual stop"):
        """Stop the trading agent."""
        self.is_running = False
        self.telegram.notify_bot_stopped(reason)
        logger.info(f"🛑 Trading Agent stopped: {reason}")

    def _main_loop(self):
        """Main trading loop iteration."""
        try:
            # Check if new day → reset daily P&L
            self._check_daily_reset()

            # Check daily loss limit
            if self.risk_manager.is_daily_loss_exceeded():
                logger.warning("🛑 Daily loss limit exceeded. Pausing trades.")
                return

            # Check and close positions that hit SL/TP
            closed_trades = self.order_manager.check_and_close_positions()
            for trade in closed_trades:
                self.risk_manager.update_pnl(trade.pnl)
                self.telegram.notify_trade_exit(
                    symbol=trade.symbol,
                    direction=trade.direction,
                    entry_price=trade.entry_price,
                    exit_price=trade.exit_price,
                    pnl_pct=trade.pnl_pct,
                    pnl_amount=trade.pnl,
                    reason=trade.status
                )

            # Analyze each trading pair
            for symbol in TRADING_PAIRS:
                self._analyze_and_trade(symbol)

            # Send heartbeat
            self._check_heartbeat()

        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            self.telegram.notify_error(f"Loop error: {str(e)}")

    def _analyze_and_trade(self, symbol: str):
        """Analyze a symbol and execute trade if signal is valid."""
        # Skip if already in a position for this symbol
        if self.order_manager.has_open_position(symbol):
            return

        # Check max positions
        active_count = self.order_manager.get_active_trades_count()
        if not self.risk_manager.can_open_position(active_count):
            return

        # Fetch market data
        df = self.data_fetcher.get_candles(symbol)
        if df.empty:
            return

        # Run AI strategy analysis
        signal = self.strategy.analyze(df, symbol)
        if not signal or not signal.is_valid:
            return

        # Calculate SL/TP
        stop_loss = self.risk_manager.calculate_stop_loss(signal)
        take_profit = self.risk_manager.calculate_take_profit(signal, stop_loss)

        # Evaluate Risk:Reward
        if not self.strategy.evaluate_risk_reward(signal, signal.current_price, stop_loss, take_profit):
            self.telegram.notify_signal_skip(
                symbol, f"R:R ratio too low (need min 1:{self.strategy.__class__.__name__})"
            )
            return

        # Calculate position size
        balance = self.exchange.get_balance()
        amount = self.risk_manager.calculate_position_size(signal, balance, stop_loss)

        # Check minimum order amount
        min_amount = self.exchange.get_min_order_amount(symbol)
        if amount < min_amount:
            logger.warning(f"Position size {amount} below minimum {min_amount} for {symbol}")
            return

        # Execute trade
        leverage = LEVERAGE_CONFIG.get(symbol, 10)
        trade = self.order_manager.execute_trade(
            signal=signal,
            amount=amount,
            stop_loss=stop_loss,
            take_profit=take_profit,
            leverage=leverage
        )

        if trade:
            # Calculate R:R for notification
            if signal.direction == "LONG":
                risk = signal.current_price - stop_loss
                reward = take_profit - signal.current_price
            else:
                risk = stop_loss - signal.current_price
                reward = signal.current_price - take_profit
            rr = reward / risk if risk > 0 else 0

            self.telegram.notify_trade_entry(
                symbol=symbol,
                direction=signal.direction,
                entry_price=signal.current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                amount=amount,
                leverage=leverage,
                rr_ratio=rr,
                score=signal.score
            )

    def _check_daily_reset(self):
        """Reset daily stats if new day."""
        today = date.today()
        if today != self.current_date:
            # Send daily summary before reset
            stats = self.order_manager.get_daily_stats()
            balance = self.exchange.get_balance()
            self.telegram.notify_daily_summary(
                total_trades=stats["trades"],
                wins=stats["wins"],
                losses=stats["losses"],
                win_rate=stats["win_rate"],
                total_pnl=stats["total_pnl"],
                balance=balance
            )

            # Reset
            self.current_date = today
            self.risk_manager.reset_daily_pnl()
            self.risk_manager.set_initial_balance(balance)
            logger.info(f"📅 New day: {today}. Daily stats reset.")

    def _check_heartbeat(self):
        """Send periodic heartbeat to Telegram."""
        now = time.time()
        if now - self.last_heartbeat >= HEARTBEAT_INTERVAL:
            balance = self.exchange.get_balance()
            open_pos = self.order_manager.get_active_trades_count()
            self.telegram.notify_heartbeat(balance, open_pos)
            self.last_heartbeat = now
