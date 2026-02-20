import feedparser
import pandas as pd
from datetime import datetime, timedelta
import urllib.parse
from bs4 import BeautifulSoup
import os
import socket

socket.setdefaulttimeout(20)

# --- CONFIGURACIÓN ---
# Keywords más específicas para evitar temas domésticos
KEYWORDS = ['"lavado de activos"', '"lavado de dinero"', '"prevención de lavado"', 'uif', 'aml', 'procelac', 'gafi', '"crimen económico"']
# Filtro negativo extremo contra tips de limpieza y otros ruidos
NEGATIVE_FILTER = [
    'dólar blue', 'dolar blue', 'clima', 'fútbol', 'pronóstico', 'vinagre', 'almohada', 'ropa', 
    'mancha', 'bicarbonato', 'limpiar', 'limpieza', 'jabón', 'colchón', 'secadora', 'lavadero',
    'baño', 'cocina', 'receta', 'sábana', 'pelo', 'cutis', 'autos'
]
DIAS_ATRAS = 5
MAX_NOTICIAS = 25 # Para asegurar que siempre veas más de 20

# Fuentes Argentinas
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
    noticias_finales = []
    
    # 1. Prioridad 1: Fiscales.gob.ar (Obligatorio)
    f_fiscales = feedparser.parse(OFFICIAL_FEEDS["Fiscales.gob.ar"]).entries
    for entry in f_fiscales:
        noticias_finales.append({
            "Fuente": "PROCELAC", "Titular": entry.title, "Resumen": clean_summary(entry.summary),
            "Link": entry.link, "Fecha": entry.get('published', 'Reciente'), "Tipo": "oficial", "Peso": 1
        })

    # 2. Prioridad 2: Medios Argentinos
    site_query = " OR ".join([f"site:{s}" for s in (ARG_SITES + GOV_SITES)])
    keyword_query = " OR ".join(KEYWORDS)
    full_query = f"({site_query}) ({keyword_query})"
    url_gn = f"https://news.google.com/rss/search?q={urllib.parse.quote(full_query)}+when:{DIAS_ATRAS}d&hl=es-419&gl=AR&ceid=AR:es-419"
    
    entries = feedparser.parse(url_gn).entries
    for entry in entries:
        t_low = entry.title.lower()
        if not any(n in t_low for n in NEGATIVE_FILTER):
            fuente = entry.source.title if hasattr(entry, 'source') else "Medio Argentino"
            noticias_finales.append({
                "Fuente": fuente, "Titular": entry.title, "Resumen": clean_summary(entry.summary),
                "Link": entry.link, "Fecha": entry.get('published', 'Reciente'), "Tipo": "prensa", "Peso": 2
            })

    # 3. Prioridad 3: GAFI / Internacional (solo si sobra cupo)
    f_gafi = feedparser.parse(OFFICIAL_FEEDS["GAFI / FATF"]).entries
    for entry in f_gafi:
        noticias_finales.append({
            "Fuente": "GAFI/FATF", "Titular": entry.title, "Resumen": clean_summary(entry.summary),
            "Link": entry.link, "Fecha": entry.get('published', 'Reciente'), "Tipo": "internacional", "Peso": 3
        })

    # Eliminar duplicados y ordenar por importancia (Oficiales primero)
    seen = set()
    resultado = []
    # Ordenamos por "Peso" para que PROCELAC quede arriba
    noticias_finales.sort(key=lambda x: x['Peso'])
    
    for n in noticias_finales:
        if n['Titular'] not in seen:
            resultado.append(n)
            seen.add(n['Titular'])
            
    return resultado[:MAX_NOTICIAS]

# --- GENERACIÓN DE HTML ---
data = fetch_news()
html_content = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AML News Dashboard - Credicoop</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
    <style>
        :root {{ --primary: #004a80; --accent: #2ecc71; --bg: #f4f7f9; --text: #2c3e50; }}
        body {{ font-family: 'Inter', sans-serif; background-color: var(--bg); color: var(--text); line-height: 1.6; margin: 0; padding: 0; }}
        header {{ background: var(--primary); color: white; padding: 2rem 1rem; text-align: center; }}
        .container {{ max-width: 900px; margin: 2rem auto; padding: 0 1rem; }}
        .card {{ background: white; border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem; box-shadow: 0 2px 8px rgba(0,0,0,0.05); border-left: 6px solid #d1d8e0; }}
        .card.oficial {{ border-left-color: var(--accent); background: #fafffa; }}
        .card.prensa {{ border-left-color: #3498db; }}
        .badge {{ display: inline-block; padding: 0.2rem 0.6rem; border-radius: 10px; font-size: 0.7rem; font-weight: 700; text-transform: uppercase; }}
        .badge-oficial {{ background: #e8f5e9; color: #2e7d32; }}
        .badge-prensa {{ background: #e3f2fd; color: #1565c0; }}
        h3 {{ margin: 0.5rem 0; font-size: 1.2rem; }}
        h3 a {{ color: var(--primary); text-decoration: none; font-weight: 800; }}
        .meta {{ font-size: 0.8rem; color: #7f8c8d; }}
        .summary {{ font-size: 0.9rem; margin-top: 10px; color: #444; }}
    </style>
</head>
<body>
    <header>
        <h1>🗞️ AML News Dashboard</h1>
        <p>Principales Noticias de Lavados de Activos para AML BCCL| {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
    </header>
    <div class="container">
"""

for n in data:
    badge_class = "badge-oficial" if n['Tipo'] == "oficial" else "badge-prensa"
    html_content += f"""
    <div class="card {n['Tipo']}">
        <span class="badge {badge_class}">{n['Fuente']}</span>
        <h3><a href="{n['Link']}" target="_blank">{n['Titular']}</a></h3>
        <div class="meta">{n['Fecha']}</div>
        <div class="summary">{n['Resumen']}</div>
    </div>
    """

html_content += "</div></body></html>"

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_content)
