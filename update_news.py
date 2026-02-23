import feedparser
import urllib.parse
from bs4 import BeautifulSoup
import socket
from datetime import datetime, timezone, timedelta
import requests

# Configuración técnica
socket.setdefaulttimeout(30)
tz_ar = timezone(timedelta(hours=-3))
now_ar = datetime.now(tz_ar)

# 1. DEFINICIÓN DE VARIABLES
BASE_AML = '("lavado de dinero" OR "lavado de activos" OR "blanqueo de capitales" OR "blanqueamiento")'

# 2. FILTROS DE RUIDO (Cero aguacate, deportes o limpieza)
GENERAL_NEG = [
    'dental', 'dientes', 'odontologia', 'aguacate', 'receta', 'futbol', 'clima',
    'vinagre', 'almohada', 'mancha', 'jabon', 'limpieza', 'ropa', 'suavizante',
    'lavarropas', 'pelo', 'cutis', 'dieta', 'cocina', 'alianza lima', 'via expresa'
]

# 3. FILTRO POLICIAL (Para Actualizaciones)
POLICIAL_NEG = GENERAL_NEG + ['policial', 'crimen', 'asesinato', 'robo', 'detenido', 'allanamiento', 'tiroteo']

# Portales privados (Prensa)
PORTALES_PRENSA = (
    "site:infobae.com OR site:clarin.com OR site:lanacion.com.ar OR site:pagina12.com.ar OR "
    "site:tn.com.ar OR site:perfil.com OR site:iprofesional.com OR site:ambito.com OR site:cronista.com"
)

session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0 NewsBot/BCCL'})

def clean_summary(text):
    if not text: return "Sin descripción."
    try:
        return BeautifulSoup(text, "html.parser").get_text()[:220] + "..."
    except:
        return str(text)[:220] + "..."

def fetch_news_refined(query, limit, neg_list):
    url = "https://news.google.com/rss/search?q={}&hl=es-419&gl=AR&ceid=AR:es-419".format(
        urllib.parse.quote(query + " when:5d")
    )
    try:
        resp = session.get(url, timeout=15)
        entries = feedparser.parse(resp.content).entries
    except:
        return []

    results = []
    seen_titles = set()
    for entry in entries:
        t_low = entry.title.lower()
        if entry.title not in seen_titles and not any(n in t_low for n in neg_list):
            results.append({
                "fuente": entry.source.title if hasattr(entry, 'source') else "Medio",
                "titular": entry.title.replace('"', '&quot;'),
                "link": entry.link,
                "fecha": entry.get('published', 'Reciente')[:16],
                "resumen": clean_summary(entry.summary if 'summary' in entry else "")
            })
            seen_titles.add(entry.title)
    return results[:limit]

# --- PROCESAMIENTO ---
news_noticias = fetch_news_refined(f'({BASE_AML} OR "dolar blue") AND ({PORTALES_PRENSA})', 25, GENERAL_NEG)
news_actualizaciones = fetch_category = fetch_news_refined(f'({BASE_AML}) AND ("uif" OR "bcra" OR "arca" OR "cnv" OR "normativa")', 6, POLICIAL_NEG)

# --- GENERACIÓN DE HTML ---
fecha_actual_texto = now_ar.strftime('%d/%m/%Y %H:%M')

def make_cards(news_list, color):
    if not news_list: return '<p style="text-align:center;color:#888;padding:40px;">No hay noticias nuevas.</p>'
    return "".join([
        f'<div class="card" style="border-left:6px solid {color}"><span class="badge">{n["fuente"]}</span><p style="font-size:0.7rem;color:#999">{n["fecha"]}</p><h3><a href="{n["link"]}" target="_blank">{n["titular"]}</a></h3><p>{n["resumen"]}</p></div>'
        for n in news_list
    ])

HTML_CONTENT = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AML Monitor - BCCL</title>
    <style>
        body {{ font-family: sans-serif; background: #f4f7f9; margin: 0; padding: 20px; }}
        header {{ background: #004a80; color: white; text-align: center; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; max-width: 1100px; margin: 0 auto; }}
        .card {{ background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
        .badge {{ background: #eee; padding: 2px 5px; font-size: 0.7rem; font-weight: bold; }}
        h3 a {{ text-decoration: none; color: #333; }}
        .tabs {{ display: flex; justify-content: center; margin-bottom: 20px; gap: 10px; }}
        .tab-btn {{ padding: 10px 20px; cursor: pointer; border: none; background: #ddd; font-weight: bold; }}
        .active-btn {{ background: #004a80; color: white; }}
    </style>
</head>
<body>
    <header><h1>Resumen AML 📰</h1><p>BCCL &middot; {fecha_actual_texto}</p></header>
    <div class="tabs">
        <button class="tab-btn active-btn" onclick="location.reload()">NOTICIAS</button>
    </div>
    <div class="grid">{make_cards(news_noticias, '#1a73e8')}</div>
    <h2 style="text-align:center; margin-top:40px;">ACTUALIZACIONES</h2>
    <div class="grid">{make_cards(news_actualizaciones, '#d4af37')}</div>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(HTML_CONTENT)
