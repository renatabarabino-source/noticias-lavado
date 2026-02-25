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

# ── 1. DEFINICIÓN DE VARIABLES ──
BASE_AML = '("lavado de activos" OR "lavado de dinero" OR "blanqueo de capitales")'

# ── 2. FILTROS DE EXCLUSIÓN ──
NEGATIVE_FILTER = [
    'dolar blue', 'reservas bcra', 'cotiza', 'cotización', 'precio', 'minuto a minuto', 
    'brecha', 'riesgo país', 'compra el bcra', 'ventas del bcra', 'dolar hoy', 'sube', 'baja',
    'dental', 'dientes', 'odontologia', 'aguacate', 'receta', 'vinagre', 'almohada', 
    'mancha', 'jabon', 'limpieza', 'ropa', 'suavizante', 'lavarropas', 'pelo', 'cutis', 
    'dieta', 'cocina', 'veterinaria', 'truco casero', 'remedio',
    'futbol', 'alianza lima', 'senamhi', 'temperaturas', 'clima', 'pronóstico', 
    'espectáculo', 'famosos', 'messi', 'partido', 'gol',
    'vía expresa', 'tránsito', 'falleció', 'accidente', 'vtv', 'choque', 'incendio', 'robo'
]

# Palabras técnicas obligatorias
STRICT_KEYWORDS = [
    'uif', 'gafi', 'bcra', 'arca', 'cnv', 'procelac', 'financiero', 'capitales',
    'compliance', 'testaferro', 'maniobra', 'sociedad', 'causa', 'imputado', 'procesado'
]

# Portales prensa
SITES_PRENSA = (
    "site:cronista.com OR site:ambito.com OR site:iprofesional.com OR site:infobae.com OR "
    "site:lanacion.com.ar OR site:clarin.com OR site:tn.com.ar OR site:perfil.com OR "
    "site:baenegocios.com OR site:eldiarioar.com OR site:eleconomista.com.ar"
)

session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0 NewsBot/BCCL'})

def clean_summary(text):
    if not text: return "Sin descripción disponible."
    try:
        return BeautifulSoup(text, "html.parser").get_text()[:240] + "..."
    except:
        return str(text)[:240] + "..."

def fetch_refined(query, limit, neg_list, mandatory_aml=False):
    url = "https://news.google.com/rss/search?q={}&hl=es-419&gl=AR&ceid=AR:es-419".format(
        urllib.parse.quote(query + " when:5d")
    )
    try:
        resp = session.get(url, timeout=20)
        entries = feedparser.parse(resp.content).entries
    except:
        return []

    results = []
    seen_titles = set()
    for entry in entries:
        t_low = entry.title.lower()
        s_low = entry.summary.lower() if hasattr(entry, 'summary') else ""
        
        if any(w in t_low for w in neg_list):
            continue
            
        if mandatory_aml:
            if not any(k in t_low or k in s_low for k in STRICT_KEYWORDS):
                continue

        if entry.title not in seen_titles and len(entry.title) > 20:
            results.append({
                "fuente": entry.source.title if hasattr(entry, 'source') else "Medio",
                "titular": entry.title.replace('"', '&quot;'),
                "link": entry.link,
                "fecha": entry.get('published', 'Reciente')[:16],
                "resumen": clean_summary(entry.summary if 'summary' in entry else "")
            })
            seen_titles.add(entry.title)
    return results[:limit]

# ── PROCESAMIENTO: SOLO ACTUALIZACIONES ──
q_act = f'({BASE_AML}) AND ("UIF" OR "GAFI" OR "BCRA" OR "ARCA" OR "CNV") AND ({SITES_PRENSA})'
news_actualizaciones = fetch_refined(q_act, 12, NEGATIVE_FILTER, mandatory_aml=True)

# ── GENERACIÓN DE HTML ──
def make_cards(news_list, color_class):
    if not news_list:
        return '<p style="text-align:center;color:#888;grid-column:1/-1;padding:40px;">No se encontraron actualizaciones técnicas de cumplimiento.</p>'
    return "".join([
        f'<div class="card {color_class}"><span class="badge">{n["fuente"]}</span><p class="date">{n["fecha"]}</p><h3><a href="{n["link"]}" target="_blank">{n["titular"]}</a></h3><p class="desc">{n["resumen"]}</p></div>'
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
        :root {{ --azul: #004a80; --dorado: #d4af37; }}
        body {{ font-family: 'Inter', sans-serif; background: #f4f7f9; margin: 0; }}
        header {{ background: var(--azul); color: white; text-align: center; padding: 30px; border-bottom: 4px solid var(--dorado); }}
        .container {{ padding: 20px; }}
        .grid {{ max-width: 1100px; margin: 0 auto; display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 20px; }}
        .card {{ background: white; border-radius: 8px; padding: 20px; border-left: 6px solid var(--dorado); box-shadow: 0 2px 5px rgba(0,0,0,0.05); transition: 0.2s; }}
        .card:hover {{ transform: translateY(-3px); box-shadow: 0 4px 10px rgba(0,0,0,0.1); }}
        .badge {{ font-size: 0.6rem; font-weight: 900; background: #eee; padding: 2px 5px; border-radius: 3px; text-transform: uppercase; }}
        .date {{ font-size: 0.65rem; color: #999; margin: 5px 0; font-weight: 600; }}
        h3 {{ font-size: 1.05rem; margin: 10px 0; line-height: 1.3; }}
        h3 a {{ text-decoration: none; color: #111; }}
        .desc {{ font-size: 0.85rem; color: #555; line-height: 1.5; }}
        @media (max-width: 600px) {{ header h1 {{ font-size: 1.4rem; }} .grid {{ grid-template-columns: 1fr; }} }}
    </style>
</head>
<body>
    <header><h1>Actualizaciones AML 📰</h1><p>Monitor Técnico de Cumplimiento &middot; BCCL &middot; {fecha_gen}</p></header>
    <div class="container">
        <div class="grid">
            {make_cards(news_actualizaciones, 'c-updates')}
        </div>
    </div>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(HTML_CONTENT)
