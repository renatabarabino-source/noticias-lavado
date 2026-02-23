# Instalar dependencias si faltan
import subprocess, sys

def pip_install(pkg):
    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"])

try:
    import feedparser
except ImportError:
    print("Instalando feedparser...")
    pip_install("feedparser")
    import feedparser

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("Instalando beautifulsoup4...")
    pip_install("beautifulsoup4")
    from bs4 import BeautifulSoup

try:
    import requests
except ImportError:
    print("Instalando requests...")
    pip_install("requests")
    import requests

import urllib.parse
import socket
from datetime import datetime, timezone, timedelta

socket.setdefaulttimeout(30)

# ── HORA ARGENTINA (UTC-3, sin dependencias externas) ──
tz_ar = timezone(timedelta(hours=-3))
now_ar = datetime.now(tz_ar)
meses = ['enero','febrero','marzo','abril','mayo','junio',
         'julio','agosto','septiembre','octubre','noviembre','diciembre']
fecha_hoy = "{} de {} de {} - {} hs (ARG)".format(
    now_ar.day, meses[now_ar.month - 1], now_ar.year, now_ar.strftime('%H:%M')
)
print("Hora Argentina:", fecha_hoy)

# ── CONFIGURACIÓN ──
NEGATIVE_FILTER = [
    'dental', 'dientes', 'odontologia', 'aguacate', 'receta', 'futbol', 'clima',
    'vinagre', 'almohada', 'mancha', 'jabon', 'limpieza', 'ropa', 'suavizante',
    'lavarropas', 'pelo', 'cutis', 'dieta', 'cocina', 'hogar'
]
ACTUALIZACION_NEG = NEGATIVE_FILTER + [
    'policial', 'crimen', 'asesinato', 'robo', 'detenido', 'allanamiento',
    'tiroteo', 'narco', 'banda', 'sicario'
]

SITES_GOV = (
    "site:argentina.gob.ar OR site:afip.gob.ar OR site:bcra.gob.ar OR "
    "site:cnv.gov.ar OR site:fiscales.gob.ar OR site:uif.gob.ar"
)
SITES_PRIVADOS = (
    "site:cronista.com OR site:ambito.com OR site:iprofesional.com OR site:infobae.com OR "
    "site:lanacion.com.ar OR site:clarin.com OR site:tn.com.ar OR site:perfil.com OR "
    "site:bloomberg.com OR site:reuters.com OR site:baenegocios.com OR site:eldiarioar.com OR "
    "site:pagina12.com.ar OR site:lapoliticaonline.com OR site:eleconomista.com.ar OR "
    "site:gacetamercantil.com OR site:apertura.com OR site:minutouno.com"
)
SITES_INTL = (
    "site:bloomberg.com OR site:reuters.com OR site:cnnespanol.cnn.com OR "
    "site:elpais.com OR site:bbc.com"
)

DIAS_NOTICIAS = 5
DIAS_ACTUALIZACIONES = 30
MAX_NOTICIAS = 25

session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) NewsBot/BCCL'})

def clean_summary(text):
    if not text:
        return "Sin descripcion disponible."
    try:
        return BeautifulSoup(text, "html.parser").get_text()[:240] + "..."
    except Exception:
        return str(text)[:240] + "..."

def safe_str(s):
    """Escapa caracteres que pueden romper HTML"""
    if not s:
        return ""
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')

def fetch_category(query, limit, negative_keywords, dias):
    url = "https://news.google.com/rss/search?q={}&hl=es-419&gl=AR&ceid=AR:es-419".format(
        urllib.parse.quote(query + " when:{}d".format(dias))
    )
    print("  Buscando:", query[:80] + "...")
    try:
        resp = session.get(url, timeout=20)
        entries = feedparser.parse(resp.content).entries
        print("  Entradas raw:", len(entries))
    except Exception as e:
        print("  ERROR fetch:", e)
        return []

    news_list = []
    seen_titles = set()
    seen_sources = {}

    for entry in entries:
        try:
            titulo = entry.title
            link = entry.link
        except AttributeError:
            continue

        t_low = titulo.lower()
        if len(titulo) < 15:
            continue
        fuente = entry.source.title if hasattr(entry, 'source') else "Medio"
        if seen_sources.get(fuente, 0) >= 3:
            continue
        if titulo not in seen_titles and not any(n in t_low for n in negative_keywords):
            news_list.append({
                "fuente": safe_str(fuente),
                "titular": safe_str(titulo),
                "link": link,
                "fecha": safe_str(entry.get('published', 'Reciente')[:16]),
                "resumen": clean_summary(entry.summary if 'summary' in entry else "")
            })
            seen_titles.add(titulo)
            seen_sources[fuente] = seen_sources.get(fuente, 0) + 1

    print("  Resultados filtrados:", len(news_list[:limit]))
    return news_list[:limit]

