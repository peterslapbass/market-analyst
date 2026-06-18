# 📊 Market Pulse

Dashboard de datos de mercado actualizado automáticamente con GitHub Actions y publicado en GitHub Pages.

> **Demo:** `[https://TU_USUARIO.github.io/NOMBRE_DEL_REPO/](https://peterslapbass.github.io/market-analyst/)`

![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-Automático-2088FF?logo=github-actions&logoColor=white)
![GitHub Pages](https://img.shields.io/badge/GitHub_Pages-Publicado-222?logo=github&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![License](https://img.shields.io/badge/Licencia-MIT-green)

---

## ¿Qué hace?

- Extrae precios de **19 activos** (índices, acciones, cripto, forex, materias primas) desde Yahoo Finance
- Corre automáticamente **lunes a viernes a las 17:00 hora Chile** vía GitHub Actions
- Publica los datos como archivos JSON estáticos en GitHub Pages
- Muestra un **dashboard interactivo** con precios, cambios, gráficos históricos y tabla completa

---

## Activos incluidos

| Categoría | Activos |
|---|---|
| Índices | S&P 500, NASDAQ, Dow Jones, IPSA Chile, Bovespa |
| Acciones | Apple, Microsoft, NVIDIA, Alphabet, Amazon |
| Cripto | Bitcoin, Ethereum, Solana |
| Materias primas | Oro, Petróleo WTI, Plata |
| Forex | USD/CLP, EUR/USD, USD/BRL |

---

## Estructura del proyecto

```
├── .github/
│   └── workflows/
│       └── market_pipeline.yml   # Cron + ejecución manual
├── extractors/
│   ├── base.py                   # Clase abstracta BaseExtractor
│   ├── yahoo.py                  # Yahoo Finance (principal)
│   ├── coingecko.py              # CoinGecko (cripto)
│   ├── fred.py                   # FRED - Federal Reserve
│   └── worldbank.py              # World Bank (macro)
├── docs/                         # Servido por GitHub Pages
│   ├── index.html                # Dashboard web
│   └── data/
│       ├── latest.json           # Resumen de todos los activos
│       └── history/
│           ├── AAPL.json         # Historial OHLCV por activo
│           └── *.json
├── pipeline_gh.py                # Script principal de extracción
└── requirements.txt
```

---

## Cómo desplegar

### 1. Clonar y subir a GitHub

```bash
git clone https://github.com/TU_USUARIO/market-pulse.git
cd market-pulse
git push -u origin main
```

### 2. Activar GitHub Pages

1. Ve a **Settings → Pages**
2. Source: **Deploy from a branch**
3. Branch: `main` · Folder: `/docs`
4. Clic en **Save**

La URL del dashboard aparece en esa misma página en 1-2 minutos.

### 3. (Opcional) API key de FRED

Para incluir datos macro de la Reserva Federal (tasas, VIX, inflación USA):

1. Regístrate gratis en [stlouisfed.org](https://fred.stlouisfed.org/docs/api/api_key.html)
2. Ve a **Settings → Secrets and variables → Actions → New repository secret**
3. Nombre: `FRED_API_KEY` · Valor: tu clave

### 4. Ejecutar el primer pipeline

Ve a **Actions → Market Data Pipeline → Run workflow** para obtener datos reales de inmediato.

---

## Agregar un activo nuevo

Edita `pipeline_gh.py` y agrega una línea al listado `ASSETS`:

```python
ASSETS = [
    # ...activos existentes...
    {"id": "META", "yahoo": "META", "name": "Meta", "cat": "stocks", "currency": "USD"},
]
```

En el próximo run de Actions se generará `docs/data/history/META.json` y aparecerá en el dashboard automáticamente.

> **Importante:** el campo `id` debe ser único y no contener caracteres especiales (`^`, `=`, `-`). Úsalo como nombre del archivo JSON.

---

## Formato de los datos

### `docs/data/latest.json`
Resumen de todos los activos con el precio y cambio del último día.

```json
{
  "updated_at": "2026-06-15T20:00:00Z",
  "assets": [
    {
      "id": "AAPL",
      "symbol": "AAPL",
      "name": "Apple",
      "category": "stocks",
      "currency": "USD",
      "close": 192.35,
      "change": 1.82,
      "change_pct": 0.96,
      "date": "2026-06-15",
      "volume": 58432100
    }
  ]
}
```

### `docs/data/history/{id}.json`
Historial OHLCV diario del activo (últimos 3 meses por defecto).

```json
{
  "id": "AAPL",
  "symbol": "AAPL",
  "name": "Apple",
  "history": [
    { "date": "2026-03-01", "open": 188.4, "high": 190.1, "low": 187.8, "close": 189.5, "volume": 61200000 },
    ...
  ]
}
```

---

## Fuentes de datos

| Fuente | Cobertura | API Key |
|---|---|---|
| [Yahoo Finance](https://finance.yahoo.com) | Acciones, índices, forex, futuros, cripto | No requerida |
| [CoinGecko](https://www.coingecko.com) | Precios cripto, market cap | No requerida |
| [World Bank](https://data.worldbank.org) | PIB, inflación, desempleo por país | No requerida |
| [FRED](https://fred.stlouisfed.org) | Tasas USA, VIX, CPI, spreads de crédito | Gratis |

---

## Tecnologías

- **Python 3.12** + `yfinance` + `pandas` para extracción
- **GitHub Actions** para automatización (cron diario)
- **GitHub Pages** para hosting estático gratuito
- **Chart.js** para gráficos en el dashboard
- **Vanilla JS + CSS** sin dependencias de build

---

## Licencia

MIT — libre para usar, modificar y distribuir.
