import feedparser
import urllib.parse
from bs4 import BeautifulSoup
import os
import socket
from datetime import datetime
import requests

socket.setdefaulttimeout(30)

# --- CONFIGURACIÓN DE SEGURIDAD Y FILTROS ---
# Filtro extremo para que NO aparezcan aguacates ni limpieza
NEGATIVE_FILTER = [
    'aguacate', 'salud', 'receta', 'dieta', 'fútbol', 'pronóstico', 'clima', 'vinagre', 
    'almohada', 'mancha', 'jabón', 'limpieza', 'lavarropas', 'ropa', 'tintorería', 
    'suavizante', 'cloro', 'bicarbonato', 'pelo', 'cutis', 'comida', 'cocina'
]

DIAS_ATRAS = 5
MAX_NOTICIAS = 30

def get_image(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        img = soup.find("meta", property="og:image") or soup.find("meta", property="twitter:image")
        return img.get("content") or img.get("href") if img else ""
    except:
        return ""

def clean_summary(text):
    if not text: return "Sin descripción disponible."
    soup = BeautifulSoup(text, "html.parser")
    return soup.get_text()[:220] + "..."

def fetch_category(query, is_intl=False):
    gl = "US" if is_intl else "AR"
    hl = "en" if is_intl else "es-419"
    url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}+when:{DIAS_ATRAS}d&hl={hl}&gl={gl}&ceid={gl}:es-419"
    entries = feedparser.parse(url).entries
    
    news_list = []
    for entry in entries:
        t_low = entry.title.lower()
        if not any(n in t_low for n in NEGATIVE_FILTER):
            news_list.append({
                "fuente": entry.source.title if hasattr(entry, 'source') else "Medio",
                "titular": entry.title,
                "link": entry.link,
                "fecha": entry.get('published', 'Reciente'),
                "resumen": clean_summary(entry.summary if 'summary' in entry else ""),
                "img": get_image(entry.link)
            })
    return news_list[:MAX_NOTICIAS]

# --- ESTRATEGIA DE BÚSQUEDA PROFESIONAL ---
# 1. PRINCIPAL (NORMATIVAS): UIF, ARCA, BCRA, CNV, GAFI
q_principal = '("lavado de activos" OR "lavado de dinero") AND (UIF OR BCRA OR ARCA OR CNV OR GAFI OR "resolución" OR "blanqueo")'
news_principal = fetch_category(q_principal)

# 2. ARGENTINA (ESCÁNDALOS): Justicia, Dólar Blue (si es por lavado), PROCELAC
q_argentina = '("lavado de dinero" OR "lavado de activos") AND ("dólar blue" OR "cueva" OR "justicia" OR "corrupción" OR "imputado")'
news_argentina = fetch_category(q_argentina)

