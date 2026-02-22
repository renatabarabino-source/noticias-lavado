import feedparser
import urllib.parse
from bs4 import BeautifulSoup
import socket
from datetime import datetime
import requests

socket.setdefaulttimeout(10)

# ── DEPENDENCIA OPCIONAL pytz ──
try:
    import pytz
    tz_ar = pytz.timezone('America/Argentina/Buenos_Aires')
    now_ar = datetime.now(tz_ar)
except ImportError:
    from datetime import timezone, timedelta
    tz_ar = timezone(timedelta(hours=-3))
    now_ar = datetime.now(tz_ar)

meses = ['enero','febrero','marzo','abril','mayo','junio',
         'julio','agosto','septiembre','octubre','noviembre','diciembre']
fecha_hoy = f"{now_ar.day} de {meses[now_ar.month-1]} de {now_ar.year} · {now_ar.strftime('%H:%M')} hs (ARG)"

# ── CONFIGURACIÓN ──
BASE_AML = '("lavado de dinero" OR "lavado de activos" OR "blanqueo" OR "blanqueamiento" OR "AML")'

GENERAL_NEG = ['dental','dientes','odontología','aguacate','receta','fútbol','clima','vinagre','limpieza']
ACTUALIZACION_NEG = GENERAL_NEG + ['policial','crimen','asesinato','robo','detenido','allanamiento','tiroteo','narco','banda']

PORTALES_PRENSA = (
    "site:infobae.com OR site:clarin.com OR site:lanacion.com.ar OR site:pagina12.com.ar OR "
    "site:minutouno.com OR site:tn.com.ar OR site:perfil.com OR site:eldestapeweb.com OR "
    "site:lapoliticaonline.com OR site:iprofesional.com OR site:ambito.com OR site:cronista.com OR "
    "site:eleconomista.com.ar OR site:baenegocios.com OR site:reuters.com OR site:bloomberg.com OR "
    "site:eldiarioar.com OR site:gacetamercantil.com OR site:apertura.com OR "
    "site:cnnespanol.cnn.com OR site:elpais.com"
)

PORTALES_ACTUALIZACIONES = (
    PORTALES_PRENSA +
    " OR site:uif.gob.ar OR site:bcra.gob.ar OR site:cnv.gob.ar OR site:argentina.gob.ar"
)

DIAS_NOTICIAS       = 5
DIAS_ACTUALIZACIONES = 30

session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0 NewsBot/BCCL'})

# ── HELPERS ──
def clean_text(text):
    if not text:
        return "Sin descripción disponible."
    txt = BeautifulSoup(text, "html.parser").get_text()
    txt = txt.replace('"', '&quot;').replace("'", '&#39;').replace('<', '&lt;').replace('>', '&gt;')
    return txt[:240] + "..."

def safe(text):
    """Escapa comillas para uso seguro dentro de atributos HTML."""
    return str(text).replace('"', '&quot;').replace("'", '&#39;')

def fetch_category(query, limit, negative_keywords, dias):
    url = (
        "https://news.google.com/rss/search?q="
        + urllib.parse.quote(query)
        + f"+when:{dias}d&hl=es-419&gl=AR&ceid=AR:es-419"
    )
    try:
        response = session.get(url, timeout=10)
        entries = feedparser.parse(response.content).entries
    except Exception as e:
        print(f"  [ERROR fetch] {e}")
        return []

    news_list   = []
    seen_titles = set()
    seen_sources = {}

    for entry in entries:
        t_low  = entry.title.lower()
        fuente = entry.source.title if hasattr(entry, 'source') else "Medio"

        if len(entry.title) < 15 or entry.link.count('/') < 4:
            continue
        if seen_sources.get(fuente, 0) >= 3:
            continue
        if entry.title in seen_titles:
            continue
        if any(n in t_low for n in negative_keywords):
            continue

        news_list.append({
            "fuente":  fuente,
            "titular": entry.title.replace('<','&lt;').replace('>','&gt;'),
            "link":    safe(entry.link),
            "resumen": clean_text(entry.get('summary', '')),
            "fecha":   entry.published[:16] if 'published' in entry else ""
        })
        seen_titles.add(entry.title)
        seen_sources[fuente] = seen_sources.get(fuente, 0) + 1

    return news_list[:limit]

# ── FETCH ──
print("Buscando noticias...")
q_noticias = f'({BASE_AML} OR "dólar blue") AND ("lavado" OR "blanqueo") AND ({PORTALES_PRENSA})'
news_noticias = fetch_category(q_noticias, 24, GENERAL_NEG, DIAS_NOTICIAS)
print(f"  Noticias encontradas: {len(news_noticias)}")

