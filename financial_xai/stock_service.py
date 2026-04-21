from __future__ import annotations

import math
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

    def get_price_series(self, ticker: str, period: str = "1mo", interval: str = "1d") -> list[tuple[str, float]]:
        if self.client is None:
            raise StockDataError("yfinance is not installed.")

        symbol = ticker.upper()
        history = self.client.Ticker(symbol).history(period=period, interval=interval)
        if history.empty:
            raise StockDataError(f"No market data was returned for {symbol}.")

        close_prices = history["Close"]
        points: list[tuple[str, float]] = []
        for idx, val in close_prices.items():
            if val is None:
                continue
            try:
                fval = float(val)
            except (TypeError, ValueError):
                continue
            if not math.isfinite(fval):
                continue
            points.append((str(idx), fval))

        if len(points) < 2:
            raise StockDataError(f"Not enough market points were returned for {symbol}.")

        return points

    def build_price_chart_svg(
        self,
        ticker: str,
        *,
        period: str = "1mo",
        interval: str = "1d",
        width: int = 760,
        height: int = 260,
    ) -> str:
        points = self.get_price_series(ticker, period=period, interval=interval)
        symbol = ticker.upper()

        prices = [p for _, p in points]
        min_p = min(prices)
        max_p = max(prices)
        span = max(max_p - min_p, 1e-9)

        pad_x = 24
        pad_y = 24
        plot_w = max(width - 2 * pad_x, 1)
        plot_h = max(height - 2 * pad_y, 1)

        def x_at(i: int) -> float:
            if len(points) == 1:
                return float(pad_x + plot_w / 2)
            return float(pad_x + (i / (len(points) - 1)) * plot_w)

        def y_at(price: float) -> float:
            t = (price - min_p) / span
            return float(pad_y + (1 - t) * plot_h)

        poly = " ".join(f"{x_at(i):.2f},{y_at(price):.2f}" for i, (_, price) in enumerate(points))

        latest = prices[-1]
        color = "#66ffd1"
        bg = "#0f141b"
        grid = "rgba(255,255,255,0.08)"
        text = "rgba(255,255,255,0.78)"
        subtext = "rgba(255,255,255,0.55)"

        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img" aria-label="{symbol} price chart">'
            f"<defs>"
            f'<linearGradient id="fill" x1="0" x2="0" y1="0" y2="1">'
            f'<stop offset="0%" stop-color="{color}" stop-opacity="0.28" />'
            f'<stop offset="100%" stop-color="{color}" stop-opacity="0.02" />'
            f"</linearGradient>"
            f"</defs>"
            f'<rect x="0" y="0" width="{width}" height="{height}" rx="18" fill="{bg}" />'
            f'<line x1="{pad_x}" y1="{pad_y}" x2="{pad_x}" y2="{height - pad_y}" stroke="{grid}" />'
            f'<line x1="{pad_x}" y1="{height - pad_y}" x2="{width - pad_x}" y2="{height - pad_y}" stroke="{grid}" />'
            f'<path d="M {pad_x:.2f},{height - pad_y:.2f} L {poly} L {width - pad_x:.2f},{height - pad_y:.2f} Z" fill="url(#fill)" />'
            f'<polyline points="{poly}" fill="none" stroke="{color}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" />'
            f'<circle cx="{x_at(len(points) - 1):.2f}" cy="{y_at(latest):.2f}" r="3.6" fill="{color}" />'
            f'<text x="{pad_x}" y="{pad_y - 8}" fill="{text}" font-size="14" font-family="ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto">'
            f"{symbol} • {period} • close"
            f"</text>"
            f'<text x="{width - pad_x}" y="{pad_y - 8}" text-anchor="end" fill="{subtext}" font-size="12" '
            f'font-family="ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto">'
            f"min {min_p:.2f} / max {max_p:.2f}"
            f"</text>"
            f"</svg>"
        )
