"""
Extractor: Yahoo Finance  (vía yfinance — sin API key)
Cubre: acciones, ETFs, índices, forex, cripto, materias primas
"""
import time
from datetime import datetime, timedelta
from typing import Optional
import yfinance as yf
from .base import BaseExtractor, MarketRecord


class YahooFinanceExtractor(BaseExtractor):

    name = "yahoo_finance"
    rate_limit_seconds = 0.5

    def extract(
        self,
        symbols: list[str],
        period: str = "1mo",        # 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, max
        interval: str = "1d",       # 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> list[MarketRecord]:

        records: list[MarketRecord] = []

        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)

                if start and end:
                    df = ticker.history(start=start, end=end, interval=interval)
                else:
                    df = ticker.history(period=period, interval=interval)

                if df.empty:
                    self.logger.warning(f"Sin datos para {symbol}")
                    continue

                for ts, row in df.iterrows():
                    records.append(MarketRecord(
                        source=self.name,
                        symbol=symbol,
                        date=ts.to_pydatetime() if hasattr(ts, "to_pydatetime") else datetime.fromisoformat(str(ts)),
                        open=row.get("Open"),
                        high=row.get("High"),
                        low=row.get("Low"),
                        close=row.get("Close"),
                        volume=row.get("Volume"),
                        extra={
                            "dividends": row.get("Dividends", 0),
                            "stock_splits": row.get("Stock Splits", 0),
                        }
                    ))

                self.logger.info(f"[Yahoo] {symbol}: {len(df)} filas extraídas")
                time.sleep(self.rate_limit_seconds)

            except Exception as e:
                self.logger.error(f"[Yahoo] Error con {symbol}: {e}")

        return self.validate(records)


# ── Ejemplo de uso ────────────────────────────────────────────
if __name__ == "__main__":
    ext = YahooFinanceExtractor()

    symbols = [
        "AAPL",     # Apple (acción)
        "^GSPC",    # S&P 500 (índice)
        "BTC-USD",  # Bitcoin (cripto)
        "GC=F",     # Oro (futuro)
        "CLP=X",    # USD/CLP (forex Chile)
    ]

    records = ext.extract(symbols, period="5d", interval="1d")
    print(f"\nTotal registros: {len(records)}")
    for r in records[:5]:
        print(r.to_dict())
