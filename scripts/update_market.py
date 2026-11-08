#!/usr/bin/env python3
"""Baja datos públicos de mercado y escribe data/market.json.

Fuentes (todas gratuitas y sin clave):
  - ArgentinaDatos: dólar CCL histórico e inflación mensual
  - dolarapi.com:   CCL de hoy (completa el último día)
  - data912.com:    cotizaciones de CEDEARs, ONs, bonos y acciones; histórico del CEDEAR SPY
  - Nasdaq:         calendario de dividendos de acciones y ETFs de EE. UU. (no oficial; si falla,
                    el tablero sigue con la estimación por historial)

Si una fuente falla, se conserva el dato anterior y se anota el error en "status".
El script termina con código 1 si alguna fuente falló, para que GitHub avise por mail.
"""
import json, os, sys, time, datetime as dt
import urllib.request

START = "2025-01-01"          # desde cuándo guardar series históricas
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "market.json")
UA = {"User-Agent": "cartera-bot/1.0 (+github actions)"}

URL_CCL = "https://api.argentinadatos.com/v1/cotizaciones/dolares/contadoconliqui"
URL_IPC = "https://api.argentinadatos.com/v1/finanzas/indices/inflacion"
URL_CCL_HOY = "https://dolarapi.com/v1/dolares/contadoconliqui"
URL_LIVE = "https://data912.com/live/{}"
PANELS = ["arg_cedears", "arg_corp", "arg_bonds", "arg_notes", "arg_stocks"]
URL_SPY = "https://data912.com/historical/cedears/SPY"
URL_NASDAQ = "https://api.nasdaq.com/api/calendar/dividends?date={}"
NQ_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://www.nasdaq.com",
    "Referer": "https://www.nasdaq.com/",
}
DIV_BACK, DIV_AHEAD = 110, 75   # días hacia atrás (para calibrar el monto) y hacia adelante


def get(url, tries=3):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.loads(r.read().decode("utf-8-sig"))
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"{url}: {last}")


def num(x):
    try:
        v = float(x)
        return v if v == v else 0.0
    except (TypeError, ValueError):
        return 0.0


def day(s):
    return str(s)[:10]


def fetch_fx():
    rows = get(URL_CCL)
    out = {}
    for r in rows:
        d = day(r.get("fecha", ""))
        v = num(r.get("venta")) or num(r.get("compra"))
        if d >= START and v > 0:
            out[d] = v
    try:  # el CCL de hoy suele no estar en la serie histórica
        h = get(URL_CCL_HOY)
        v = num(h.get("venta"))
        d = day(h.get("fechaActualizacion") or dt.date.today().isoformat())
        if v > 0 and d > max(out):
            out[d] = v
    except Exception:  # noqa: BLE001
        pass
    if not out:
        raise RuntimeError("serie CCL vacía")
    return [[d, out[d]] for d in sorted(out)]


def fetch_ipc():
    rows = get(URL_IPC)
    out = [[day(r["fecha"]), num(r["valor"])] for r in rows if day(r.get("fecha", "")) >= START]
    out.sort()
    if not out:
        raise RuntimeError("serie de inflación vacía")
    return out


def us_date(s):
    """MM/DD/YYYY -> YYYY-MM-DD (o None)."""
    try:
        m, d, y = str(s).strip().split("/")
        return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
    except Exception:  # noqa: BLE001
        return None


def fetch_dividends(symbols):
    """Calendario de dividendos por fecha ex-dividendo, solo de los símbolos dados (CEDEARs)."""
    today = dt.date.today()
    out, ok, bad = {}, 0, 0
    for off in range(-DIV_BACK, DIV_AHEAD + 1):
        d = today + dt.timedelta(days=off)
        if d.weekday() >= 5:
            continue
        try:
            req = urllib.request.Request(URL_NASDAQ.format(d.isoformat()), headers=NQ_HEADERS)
            with urllib.request.urlopen(req, timeout=30) as r:
                j = json.loads(r.read().decode("utf-8-sig"))
            rows = ((j.get("data") or {}).get("calendar") or {}).get("rows") or []
            ok += 1
        except Exception:  # noqa: BLE001
            bad += 1
            time.sleep(1)
            continue
        for r in rows:
            r = {k.lower(): v for k, v in r.items()}
            sym = "".join(ch for ch in str(r.get("symbol", "")).upper() if ch.isalnum())
            amt = num(r.get("dividend_rate"))
            ex = us_date(r.get("dividend_ex_date")) or d.isoformat()
            if sym in symbols and amt > 0:
                out.setdefault(sym, {})[ex] = [ex, us_date(r.get("payment_date")), round(amt, 6)]
        time.sleep(0.25)
    if ok == 0 or bad > ok:
        raise RuntimeError(f"Nasdaq no respondió ({ok} ok, {bad} con error)")
    return {k: [out[k][e] for e in sorted(out[k])] for k in out}


