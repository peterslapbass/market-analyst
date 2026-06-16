"""
Extractor: FRED — Federal Reserve Economic Data
API gratuita (requiere key, registro gratis en fred.stlouisfed.org)
Cubre: tasas de interés, CPI, PIB, desempleo, M2, spreads de crédito, etc.
"""
import os
import time
import requests
from datetime import datetime
from .base import BaseExtractor, MarketRecord

FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"

# Series FRED más útiles para mercados
COMMON_FRED_SERIES = {
    "DFF":      "Fed Funds Rate",
    "DGS10":    "Treasury 10Y Yield",
    "DGS2":     "Treasury 2Y Yield",
    "T10Y2Y":   "Yield Curve Spread (10y-2y)",
    "CPIAUCSL": "CPI (inflación USA)",
    "UNRATE":   "Tasa de desempleo USA",
    "M2SL":     "Masa monetaria M2",
    "VIXCLS":   "VIX (volatilidad de mercado)",
    "BAMLH0A0HYM2": "High Yield Spread",
}


class FREDExtractor(BaseExtractor):

    name = "fred"
    rate_limit_seconds = 0.5

    def __init__(self, api_key: str = ""):
        super().__init__()
        # Acepta clave vía argumento o variable de entorno
        self.api_key = api_key or os.getenv("FRED_API_KEY", "")
        if not self.api_key:
            self.logger.warning(
                "FRED_API_KEY no configurada. "
                "Regístrate gratis en https://fred.stlouisfed.org/docs/api/api_key.html"
            )

    def extract(
        self,
        symbols: list[str],          # series FRED, e.g. ["DFF", "VIXCLS"]
        start: str = "2020-01-01",
        end: str = "",               # vacío = hoy
        frequency: str = "",         # d=daily, w=weekly, m=monthly (vacío=nativa)
    ) -> list[MarketRecord]:

        records: list[MarketRecord] = []

        for series_id in symbols:
            params = {
                "series_id": series_id,
                "api_key": self.api_key,
                "file_type": "json",
                "observation_start": start,
                "sort_order": "asc",
            }
            if end:
                params["observation_end"] = end
            if frequency:
                params["frequency"] = frequency

            try:
                resp = requests.get(FRED_BASE, params=params, timeout=15)
                resp.raise_for_status()
                data = resp.json()

                for obs in data.get("observations", []):
                    value_str = obs.get("value", ".")
                    if value_str == ".":    # FRED usa "." para datos faltantes
                        continue
                    records.append(MarketRecord(
                        source=self.name,
                        symbol=series_id,
                        date=datetime.strptime(obs["date"], "%Y-%m-%d"),
                        close=float(value_str),
                        extra={"description": COMMON_FRED_SERIES.get(series_id, series_id)}
                    ))

                self.logger.info(
                    f"[FRED] {series_id}: {len(data.get('observations', []))} observaciones"
                )
                time.sleep(self.rate_limit_seconds)

            except requests.HTTPError as e:
                self.logger.error(f"[FRED] HTTP error {series_id}: {e}")
            except Exception as e:
                self.logger.error(f"[FRED] Error {series_id}: {e}")

        return self.validate(records)


if __name__ == "__main__":
    # Sin API key el request fallará, pero muestra la estructura
    ext = FREDExtractor(api_key="TU_KEY_AQUI")
    series = ["DFF", "VIXCLS", "T10Y2Y"]
    records = ext.extract(series, start="2024-01-01")
    print(f"Registros: {len(records)}")
    for r in records[:3]:
        print(r.to_dict())
