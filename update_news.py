import feedparser
import urllib.parse
from bs4 import BeautifulSoup
import os
import socket
from datetime import datetime, timedelta, timezone
import requests

# Configuración de red para evitar bloqueos
socket.setdefaulttimeout(15)

# --- CONFIGURACIÓN DE BÚSQUEDA Y FILTROS ---
BASE_AML = '("lavado de dinero" OR "lavado de activos" OR "blanqueo" OR "blanqueamiento" OR "AML")'

# Filtros para evitar temas dentales, de salud o limpieza
NEGATIVE_FILTER = [
    'dental', 'dientes', 'odontologia', 'aguacate', 'receta', 'futbol', 'clima', 
    'vinagre', 'almohada', 'mancha', 'jabon', 'limpieza', 'ropa', 'suavizante', 
    'lavarropas', 'pelo', 'cutis', 'dieta', 'cocina'
]

# Filtro extra para ACTUALIZACIONES: Cero noticias policiales
POLICIAL_FILTER = NEGATIVE_FILTER + [
    'policial', 'crimen', 'asesinato', 'robo', 'detenido', 'allanamiento', 
    'tiroteo', 'narco', 'banda', 'sicario', 'muerto', 'tragedia'
]

# Lista consolidada de portales privados solicitada
SITES_PRIVADOS = (
    "site:infobae.com OR site:clarin.com OR site:lanacion.com.ar OR site:pagina12.com.ar OR "
    "site:minutouno.com OR site:tn.com.ar OR site:perfil.com OR site:eldestapeweb.com OR "
    "site:lapoliticaonline.com OR site:iprofesional.com OR site:ambito.com OR site:cronista.com OR "
    "site:eleconomista.com.ar OR site:baenegocios.com OR site:reuters.com OR site:bloomberg.com OR "
    "site:eldiarioar.com OR site:prensaobrera.com OR site:gacetamercantil.com OR site:apertura.com OR "
    "site:cnnespanol.cnn.com OR site:elpais.com"
)

DIAS_ATRAS = 5
session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0 NewsBot/BCCL'})

def clean_text(text):
    if not text: return "Sin descripción disponible."
    try:
        return BeautifulSoup(text, "html.parser").get_text()[:240] + "..."
    except:
        return str(text)[:240] + "..."

def fetch_category(query, limit, negative_keywords):
    # Forzamos la búsqueda en Argentina
    url = "https://news.google.com/rss/search?q={}&hl=es-419&gl=AR&ceid=AR:es-419".format(
        urllib.parse.quote(query + " when:{}d".format(DIAS_ATRAS))
    )
    try:
        response = session.get(url, timeout=12)
        entries = feedparser.parse(response.content).entries
    except:
        return []

    news_list = []
    seen_titles = set()
    for entry in entries:
        t_low = entry.title.lower()
        # Filtro de links vacíos y palabras prohibidas
        if len(entry.title) < 15 or entry.link.count('/') < 4:
            continue
        if entry.title not in seen_titles and not any(n in t_low for n in negative_keywords):
            news_list.append({
                "fuente": entry.source.title if hasattr(entry, 'source') else "Medio",
                "titular": entry.title.replace('"', '&quot;'),
                "link": entry.link,
                "resumen": clean_text(entry.summary if 'summary' in entry else "")
            })
            seen_titles.add(entry.title)
    return news_list[:limit]

# --- PROCESAMIENTO DE LAS 2 SOLAPAS ---

# 1. NOTICIAS (Prensa General): Tope 25
q_noticias = '({} OR "dolar blue") AND ("lavado" OR "blanqueo") AND ({})'.format(BASE_AML, SITES_PRIVADOS)
news_noticias = fetch_category(q_noticias, limit=25, negative_keywords=NEGATIVE_FILTER)

# 2. ACTUALIZACIONES (Normativas): Solo portales privados, SIN policiales. Tope 6
q_actualizaciones = '({}) AND ({}) AND ("normativa" OR "resolucion" OR "arca" OR "uif" OR "gafi" OR "cnv" OR "bcra" OR "ley")'.format(BASE_AML, SITES_PRIVADOS)
news_actualizaciones = fetch_category(q_actualizaciones, limit=6, negative_keywords=POLICIAL_FILTER)

# --- GENERACIÓN DEL HTML ---
fecha_actual = datetime.now(timezone(timedelta(hours=-3))).strftime('%d/%m/%Y %H:%M')

