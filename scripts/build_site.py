#!/usr/bin/env python3
"""Arma _site/ envolviendo index.html en un documento HTML completo y copiando data/."""
import os, shutil

root = os.path.join(os.path.dirname(__file__), "..")
site = os.path.join(root, "_site")
shutil.rmtree(site, ignore_errors=True)
os.makedirs(site)
body = open(os.path.join(root, "index.html"), encoding="utf-8").read()
head = """<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<style>:root{color-scheme:light;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}body{margin:0;font:14px system-ui,sans-serif}img{max-width:100%}[hidden]{display:none!important}</style>
</head><body>
"""
open(os.path.join(site, "index.html"), "w", encoding="utf-8").write(head + body + "\n</body></html>\n")
if os.path.isdir(os.path.join(root, "data")):
    shutil.copytree(os.path.join(root, "data"), os.path.join(site, "data"))
print("sitio listo en", site)