q_actualizaciones = (
    f'({BASE_AML}) AND '
    '("UIF" OR "GAFI" OR "BCRA" OR "ARCA" OR "CNV") AND '
    '("resolución" OR "comunicado" OR "normativa" OR "circular" OR '
    '"disposición" OR "decreto" OR "recomendación" OR "alerta" OR "informe") AND '
    f'"Argentina" AND ({PORTALES_ACTUALIZACIONES})'
)
news_actualizaciones = fetch_category(q_actualizaciones, 6, ACTUALIZACION_NEG, DIAS_ACTUALIZACIONES)
print(f"  Actualizaciones encontradas: {len(news_actualizaciones)}")

# ── IMÁGENES DE FONDO ──
BG_NOTICIAS = [
    "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=800&auto=format",
    "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=600&auto=format",
    "https://images.unsplash.com/photo-1559526324-4b87b5e36e44?w=600&auto=format",
    "https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?w=600&auto=format",
    "https://images.unsplash.com/photo-1526304640581-d334cdbbf45e?w=600&auto=format",
    "https://images.unsplash.com/photo-1518186285589-2f7649de83e0?w=600&auto=format",
    "https://images.unsplash.com/photo-1601597111158-2fceff292cdc?w=600&auto=format",
    "https://images.unsplash.com/photo-1543286386-713bdd548da4?w=600&auto=format",
    "https://images.unsplash.com/photo-1507679799987-c73779587ccf?w=600&auto=format",
    "https://images.unsplash.com/photo-1553729459-efe14ef6055d?w=600&auto=format",
    "https://images.unsplash.com/photo-1590283603385-17ffb3a7f29f?w=600&auto=format",
    "https://images.unsplash.com/photo-1565372195458-9de0b320ef04?w=600&auto=format",
]
BG_ACTUALIZACIONES = [
    "https://images.unsplash.com/photo-1521791136064-7986c2920216?w=600&auto=format",
    "https://images.unsplash.com/photo-1554224154-26032ffc0d07?w=600&auto=format",
    "https://images.unsplash.com/photo-1450101499163-c8848c66ca85?w=600&auto=format",
    "https://images.unsplash.com/photo-1507679799987-c73779587ccf?w=600&auto=format",
    "https://images.unsplash.com/photo-1590283603385-17ffb3a7f29f?w=600&auto=format",
    "https://images.unsplash.com/photo-1436491865332-7a61a109cc05?w=600&auto=format",
]

# ── RENDER ──
def render_noticias(news_list):
    if not news_list:
        return '<div class="no-news">No se encontraron noticias para este período.</div>'
    html = ""
    for i, n in enumerate(news_list):
        if i == 0:
            cls = "card-large"
        elif i < 3:
            cls = "card-medium"
        else:
            cls = "card-small"
        bg = BG_NOTICIAS[i % len(BG_NOTICIAS)]
        html += (
            '<article class="card ' + cls + '" '
            'style="background-image:url(\'' + bg + '\')" '
            'onclick="window.open(\'' + n['link'] + '\',\'_blank\')">'
            '<div class="card-overlay"></div>'
            '<div class="card-content">'
            '<div class="card-top">'
            '<span class="badge">' + n['fuente'] + '</span>'
            '<span class="card-date">' + n['fecha'] + '</span>'
            '</div>'
            '<h3>' + n['titular'] + '</h3>'
            '<p class="desc">' + n['resumen'] + '</p>'
            '<span class="read-more">Leer nota &rarr;</span>'
            '</div></article>\n'
        )
    return html

def render_actualizaciones(news_list):
    if not news_list:
        return '<div class="no-news">No se encontraron actualizaciones en los últimos 30 días.</div>'
    html = ""
    for i, n in enumerate(news_list):
        bg = BG_ACTUALIZACIONES[i % len(BG_ACTUALIZACIONES)]
        html += (
            '<article class="card card-reg" '
            'style="background-image:url(\'' + bg + '\')" '
            'onclick="window.open(\'' + n['link'] + '\',\'_blank\')">'
            '<div class="card-overlay"></div>'
            '<div class="card-content">'
            '<div class="card-top">'
            '<span class="badge badge-gold">' + n['fuente'] + '</span>'
            '<span class="card-date">' + n['fecha'] + '</span>'
            '</div>'
            '<h3>' + n['titular'] + '</h3>'
            '<p class="desc">' + n['resumen'] + '</p>'
            '<span class="read-more gold-link">Ver resolución &rarr;</span>'
            '</div></article>\n'
        )
    return html

