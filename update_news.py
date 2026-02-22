import feedparser
import urllib.parse
from bs4 import BeautifulSoup
import socket
from datetime import datetime, timezone, timedelta
import requests

socket.setdefaulttimeout(30)

# ── HORA ARGENTINA (UTC-3, sin pytz) ──
tz_ar = timezone(timedelta(hours=-3))
now_ar = datetime.now(tz_ar)
meses = ['enero','febrero','marzo','abril','mayo','junio',
         'julio','agosto','septiembre','octubre','noviembre','diciembre']
fecha_hoy = "{} de {} de {} · {} hs (ARG)".format(
    now_ar.day, meses[now_ar.month - 1], now_ar.year, now_ar.strftime('%H:%M')
)

# ── CONFIGURACIÓN ──
BASE_AML = '("lavado de dinero" OR "lavado de activos" OR "blanqueo" OR "blanqueamiento" OR "AML")'

NEGATIVE_FILTER = [
    'dental', 'dientes', 'odontología', 'aguacate', 'receta', 'fútbol', 'clima',
    'vinagre', 'almohada', 'mancha', 'jabón', 'limpieza', 'ropa', 'suavizante',
    'lavarropas', 'pelo', 'cutis', 'salud', 'dieta'
]
ACTUALIZACION_NEG = NEGATIVE_FILTER + [
    'policial', 'crimen', 'asesinato', 'robo', 'detenido', 'allanamiento', 'tiroteo', 'narco', 'banda'
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

DIAS_NOTICIAS = 5
DIAS_ACTUALIZACIONES = 30
MAX_NOTICIAS = 25

session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0 NewsBot/BCCL'})

def clean_summary(text):
    if not text: return "Sin descripción disponible."
    return BeautifulSoup(text, "html.parser").get_text()[:240] + "..."

def fetch_category(query, limit, negative_keywords, dias):
    url = "https://news.google.com/rss/search?q={}&hl=es-419&gl=AR&ceid=AR:es-419".format(
        urllib.parse.quote(query + " when:{}d".format(dias))
    )
    try:
        resp = session.get(url, timeout=15)
        entries = feedparser.parse(resp.content).entries
    except Exception as e:
        print("Error:", e)
        return []

    news_list = []
    seen_titles = set()
    seen_sources = {}

    for entry in entries:
        t_low = entry.title.lower()
        if len(entry.title) < 15 or entry.link.count('/') < 4:
            continue
        fuente = entry.source.title if hasattr(entry, 'source') else "Medio"
        if seen_sources.get(fuente, 0) >= 3:
            continue
        if entry.title not in seen_titles and not any(n in t_low for n in negative_keywords):
            news_list.append({
                "fuente": fuente,
                "titular": entry.title,
                "link": entry.link,
                "fecha": entry.get('published', 'Reciente')[:16],
                "resumen": clean_summary(entry.summary if 'summary' in entry else "")
            })
            seen_titles.add(entry.title)
            seen_sources[fuente] = seen_sources.get(fuente, 0) + 1

    return news_list[:limit]

# ── QUERIES ──

# TAB 1 — NOTICIAS: Argentina, lavado, blanqueo, dólar
q_noticias = '({} OR "dólar blue") AND ("lavado" OR "blanqueo") AND ({})'.format(
    BASE_AML, SITES_PRIVADOS
)
news_noticias = fetch_category(q_noticias, MAX_NOTICIAS, NEGATIVE_FILTER, DIAS_NOTICIAS)

# TAB 2 — ACTUALIZACIONES NORMATIVAS: UIF, GAFI, BCRA, ARCA, CNV — últimos 30 días
q_actualizaciones = (
    '({}) AND ("UIF" OR "GAFI" OR "BCRA" OR "ARCA" OR "CNV") AND '
    '("resolución" OR "comunicado" OR "normativa" OR "regulación" OR "circular" OR '
    '"disposición" OR "actualización" OR "ley" OR "decreto" OR "alerta" OR "informe") AND '
    '"Argentina" AND (({}) OR ({}))'.format(BASE_AML, SITES_GOV, SITES_PRIVADOS)
)
news_actualizaciones = fetch_category(q_actualizaciones, 6, ACTUALIZACION_NEG, DIAS_ACTUALIZACIONES)

print("Noticias: {}  |  Actualizaciones: {}".format(len(news_noticias), len(news_actualizaciones)))

# ── RENDER CARDS ──
def render_cards(news_list):
    if not news_list:
        return '<p style="text-align:center;color:#888;padding:40px">No se encontraron noticias para este período.</p>'
    parts = []
    for n in news_list:
        parts.append(
            '<div class="card">'
            '<span class="badge">{fuente}</span>'
            '<h3><a href="{link}" target="_blank" rel="noopener">{titular}</a></h3>'
            '<p class="fecha">{fecha}</p>'
            '<p class="desc">{resumen}</p>'
            '</div>'.format(
                fuente=n["fuente"], link=n["link"],
                titular=n["titular"], fecha=n["fecha"],
                resumen=n["resumen"]
            )
        )
    return "\n".join(parts)

cards_noticias      = render_cards(news_noticias)
cards_actualizaciones = render_cards(news_actualizaciones)
cnt_n = len(news_noticias)
cnt_a = len(news_actualizaciones)

# ── HTML ──
HTML = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Resumen AML - BCCL</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&display=swap" rel="stylesheet">
    <style>
        :root {
            --p-color: #004a80;
            --a-color: #b8860b;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Inter', sans-serif; background: #f2f4f7; color: #1a1a1a; }

        header {
            background: var(--p-color);
            color: white;
            text-align: center;
            padding: 36px 20px 28px;
            border-bottom: 4px solid #d4af37;
        }
        header h1 { font-size: 1.9rem; font-weight: 900; margin-bottom: 4px; letter-spacing: -0.5px; }
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
            padding: 14px 24px;
            border: none;
            background: none;
            cursor: pointer;
            font-family: 'Inter', sans-serif;
            font-weight: 700;
            font-size: 0.78rem;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            color: #777;
            border-bottom: 3px solid transparent;
            transition: all 0.2s;
        }
        .tab-btn:hover { color: #333; }
        .tab-btn.active { color: var(--p-color); border-bottom-color: var(--p-color); }
        .tab-count {
            display: inline-block;
            background: #eee;
            color: #555;
            font-size: 0.6rem;
            padding: 1px 6px;
            border-radius: 10px;
            margin-left: 5px;
            font-weight: 800;
        }
        .tab-btn.active .tab-count { background: var(--p-color); color: white; }

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
        #actualizaciones .card { border-left-color: var(--a-color); }

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
        h3 a:hover { color: var(--p-color); text-decoration: underline; }
        .fecha { font-size: 0.65rem; color: #aaa; font-weight: 600; }
        .desc  { font-size: 0.85rem; color: #555; line-height: 1.55; flex: 1; }

        footer {
            background: var(--p-color);
            color: rgba(255,255,255,0.5);
            text-align: center;
            padding: 18px;
            font-size: 0.68rem;
            border-top: 3px solid #d4af37;
        }
        footer strong { color: #d4af37; }

        @media (max-width: 600px) {
            header h1 { font-size: 1.4rem; }
            .tab-btn { padding: 12px 12px; font-size: 0.68rem; }
            .grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>

<header>
    <h1>Resumen de Noticias AML &#128240;</h1>
    <p>Monitor de Cumplimiento &middot; BCCL &#128181;&#128200;</p>
    <p class="header-date">""" + fecha_hoy + """</p>
</header>

<div class="tabs">
    <button class="tab-btn active" onclick="showTab('noticias', this)">
        Noticias <span class="tab-count">""" + str(cnt_n) + """</span>
    </button>
    <button class="tab-btn" onclick="showTab('actualizaciones', this)">
        Actualizaciones Normativas <span class="tab-count">""" + str(cnt_a) + """</span>
    </button>
</div>

<div id="noticias" class="page active">
    <div class="section-header">
        <span class="section-title">Argentina &middot; Lavado &middot; Blanqueo &middot; D&oacute;lar</span>
        <span class="section-period">&#218;ltimos 5 d&iacute;as</span>
    </div>
    <div class="grid">""" + cards_noticias + """</div>
</div>

<div id="actualizaciones" class="page">
    <div class="section-header">
        <span class="section-title">UIF &middot; GAFI &middot; BCRA &middot; ARCA &middot; CNV &mdash; Resoluciones y Normativas</span>
        <span class="section-period">&#218;ltimos 30 d&iacute;as</span>
    </div>
    <div class="grid">""" + cards_actualizaciones + """</div>
</div>

<footer>
    Generado para <strong>AML &middot; BCCL</strong> &nbsp;&middot;&nbsp;
    Fuente: Google News &nbsp;&middot;&nbsp; """ + fecha_hoy + """
</footer>

<script>
function showTab(tabId, btn) {
    document.querySelectorAll('.page').forEach(function(p) { p.classList.remove('active'); });
    document.querySelectorAll('.tab-btn').forEach(function(b) { b.classList.remove('active'); });
    document.getElementById(tabId).classList.add('active');
    btn.classList.add('active');
    window.scrollTo({ top: 0, behavior: 'smooth' });
}
</script>
</body>
</html>"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(HTML)

print("OK — index.html generado: {} noticias | {} actualizaciones | {}".format(
    cnt_n, cnt_a, fecha_hoy))
