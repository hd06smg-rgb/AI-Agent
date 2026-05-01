import asyncio
import aiohttp
from datetime import datetime
from config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from utils.logger import logger


class TelegramNotifier:
    """Send trade notifications and alerts to Telegram."""

    def __init__(self):
        self.bot_token = TELEGRAM_BOT_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.enabled = bool(self.bot_token and self.chat_id)

        if not self.enabled:
            logger.warning("⚠️ Telegram notifications disabled (missing token/chat_id)")

    async def _send_message(self, text: str, parse_mode: str = "HTML"):
        """Send message to Telegram chat."""
        if not self.enabled:
            return

        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as resp:
                    if resp.status != 200:
                        error = await resp.text()
                        logger.error(f"Telegram API error: {error}")
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")

    def send_message(self, text: str):
        """Synchronous wrapper for sending messages."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(self._send_message(text))
            else:
                loop.run_until_complete(self._send_message(text))
        except RuntimeError:
            asyncio.run(self._send_message(text))

    def notify_trade_entry(self, symbol: str, direction: str, entry_price: float,
                           stop_loss: float, take_profit: float, amount: float,
                           leverage: int, rr_ratio: float, score: int,
                           ai_confidence: float = 0.0, ai_reasoning: str = ""):
        """Send trade entry notification."""
        emoji = "🟢" if direction == "LONG" else "🔴"
        ai_section = ""
        if ai_reasoning:
            ai_section = (
                f"\n🧠 <b>AI Analysis:</b>\n"
                f"   Confidence: {ai_confidence:.0%}\n"
                f"   {ai_reasoning[:150]}\n"
            )
        msg = (
            f"{emoji} <b>NEW TRADE OPENED</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📊 <b>Symbol:</b> {symbol}\n"
            f"📍 <b>Direction:</b> {direction}\n"
            f"💰 <b>Entry:</b> {entry_price}\n"
            f"🛑 <b>Stop Loss:</b> {stop_loss}\n"
            f"🎯 <b>Take Profit:</b> {take_profit}\n"
            f"📐 <b>Size:</b> {amount}\n"
            f"⚡ <b>Leverage:</b> {leverage}x\n"
            f"📊 <b>R:R Ratio:</b> 1:{rr_ratio:.2f}\n"
            f"🎯 <b>Signal Score:</b> {score}/3\n"
            f"{ai_section}"
            f"🕐 <b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        self.send_message(msg)

    def notify_trade_exit(self, symbol: str, direction: str, entry_price: float,
                          exit_price: float, pnl_pct: float, pnl_amount: float,
                          reason: str):
        """Send trade exit notification."""
        emoji = "✅" if pnl_pct > 0 else "❌"
        pnl_emoji = "💚" if pnl_pct > 0 else "💔"

        msg = (
            f"{emoji} <b>TRADE CLOSED</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📊 <b>Symbol:</b> {symbol}\n"
            f"📍 <b>Direction:</b> {direction}\n"
            f"💰 <b>Entry:</b> {entry_price}\n"
            f"💰 <b>Exit:</b> {exit_price}\n"
            f"{pnl_emoji} <b>P&L:</b> {pnl_pct:.2f}%\n"
            f"💵 <b>P&L ($):</b> ${pnl_amount:.2f}\n"
            f"📋 <b>Reason:</b> {reason}\n"
            f"🕐 <b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        self.send_message(msg)

    def notify_daily_summary(self, total_trades: int, wins: int, losses: int,
                             win_rate: float, total_pnl: float, balance: float):
        """Send daily trading summary."""
        pnl_emoji = "📈" if total_pnl >= 0 else "📉"
        msg = (
            f"📊 <b>DAILY SUMMARY</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📅 <b>Date:</b> {datetime.now().strftime('%Y-%m-%d')}\n"
            f"🔢 <b>Total Trades:</b> {total_trades}\n"
            f"✅ <b>Wins:</b> {wins}\n"
            f"❌ <b>Losses:</b> {losses}\n"
            f"🎯 <b>Win Rate:</b> {win_rate:.1f}%\n"
            f"{pnl_emoji} <b>Daily P&L:</b> ${total_pnl:.2f}\n"
            f"💰 <b>Balance:</b> ${balance:.2f}\n"
            f"━━━━━━━━━━━━━━━"
        )
        self.send_message(msg)

    def notify_error(self, error_msg: str):
        """Send error alert."""
        msg = (
            f"⚠️ <b>ERROR ALERT</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🚨 {error_msg}\n"
            f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        self.send_message(msg)

    def notify_bot_started(self):
        """Send bot start notification."""
        msg = (
            f"🤖 <b>TRADING BOT STARTED</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"✅ Bot is now running 24/7\n"
            f"📊 Pairs: BTC, ETH, SOL (USDT Futures)\n"
            f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        self.send_message(msg)

    def notify_bot_stopped(self, reason: str = "Manual stop"):
        """Send bot stop notification."""
        msg = (
            f"🛑 <b>TRADING BOT STOPPED</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📋 Reason: {reason}\n"
            f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        self.send_message(msg)

    def notify_heartbeat(self, balance: float, open_positions: int):
        """Send hourly heartbeat to confirm bot is alive."""
        msg = (
            f"💓 <b>BOT HEARTBEAT</b>\n"
            f"✅ Running normally\n"
            f"💰 Balance: ${balance:.2f}\n"
            f"📊 Open positions: {open_positions}\n"
            f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        self.send_message(msg)

    def notify_signal_skip(self, symbol: str, reason: str):
        """Notify when a signal is skipped (optional, for debugging)."""
        msg = (
            f"⏭️ <b>Signal Skipped</b>\n"
            f"📊 {symbol}\n"
            f"📋 {reason}"
        )
        self.send_message(msg)
