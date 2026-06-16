"""
pipeline_gh.py — Pipeline optimizado para GitHub Actions + GitHub Pages.

Diferencias vs pipeline.py:
  - No usa DuckDB (no se puede persistir entre runs de GH Actions)
  - Exporta JSON a docs/data/ (servidos por GitHub Pages)
  - Genera docs/data/latest.json  → resumen de todos los activos
  - Genera docs/data/history/{id}.json → historial OHLCV por activo
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))


class _NumpyEncoder(json.JSONEncoder):
    """Convierte tipos numpy/pandas a tipos nativos de Python antes de serializar."""
    def default(self, obj):
        import numpy as np
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        return super().default(obj)

from extractors.yahoo import YahooFinanceExtractor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("pipeline_gh")

# ── Configuración de activos ───────────────────────────────────────────────────
# Cada activo: id (nombre de archivo seguro), yahoo_symbol, name, category, currency

ASSETS = [
    # Índices
    {"id": "GSPC",   "yahoo": "^GSPC",    "name": "S&P 500",       "cat": "indices",    "currency": "USD"},
    {"id": "IXIC",   "yahoo": "^IXIC",    "name": "NASDAQ",         "cat": "indices",    "currency": "USD"},
    {"id": "DJI",    "yahoo": "^DJI",     "name": "Dow Jones",      "cat": "indices",    "currency": "USD"},
    {"id": "IPSA",   "yahoo": "^IPSA",    "name": "IPSA Chile",     "cat": "indices",    "currency": "CLP"},
    {"id": "BVSP",   "yahoo": "^BVSP",    "name": "Bovespa",        "cat": "indices",    "currency": "BRL"},
    # Acciones
    {"id": "AAPL",   "yahoo": "AAPL",     "name": "Apple",          "cat": "stocks",     "currency": "USD"},
    {"id": "MSFT",   "yahoo": "MSFT",     "name": "Microsoft",      "cat": "stocks",     "currency": "USD"},
    {"id": "NVDA",   "yahoo": "NVDA",     "name": "NVIDIA",         "cat": "stocks",     "currency": "USD"},
    {"id": "GOOGL",  "yahoo": "GOOGL",    "name": "Alphabet",       "cat": "stocks",     "currency": "USD"},
    {"id": "AMZN",   "yahoo": "AMZN",     "name": "Amazon",         "cat": "stocks",     "currency": "USD"},
    # Cripto
    {"id": "BTC",    "yahoo": "BTC-USD",  "name": "Bitcoin",        "cat": "crypto",     "currency": "USD"},
    {"id": "ETH",    "yahoo": "ETH-USD",  "name": "Ethereum",       "cat": "crypto",     "currency": "USD"},
    {"id": "SOL",    "yahoo": "SOL-USD",  "name": "Solana",         "cat": "crypto",     "currency": "USD"},
    # Materias primas
    {"id": "GCF",    "yahoo": "GC=F",     "name": "Oro",            "cat": "commodities","currency": "USD"},
    {"id": "CLF",    "yahoo": "CL=F",     "name": "Petróleo WTI",   "cat": "commodities","currency": "USD"},
    {"id": "SIF",    "yahoo": "SI=F",     "name": "Plata",          "cat": "commodities","currency": "USD"},
    {"id": "COP",    "yahoo": "HG=F",     "name": "Cobre",           "cat": "commoditines","currency": "USD"},
    # Forex
    {"id": "CLPX",   "yahoo": "CLP=X",   "name": "USD/CLP",        "cat": "forex",      "currency": "CLP"},
    {"id": "EURUSD", "yahoo": "EURUSD=X", "name": "EUR/USD",        "cat": "forex",      "currency": "USD"},
    {"id": "USDBRL", "yahoo": "USDBRL=X", "name": "USD/BRL",        "cat": "forex",      "currency": "BRL"},
]

DOCS_DIR    = Path(__file__).parent / "docs"
DATA_DIR    = DOCS_DIR / "data"
HISTORY_DIR = DATA_DIR / "history"


def setup_dirs():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)


def extract_all(period: str = "3mo") -> dict[str, pd.DataFrame]:
    """Extrae datos de Yahoo Finance para todos los activos. Devuelve {id: DataFrame}."""
    ext = YahooFinanceExtractor()
    yahoo_symbols = [a["yahoo"] for a in ASSETS]

    logger.info(f"Extrayendo {len(yahoo_symbols)} símbolos | período={period}")
    records = ext.extract(yahoo_symbols, period=period, interval="1d")

    # Agrupar por símbolo yahoo → id de activo
    yahoo_to_id = {a["yahoo"]: a["id"] for a in ASSETS}
    dataframes: dict[str, pd.DataFrame] = {}

    for record in records:
        asset_id = yahoo_to_id.get(record.symbol)
        if not asset_id:
            continue
        row = {
            "date":   record.date.strftime("%Y-%m-%d") if hasattr(record.date, "strftime") else str(record.date)[:10],
            "open":   round(record.open,  4) if record.open   is not None else None,
            "high":   round(record.high,  4) if record.high   is not None else None,
            "low":    round(record.low,   4) if record.low    is not None else None,
            "close":  round(record.close, 4),
            "volume": int(record.volume)  if record.volume is not None else None,
        }
        if asset_id not in dataframes:
            dataframes[asset_id] = []
        dataframes[asset_id].append(row)

    # Convertir a DataFrame y ordenar por fecha
    result = {}
    for aid, rows in dataframes.items():
        df = pd.DataFrame(rows).sort_values("date").drop_duplicates("date")
        result[aid] = df

    return result


def compute_change(df: pd.DataFrame) -> tuple[float, float]:
    """Devuelve (change_abs, change_pct) comparando los últimos dos cierres."""
    if len(df) < 2:
        return 0.0, 0.0
    last  = df["close"].iloc[-1]
    prev  = df["close"].iloc[-2]
    delta = last - prev
    pct   = (delta / prev * 100) if prev else 0.0
    return round(delta, 4), round(pct, 4)


def save_history(asset_id: str, asset_meta: dict, df: pd.DataFrame):
    """Guarda docs/data/history/{id}.json con el historial OHLCV."""
    path = HISTORY_DIR / f"{asset_id}.json"
    payload = {
        "id":       asset_id,
        "symbol":   asset_meta["yahoo"],
        "name":     asset_meta["name"],
        "category": asset_meta["cat"],
        "currency": asset_meta["currency"],
        "history":  df.to_dict(orient="records"),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, cls=_NumpyEncoder), encoding="utf-8")
    logger.info(f"  Guardado {path.name}  ({len(df)} puntos)")


def save_latest(asset_summaries: list[dict]):
    """Guarda docs/data/latest.json con resumen de todos los activos."""
    path = DATA_DIR / "latest.json"
    payload = {
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "assets": asset_summaries,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, cls=_NumpyEncoder), encoding="utf-8")
    logger.info(f"Guardado latest.json — {len(asset_summaries)} activos")


def run(period: str = "3mo"):
    setup_dirs()
    start = datetime.now()

    # 1. Extraer
    dataframes = extract_all(period)
    logger.info(f"Activos con datos: {len(dataframes)}/{len(ASSETS)}")

    # 2. Guardar historial y construir resumen
    asset_meta_map = {a["id"]: a for a in ASSETS}
    summaries = []

    for asset in ASSETS:
        aid = asset["id"]
        df  = dataframes.get(aid)

        if df is None or df.empty:
            logger.warning(f"Sin datos para {aid} ({asset['yahoo']})")
            summaries.append({
                "id": aid, "symbol": asset["yahoo"], "name": asset["name"],
                "category": asset["cat"], "currency": asset["currency"],
                "close": None, "change": None, "change_pct": None, "date": None,
            })
            continue

        # Guardar historial
        save_history(aid, asset, df)

        # Calcular cambio
        change, change_pct = compute_change(df)
        last_row = df.iloc[-1]

        summaries.append({
            "id":         aid,
            "symbol":     asset["yahoo"],
            "name":       asset["name"],
            "category":   asset["cat"],
            "currency":   asset["currency"],
            "close":      last_row["close"],
            "change":     change,
            "change_pct": change_pct,
            "date":       last_row["date"],
            "volume":     last_row["volume"],
        })

    # 3. Guardar resumen
    save_latest(summaries)

    elapsed = (datetime.now() - start).total_seconds()
    success  = sum(1 for s in summaries if s["close"] is not None)
    logger.info(f"\nPipeline completado en {elapsed:.1f}s | {success}/{len(ASSETS)} activos OK")


if __name__ == "__main__":
    period = os.getenv("PIPELINE_PERIOD", "3mo")
    if len(sys.argv) > 1:
        period = sys.argv[1]
    run(period)
