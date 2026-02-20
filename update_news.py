import feedparser
import pandas as pd
from datetime import datetime, timedelta
import urllib.parse
from bs4 import BeautifulSoup
import os
import socket # <--- AGREGAMOS ESTA LIBRERÍA

# Forzamos un límite de tiempo de 15 segundos para que no se cuelgue
socket.setdefaulttimeout(15) 

# --- CONFIGURACIÓN ---
# (El resto del código dejalo todo igual)


# --- CONFIGURACIÓN ---
KEYWORDS = ['lavado de activos', 'lavado de dinero', 'prevención de lavado', 'uif', 'aml', 'procelac', 'gafi']
# Excluimos "dólar blue" por política de cumplimiento
NEGATIVE_FILTER = ['dólar blue', 'dolar blue', 'clima', 'fútbol', 'pronóstico']
DIAS_ATRAS = 5
MAX_NOTICIAS = 25

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
    
    # 1. Búsqueda en Medios Argentinos
    all_arg = ARG_SITES + GOV_SITES
    site_query = " OR ".join([f"site:{s}" for s in all_arg])
    # Construcción segura para evitar errores de sintaxis en GitHub Actions
    kw_parts = ['"' + k + '"' for k in KEYWORDS]
    keyword_query = " OR ".join(kw_parts)
    full_query = f"({site_query}) ({keyword_query})"
    
    url_gn = f"https://news.google.com/rss/search?q={urllib.parse.quote(full_query)}+when:{DIAS_ATRAS}d&hl=es-419&gl=AR&ceid=AR:es-419"
    entries = feedparser.parse(url_gn).entries

    # 2. Feeds Oficiales Directos (Prioridad)
    f_fiscales = feedparser.parse(OFFICIAL_FEEDS["Fiscales.gob.ar"]).entries
    f_gafi = feedparser.parse(OFFICIAL_FEEDS["GAFI / FATF"]).entries

    # Procesar Fiscales primero para asegurar presencia
    for entry in f_fiscales:
        noticias_finales.append({
            "Fuente": "PROCELAC", 
            "Titular": entry.title, 
            "Resumen": clean_summary(entry.summary if 'summary' in entry else ""), 
            "Link": entry.link, 
            "Fecha": entry.get('published', 'Reciente'), 
            "Tipo": "oficial"
        })

    # Procesar Prensa Argentina
    for entry in entries:
        if not any(n in entry.title.lower() for n in NEGATIVE_FILTER):
            fuente = entry.source.title if hasattr(entry, 'source') else "Medio Argentino"
            noticias_finales.append({
                "Fuente": fuente, 
                "Titular": entry.title, 
                "Resumen": clean_summary(entry.summary if 'summary' in entry else ""), 
                "Link": entry.link, 
                "Fecha": entry.get('published', 'Reciente'), 
                "Tipo": "prensa"
            })

    # Procesar Internacionales (GAFI)
    for entry in f_gafi:
        noticias_finales.append({
            "Fuente": "GAFI/FATF", 
            "Titular": entry.title, 
            "Resumen": clean_summary(entry.summary if 'summary' in entry else ""), 
            "Link": entry.link, 
            "Fecha": entry.get('published', 'Reciente'), 
            "Tipo": "internacional"
        })

    # Eliminar duplicados por título y limitar a lo que pediste
    seen = set()
    return [n for n in noticias_finales if not (n['Titular'] in seen or seen.add(n['Titular']))][:MAX_NOTICIAS]

# --- GENERACIÓN DE HTML (Dashboard Premium) ---
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
        header {{ background: var(--primary); color: white; padding: 2rem 1rem; text-align: center; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
        header h1 {{ margin: 0; font-weight: 800; letter-spacing: -1px; }}
        .container {{ max-width: 900px; margin: 2rem auto; padding: 0 1rem; }}
        .card {{ background: white; border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem; box-shadow: 0 2px 8px rgba(0,0,0,0.05); transition: transform 0.2s; border-left: 6px solid #d1d8e0; }}
        .card:hover {{ transform: translateY(-3px); box-shadow: 0 4px 15px rgba(0,0,0,0.1); }}
        .card.oficial {{ border-left-color: var(--accent); }}
        .card.prensa {{ border-left-color: #3498db; }}
        .badge {{ display: inline-block; padding: 0.25rem 0.75rem; border-radius: 20px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; margin-bottom: 0.5rem; }}
        .badge-oficial {{ background: #e8f5e9; color: #2e7d32; }}
        .badge-prensa {{ background: #e3f2fd; color: #1565c0; }}
        h3 {{ margin: 0.5rem 0; font-size: 1.25rem; }}
        h3 a {{ color: var(--primary); text-decoration: none; }}
        .meta {{ font-size: 0.85rem; color: #7f8c8d; margin-bottom: 1rem; }}
        .summary {{ font-size: 0.95rem; color: #576574; }}
        footer {{ text-align: center; padding: 2rem; color: #95a5a6; font-size: 0.8rem; }}
    </style>
</head>
<body>
    <header>
        <h1>🗞️ AML News Dashboard</h1>
        <p>Inteligencia Financiera para el Banco Credicoop | {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
    </header>
    <div class="container">
"""

for n in data:
    badge_class = f"badge-{n['Tipo']}" if n['Tipo'] in ['oficial', 'prensa'] else "badge-prensa"
    html_content += f"""
    <div class="card {n['Tipo']}">
        <span class="badge {badge_class}">{n['Fuente']}</span>
        <h3><a href="{n['Link']}" target="_blank">{n['Titular']}</a></h3>
        <div class="meta">Publicado: {n['Fecha']}</div>
        <div class="summary">{n['Resumen']}</div>
    </div>
    """

html_content += """
    </div>
    <footer>
        Actualizado automáticamente cada mañana. Fuente: PROCELAC, GAFI y Medios Nacionales.
    </footer>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_content)
