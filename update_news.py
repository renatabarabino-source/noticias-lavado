import feedparser
import urllib.parse
from bs4 import BeautifulSoup
import os
import socket
from datetime import datetime
import requests

socket.setdefaulttimeout(10)

# --- CONFIGURACIÓN DE FUENTES Y FILTROS ---
BASE_AML = '("lavado de dinero" OR "lavado de activos" OR "blanqueo" OR "blanqueamiento" OR "AML")'

# Filtro general: Cero odontología, vegetación o limpieza
GENERAL_NEG = ['dental', 'dientes', 'odontología', 'aguacate', 'receta', 'fútbol', 'clima', 'vinagre', 'limpieza']

# Filtro específico para ACTUALIZACIONES: Cero policiales
ACTUALIZACION_NEG = GENERAL_NEG + ['policial', 'crimen', 'asesinato', 'robo', 'detenido', 'allanamiento', 'tiroteo']

# Tu lista completa de portales privados (Prensa)
PORTALES_PRENSA = (
    "site:infobae.com OR site:clarin.com OR site:lanacion.com.ar OR site:pagina12.com.ar OR "
    "site:minutouno.com OR site:tn.com.ar OR site:perfil.com OR site:eldestapeweb.com OR "
    "site:lapoliticaonline.com OR site:iprofesional.com OR site:ambito.com OR site:cronista.com OR "
    "site:eleconomista.com.ar OR site:baenegocios.com OR site:reuters.com OR site:bloomberg.com OR "
    "site:eldiarioar.com OR site:prensaobrera.com OR site:gacetamercantil.com OR site:apertura.com OR "
    "site:cnnespanol.cnn.com OR site:elpais.com"
)

DIAS_ATRAS = 5
session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) NewsBot/BCCL'})

def clean_text(text):
    if not text: return "Sin descripción."
    return BeautifulSoup(text, "html.parser").get_text()[:220] + "..."

def fetch_category(query, limit, negative_keywords):
    url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}+when:{DIAS_ATRAS}d&hl=es-419&gl=AR&ceid=AR:es-419"
    try:
        response = session.get(url, timeout=10)
        entries = feedparser.parse(response.content).entries
    except:
        return []

    news_list = []
    seen_titles = set()
    for entry in entries:
        t_low = entry.title.lower()
        if len(entry.title) < 15 or entry.link.count('/') < 4:
            continue
        if entry.title not in seen_titles and not any(n in t_low for n in negative_keywords):
            news_list.append({
                "fuente": entry.source.title if hasattr(entry, 'source') else "Medio",
                "titular": entry.title,
                "link": entry.link,
                "resumen": clean_text(entry.summary if 'summary' in entry else "")
            })
            seen_titles.add(entry.title)
    return news_list[:limit]

# --- EJECUCIÓN DE LAS 2 SOLAPAS (ORden Solicitado) ---

# 1. NOTICIAS (Prensa): Tope 25 noticias
q_noticias = f'({BASE_AML} OR "dólar blue") AND ("lavado" OR "blanqueo") AND ({PORTALES_PRENSA})'
news_noticias = fetch_category(q_noticias, limit=25, negative_keywords=GENERAL_NEG)

# 2. ACTUALIZACIONES (Normativas): Solo portales privados, sin Policiales. Tope 6
q_actualizaciones = f'({BASE_AML}) AND ({PORTALES_PRENSA}) AND ("normativa" OR "resolución" OR "arca" OR "uif" OR "gafi" OR "cnv" OR "bcra" OR "ley")'
news_actualizaciones = fetch_category(q_actualizaciones, limit=6, negative_keywords=ACTUALIZACION_NEG)

# --- GENERACIÓN DE HTML (OPTIMIZADO PARA WEB/CELU) ---
html_template = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Resumen de Noticias AML - BCCL</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&display=swap" rel="stylesheet">
    <style>
        :root {{ --p-color: #004a80; --a-color: #3498db; }}
        body {{ font-family: 'Inter', sans-serif; margin: 0; background: #fdfdfd; color: #333; }}
        header {{ background: var(--p-color); color: white; text-align: center; padding: 30px 10px; }}
        header h1 {{ margin: 0; font-size: 1.8rem; font-weight: 900; }}
        header p {{ margin: 5px 0; font-weight: 700; opacity: 0.9; }}
        
        .tabs {{ display: flex; justify-content: center; background: #fff; position: sticky; top: 0; z-index: 100; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .tab-btn {{ padding: 15px 25px; border: none; background: none; cursor: pointer; font-weight: 700; font-size: 0.9rem; color: #666; border-bottom: 4px solid transparent; transition: 0.3s; }}
        .tab-btn.active {{ color: var(--p-color); border-bottom-color: var(--p-color); }}

        .page {{ display: none; padding: 20px 10px; min-height: 80vh; }}
        .page.active {{ display: block; }}
        
        #noticias {{ background: linear-gradient(rgba(240,248,255,0.95), rgba(240,248,255,0.95)), url('https://images.unsplash.com/photo-1571171637578-41bc2dd41cd2?w=800'); background-size: cover; background-attachment: fixed; }}
        #actualizaciones {{ background: linear-gradient(rgba(255,255,255,0.95), rgba(255,255,255,0.95)), url('https://images.unsplash.com/photo-1554224155-1696413575b3?w=800'); background-size: cover; }}

        .grid {{ max-width: 1100px; margin: 0 auto; display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 15px; }}
        .card {{ background: white; border-radius: 10px; padding: 15px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); border-left: 5px solid #ddd; }}
        #noticias .card {{ border-left-color: var(--a-color); }}
        #actualizaciones .card {{ border-left-color: var(--p-color); }}
        
        .badge {{ display: inline-block; padding: 3px 6px; border-radius: 4px; font-size: 0.6rem; font-weight: 800; background: #f0f2f5; margin-bottom: 8px; text-transform: uppercase; }}
        h3 {{ margin: 0 0 8px; font-size: 1.05rem; font-weight: 800; line-height: 1.3; }}
        h3 a {{ text-decoration: none; color: #111; }}
        .desc {{ font-size: 0.85rem; color: #555; }}

        @media (max-width: 600px) {{
            header h1 {{ font-size: 1.4rem; }}
            .tab-btn {{ padding: 12px 10px; font-size: 0.8rem; }}
        }}
    </style>
</head>
<body>
    <header>
        <h1>Resumen de Noticias 📰</h1>
        <p>Para AML BCCL 💵📈</p>
    </header>
    <div class="tabs">
        <button class="tab-btn active" onclick="showTab('noticias')">NOTICIAS</button>
        <button class="tab-btn" onclick="showTab('actualizaciones')">ACTUALIZACIONES</button>
    </div>
    
    <div id="noticias" class="page active"><div class="grid">{''.join([f'<div class="card"><span class="badge">{n["fuente"]}</span><h3><a href="{n["link"]}" target="_blank">{n["titular"]}</a></h3><p class="desc">{n["resumen"]}</p></div>' for n in news_noticias])}</div></div>
    
    <div id="actualizaciones" class="page"><div class="grid">{''.join([f'<div class="card"><span class="badge">{n["fuente"]}</span><h3><a href="{n["link"]}" target="_blank">{n["titular"]}</a></h3><p class="desc">{n["resumen"]}</p></div>' for n in news_actualizaciones])}</div></div>

    <script>
        function showTab(tabId) {{
            document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.getElementById(tabId).classList.add('active');
            event.currentTarget.classList.add('active');
            window.scrollTo(0,0);
        }}
    </script>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_template)
