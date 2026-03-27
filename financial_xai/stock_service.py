from __future__ import annotations

from typing import Any

try:
    import yfinance as yf
except ImportError:  # pragma: no cover - handled at runtime
    yf = None


class StockDataError(RuntimeError):
    pass


class StockDataService:
    def __init__(self) -> None:
        self.client = yf

    def get_stock_snapshot(self, ticker: str) -> dict[str, Any]:
        if self.client is None:
            raise StockDataError("yfinance is not installed.")

        symbol = ticker.upper()
        history = self.client.Ticker(symbol).history(period="5d")
        if history.empty:
            raise StockDataError(f"No market data was returned for {symbol}.")

        close_prices = history["Close"]
        latest_price = float(close_prices.iloc[-1])
        previous_price = float(close_prices.iloc[-2]) if len(close_prices) > 1 else latest_price
        first_price = float(close_prices.iloc[0])
        daily_change = latest_price - previous_price
        daily_change_pct = (daily_change / previous_price * 100) if previous_price else 0.0

        if latest_price > first_price:
            trend = "uptrend"
        elif latest_price < first_price:
            trend = "downtrend"
        else:
            trend = "sideways"

        spread = max(float(close_prices.max()) - float(close_prices.min()), 0.0)
        volatility = spread / latest_price * 100 if latest_price else 0.0
        if volatility >= 5:
            risk_level = "high"
        elif volatility >= 2:
            risk_level = "medium"
        else:
            risk_level = "low"

        as_of = str(history.index[-1])
        return {
            "ticker": symbol,
            "price": round(latest_price, 2),
            "daily_change": round(daily_change, 2),
            "daily_change_pct": round(daily_change_pct, 2),
            "trend": trend,
            "risk_level": risk_level,
            "as_of": as_of,
        }