# ── QUERIES ──
print("\n[1/3] Buscando noticias Argentina...")
q_arg = (
    '("lavado de dinero" OR "lavado de activos" OR "blanqueo de capitales" OR "blanqueamiento") '
    'AND ("Argentina" OR "argentino" OR "BCRA" OR "UIF" OR "peso") '
    'AND ({})'.format(SITES_PRIVADOS)
)
news_arg = fetch_category(q_arg, 20, NEGATIVE_FILTER, DIAS_NOTICIAS)

print("\n[2/3] Buscando noticias internacionales...")
q_intl_n = (
    '("lavado de dinero" OR "lavado de activos" OR "blanqueo de capitales" OR "money laundering") '
    'AND ({})'.format(SITES_INTL)
)
news_intl_n = fetch_category(q_intl_n, 8, NEGATIVE_FILTER, DIAS_NOTICIAS)

# Combinar sin duplicados: Argentina primero
seen_arg = set(n["titular"] for n in news_arg)
news_intl_n = [n for n in news_intl_n if n["titular"] not in seen_arg]
news_noticias = (news_arg + news_intl_n)[:MAX_NOTICIAS]

print("\n[3/3] Buscando actualizaciones normativas...")
q_actualizaciones = (
    '("lavado de dinero" OR "lavado de activos" OR "blanqueo" OR "AML") AND '
    '("UIF" OR "GAFI" OR "BCRA" OR "ARCA" OR "CNV") AND '
    '("resolucion" OR "comunicado" OR "normativa" OR "circular" OR '
    '"disposicion" OR "ley" OR "decreto" OR "alerta" OR "informe") AND '
    '"Argentina" AND (({}) OR ({}))'.format(SITES_GOV, SITES_PRIVADOS)
)
news_actualizaciones = fetch_category(q_actualizaciones, 6, ACTUALIZACION_NEG, DIAS_ACTUALIZACIONES)

print("\nRESUMEN: {} noticias | {} actualizaciones".format(
    len(news_noticias), len(news_actualizaciones)))

# ── RENDER CARDS ──
def render_cards(news_list):
    if not news_list:
        return '<p style="text-align:center;color:#888;padding:40px;font-size:0.9rem">No se encontraron noticias para este periodo.</p>'
    parts = []
    for n in news_list:
        card = (
            '<div class="card">'
            '<span class="badge">' + n["fuente"] + '</span>'
            '<h3><a href="' + n["link"] + '" target="_blank" rel="noopener">' + n["titular"] + '</a></h3>'
            '<p class="fecha">' + n["fecha"] + '</p>'
            '<p class="desc">' + n["resumen"] + '</p>'
            '</div>'
        )
        parts.append(card)
    return "\n".join(parts)

cards_noticias        = render_cards(news_noticias)
cards_actualizaciones = render_cards(news_actualizaciones)
cnt_n = len(news_noticias)
cnt_a = len(news_actualizaciones)

