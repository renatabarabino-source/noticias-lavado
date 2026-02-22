import feedparser
import urllib.parse
from bs4 import BeautifulSoup
import os
import socket
from datetime import datetime
import requests

# Timeout estricto de 8 segundos por sitio para no colgar el proceso
socket.setdefaulttimeout(8)

# --- CONFIGURACIÓN DE FUENTES ---
BASE_AML = '("lavado de dinero" OR "lavado de activos" OR "blanqueo" OR "blanqueamiento" OR "AML")'

# Filtro negativo reforzado (Cero odontología y cero limpieza)
NEGATIVE_FILTER = [
    'dental', 'dientes', 'odontología', 'aguacate', 'receta', 'fútbol', 'clima', 
    'vinagre', 'almohada', 'mancha', 'jabón', 'limpieza', 'ropa', 'suavizante'
]

# Agrupamos portales para optimizar la consulta de Google
PORTALES_PRESS = (
    "site:cronista.com OR site:ambito.com OR site:iprofesional.com OR site:infobae.com OR "
    "site:lanacion.com.ar OR site:clarin.com OR site:tn.com.ar OR site:perfil.com OR "
    "site:baenegocios.com OR site:eldiarioar.com OR site:pagina12.com.ar OR site:reuters.com"
)

SITES_GOV = "site:argentina.gob.ar OR site:bcra.gob.ar OR site:cnv.gov.ar OR site:fiscales.gob.ar"

DIAS_ATRAS = 5
MAX_NOTICIAS = 30

# Usamos una sesión para que las peticiones sean más rápidas
session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) NewsBot/1.0'})

def clean_summary(text):
    if not text: return "Sin descripción disponible."
    soup = BeautifulSoup(text, "html.parser")
    return soup.get_text()[:240] + "..."

def fetch_category(query, is_intl=False, prioritize=False):
    gl = "US" if is_intl else "AR"
    hl = "en" if is_intl else "es-419"
    url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}+when:{DIAS_ATRAS}d&hl={hl}&gl={gl}&ceid={gl}:es-419"
    
    try:
        # Petición ultra rápida con la sesión
        response = session.get(url, timeout=8)
        entries = feedparser.parse(response.content).entries
    except:
        return []

    news_list = []
    seen_titles = set()
    
    # Palabras clave de alta prioridad para BCCL
    keywords_pri = ['uif', 'gafi', 'bcra', 'arca', 'normativa', 'resolución', 'ley', 'cnv']

    for entry in entries:
        t_low = entry.title.lower()
        if entry.title not in seen_titles and not any(n in t_low for n in NEGATIVE_FILTER):
            weight = 1
            if prioritize and any(k in t_low for k in keywords_pri):
                weight = 0 # Prioridad máxima
            
            news_list.append({
                "fuente": entry.source.title if hasattr(entry, 'source') else "Medio",
                "titular": entry.title,
                "link": entry.link,
                "resumen": clean_summary(entry.summary if 'summary' in entry else ""),
                "weight": weight
            })
            seen_titles.add(entry.title)
    
    news_list.sort(key=lambda x: x['weight'])
    return news_list[:MAX_NOTICIAS]

# --- EJECUCIÓN ---
# 1. PRINCIPAL: Foco en ARCA, CNV, BCRA y UIF
q_principal = f'({BASE_AML}) AND (({SITES_GOV}) OR (({PORTALES_PRESS}) AND ("normativa" OR "resolución" OR "arca" OR "uif" OR "cnv")))'
news_principal = fetch_category(q_principal, prioritize=True)

# 2. ARGENTINA: Prensa con Dólar Blue (solo si es por lavado)
q_solo_arg = f'({BASE_AML} OR "dólar blue") AND "lavado" AND ({PORTALES_PRESS})'
news_solo_arg = fetch_category(q_solo_arg, prioritize=True)

# 3. INTERNACIONAL: Medios globales (Bloomberg, Reuters, El País)
q_solo_intl = f'({BASE_AML}) AND (site:bloomberg.com OR site:reuters.com OR site:elpais.com OR "FATF") -site:gov.ar'
news_solo_intl = fetch_category(q_solo_intl, is_intl=True)

# --- GENERACIÓN DE HTML ---
# Usamos doble llave {{ }} para que el CSS no rompa el f-string de Python
html_template = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Dashboard AML - BCCL</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&display=swap" rel="stylesheet">
    <style>
        :root {{ --p-color: #004a80; --a-color: #3498db; --i-color: #d4af37; }}
        body {{ font-family: 'Inter', sans-serif; margin: 0; background: #fdfdfd; }}
        header {{ background: var(--p-color); color: white; text-align: center; padding: 40px 20px; }}
        .tabs {{ display: flex; justify-content: center; background: #fff; position: sticky; top: 0; z-index: 100; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .tab-btn {{ padding: 15px 20px; border: none; background: none; cursor: pointer; font-weight: 700; font-size: 0.85rem; color: #666; border-bottom: 4px solid transparent; }}
        .tab-btn.active {{ color: var(--p-color); border-bottom-color: var(--p-color); }}
        .page {{ display: none; padding: 30px 15px; min-height: 80vh; }}
        .page.active {{ display: block; }}
        .grid {{ max-width: 1100px; margin: 0 auto; display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 20px; }}
        .card {{ background: white; border-radius: 12px; padding: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.06); border-left: 6px solid #ddd; }}
        .priority {{ border-left-color: #e74c3c !important; background: #fffcfc; }}
        #principal .card {{ border-left-color: var(--p-color); }}
        #solo_arg .card {{ border-left-color: var(--a-color); }}
        #solo_intl .card {{ border-left-color: var(--i-color); }}
        .badge {{ display: inline-block; padding: 3px 7px; border-radius: 4px; font-size: 0.65rem; font-weight: 800; background: #f0f2f5; margin-bottom: 10px; }}
        h3 {{ margin: 0 0 10px; font-size: 1.1rem; font-weight: 800; }}
        h3 a {{ text-decoration: none; color: #1a1a1a; }}
        .desc {{ font-size: 0.85rem; color: #555; line-height: 1.5; }}
        
        /* Fondos temáticos con transparencia alta para lectura */
        #principal {{ background: linear-gradient(rgba(255,255,255,0.95), rgba(255,255,255,0.95)), url('https://images.unsplash.com/photo-1554224155-1696413575b3?w=800'); background-size: cover; }}
        #solo_arg {{ background: linear-gradient(rgba(240,248,255,0.95), rgba(240,248,255,0.95)), url('https://images.unsplash.com/photo-1571171637578-41bc2dd41cd2?w=800'); background-size: cover; }}
        #solo_intl {{ background: linear-gradient(rgba(255,252,240,0.95), rgba(255,252,240,0.95)), url('https://images.unsplash.com/photo-1436491865332-7a61a109c0f2?w=800'); background-size: cover; }}
    </style>
</head>
<body>
    <header>
        <h1>Resumen de Noticias 📰</h1>
        <p>Para AML BCCL 💵📈</p>
        <small>Última actualización: {datetime.now().strftime('%d/%m/%Y %H:%M')}</small>
    </header>
    <div class="tabs">
        <button class="tab-btn active" onclick="showTab('principal')">PRINCIPAL (MIX)</button>
        <button class="tab-btn" onclick="showTab('solo_arg')">ARGENTINA (PRENSA)</button>
        <button class="tab-btn" onclick="showTab('solo_intl')">INTERNACIONAL (PRENSA)</button>
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
            window.scrollTo(0,0);
        }}
    </script>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_template)
