"""Prueba del script con respuestas simuladas (sin internet)."""
import json, os, sys, importlib.util, datetime as dt
here = os.path.dirname(__file__)
spec = importlib.util.spec_from_file_location("um", os.path.join(here, "..", "scripts", "update_market.py"))
um = importlib.util.module_from_spec(spec); spec.loader.exec_module(um)

def fake_get(url, tries=3):
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
    if "historical/cedears/SPY" in url:
        return [{"date": "2025-03-04", "c": 36000.0}, {"date": "2026-10-23", "c": 41000.0}]
    raise RuntimeError("sin red: " + url)

um.get = fake_get
um.OUT = os.path.join(os.environ["TMPDIR_T"], "market.json")
code = um.main()
d = json.load(open(um.OUT))
assert d["fx"][-1] == ["2026-10-26", 1520.0], d["fx"][-1]
assert d["prices"]["YFCLO"] == 162700.0 and d["prices"]["KO"] == 105.0
assert d["spy"][0][0] == "2025-03-04" and abs(d["spy"][0][1] - 36000 / 1014) < 1e-3
assert d["status"]["fx"] == "ok" and d["status"]["spy"] == "ok"
# arg_bonds, arg_notes y arg_stocks fallan en el mock: ok parcial y código 1 no corresponde porque hubo precios
assert d["status"]["prices"].startswith("ok (parcial)"), d["status"]
print("OK", code, d["status"]["prices"][:60])
