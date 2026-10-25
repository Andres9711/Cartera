# Cartera

Tablero de seguimiento de portfolio. Cargás el Excel de movimientos del broker y calcula posiciones, resultados realizados y no realizados, TIR, flujos y comparaciones contra SPY, dólar e inflación, en ARS y USD.

- Tus movimientos **no salen de tu navegador**. El repositorio solo contiene datos públicos de mercado.
- Los datos de mercado (dólar CCL, inflación, cotizaciones de CEDEARs, ONs y bonos, SPY) se bajan solos cada día hábil a las 19:30 (hora de Argentina) y se guardan en `data/market.json`.

## Cómo funciona

| Archivo | Qué hace |
|---|---|
| `index.html` | El tablero completo (una sola página). |
| `scripts/update_market.py` | Baja los datos de ArgentinaDatos, dolarapi y data912. Si una fuente falla, conserva el dato anterior y GitHub te avisa por mail. |
| `scripts/build_site.py` | Arma el sitio publicable. |
| `.github/workflows/actualizar.yml` | Corre todo cada día y publica en GitHub Pages. También se puede correr a mano desde la pestaña Actions (Run workflow). |
| `tests/test_update.py` | Prueba del script con respuestas simuladas. |

## Mantenimiento

- Si un día falla una fuente, mirá la pestaña Actions, paso "Bajar datos de mercado". Normalmente es un cambio de formato en una API y se arregla en `scripts/update_market.py`.
- Lo que cargues a mano en la pestaña Datos del tablero pisa lo automático.