def price_of(r):
    c = num(r.get("c"))
    if c > 0:
        return c
    b, a = num(r.get("px_bid")), num(r.get("px_ask"))
    if b > 0 and a > 0:
        return (a + b) / 2
    return b or a


def fetch_prices():
    prices, errors = {}, []
    for p in PANELS:
        try:
            for r in get(URL_LIVE.format(p)):
                sym = str(r.get("symbol", "")).upper().replace(".", "")
                v = price_of(r)
                if sym and v > 0:
                    prices[sym] = round(v, 4)
        except Exception as e:  # noqa: BLE001
            errors.append(f"{p}: {e}")
    if not prices:
        raise RuntimeError("; ".join(errors) or "sin precios")
    if errors:
        prices["__partial__"] = 0  # marca interna, se limpia abajo
        prices.pop("__partial__")
    return prices, errors


def fetch_spy(fx):
    """SPY en dólares = CEDEAR SPY en pesos / CCL del día (el split lo corrige la página)."""
    rows = get(URL_SPY)
    ds = [d for d, _ in fx]
    out, j = [], -1
    for r in sorted(rows, key=lambda r: str(r.get("date"))):
        d = day(r.get("date", ""))
        v = num(r.get("c"))
        if d < START or v <= 0:
            continue
        while j + 1 < len(ds) and ds[j + 1] <= d:
            j += 1
        if j < 0:
            continue
        out.append([d, round(v / fx[j][1], 4)])
    if not out:
        raise RuntimeError("serie SPY vacía")
    return out


TICKERS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config", "tickers.txt")
URL_HIST = "https://data912.com/historical/cedears/"
HIST_DAYS = 430


def fetch_history(tickers=None):
    """Cierres diarios en pesos de los CEDEARs de config/tickers.txt (los últimos ~14 meses)."""
    if tickers is None:
        with open(TICKERS, encoding="utf-8") as f:
            tickers = [l.strip().upper() for l in f if l.strip() and not l.lstrip().startswith("#")]
    since = (dt.date.today() - dt.timedelta(days=HIST_DAYS)).isoformat()
    out, bad = {}, []
    for tk in tickers:
        try:
            rows = get(URL_HIST + tk, tries=2)
            ser = []
            for r in sorted(rows, key=lambda r: str(r.get("date"))):
                d, v = day(r.get("date", "")), num(r.get("c"))
                if d >= since and v > 0:
                    ser.append([d, round(v, 4)])
            if len(ser) >= 20:
                out[tk] = ser
            else:
                bad.append(tk)
        except Exception:  # noqa: BLE001
            bad.append(tk)
    if not out:
        raise RuntimeError("sin histórico para ningún ticker")
    if bad:
        print("[history] sin datos: " + ", ".join(bad), file=sys.stderr)
    return out, bad


def main():
    try:
        with open(OUT, encoding="utf-8") as f:
            prev = json.load(f)
    except Exception:  # noqa: BLE001
        prev = {}
    data = {k: prev.get(k) for k in ("fx", "ipc", "prices", "spy", "dividends", "history")}
    status, failed = {}, False

    def run(name, fn, soft=False):
        nonlocal failed
        try:
            res = fn()
            status[name] = "ok"
            return res
        except Exception as e:  # noqa: BLE001
            failed = failed or not soft
            status[name] = f"error: {str(e)[:200]}"
            print(f"[{name}] {e}", file=sys.stderr)
            return None

    fx = run("fx", fetch_fx)
    if fx:
        data["fx"] = fx
    ipc = run("ipc", fetch_ipc)
    if ipc:
        data["ipc"] = ipc
    pr = run("prices", fetch_prices)
    if pr:
        data["prices"], errs = pr
        if errs:
            status["prices"] = "ok (parcial): " + " | ".join(errs)[:200]
    if data.get("fx"):
        spy = run("spy", lambda: fetch_spy(data["fx"]))
        if spy:
            data["spy"] = spy
    if data.get("prices"):
        dv = run("dividends", lambda: fetch_dividends(set(data["prices"])), soft=True)
        if dv is not None:
            data["dividends"] = dv
    hs = run("history", fetch_history, soft=True)
    if hs:
        data["history"] = hs[0]
        if hs[1]:
            status["history"] = "ok (sin datos: " + ", ".join(hs[1])[:150] + ")"
    data["updated"] = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    data["status"] = status
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    print(json.dumps(status, ensure_ascii=False))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
