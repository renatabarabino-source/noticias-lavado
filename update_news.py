import feedparser
import urllib.parse
from bs4 import BeautifulSoup
import os
import socket
from datetime import datetime
import requests

socket.setdefaulttimeout(30)

# --- CONFIGURACIÓN DE FUENTES Y FILTROS ---
BASE_AML = '("lavado de dinero" OR "lavado de activos" OR "blanqueo" OR "blanqueamiento" OR "AML")'

# Filtro estricto para evitar temas dentales o domésticos
NEGATIVE_FILTER = [
    'dental', 'dientes', 'odontología', 'aguacate', 'receta', 'fútbol', 'clima', 
    'vinagre', 'almohada', 'mancha', 'jabón', 'limpieza', 'ropa'
]

# Lista de portales privados que proporcionaste
SITES_PRIVADOS = (
    "site:infobae.com OR site:clarin.com OR site:lanacion.com.ar OR site:pagina12.com.ar OR "
    "site:minutouno.com OR site:tn.com.ar OR site:perfil.com OR site:eldestapeweb.com OR "
    "site:lapoliticaonline.com OR site:iprofesional.com OR site:ambito.com OR site:cronista.com OR "
    "site:eleconomista.com.ar OR site:baenegocios.com OR site:laprensa.com.ar OR site:eldiarioar.com"
)

SITES_INTL_PORTALS = "site:bloomberg.com OR site:reuters.com OR site:cnnespanol.cnn.com OR site:elpais.com"

# Sitios gubernamentales para la solapa Principal
SITES_GOV = "site:argentina.gob.ar OR site:bcra.gob.ar OR site:cnv.gov.ar OR site:fiscales.gob.ar"

DIAS_ATRAS = 5
MAX_NOTICIAS = 30

def clean_summary(text):
    if not text: return "Sin descripción disponible."
    soup = BeautifulSoup(text, "html.parser")
    return soup.get_text()[:240] + "..."

def fetch_category(query, is_intl=False, prioritize_keywords=None):
    gl = "US" if is_intl else "AR"
    hl = "en" if is_intl else "es-419"
    url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}+when:{DIAS_ATRAS}d&hl={hl}&gl={gl}&ceid={gl}:es-419"
    entries = feedparser.parse(url).entries
    
    news_list = []
    seen_titles = set()
    
    for entry in entries:
        t_low = entry.title.lower()
        if entry.title not in seen_titles and not any(n in t_low for n in NEGATIVE_FILTER):
            # Sistema de prioridad: calculamos un peso
            weight = 1
            if prioritize_keywords and any(k in t_low for k in prioritize_keywords):
                weight = 0 # Menor peso = más arriba en la lista
            
            news_list.append({
                "fuente": entry.source.title if hasattr(entry, 'source') else "Medio",
                "titular": entry.title,
                "link": entry.link,
                "fecha": entry.get('published', 'Reciente'),
                "resumen": clean_summary(entry.summary if 'summary' in entry else ""),
                "weight": weight
            })
            seen_titles.add(entry.title)
    
    # Ordenar por peso (prioridad arriba) y luego por fecha si es posible
    news_list.sort(key=lambda x: x['weight'])
    return news_list[:MAX_NOTICIAS]

# --- ESTRATEGIA DE BÚSQUEDA ---

# 1. PRINCIPAL (NORMATIVAS): Híbrido Gobierno + Privados
q_principal = f'({BASE_AML}) AND (({SITES_GOV}) OR (({SITES_PRIVADOS}) AND ("normativa" OR "resolución" OR "arca" OR "uif")))'
news_principal = fetch_category(q_principal)

# 2. SOLO ARGENTINA (PRENSA): Prioridad UIF, GAFI, BCRA, ARCA
keywords_pri_arg = ['uif', 'gafi', 'bcra', 'arca', 'normativa', 'regulación', 'ley']
q_solo_arg = f'{BASE_AML} AND ({SITES_PRIVADOS})'
news_solo_arg = fetch_category(q_solo_arg, prioritize_keywords=keywords_pri_arg)

# 3. SOLO INTERNACIONAL (PRENSA): Sin sitios .ar
q_solo_intl = f'{BASE_AML} AND ({SITES_INTL_PORTALS} OR "FATF" OR "FinCEN") -site:gov.ar'
news_solo_intl = fetch_category(q_solo_intl, is_intl=True)

