"""Prueba del script con respuestas simuladas (sin internet)."""
import json, os, sys, importlib.util, datetime as dt
here = os.path.dirname(__file__)
spec = importlib.util.spec_from_file_location("um", os.path.join(here, "..", "scripts", "update_market.py"))
um = importlib.util.module_from_spec(spec); spec.loader.exec_module(um)

def fake_get(url, tries=3, headers=None):
    if "finnhub.io" in url:
        assert headers and headers.get("X-Finnhub-Token") == "k" and "token" not in url
        if "symbol=KO" in url and "metric" in url:
            return {"metric": {"peTTM": 24.5, "roeTTM": 40.1, "dividendYieldIndicatedAnnual": 3.1, "marketCapitalization": 270000}}
        if "profile2" in url:
            return {"name": "Coca-Cola", "finnhubIndustry": "Beverages"}
        return {"metric": {}}
    if "contadoconliqui" in url and "argentinadatos" in url:
        return [{"fecha": "2025-03-0%d" % i, "compra": 1000 + i, "venta": 1010 + i, "casa": "contadoconliqui"} for i in range(1, 6)] + \
               [{"fecha": "2026-10-23", "compra": 1500, "venta": 1510, "casa": "contadoconliqui"}]
    if "dolarapi" in url:
        return {"venta": 1520, "fechaActualizacion": "2026-10-26T15:00:00.000Z"}
    if "inflacion" in url:
        return [{"fecha": "2025-03-31", "valor": 3.7}, {"fecha": "2026-09-30", "valor": 2.1}]
    if "live/arg_corp" in url:
        return json.load(open(os.environ["CORP"]))
    if "live/arg_cedears" in url:
        return [{"symbol": "SPY", "c": 41625.0, "px_bid": 0, "px_ask": 0}, {"symbol": "KO", "c": 0.0, "px_bid": 100.0, "px_ask": 110.0}]
    if "historical/cedears/KO" in url:
        b = dt.date.today() - dt.timedelta(days=40)
        return [{"date": (b + dt.timedelta(days=i)).isoformat(), "c": 100.0 + i} for i in range(30)]
    if "historical/cedears/SPY" in url:
        return [{"date": "2025-03-04", "c": 36000.0}, {"date": "2026-10-23", "c": 41000.0}]
    raise RuntimeError("sin red: " + url)

um.get = fake_get
um.fetch_dividends = lambda symbols: {"MSFT": [["2026-11-18", "2026-12-09", 0.91]]}
os.environ["FINNHUB_KEY"] = "k"; um.FH_PAUSE = 0
um.OUT = os.path.join(os.environ["TMPDIR_T"], "market.json")
code = um.main()
d = json.load(open(um.OUT))
assert d["fx"][-1] == ["2026-10-26", 1520.0], d["fx"][-1]
assert d["prices"]["YFCLO"] == 162700.0 and d["prices"]["KO"] == 105.0
assert d["spy"][0][0] == "2025-03-04" and abs(d["spy"][0][1] - 36000 / 1014) < 1e-3
assert d["dividends"]["MSFT"][0][2] == 0.91 and d["status"]["dividends"] == "ok"
assert d["status"]["fx"] == "ok" and d["status"]["spy"] == "ok"
# arg_bonds, arg_notes y arg_stocks fallan en el mock: ok parcial y código 1 no corresponde porque hubo precios
assert d["status"]["prices"].startswith("ok (parcial)"), d["status"]
assert len(d["history"]["KO"]) == 30 and d["history"]["KO"][-1][1] == 129.0 and "SPY" not in d["history"], d.get("history", {}).keys()
assert d["status"]["history"].startswith("ok"), d["status"]
assert d["fundamentals"]["KO"]["pe"] == 24.5 and d["fundamentals"]["KO"]["name"] == "Coca-Cola" and "SPY" not in d["fundamentals"], d.get("fundamentals")
print("OK", code, d["status"]["prices"][:60])