html_template = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Resumen AML - BCCL</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&display=swap" rel="stylesheet">
    <style>
        :root {{ --azul: #004a80; --dorado: #d4af37; --celeste: #1a73e8; }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: 'Inter', sans-serif; background: #f2f4f7; color: #1a1a1a; }}
        header {{ background: var(--azul); color: white; text-align: center; padding: 35px 20px; border-bottom: 4px solid var(--dorado); }}
        header h1 {{ font-size: 1.8rem; font-weight: 900; }}
        header p {{ font-size: 0.9rem; opacity: 0.8; margin-top: 5px; }}
        .tabs {{ display: flex; justify-content: center; background: #fff; position: sticky; top: 0; z-index: 100; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .tab-btn {{ padding: 15px 25px; border: none; background: none; cursor: pointer; font-weight: 700; font-size: 0.85rem; color: #666; border-bottom: 4px solid transparent; transition: 0.3s; text-transform: uppercase; }}
        .tab-btn.active {{ color: var(--azul); border-bottom-color: var(--azul); }}
        .page {{ display: none; padding: 25px 15px; min-height: 80vh; }}
        .page.active {{ display: block; }}
        #noticias {{ background: linear-gradient(rgba(240,248,255,0.95), rgba(240,248,255,0.95)), url('https://images.unsplash.com/photo-1571171637578-41bc2dd41cd2?w=800'); background-size: cover; background-attachment: fixed; }}
        #actualizaciones {{ background: linear-gradient(rgba(255,255,255,0.95), rgba(255,255,255,0.95)), url('https://images.unsplash.com/photo-1554224155-1696413575b3?w=800'); background-size: cover; }}
        .grid {{ max-width: 1100px; margin: 0 auto; display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 18px; }}
        .card {{ background: white; border-radius: 10px; padding: 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); border-left: 6px solid #ddd; }}
        #noticias .card {{ border-left-color: var(--celeste); }}
        #actualizaciones .card {{ border-left-color: var(--dorado); }}
        .badge {{ display: inline-block; padding: 3px 6px; border-radius: 4px; font-size: 0.6rem; font-weight: 800; background: #f0f2f5; margin-bottom: 8px; text-transform: uppercase; }}
        h3 {{ margin: 0 0 8px; font-size: 1.05rem; font-weight: 800; line-height: 1.3; }}
        h3 a {{ text-decoration: none; color: #111; }}
        .desc {{ font-size: 0.85rem; color: #555; line-height: 1.5; }}
        footer {{ background: var(--azul); color: white; text-align: center; padding: 20px; font-size: 0.7rem; margin-top: 40px; }}
        @media (max-width: 600px) {{ header h1 {{ font-size: 1.4rem; }} .tab-btn {{ padding: 12px 10px; font-size: 0.75rem; }} }}
    </style>
</head>
<body>
    <header>
        <h1>Resumen de Noticias AML 📰</h1>
        <p>Monitor de Cumplimiento &middot; BCCL &middot; {fecha}</p>
    </header>
    <div class="tabs">
        <button class="tab-btn active" onclick="showTab('noticias', this)">Noticias</button>
        <button class="tab-btn" onclick="showTab('actualizaciones', this)">Actualizaciones</button>
    </div>
    <div id="noticias" class="page active"><div class="grid">{cards_noticias}</div></div>
    <div id="actualizaciones" class="page"><div class="grid">{cards_actualizaciones}</div></div>
    <footer>Generado para <strong>AML BCCL</strong> &middot; Fuente: Google News</footer>
    <script>
        function showTab(tabId, btn) {{
            document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.getElementById(tabId).classList.add('active');
            btn.classList.add('active');
            window.scrollTo(0,0);
        }}
    </script>
</body>
</html>
"""

def make_cards(news_list):
    if not news_list:
        return '<p style="text-align:center;color:#888;grid-column:1/-1;padding:40px;">No se encontraron noticias recientes.</p>'
    return "".join([
        '<div class="card"><span class="badge">{}</span><h3><a href="{}" target="_blank">{}</a></h3><p class="desc">{}</p></div>'.format(
            n["fuente"], n["link"], n["titular"], n["resumen"]
        ) for n in news_list
    ])

# Generar el archivo final
final_html = html_template.format(
    fecha=fecha_actual,
    cards_noticias=make_cards(news_noticias),
    cards_actualizaciones=make_cards(news_actualizaciones)
)

with open("index.html", "w", encoding="utf-8") as f:
    f.write(final_html)

print("Proceso completado: index.html generado con {} noticias.".format(len(news_noticias) + len(news_actualizaciones)))
