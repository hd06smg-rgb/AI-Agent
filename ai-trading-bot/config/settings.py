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
# For small capital, focus on 1-2 pairs with good liquidity (BTC, ETH)
TRADING_PAIRS = ["BTC/USDT:USDT", "ETH/USDT:USDT"]

# =============================================================================
# Leverage & Margin Configuration (per symbol)
# OPTIMIZED FOR $100 CAPITAL: 5x leverage per pair
# =============================================================================
LEVERAGE_CONFIG = {
    "BTC/USDT:USDT": 5,
    "ETH/USDT:USDT": 5,
    "SOL/USDT:USDT": 5,
}

# Margin mode: "isolated" or "cross"
# Isolated is safer - loss limited to position amount
MARGIN_MODE = "isolated"

# =============================================================================
# Risk Management - OPTIMIZED FOR $100 CAPITAL
# =============================================================================
# $100 capital = $2 per trade (2% risk)
MAX_RISK_PER_TRADE = 0.02       # 2% of balance per trade = $2 per trade

# Minimum R:R ratio (higher = more conservative)
MIN_RISK_REWARD_RATIO = 2.0     # 1:2 ratio = need $4 profit for $2 risk

# Max daily loss before stopping trades
# For small capital, tighter limit = safer
MAX_DAILY_LOSS = 0.10           # 10% max daily loss = $10 loss then STOP

# Max simultaneous open positions
# For small capital, fewer positions = less risk
MAX_OPEN_POSITIONS = 2          # Max 2 trades at same time (reduced from 3)

# =============================================================================
# Strategy Configuration
# =============================================================================
TIMEFRAME = "15m"               # 15m timeframe = balance between noise & speed
CANDLE_LIMIT = 100              # Number of candles to fetch

# RSI Settings (unchanged - these work well)
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
# Higher = more selective = fewer but better quality trades
MIN_SIGNAL_SCORE = 2

# =============================================================================
# Bot Loop Configuration
# =============================================================================
LOOP_INTERVAL_SECONDS = 60      # Check every 60 seconds (balanced frequency)
HEARTBEAT_INTERVAL = 3600       # Send heartbeat to Telegram every hour
