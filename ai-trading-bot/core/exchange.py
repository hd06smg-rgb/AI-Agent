import ccxt
from config.settings import (
    OKX_API_KEY, OKX_SECRET_KEY, OKX_PASSPHRASE,
    OKX_DEMO_MODE, LEVERAGE_CONFIG, MARGIN_MODE
)
from utils.logger import logger


class OKXExchange:
    """OKX Futures exchange wrapper using ccxt."""

    def __init__(self):
        self.exchange = ccxt.okx({
            "apiKey": OKX_API_KEY,
            "secret": OKX_SECRET_KEY,
            "password": OKX_PASSPHRASE,
            "enableRateLimit": True,
            "options": {
                "defaultType": "swap",  # Perpetual futures
            },
        })

        # Enable demo/sandbox mode
        if OKX_DEMO_MODE:
            self.exchange.set_sandbox_mode(True)
            logger.info("🟡 Running in DEMO/PAPER TRADING mode")
        else:
            logger.warning("🔴 Running in LIVE TRADING mode")

        self._setup_leverage()

    def _setup_leverage(self):
        """Set leverage and margin mode for all trading pairs."""
        # Skip leverage setup in DEMO mode (OKX sandbox API has limitations)
        if OKX_DEMO_MODE:
            logger.info("⚠️ Skipping leverage setup in DEMO mode (OKX sandbox has API limitations)")
            logger.info("   Leverage will use default. For production, set manually in OKX.")
            return
        
        # In LIVE mode, attempt to set leverage
        # NOTE: Leverage should be pre-configured in OKX account settings for best results
        logger.info("🔧 Attempting to set leverage for trading pairs...")
        
        for symbol, leverage in LEVERAGE_CONFIG.items():
            try:
                self.exchange.set_margin_mode(MARGIN_MODE, symbol)
                self.exchange.set_leverage(leverage, symbol)
                logger.info(f"✅ Set {symbol}: leverage={leverage}x, margin={MARGIN_MODE}")
            except ccxt.ExchangeError as e:
                # OKX API error - leverage might need to be set manually
                error_str = str(e)
                if "should be between" in error_str or "lever" in error_str:
                    logger.warning(
                        f"⚠️ Could not set leverage for {symbol} via API.\n"
                        f"   → Set manually in OKX account: Futures → {symbol} → Settings\n"
                        f"   → Set Leverage to {leverage}x and Margin Mode to {MARGIN_MODE}\n"
                        f"   → API Error: {e}"
                    )
                else:
                    logger.warning(f"⚠️ Could not set leverage for {symbol}: {e}")
            except Exception as e:
                logger.warning(f"⚠️ Error setting leverage for {symbol}: {e}")

    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 100) -> list:
        """Fetch OHLCV candle data."""
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            return ohlcv
        except Exception as e:
            logger.error(f"Error fetching OHLCV for {symbol}: {e}")
            return []

    def get_balance(self) -> float:
        """Get available USDT balance."""
        try:
            balance = self.exchange.fetch_balance()
            usdt_free = balance.get("USDT", {}).get("free", 0)
            return float(usdt_free)
        except Exception as e:
            logger.error(f"Error fetching balance: {e}")
            logger.warning("⚠️ Returning $0.00 balance. Check API keys, permissions, and IP whitelist.")
            return 0.0

    def get_total_equity(self) -> float:
        """Get total equity in USDT."""
        try:
            balance = self.exchange.fetch_balance()
            usdt_total = balance.get("USDT", {}).get("total", 0)
            return float(usdt_total)
        except Exception as e:
            logger.error(f"Error fetching equity: {e}")
            return 0.0

    def get_open_positions(self) -> list:
        """Get all open futures positions."""
        try:
            positions = self.exchange.fetch_positions()
            open_positions = [
                p for p in positions
                if float(p.get("contracts", 0)) > 0
            ]
            return open_positions
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            return []

    def get_position_for_symbol(self, symbol: str) -> dict | None:
        """Get position for a specific symbol."""
        positions = self.get_open_positions()
        for pos in positions:
            if pos.get("symbol") == symbol:
                return pos
        return None

    def place_market_order(self, symbol: str, side: str, amount: float,
                           stop_loss: float = None, take_profit: float = None) -> dict | None:
        """
        Place a market order for futures.
        side: 'buy' (long) or 'sell' (short)
        amount: contract size in base currency units
        """
        try:
            params = {}

            # Set SL/TP if provided
            if stop_loss:
                params["stopLossPrice"] = stop_loss
            if take_profit:
                params["takeProfitPrice"] = take_profit

            order = self.exchange.create_market_order(
                symbol=symbol,
                side=side,
                amount=amount,
                params=params
            )
            logger.info(f"✅ Order placed: {side.upper()} {amount} {symbol}")
            return order
        except Exception as e:
            logger.error(f"❌ Order failed for {symbol}: {e}")
            return None

    def close_position(self, symbol: str, side: str, amount: float) -> dict | None:
        """Close a position by placing opposite order."""
        close_side = "sell" if side == "buy" else "buy"
        try:
            params = {"reduceOnly": True}
            order = self.exchange.create_market_order(
                symbol=symbol,
                side=close_side,
                amount=amount,
                params=params
            )
            logger.info(f"✅ Position closed: {symbol}")
            return order
        except Exception as e:
            logger.error(f"❌ Close position failed for {symbol}: {e}")
            return None

    def get_ticker_price(self, symbol: str) -> float:
        """Get current market price."""
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return float(ticker["last"])
        except Exception as e:
            logger.error(f"Error fetching ticker for {symbol}: {e}")
            return 0.0

    def get_min_order_amount(self, symbol: str) -> float:
        """Get minimum order amount for a symbol."""
        try:
            market = self.exchange.market(symbol)
            return float(market.get("limits", {}).get("amount", {}).get("min", 0.001))
        except Exception as e:
            logger.warning(f"Could not get min amount for {symbol}: {e}")
            return 0.001
