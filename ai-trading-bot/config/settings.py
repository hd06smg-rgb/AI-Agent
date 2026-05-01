import os
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# OKX API Configuration
# =============================================================================
OKX_API_KEY = os.getenv("OKX_API_KEY", "")
OKX_SECRET_KEY = os.getenv("OKX_SECRET_KEY", "")
OKX_PASSPHRASE = os.getenv("OKX_PASSPHRASE", "")
OKX_DEMO_MODE = os.getenv("OKX_DEMO_MODE", "True").lower() == "true"

# =============================================================================
# OpenRouter AI Configuration
# =============================================================================
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
AI_ENABLED = True  # Set False to use only indicator confluence without AI

# =============================================================================
# Telegram Configuration
# =============================================================================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# =============================================================================
# Trading Pairs (USDT Perpetual Futures)
# =============================================================================
TRADING_PAIRS = ["BTC/USDT:USDT", "ETH/USDT:USDT", "SOL/USDT:USDT"]

# =============================================================================
# Leverage & Margin Configuration (per symbol)
# =============================================================================
LEVERAGE_CONFIG = {
    "BTC/USDT:USDT": 10,
    "ETH/USDT:USDT": 10,
    "SOL/USDT:USDT": 10,
}

# Margin mode: "isolated" or "cross"
MARGIN_MODE = "isolated"

# =============================================================================
# Risk Management
# =============================================================================
MAX_RISK_PER_TRADE = 0.02       # 2% of balance per trade
MIN_RISK_REWARD_RATIO = 2.0     # Minimum R:R = 1:2
MAX_DAILY_LOSS = 0.06           # 6% max daily loss → stop trading
MAX_OPEN_POSITIONS = 3          # Max simultaneous positions

# =============================================================================
# Strategy Configuration
# =============================================================================
TIMEFRAME = "15m"               # Candle timeframe
CANDLE_LIMIT = 100              # Number of candles to fetch

# RSI Settings
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30

# MACD Settings
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

# SuperTrend Settings
SUPERTREND_PERIOD = 10
SUPERTREND_MULTIPLIER = 3.0

# Minimum signal confluence score (out of 3)
MIN_SIGNAL_SCORE = 2

# =============================================================================
# Bot Loop Configuration
# =============================================================================
LOOP_INTERVAL_SECONDS = 60      # Check every 60 seconds
HEARTBEAT_INTERVAL = 3600       # Send heartbeat to Telegram every hour (seconds)
