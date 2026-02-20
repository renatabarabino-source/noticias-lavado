import feedparser
import pandas as pd
from datetime import datetime, timedelta
import urllib.parse
from bs4 import BeautifulSoup
import os

# --- CONFIGURACIÓN ---
KEYWORDS = ['lavado de activos', 'lavado de dinero', 'prevención de lavado', 'uif', 'aml', 'procelac', 'gafi']
NEGATIVE_FILTER = ['dólar blue', 'dolar blue', 'clima', 'fútbol']
DIAS_ATRAS = 5
MAX_NOTICIAS = 10

SITES = ["lanacion.com.ar", "tn.com.ar", "infobae.com", "ambito.com", "afip.gob.ar", "argentina.gob.ar"]
OFFICIAL_FEEDS = {
    "Fiscales.gob.ar": "https://www.fiscales.gob.ar/criminalidad-economica/feed/",
    "GAFI / FATF": "https://www.fatf-gafi.org/en/publications.rss"
}

def clean_summary(text):
    if not text: return "Sin resumen disponible."
    soup = BeautifulSoup(text, "html.parser")
    return soup.get_text()[:250] + "..."

def fetch_news():
    noticias = []
    # 1. Google News para medios generales
    query = f"({' OR '.join(['site:'+s for s in SITES])}) ({' OR '.join(['\"'+k+'\"' for k in KEYWORDS])})"
    url_gn = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}+when:{DIAS_ATRAS}d&hl=es-419&gl=AR&ceid=AR:es-419"
    
    entries = feedparser.parse(url_gn).entries
    # 2. Feeds oficiales
    for name, url in OFFICIAL_FEEDS.items():
        entries += feedparser.parse(url).entries

    for entry in entries:
        title = entry.title.lower()
        if any(k in title for k in KEYWORDS) and not any(n in title for n in NEGATIVE_FILTER):
            noticias.append({
                "Fuente": entry.source.title if hasattr(entry, 'source') else "Oficial/Medios",
                "Titular": entry.title,
                "Resumen": clean_summary(entry.summary if 'summary' in entry else ""),
                "Link": entry.link,
                "Fecha": entry.get('published', 'Reciente')
            })
    
    # Ordenar y limitar a las 10 mejores
    return noticias[:MAX_NOTICIAS]

# --- GENERACIÓN DE LA PÁGINA HTML ---
data = fetch_news()
html_content = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Reporte Lavado de Activos</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/water.css@2/out/water.css">
</head>
<body>
    <h1>🗞️ Noticias Lavado de Activos</h1>
    <p>Actualizado: {datetime.now().strftime('%d/%m/%Y %H:%M')} (Últimos 5 días)</p>
    <hr>
"""

for n in data:
    html_content += f"""
    <div>
        <h3><a href="{n['Link']}" target="_blank">{n['Titular']}</a></h3>
        <small><b>{n['Fuente']}</b> | {n['Fecha']}</small>
        <p>{n['Resumen']}</p>
    </div>
    """

html_content += "</body></html>"

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_content)
