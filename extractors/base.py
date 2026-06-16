"""
Base class para todos los extractores de mercado.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)


@dataclass
class MarketRecord:
    """Registro normalizado de dato de mercado."""
    source: str
    symbol: str
    date: datetime
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    volume: Optional[float] = None
    extra: dict = field(default_factory=dict)

    def to_dict(self):
        return {
            "source": self.source,
            "symbol": self.symbol,
            "date": self.date.isoformat() if isinstance(self.date, datetime) else str(self.date),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            **self.extra,
        }


class BaseExtractor(ABC):
    """Extractor base que deben implementar todas las fuentes."""

    name: str = "base"
    rate_limit_seconds: float = 1.0   # pausa mínima entre requests

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def extract(self, symbols: list[str], **kwargs) -> list[MarketRecord]:
        """Extrae datos para los símbolos indicados."""
        ...

    def validate(self, records: list[MarketRecord]) -> list[MarketRecord]:
        """Filtra registros con close nulo o negativo."""
        valid = [r for r in records if r.close is not None and r.close > 0]
        dropped = len(records) - len(valid)
        if dropped:
            self.logger.warning(f"Se descartaron {dropped} registros inválidos.")
        return valid
