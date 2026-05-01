import json
import aiohttp
import asyncio
from config.settings import OPENROUTER_API_KEY, OPENROUTER_MODEL, OPENROUTER_BASE_URL
from utils.logger import logger


class OpenRouterAI:
    """
    OpenRouter AI model integration.
    Uses LLM to analyze market conditions and validate trading signals.
    """

    def __init__(self):
        self.api_key = OPENROUTER_API_KEY
        self.model = OPENROUTER_MODEL
        self.base_url = OPENROUTER_BASE_URL
        self.enabled = bool(self.api_key)

        if not self.enabled:
            logger.warning("⚠️ OpenRouter AI disabled (missing API key)")

    def analyze_trade(self, market_data: dict) -> dict:
        """
        Send market data to AI model for analysis.
        Returns AI decision with reasoning.
        
        market_data should contain:
        - symbol, direction, price, rsi, macd_signal, supertrend_signal
        - score, atr, recent_candles (last 5 OHLCV)
        """
        if not self.enabled:
            return {
                "approved": True,
                "confidence": 0.7,
                "reasoning": "AI disabled - using indicator confluence only",
                "suggestion": "N/A"
            }

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    result = pool.submit(asyncio.run, self._async_analyze(market_data)).result()
                return result
            else:
                return loop.run_until_complete(self._async_analyze(market_data))
        except RuntimeError:
            return asyncio.run(self._async_analyze(market_data))
        except Exception as e:
            logger.error(f"AI analysis error: {e}")
            return {
                "approved": True,
                "confidence": 0.5,
                "reasoning": f"AI error: {str(e)} - falling back to indicators",
                "suggestion": "Proceed with caution"
            }

    async def _async_analyze(self, market_data: dict) -> dict:
        """Async call to OpenRouter API."""
        prompt = self._build_prompt(market_data)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://ai-trading-bot.local",
            "X-Title": "AI Trading Bot"
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": self._get_system_prompt()
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.3,
            "max_tokens": 500
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.base_url,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    if resp.status != 200:
                        error = await resp.text()
                        logger.error(f"OpenRouter API error ({resp.status}): {error}")
                        return self._fallback_response()

                    data = await resp.json()
                    content = data["choices"][0]["message"]["content"]
                    return self._parse_ai_response(content)

        except asyncio.TimeoutError:
            logger.warning("OpenRouter API timeout - using fallback")
            return self._fallback_response()
        except Exception as e:
            logger.error(f"OpenRouter request failed: {e}")
            return self._fallback_response()

    def _get_system_prompt(self) -> str:
        """System prompt for the AI trading analyst."""
        return """You are an expert crypto futures trading analyst AI. Your job is to evaluate trading signals and decide whether to approve or reject a trade.

You receive technical indicator data (RSI, MACD, SuperTrend) and market context. You must:
1. Analyze if the indicators align properly for the proposed direction
2. Consider the Risk:Reward ratio
3. Look for potential false signals or divergences
4. Give a final decision: APPROVE or REJECT

IMPORTANT: You must respond ONLY in valid JSON format with these exact fields:
{
    "decision": "APPROVE" or "REJECT",
    "confidence": 0.0 to 1.0,
    "reasoning": "Brief explanation of your analysis",
    "suggestion": "Any adjustment suggestion (e.g., tighter SL, wait for confirmation)"
}

Be conservative - only approve trades with strong confluence. Reject if:
- RSI is in neutral zone (40-60) with weak momentum
- MACD histogram is weakening against the trade direction
- SuperTrend just flipped (potential false signal)
- Market structure suggests ranging/choppy conditions"""

    def _build_prompt(self, data: dict) -> str:
        """Build analysis prompt from market data."""
        candles_str = ""
        if "recent_candles" in data:
            candles_str = "\nRecent 5 candles (O/H/L/C):\n"
            for c in data["recent_candles"]:
                candles_str += f"  {c['open']:.2f} / {c['high']:.2f} / {c['low']:.2f} / {c['close']:.2f}\n"

        prompt = f"""Analyze this trading setup:

SYMBOL: {data.get('symbol', 'N/A')}
PROPOSED DIRECTION: {data.get('direction', 'N/A')}
CURRENT PRICE: {data.get('price', 0):.4f}

INDICATORS:
- RSI (14): {data.get('rsi', 0):.2f} (Signal: {'LONG' if data.get('rsi_signal') == 1 else 'SHORT' if data.get('rsi_signal') == -1 else 'NEUTRAL'})
- MACD: {'Bullish' if data.get('macd_signal') == 1 else 'Bearish' if data.get('macd_signal') == -1 else 'Neutral'} (Signal: {'LONG' if data.get('macd_signal') == 1 else 'SHORT' if data.get('macd_signal') == -1 else 'NEUTRAL'})
- SuperTrend: {'Bullish (price above)' if data.get('supertrend_signal') == 1 else 'Bearish (price below)'}
- ATR: {data.get('atr', 0):.4f}

CONFLUENCE SCORE: {data.get('score', 0)}/3
{candles_str}
RISK MANAGEMENT:
- Stop Loss distance: {data.get('sl_distance_pct', 0):.2f}%
- Take Profit distance: {data.get('tp_distance_pct', 0):.2f}%
- Risk:Reward Ratio: 1:{data.get('rr_ratio', 0):.2f}

Should this trade be executed? Analyze and respond in JSON format."""

        return prompt

    def _parse_ai_response(self, content: str) -> dict:
        """Parse AI response JSON."""
        try:
            # Try to extract JSON from response
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            result = json.loads(content)

            approved = result.get("decision", "").upper() == "APPROVE"
            confidence = float(result.get("confidence", 0.5))
            reasoning = result.get("reasoning", "No reasoning provided")
            suggestion = result.get("suggestion", "N/A")

            logger.info(
                f"🧠 AI Decision: {'APPROVE ✅' if approved else 'REJECT ❌'} | "
                f"Confidence: {confidence:.0%} | {reasoning[:80]}"
            )

            return {
                "approved": approved,
                "confidence": confidence,
                "reasoning": reasoning,
                "suggestion": suggestion
            }

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Could not parse AI response: {e}. Content: {content[:200]}")
            return self._fallback_response()

    def _fallback_response(self) -> dict:
        """Fallback response when AI is unavailable."""
        return {
            "approved": True,
            "confidence": 0.6,
            "reasoning": "AI unavailable - using indicator confluence as fallback",
            "suggestion": "Monitor trade closely"
        }
