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

# 1. DEFINICIÓN DE VARIABLES (Evita el NameError)
BASE_AML = '("lavado de dinero" OR "lavado de activos" OR "blanqueo de capitales" OR "blanqueamiento")'

# 2. FILTROS DE RUIDO (Aguacate, Dental, Deportes, Tránsito)
GENERAL_NEG = [
    'dental', 'dientes', 'odontologia', 'aguacate', 'receta', 'futbol', 'clima',
    'vinagre', 'almohada', 'mancha', 'jabon', 'limpieza', 'ropa', 'suavizante',
    'lavarropas', 'pelo', 'cutis', 'dieta', 'cocina', 'alianza lima', 'partido', 
    'goles', 'campeonato', 'via expresa', 'transito'
]

# 3. FILTRO POLICIAL ESTRICTO (Para la pestaña Actualizaciones)
POLICIAL_NEG = GENERAL_NEG + [
    'policia', 'policial', 'crimen', 'asesinato', 'robo', 'detenido', 'allanamiento',
    'tiroteo', 'narco', 'banda', 'sicario', 'droga', 'estupefacientes', 'homicidio',
    'preso', 'carcel', 'penal', 'detencion', 'captura', 'fallecio', 'muerto', 
    'sospechoso', 'delincuente', 'asalto', 'secuestro', 'enfrentamiento'
]

# Palabras que DEBEN estar presentes para validar que es AML/Normativo
STRICT_KEYWORDS = [
    'uif', 'gafi', 'bcra', 'arca', 'cnv', 'lavado', 'activos', 'dinero', 
    'blanqueo', 'capitales', 'normativa', 'resolucion', 'ley', 'regulacion',
    'procelac', 'financiero', 'compliance'
]

# Portales privados seleccionados (Prensa)
PORTALES_PRENSA = (
    "site:infobae.com OR site:clarin.com OR site:lanacion.com.ar OR site:pagina12.com.ar OR "
    "site:minutouno.com OR site:tn.com.ar OR site:perfil.com OR site:eldestapeweb.com OR "
    "site:lapoliticaonline.com OR site:iprofesional.com OR site:ambito.com OR site:cronista.com OR "
    "site:eleconomista.com.ar OR site:baenegocios.com OR site:reuters.com OR site:bloomberg.com OR "
    "site:eldiarioar.com OR site:gacetamercantil.com OR site:cnnespanol.cnn.com OR site:elpais.com"
)

session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0 NewsBot/BCCL'})

def clean_summary(text):
    if not text: return "Sin descripción."
    try:
        return BeautifulSoup(text, "html.parser").get_text()[:220] + "..."
    except:
        return str(text)[:220] + "..."

def fetch_news_refined(query, limit, neg_list, mandatory_aml=False):
    # Filtro de tiempo: 5 días
    q_encoded = urllib.parse.quote(query + " when:5d")
    url = f"https://news.google.com/rss/search?q={q_encoded}&hl=es-419&gl=AR&ceid=AR:es-419"
    
    try:
        resp = session.get(url, timeout=15)
        entries = feedparser.parse(resp.content).entries
    except:
        return []

    results = []
    seen_titles = set()

    for entry in entries:
        t_low = entry.title.lower()
        s_low = entry.summary.lower() if hasattr(entry, 'summary') else ""
        
        # Filtro 1: Exclusión de palabras negativas
        if any(w in t_low for w in neg_list):
            continue
            
        # Filtro 2: Validación obligatoria de palabras clave AML (Solo para Actualizaciones)
        if mandatory_aml:
            if not any(k in t_low or k in s_low for k in STRICT_KEYWORDS):
                continue

        # Filtro 3: Evitar links vacíos y duplicados
        if entry.title not in seen_titles and len(entry.title) > 20:
            fecha_noticia = entry.get('published', 'Reciente')
            results.append({
                "fuente": entry.source.title if hasattr(entry, 'source') else "Medio",
                "titular": entry.title.replace('"', '&quot;'),
                "link": entry.link,
                "fecha": fecha_noticia[:16], # Muestra la fecha solicitada
                "resumen": clean_summary(entry.summary if 'summary' in entry else "")
            })
            seen_titles.add(entry.title)

    return results[:limit]

# --- PROCESAMIENTO DE LAS 2 SOLAPAS ---

