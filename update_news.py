import feedparser
import pandas as pd
from datetime import datetime, timedelta
import urllib.parse
from bs4 import BeautifulSoup
import os

# --- CONFIGURACIÓN ---
KEYWORDS = ['lavado de activos', 'lavado de dinero', 'prevención de lavado', 'uif', 'aml', 'procelac', 'gafi']
# Excluimos "dólar blue" por pedido del usuario
NEGATIVE_FILTER = ['dólar blue', 'dolar blue', 'clima', 'fútbol', 'pronóstico']
DIAS_ATRAS = 5
MAX_NOTICIAS = 25 # Pediste al menos 20, ponemos un margen

# Fuentes priorizadas (Argentinas)
ARG_SITES = ["lanacion.com.ar", "tn.com.ar", "infobae.com", "ambito.com", "perfil.com", "pagina12.com.ar"]
GOV_SITES = ["afip.gob.ar", "argentina.gob.ar", "cnv.gov.ar"]

OFFICIAL_FEEDS = {
    "Fiscales.gob.ar": "https://www.fiscales.gob.ar/criminalidad-economica/feed/",
    "GAFI / FATF": "https://www.fatf-gafi.org/en/publications.rss"
}

def clean_summary(text):
    if not text: return "Sin resumen disponible."
    soup = BeautifulSoup(text, "html.parser")
    return soup.get_text()[:300] + "..."

def fetch_news():
    noticias_argentinas = []
    noticias_internacionales = []
    noticias_fiscales = []
    noticias_gafi = []

    # 1. Búsqueda en Medios Argentinos y Gobierno vía Google News
    all_arg = ARG_SITES + GOV_SITES
    site_query = " OR ".join([f"site:{s}" for s in all_arg])
    keyword_query = " OR ".join(['"' + k + '"' for k in KEYWORDS])
    full_query = f"({site_query}) ({keyword_query})"
    
    url_gn_arg = f"https://news.google.com/rss/search?q={urllib.parse.quote(full_query)}+when:{DIAS_ATRAS}d&hl=es-419&gl=AR&ceid=AR:es-419"
    entries_arg = feedparser.parse(url_gn_arg).entries

    # 2. Búsqueda Internacional (para ver qué se repite)
    int_query = f"({keyword_query}) -site:ar"
    url_gn_int = f"https://news.google.com/rss/search?q={urllib.parse.quote(int_query)}+when:{DIAS_ATRAS}d&hl=es&gl=US&ceid=US:es"
    entries_int = feedparser.parse(url_gn_int).entries

    # 3. Feeds Oficiales Directos
    f_fiscales = feedparser.parse(OFFICIAL_FEEDS["Fiscales.gob.ar"]).entries
    f_gafi = feedparser.parse(OFFICIAL_FEEDS["GAFI / FATF"]).entries

    # Procesar Fiscales (Prioridad Máxima)
    for entry in f_fiscales:
        noticias_fiscales.append({
            "Fuente": "Fiscales.gob.ar (Oficial)",
            "Titular": entry.title,
            "Resumen": clean_summary(entry.summary if 'summary' in entry else ""),
            "Link": entry.link,
            "Fecha": entry.get('published', 'Reciente'),
            "Prioridad": 1
        })

    # Procesar Argentinas
    for entry in entries_arg:
        if not any(n in entry.title.lower() for n in NEGATIVE_FILTER):
            noticias_argentinas.append({
                "Fuente": entry.source.title if hasattr(entry, 'source') else "Medio Argentino",
                "Titular": entry.title,
                "Resumen": clean_summary(entry.summary if 'summary' in entry else ""),
                "Link": entry.link,
                "Fecha": entry.get('published', 'Reciente'),
                "Prioridad": 2
            })

    # Procesar GAFI e Internacionales
    for entry in f_gafi:
        noticias_gafi.append({
            "Fuente": "GAFI / FATF (Oficial)",
            "Titular": entry.title,
            "Resumen": clean_summary(entry.summary if 'summary' in entry else ""),
            "Link": entry.link,
            "Fecha": entry.get('published', 'Reciente'),
            "Prioridad": 3
        })

    for entry in entries_int[:10]: # Solo las más relevantes internacionales
        if not any(n in entry.title.lower() for n in NEGATIVE_FILTER):
            noticias_internacionales.append({
                "Fuente": entry.source.title if hasattr(entry, 'source') else "Internacional",
                "Titular": entry.title,
                "Resumen": clean_summary(entry.summary if 'summary' in entry else ""),
                "Link": entry.link,
                "Fecha": entry.get('published', 'Reciente'),
                "Prioridad": 4
            })

    # Combinar asegurando variedad y el cupo de 20
    # Ponemos fiscales primero, luego argentinas, luego el resto
    resultado = noticias_fiscales + noticias_argentinas + noticias_gafi + noticias_internacionales
    
    # Eliminamos duplicados por título
    seen = set()
    final_list = []
    for n in resultado:
        if n['Titular'] not in seen:
            final_list.append(n)
            seen.add(n['Titular'])

    return final_list[:MAX_NOTICIAS]

# --- GENERACIÓN DE LA PÁGINA HTML ---
data = fetch_news()
html_content = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Reporte Profesional AML - Lavado de Activos</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/water.css@2/out/water.css">
    <style>
        .oficial {{ border-left: 5px solid #2ecc71; background: #fafffa; padding-left: 15px; }}
        .argentina {{ border-left: 5px solid #3498db; padding-left: 15px; }}
        .internacional {{ border-left: 5px solid #95a5a6; padding-left: 15px; }}
        small {{ color: #7f8c8d; }}
        h3 {{ margin-bottom: 5px; }}
    </style>
</head>
<body>
    <h1>🗞️ Reporte de Lavado de Activos</h1>
    <p><b>Análisis para:</b> Banco Credicoop | <b>Actualizado:</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
    <p style="font-size: 0.8em; color: #666;">Fuentes: Fiscales, GAFI, Medios Nacionales e Internacionales (Últimos 5 días).</p>
    <hr>
"""

for n in data:
    clase = "argentina"
    if "Oficial" in n['Fuente']: clase = "oficial"
    if n['Prioridad'] == 4: clase = "internacional"
    
    html_content += f"""
    <div class="{clase}" style="margin-bottom: 25px;">
        <h3><a href="{n['Link']}" target="_blank">{n['Titular']}</a></h3>
        <small><b>Fuente:</b> {n['Fuente']} | <b>Fecha:</b> {n['Fecha']}</small>
        <p>{n['Resumen']}</p>
    </div>
    """

if len(data) < 1:
    html_content += "<p>No se encontraron noticias relevantes en los últimos 5 días.</p>"

html_content += "</body></html>"

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_content)
