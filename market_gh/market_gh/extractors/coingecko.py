"""
Extractor: CoinGecko (API pública gratuita, sin key)
Cubre: criptomonedas — precios, market cap, volumen, dominancia BTC
"""
import time
import requests
from datetime import datetime, timezone
from .base import BaseExtractor, MarketRecord

COINGECKO_BASE = "https://api.coingecko.com/api/v3"


class CoinGeckoExtractor(BaseExtractor):

    name = "coingecko"
    rate_limit_seconds = 1.5      # CoinGecko free tier: ~30 req/min

    # Mapa de símbolos comunes → IDs de CoinGecko
    COIN_ID_MAP = {
        "BTC":   "bitcoin",
        "ETH":   "ethereum",
        "BNB":   "binancecoin",
        "SOL":   "solana",
        "USDT":  "tether",
        "XRP":   "ripple",
        "ADA":   "cardano",
        "AVAX":  "avalanche-2",
        "DOGE":  "dogecoin",
        "DOT":   "polkadot",
    }

    def _resolve_id(self, symbol: str) -> str:
        """Convierte ticker (BTC) a ID de CoinGecko (bitcoin)."""
        return self.COIN_ID_MAP.get(symbol.upper(), symbol.lower())

    def extract(
        self,
        symbols: list[str],          # tickers como "BTC", "ETH" o IDs directos
        vs_currency: str = "usd",
        days: int = 30,              # 1, 7, 14, 30, 90, 180, 365, max
    ) -> list[MarketRecord]:

        records: list[MarketRecord] = []

        for symbol in symbols:
            coin_id = self._resolve_id(symbol)
            url = f"{COINGECKO_BASE}/coins/{coin_id}/market_chart"
            params = {"vs_currency": vs_currency, "days": days}

            try:
                resp = requests.get(url, params=params, timeout=15)
                resp.raise_for_status()
                data = resp.json()

                prices     = {int(ts): p   for ts, p   in data.get("prices", [])}
                market_cap = {int(ts): mc  for ts, mc  in data.get("market_caps", [])}
                volumes    = {int(ts): v   for ts, v   in data.get("total_volumes", [])}

                for ts_ms, price in prices.items():
                    dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
                    records.append(MarketRecord(
                        source=self.name,
                        symbol=symbol.upper(),
                        date=dt,
                        close=price,
                        volume=volumes.get(ts_ms),
                        extra={
                            "market_cap": market_cap.get(ts_ms),
                            "vs_currency": vs_currency,
                            "coin_id": coin_id,
                        }
                    ))

                self.logger.info(f"[CoinGecko] {symbol}: {len(prices)} puntos")
                time.sleep(self.rate_limit_seconds)

            except requests.HTTPError as e:
                status = e.response.status_code if e.response else "?"
                if status == 429:
                    self.logger.warning(f"[CoinGecko] Rate limit en {symbol}, esperando 60s")
                    time.sleep(60)
                else:
                    self.logger.error(f"[CoinGecko] HTTP {status} en {symbol}: {e}")
            except Exception as e:
                self.logger.error(f"[CoinGecko] Error {symbol}: {e}")

        return self.validate(records)

    def get_top_coins(self, n: int = 20, vs_currency: str = "usd") -> list[dict]:
        """Lista los top-N coins por market cap (útil para descubrimiento)."""
        url = f"{COINGECKO_BASE}/coins/markets"
        params = {
            "vs_currency": vs_currency,
            "order": "market_cap_desc",
            "per_page": n,
            "page": 1,
        }
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()


if __name__ == "__main__":
    ext = CoinGeckoExtractor()
    records = ext.extract(["BTC", "ETH", "SOL"], days=7)
    print(f"Registros cripto: {len(records)}")
    for r in records[:3]:
        print(r.to_dict())