cards_noticias       = render_noticias(news_noticias)
cards_actualizaciones = render_actualizaciones(news_actualizaciones)
cnt_n = str(len(news_noticias))
cnt_a = str(len(news_actualizaciones))

# ── HTML ──
HEAD = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AML Monitor · BCCL</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@400;500;700&display=swap" rel="stylesheet">
<style>
:root{
  --navy:#050d1a;--navy2:#0b1a2e;--navy3:#0f2040;
  --gold:#d4a843;--gold2:#f0c96a;
  --white:#f0eee8;--muted:rgba(240,238,232,0.5);
  --serif:'DM Serif Display',Georgia,serif;
  --sans:'DM Sans',system-ui,sans-serif;
}
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:var(--sans);background:var(--navy);color:var(--white);min-height:100vh;}
...
</style>
</head>
<body>
"""

HERO = (
    '<header class="hero">'
    '<div class="hero-bg"></div>'
    '<div class="hero-content">'
    '<p class="hero-eyebrow">&#9679; Monitor de Cumplimiento &middot; AML &middot; Argentina</p>'
    '<h1 class="hero-title">Prevenci&oacute;n del<br><em>Lavado de Activos</em></h1>'
    '<p class="hero-sub">Actualizado: ' + fecha_hoy + '</p>'
    '</div></header>'
)

TICKER = (
    '<div class="ticker-bar"><div class="ticker-inner">'
    '<span>UIF &middot; Unidad de Informaci&oacute;n Financiera</span>'
    '<span>BCRA &middot; Banco Central de la Rep&uacute;blica Argentina</span>'
    '<span>CNV &middot; Comisi&oacute;n Nacional de Valores</span>'
    '<span>GAFI &middot; Grupo de Acci&oacute;n Financiera Internacional</span>'
    '<span>ARCA &middot; Agencia de Recaudaci&oacute;n y Control Aduanero</span>'
    '<span>PLA/FT &middot; Prevenci&oacute;n del Lavado de Activos y Financiamiento del Terrorismo</span>'
    '</div></div>'
)

NAV = (
    '<nav class="nav-bar"><div class="nav-inner">'
    '<button class="tab-btn active" onclick="showTab(\'noticias\',this)">'
    'Noticias <span class="tab-count">' + cnt_n + '</span></button>'
    '<button class="tab-btn" onclick="showTab(\'actualizaciones\',this)">'
    'Actualizaciones Normativas <span class="tab-count">' + cnt_a + '</span></button>'
    '</div></nav>'
)

PAGE_N = (
    '<div id="noticias" class="page active">'
    '<div class="section-label">'
    '<span class="section-label-text">&Uacute;ltimos ' + str(DIAS_NOTICIAS) + ' d&iacute;as &middot; AML &middot; Lavado &middot; Blanqueo</span>'
    '<div class="section-label-line"></div></div>'
    '<div class="news-grid">' + cards_noticias + '</div>'
    '</div>'
)

PAGE_A = (
    '<div id="actualizaciones" class="page">'
    '<div class="section-label">'
    '<span class="section-label-text">&Uacute;ltimos 30 d&iacute;as &middot; Resoluciones &middot; Circulares &middot; UIF &middot; GAFI &middot; BCRA &middot; ARCA &middot; CNV</span>'
    '<div class="section-label-line"></div></div>'
    '<div class="reg-grid">' + cards_actualizaciones + '</div>'
    '</div>'
)

FOOTER = (
    '<footer>Generado autom&aacute;ticamente para <strong>AML &middot; BCCL</strong>'
    ' &nbsp;&middot;&nbsp; Fuente: Google News &nbsp;&middot;&nbsp; ' + fecha_hoy + '</footer>'
)

JS = (
    '<script>'
    'function showTab(tabId,btn){'
    'document.querySelectorAll(".page").forEach(p=>p.classList.remove("active"));'
    'document.querySelectorAll(".tab-btn").forEach(b=>b.classList.remove("active"));'
    'document.getElementById(tabId).classList.add("active");'
    'btn.classList.add("active");'
    'window.scrollTo({top:0,behavior:"smooth"});'
    '}'
    '</script>'
)

TAIL = '</body></html>'

html_final = HEAD + HERO + TICKER + NAV + PAGE_N + PAGE_A + FOOTER + JS + TAIL

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_final)

print(f"OK · {cnt_n} noticias · {cnt_a} actualizaciones · {fecha_hoy}")
