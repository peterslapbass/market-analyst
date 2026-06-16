"""
Extractor: World Bank Open Data (API pública, sin key)
Cubre: PIB, inflación, exportaciones, indicadores macroeconómicos por país
Documentación: https://datahelpdesk.worldbank.org/knowledgebase/articles/898581
"""
import time
import requests
from datetime import datetime
from .base import BaseExtractor, MarketRecord

WB_BASE = "https://api.worldbank.org/v2"

# Indicadores clave del World Bank
COMMON_WB_INDICATORS = {
    "NY.GDP.MKTP.CD":       "PIB (USD corriente)",
    "FP.CPI.TOTL.ZG":       "Inflación (% anual)",
    "BN.CAB.XOKA.CD":       "Cuenta corriente (USD)",
    "NE.EXP.GNFS.ZS":       "Exportaciones (% PIB)",
    "NE.IMP.GNFS.ZS":       "Importaciones (% PIB)",
    "GC.DOD.TOTL.GD.ZS":    "Deuda pública (% PIB)",
    "SL.UEM.TOTL.ZS":       "Desempleo (%)",
    "PA.NUS.FCRF":          "Tipo de cambio oficial",
}

# Códigos ISO de países de interés latinoamericano
LATAM_COUNTRIES = ["CL", "BR", "MX", "CO", "PE", "AR", "UY", "EC"]


class WorldBankExtractor(BaseExtractor):

    name = "world_bank"
    rate_limit_seconds = 1.0

    def extract(
        self,
        symbols: list[str],          # indicadores WB, e.g. ["NY.GDP.MKTP.CD"]
        countries: list[str] = None, # ISO-2, e.g. ["CL", "US", "BR"]; None=todos
        start_year: int = 2010,
        end_year: int = 2024,
    ) -> list[MarketRecord]:

        records: list[MarketRecord] = []
        country_filter = ";".join(countries) if countries else "all"

        for indicator in symbols:
            url = f"{WB_BASE}/country/{country_filter}/indicator/{indicator}"
            params = {
                "format": "json",
                "per_page": 1000,
                "date": f"{start_year}:{end_year}",
                "mrv": 1 if end_year == start_year else None,
            }
            # Limpiar params nulos
            params = {k: v for k, v in params.items() if v is not None}

            page = 1
            while True:
                params["page"] = page
                try:
                    resp = requests.get(url, params=params, timeout=20)
                    resp.raise_for_status()
                    raw = resp.json()

                    if not isinstance(raw, list) or len(raw) < 2:
                        break

                    meta, data = raw[0], raw[1]
                    if data is None:
                        break

                    for obs in data:
                        if obs.get("value") is None:
                            continue
                        country_code = obs.get("countryiso3code") or obs["country"]["id"]
                        symbol_key = f"{country_code}:{indicator}"
                        records.append(MarketRecord(
                            source=self.name,
                            symbol=symbol_key,
                            date=datetime(int(obs["date"]), 12, 31),  # año → dic
                            close=float(obs["value"]),
                            extra={
                                "indicator": indicator,
                                "indicator_name": COMMON_WB_INDICATORS.get(indicator, indicator),
                                "country": obs["country"]["value"],
                                "country_iso": country_code,
                                "unit": obs.get("unit", ""),
                            }
                        ))

                    total_pages = meta.get("pages", 1)
                    self.logger.info(
                        f"[WorldBank] {indicator} | página {page}/{total_pages} "
                        f"| {len(data)} obs"
                    )
                    if page >= total_pages:
                        break
                    page += 1
                    time.sleep(self.rate_limit_seconds)

                except Exception as e:
                    self.logger.error(f"[WorldBank] Error {indicator}: {e}")
                    break

        return records   # WB tiene muchos nulls; se filtran en extract


if __name__ == "__main__":
    ext = WorldBankExtractor()
    records = ext.extract(
        symbols=["FP.CPI.TOTL.ZG", "NY.GDP.MKTP.CD"],
        countries=LATAM_COUNTRIES,
        start_year=2018,
        end_year=2024,
    )
    print(f"Registros macro: {len(records)}")
    for r in records[:5]:
        print(r.to_dict())