# 1. NOTICIAS (Prensa General): Tope 25 noticias
q_noticias = f'({BASE_AML} OR "dolar blue") AND ({PORTALES_PRENSA})'
news_noticias = fetch_news_refined(q_noticias, 25, GENERAL_NEG)

# 2. ACTUALIZACIONES (Normativas): Solo privados, SIN Policiales, SIN Gov. Tope 6
q_actualizaciones = f'({BASE_AML}) AND ({PORTALES_PRENSA}) AND ("uif" OR "bcra" OR "arca" OR "cnv" OR "normativa")'
news_actualizaciones = fetch_news_refined(q_actualizaciones, 6, POLICIAL_NEG, mandatory_aml=True)

# --- GENERACIÓN DE HTML (Optimizado para Web y Celu) ---
def make_cards(news_list, color_class):
    if not news_list:
        return '<p style="text-align:center;color:#888;grid-column:1/-1;padding:40px;">No se encontraron noticias técnicas recientes.</p>'
    return "".join([
        f'<div class="card {color_class}"><span class="badge">{n["fuente"]}</span><p class="date">Publicado: {n["fecha"]}</p><h3><a href="{n["link"]}" target="_blank">{n["titular"]}</a></h3><p class="desc">{n["resumen"]}</p></div>'
        for n in news_list
    ])

fecha_gen = now_ar.strftime('%d/%m/%Y %H:%M')
HTML_CONTENT = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AML Monitor - BCCL</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&display=swap" rel="stylesheet">
    <style>
        :root {{ --azul: #004a80; --dorado: #d4af37; --celeste: #1a73e8; }}
        body {{ font-family: 'Inter', sans-serif; background: #f4f7f9; margin: 0; }}
        header {{ background: var(--azul); color: white; text-align: center; padding: 30px; border-bottom: 4px solid var(--dorado); }}
        .tabs {{ display: flex; justify-content: center; background: white; position: sticky; top: 0; z-index: 100; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
        .tab-btn {{ padding: 15px 25px; border: none; background: none; cursor: pointer; font-weight: 700; text-transform: uppercase; color: #666; border-bottom: 3px solid transparent; transition: 0.3s; }}
        .tab-btn.active {{ color: var(--azul); border-bottom-color: var(--azul); }}
        .page {{ display: none; padding: 20px; }}
        .page.active {{ display: block; }}
        .grid {{ max-width: 1100px; margin: 0 auto; display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 20px; }}
        .card {{ background: white; border-radius: 8px; padding: 20px; border-left: 6px solid #ccc; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }}
        .c-news {{ border-left-color: var(--celeste); }}
        .c-updates {{ border-left-color: var(--dorado); }}
        .badge {{ font-size: 0.6rem; font-weight: 900; background: #eee; padding: 2px 5px; border-radius: 3px; text-transform: uppercase; }}
        .date {{ font-size: 0.65rem; color: #999; margin: 5px 0; font-weight: 600; }}
        h3 {{ font-size: 1.1rem; margin: 10px 0; line-height: 1.4; }}
        h3 a {{ text-decoration: none; color: #222; }}
        .desc {{ font-size: 0.85rem; color: #666; line-height: 1.5; }}
        @media (max-width: 600px) {{ header h1 {{ font-size: 1.4rem; }} .tab-btn {{ padding: 12px 10px; font-size: 0.75rem; }} .grid {{ grid-template-columns: 1fr; }} }}
    </style>
</head>
<body>
    <header><h1>Resumen de Noticias AML 📰</h1><p>Monitor de Cumplimiento &middot; BCCL &middot; {fecha_gen}</p></header>
    <div class="tabs">
        <button class="tab-btn active" onclick="showTab('noticias', this)">Noticias</button>
        <button class="tab-btn" onclick="showTab('actualizaciones', this)">Actualizaciones</button>
    </div>
    <div id="noticias" class="page active"><div class="grid">{make_cards(news_noticias, 'c-news')}</div></div>
    <div id="actualizaciones" class="page"><div class="grid">{make_cards(news_actualizaciones, 'c-updates')}</div></div>
    <script>
        function showTab(t, b) {{
            document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
            document.getElementById(t).classList.add('active');
            b.classList.add('active');
            window.scrollTo(0,0);
        }}
    </script>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(HTML_CONTENT)