# --- GENERACIÓN DE HTML ---
html_template = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Resumen de Noticias AML - BCCL</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&display=swap" rel="stylesheet">
    <style>
        :root {{ --p-color: #004a80; --a-color: #3498db; --i-color: #d4af37; }}
        body {{ font-family: 'Inter', sans-serif; margin: 0; background: #fdfdfd; }}
        header {{ background: var(--p-color); color: white; text-align: center; padding: 40px 20px; }}
        header h1 {{ margin: 0; font-weight: 900; font-size: 2.2rem; }}
        header p {{ margin: 10px 0 0; font-weight: 700; font-size: 1.2rem; opacity: 0.9; }}
        .tabs {{ display: flex; justify-content: center; background: #fff; position: sticky; top: 0; z-index: 100; box-shadow: 0 2px 10px rgba(0,0,0,0.1); overflow-x: auto; }}
        .tab-btn {{ padding: 15px 20px; border: none; background: none; cursor: pointer; font-weight: 700; font-size: 0.85rem; color: #666; transition: 0.3s; border-bottom: 4px solid transparent; white-space: nowrap; }}
        .tab-btn.active {{ color: var(--p-color); border-bottom-color: var(--p-color); }}
        .page {{ display: none; padding: 30px 15px; min-height: 80vh; }}
        .page.active {{ display: block; }}
        #principal {{ background: linear-gradient(rgba(255,255,255,0.94), rgba(255,255,255,0.94)), url('https://images.unsplash.com/photo-1554224155-1696413575b3?auto=format&fit=crop&w=1920&q=80'); background-size: cover; background-attachment: fixed; }}
        #solo_arg {{ background: linear-gradient(rgba(240,248,255,0.94), rgba(240,248,255,0.94)), url('https://images.unsplash.com/photo-1571171637578-41bc2dd41cd2?auto=format&fit=crop&w=1920&q=80'); background-size: cover; }}
        #solo_intl {{ background: linear-gradient(rgba(255,252,240,0.94), rgba(255,252,240,0.94)), url('https://images.unsplash.com/photo-1436491865332-7a61a109c0f2?auto=format&fit=crop&w=1920&q=80'); background-size: cover; }}
        .grid {{ max-width: 1100px; margin: 0 auto; display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 20px; }}
        .card {{ background: white; border-radius: 12px; padding: 20px; box-shadow: 0 5px 15px rgba(0,0,0,0.08); border-left: 6px solid #ddd; }}
        .priority {{ border-left-color: #e74c3c !important; background: #fff9f9; }}
        #principal .card {{ border-left-color: var(--p-color); }}
        #solo_arg .card {{ border-left-color: var(--a-color); }}
        #solo_intl .card {{ border-left-color: var(--i-color); }}
        .badge {{ display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 0.65rem; font-weight: 800; text-transform: uppercase; margin-bottom: 12px; background: #eee; color: #444; }}
        h3 {{ margin: 0 0 12px; font-size: 1.15rem; line-height: 1.35; font-weight: 800; }}
        h3 a {{ text-decoration: none; color: #1a1a1a; }}
        .desc {{ font-size: 0.9rem; color: #555; line-height: 1.5; }}
    </style>
</head>
<body>
    <header>
        <h1>Resumen de Noticias 📰</h1>
        <p>Para AML BCCL 💵📈</p>
    </header>
    <div class="tabs">
        <button class="tab-btn active" onclick="showTab('principal')">PRINCIPAL (MIX)</button>
        <button class="tab-btn" onclick="showTab('solo_arg')">SOLO ARG (PRENSA)</button>
        <button class="tab-btn" onclick="showTab('solo_intl')">SOLO INT (PRENSA)</button>
    </div>
    <div id="principal" class="page active"><div class="grid">{''.join([f'<div class="card"><span class="badge">{n["fuente"]}</span><h3><a href="{n["link"]}" target="_blank">{n["titular"]}</a></h3><p class="desc">{n["resumen"]}</p></div>' for n in news_principal])}</div></div>
    <div id="solo_arg" class="page"><div class="grid">{''.join([f'<div class="card {"priority" if n["weight"]==0 else ""}"><span class="badge">{n["fuente"]}</span><h3><a href="{n["link"]}" target="_blank">{n["titular"]}</a></h3><p class="desc">{n["resumen"]}</p></div>' for n in news_solo_arg])}</div></div>
    <div id="solo_intl" class="page"><div class="grid">{''.join([f'<div class="card"><span class="badge">{n["fuente"]}</span><h3><a href="{n["link"]}" target="_blank">{n["titular"]}</a></h3><p class="desc">{n["resumen"]}</p></div>' for n in news_solo_intl])}</div></div>
    <script>
        function showTab(tabId) {{
            document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.getElementById(tabId).classList.add('active');
            event.currentTarget.classList.add('active');
        }}
    </script>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_template)
