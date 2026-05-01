"""
AI Agent Auto Trading Bot - OKX Futures
=========================================
Trades BTC/USDT, ETH/USDT, SOL/USDT perpetual futures
using RSI, MACD, SuperTrend indicators with AI confluence scoring.

Run: python main.py
"""

import sys
import signal
from agents.trading_agent import TradingAgent
from utils.logger import logger


def main():
    """Main entry point for the trading bot."""
    logger.info("=" * 60)
    logger.info("🤖 AI AGENT AUTO TRADING BOT")
    logger.info("📊 Pairs: BTC/USDT, ETH/USDT, SOL/USDT (Futures)")
    logger.info("📈 Strategy: RSI + MACD + SuperTrend Confluence")
    logger.info("=" * 60)

    # Initialize agent
    agent = TradingAgent()

    # Handle graceful shutdown
    def signal_handler(sig, frame):
        logger.info("\n⏹️ Shutdown signal received...")
        agent.stop("System shutdown signal")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start trading
    agent.start()


if __name__ == "__main__":
    main()