# 3. INTERNACIONAL: Global AML, FATF, FinCEN
q_intl = '("money laundering" OR "lavado de activos") AND (FATF OR "Interpol" OR "compliance" OR "global") -ARCA -UIF -BCRA'
news_intl = fetch_category(q_intl, is_intl=True)

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
        body {{ font-family: 'Inter', sans-serif; margin: 0; background: #fdfdfd; overflow-x: hidden; }}
        header {{ background: var(--p-color); color: white; text-align: center; padding: 45px 20px; }}
        header h1 {{ margin: 0; font-weight: 900; font-size: 2.3rem; }}
        header p {{ margin: 10px 0 0; font-weight: 700; font-size: 1.3rem; opacity: 0.9; }}

        /* TABS ESTILO MODERNO */
        .tabs {{ display: flex; justify-content: center; background: #fff; position: sticky; top: 0; z-index: 100; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .tab-btn {{ padding: 18px 25px; border: none; background: none; cursor: pointer; font-weight: 700; font-size: 0.9rem; color: #666; border-bottom: 4px solid transparent; transition: 0.3s; }}
        .tab-btn.active {{ color: var(--p-color); border-bottom-color: var(--p-color); }}

        .page {{ display: none; padding: 40px 15px; min-height: 80vh; }}
        .page.active {{ display: block; }}
        
        /* DISEÑOS DE FONDO POR SOLAPA */
        #principal {{ 
            background: linear-gradient(rgba(255,255,255,0.92), rgba(255,255,255,0.92)), url('https://images.unsplash.com/photo-1554224155-1696413575b3?auto=format&fit=crop&w=1920&q=80'); 
            background-size: cover; background-attachment: fixed;
        }}
        #argentina {{ 
            background: linear-gradient(rgba(240,248,255,0.93), rgba(240,248,255,0.93)), url('https://images.unsplash.com/photo-1571171637578-41bc2dd41cd2?auto=format&fit=crop&w=1920&q=80'); 
            background-size: cover; background-attachment: fixed;
        }}
        #international {{ 
            background: linear-gradient(rgba(255,252,240,0.93), rgba(255,252,240,0.93)), url('https://images.unsplash.com/photo-1436491865332-7a61a109c0f2?auto=format&fit=crop&w=1920&q=80'); 
            background-size: cover; background-attachment: fixed;
        }}

        .grid {{ max-width: 1150px; margin: 0 auto; display: grid; grid-template-columns: repeat(auto-fill, minmax(330px, 1fr)); gap: 25px; }}
        
        /* CARD ESTILO JEKYLL */
        .card {{ background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 8px 20px rgba(0,0,0,0.06); transition: 0.3s; display: flex; flex-direction: column; border: 1px solid #eee; }}
        .card:hover {{ transform: translateY(-8px); box-shadow: 0 12px 30px rgba(0,0,0,0.12); }}
        .card img {{ width: 100%; height: 210px; object-fit: cover; background: #f0f0f0; }}
        .card-content {{ padding: 22px; flex-grow: 1; }}
        .badge {{ display: inline-block; padding: 4px 10px; border-radius: 5px; font-size: 0.7rem; font-weight: 800; text-transform: uppercase; margin-bottom: 12px; background: #e3f2fd; color: #004a80; }}
        
        h3 {{ margin: 0 0 12px; font-size: 1.2rem; line-height: 1.4; font-weight: 800; }}
        h3 a {{ text-decoration: none; color: #111; }}
        .desc {{ font-size: 0.92rem; color: #444; line-height: 1.6; }}
    </style>
</head>
<body>
    <header>
        <h1>Resumen de Noticias 📰</h1>
        <p>Para AML BCCL 💵📈</p>
    </header>

    <div class="tabs">
        <button class="tab-btn active" onclick="showTab('principal')">PRINCIPAL (NORMATIVAS)</button>
        <button class="tab-btn" onclick="showTab('argentina')">ARGENTINA</button>
        <button class="tab-btn" onclick="showTab('international')">INTERNACIONAL</button>
    </div>

    <div id="principal" class="page active">
        <div class="grid">
            {''.join([f'<div class="card">{"<img src="+n["img"]+">" if n["img"] else ""}<div class="card-content"><span class="badge">{n["fuente"]}</span><h3><a href="{n["link"]}" target="_blank">{n["titular"]}</a></h3><p class="desc">{n["resumen"]}</p></div></div>' for n in news_principal])}
        </div>
    </div>
    
    <div id="argentina" class="page">
        <div class="grid">
            {''.join([f'<div class="card">{"<img src="+n["img"]+">" if n["img"] else ""}<div class="card-content"><span class="badge" style="background:#fff3e0;color:#e65100">{n["fuente"]}</span><h3><a href="{n["link"]}" target="_blank">{n["titular"]}</a></h3><p class="desc">{n["resumen"]}</p></div></div>' for n in news_argentina])}
        </div>
    </div>
    
    <div id="international" class="page">
        <div class="grid">
            {''.join([f'<div class="card">{"<img src="+n["img"]+">" if n["img"] else ""}<div class="card-content"><span class="badge" style="background:#f5f5f5;color:#424242">{n["fuente"]}</span><h3><a href="{n["link"]}" target="_blank">{n["titular"]}</a></h3><p class="desc">{n["resumen"]}</p></div></div>' for n in news_intl])}
        </div>
    </div>

    <script>
        function showTab(tabId) {{
            document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.getElementById(tabId).classList.add('active');
            event.currentTarget.classList.add('active');
            window.scrollTo(0, 0);
        }}
    </script>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_template)