# ── GENERAR HTML ──
CSS = """
    :root { --azul: #004a80; --gold: #d4af37; }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'Inter', sans-serif; background: #f2f4f7; color: #1a1a1a; }

    header {
        background: var(--azul);
        color: white;
        text-align: center;
        padding: 36px 20px 28px;
        border-bottom: 4px solid var(--gold);
    }
    header h1 { font-size: 1.9rem; font-weight: 900; margin-bottom: 4px; }
    header p  { font-size: 0.9rem; font-weight: 600; opacity: 0.8; }
    .header-date { font-size: 0.72rem; opacity: 0.6; margin-top: 6px; font-weight: 400; }

    .tabs {
        display: flex;
        justify-content: center;
        background: #fff;
        position: sticky;
        top: 0;
        z-index: 100;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        border-bottom: 1px solid #e0e0e0;
    }
    .tab-btn {
        padding: 15px 28px;
        border: none;
        background: none;
        cursor: pointer;
        font-family: 'Inter', sans-serif;
        font-weight: 700;
        font-size: 0.82rem;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        color: #777;
        border-bottom: 3px solid transparent;
        transition: all 0.2s;
    }
    .tab-btn:hover { color: #333; }
    .tab-btn.active { color: var(--azul); border-bottom-color: var(--azul); }
    .tab-count {
        display: inline-block;
        background: #eee;
        color: #555;
        font-size: 0.6rem;
        padding: 1px 6px;
        border-radius: 10px;
        margin-left: 6px;
        font-weight: 800;
    }
    .tab-btn.active .tab-count { background: var(--azul); color: white; }

    .page { display: none; padding: 28px 16px 60px; min-height: 80vh; }
    .page.active { display: block; }
    #noticias        { background: #f0f7ff; }
    #actualizaciones { background: #fffdf5; }

    .section-header {
        max-width: 1100px;
        margin: 0 auto 20px;
        padding-bottom: 10px;
        border-bottom: 2px solid #e0e0e0;
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 6px;
    }
    .section-title  { font-size: 0.7rem; font-weight: 800; letter-spacing: 0.12em; text-transform: uppercase; color: #888; }
    .section-period { font-size: 0.65rem; color: #aaa; font-weight: 600; }

    .grid {
        max-width: 1100px;
        margin: 0 auto;
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
        gap: 18px;
    }

    .card {
        background: #ffffff;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        border-left: 5px solid #ddd;
        display: flex;
        flex-direction: column;
        gap: 8px;
        transition: transform 0.18s, box-shadow 0.18s;
    }
    .card:hover { transform: translateY(-3px); box-shadow: 0 8px 20px rgba(0,0,0,0.1); }
    #noticias .card        { border-left-color: #1a73e8; }
    #actualizaciones .card { border-left-color: #b8860b; }

    .badge {
        display: inline-block;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.58rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        align-self: flex-start;
    }
    #noticias .badge        { background: #dbeafe; color: #1e40af; }
    #actualizaciones .badge { background: #fef3cd; color: #856404; }

    h3 { font-size: 1.05rem; font-weight: 800; line-height: 1.35; }
    h3 a { text-decoration: none; color: #111; }
    h3 a:hover { color: var(--azul); text-decoration: underline; }
    .fecha { font-size: 0.65rem; color: #aaa; font-weight: 600; }
    .desc  { font-size: 0.85rem; color: #555; line-height: 1.55; }

    footer {
        background: var(--azul);
        color: rgba(255,255,255,0.5);
        text-align: center;
        padding: 18px;
        font-size: 0.68rem;
        border-top: 3px solid var(--gold);
    }
    footer strong { color: var(--gold); }

    @media (max-width: 600px) {
        header h1 { font-size: 1.4rem; }
        .tab-btn { padding: 12px 14px; font-size: 0.72rem; }
        .grid { grid-template-columns: 1fr; }
    }
"""

JS = """
function showTab(tabId, btn) {
    document.querySelectorAll('.page').forEach(function(p) { p.classList.remove('active'); });
    document.querySelectorAll('.tab-btn').forEach(function(b) { b.classList.remove('active'); });
    document.getElementById(tabId).classList.add('active');
    btn.classList.add('active');
    window.scrollTo({ top: 0, behavior: 'smooth' });
}
"""

html_parts = [
    '<!DOCTYPE html>',
    '<html lang="es">',
    '<head>',
    '<meta charset="UTF-8">',
    '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
    '<title>Resumen AML - BCCL</title>',
    '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&display=swap" rel="stylesheet">',
    '<style>' + CSS + '</style>',
    '</head>',
    '<body>',

    '<header>',
    '<h1>Resumen de Noticias AML &#128240;</h1>',
    '<p>Monitor de Cumplimiento &middot; BCCL</p>',
    '<p class="header-date">' + fecha_hoy + '</p>',
    '</header>',

    '<div class="tabs">',
    '<button class="tab-btn active" onclick="showTab(\'noticias\', this)">',
    'Noticias <span class="tab-count">' + str(cnt_n) + '</span>',
    '</button>',
    '<button class="tab-btn" onclick="showTab(\'actualizaciones\', this)">',
    'Actualizaciones Normativas <span class="tab-count">' + str(cnt_a) + '</span>',
    '</button>',
    '</div>',

    '<div id="noticias" class="page active">',
    '<div class="section-header">',
    '<span class="section-title">Argentina &middot; Lavado &middot; Blanqueo de Activos &middot; Internacional</span>',
    '<span class="section-period">Ultimos 5 dias</span>',
    '</div>',
    '<div class="grid">',
    cards_noticias,
    '</div></div>',

    '<div id="actualizaciones" class="page">',
    '<div class="section-header">',
    '<span class="section-title">UIF &middot; GAFI &middot; BCRA &middot; ARCA &middot; CNV &mdash; Resoluciones y Normativas</span>',
    '<span class="section-period">Ultimos 30 dias</span>',
    '</div>',
    '<div class="grid">',
    cards_actualizaciones,
    '</div></div>',

    '<footer>',
    'Generado para <strong>AML &middot; BCCL</strong> &nbsp;&middot;&nbsp; Fuente: Google News &nbsp;&middot;&nbsp; ' + fecha_hoy,
    '</footer>',

    '<script>' + JS + '</script>',
    '</body>',
    '</html>'
]

HTML = "\n".join(html_parts)

with open("index.html", "w", encoding="utf-8") as f:
    f.write(HTML)

print("index.html generado correctamente ({} bytes)".format(len(HTML)))
