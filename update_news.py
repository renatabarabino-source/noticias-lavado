import feedparser
import urllib.parse
from bs4 import BeautifulSoup
import socket
from datetime import datetime, timezone, timedelta
import requests
import html as html_escape

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
    if not text:
        return "Sin descripción disponible."
    # Extraer texto plano y truncar sin romper entidades
    s = BeautifulSoup(text, "html.parser").get_text()
    s = s.strip()
    if len(s) > 240:
        return s[:240].rstrip() + "..."
    return s

def safe_text(s):
    return html_escape.escape(s) if s else ""

def fetch_category(query, limit, negative_keywords, dias):
    # Construir URL para Google News RSS con filtro de días
    q = "{} when:{}d".format(query, dias)
    url = "https://news.google.com/rss/search?q={}&hl=es-419&gl=AR&ceid=AR:es-419".format(
        urllib.parse.quote(q)
    )
    try:
        resp = session.get(url, timeout=15)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)
        entries = feed.entries
    except Exception as e:
        print("Error al obtener feed:", e)
        return []

    news_list = []
    seen_titles = set()
    seen_sources = {}

    for entry in entries:
        title = entry.get('title', '').strip()
        if not title or len(title) < 15:
            continue
        # Filtrar títulos cortos o links sospechosos
        link = entry.get('link', '')
        if not link or link.count('/') < 3:
            continue

        t_low = title.lower()
        if any(n in t_low for n in negative_keywords):
            continue

        fuente = entry.source.title if hasattr(entry, 'source') and getattr(entry, 'source') else entry.get('source', {}).get('title', 'Medio')
        fuente = fuente if fuente else "Medio"

        # Limitar por fuente para evitar saturación
        if seen_sources.get(fuente, 0) >= 3:
            continue

        if title in seen_titles:
            continue

        # Fecha: usar published si existe, sino 'Reciente'
        fecha = entry.get('published', '') or entry.get('updated', '') or 'Reciente'
        # Resumen: preferir summary, luego description, sino vacío
        resumen_raw = entry.get('summary', '') or entry.get('description', '')
        resumen = clean_summary(resumen_raw)

        news_list.append({
            "fuente": safe_text(fuente),
            "titular": safe_text(title),
            "link": link,
            "fecha": safe_text(fecha[:16]),
            "resumen": safe_text(resumen)
        })
        seen_titles.add(title)
        seen_sources[fuente] = seen_sources.get(fuente, 0) + 1

        if len(news_list) >= limit:
            break

    return news_list[:limit]

# ── QUERIES ──

SITES_INTL = "site:bloomberg.com OR site:reuters.com OR site:cnnespanol.cnn.com OR site:elpais.com OR site:bbc.com"

# TAB 1 — NOTICIAS: Argentina primero (AML estricto), luego internacional
q_arg = (
    '("lavado de dinero" OR "lavado de activos" OR "blanqueo de capitales" OR "blanqueamiento") '
    'AND ("Argentina" OR "argentino" OR "BCRA" OR "UIF" OR "peso") '
    'AND ({})'.format(SITES_PRIVADOS)
)
q_intl_n = (
    '("lavado de dinero" OR "lavado de activos" OR "blanqueo de capitales" OR "money laundering") '
    'AND ({})'.format(SITES_INTL)
)
news_arg    = fetch_category(q_arg,    20, NEGATIVE_FILTER, DIAS_NOTICIAS)
news_intl_n = fetch_category(q_intl_n,  8, NEGATIVE_FILTER, DIAS_NOTICIAS)

# Combinar sin duplicados: Argentina primero, internacional al final
seen_arg = set(n["titular"] for n in news_arg)
news_intl_n = [n for n in news_intl_n if n["titular"] not in seen_arg]
news_noticias = (news_arg + news_intl_n)[:MAX_NOTICIAS]

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
            '<h3><a href="{link}" target="_blank" rel="noopener noreferrer">{titular}</a></h3>'
            '<p class="fecha">{fecha}</p>'
            '<p class="desc">{resumen}</p>'
            '</div>'.format(
                fuente=n["fuente"], link=n["link"],
                titular=n["titular"], fecha=n["fecha"],
                resumen=n["resumen"]
            )
        )
    return "\n".join(parts)

cards_noticias = render_cards(news_noticias)
cards_actualizaciones = render_cards(news_actualizaciones)
cnt_n = len(news_noticias)
cnt_a = len(news_actualizaciones)

# ── HTML ──
HTML = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Resumen AML - BCCL</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&display=swap" rel="stylesheet">
    <style>
        :root{{--bg:#0f1724;--card:#0b1220;--muted:#9aa4b2;--accent:#06b6d4;--text:#e6eef6}}
        html,body{{height:100%;margin:0;font-family:Inter,system-ui,-apple-system,Segoe UI,Roboto,"Helvetica Neue",Arial; background:linear-gradient(180deg,#071022 0%, #071827 100%);color:var(--text)}}
        .container{{max-width:1100px;margin:32px auto;padding:28px;background:rgba(255,255,255,0.02);border-radius:12px;box-shadow:0 6px 30px rgba(2,6,23,0.6)}}
        header{{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:18px}}
        .title{{display:flex;flex-direction:column}}
        .title h1{{margin:0;font-size:20px;letter-spacing:-0.2px}}
        .meta{{color:var(--muted);font-size:13px}}
        .counts{{text-align:right;color:var(--muted);font-size:13px}}
        .tabs{{display:grid;grid-template-columns:1fr 320px;gap:18px}}
        .panel{{background:var(--card);padding:16px;border-radius:10px;min-height:220px}}
        .panel h2{{margin:0 0 8px 0;font-size:16px}}
        .card{{background:linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01));padding:12px;border-radius:8px;margin-bottom:12px;border:1px solid rgba(255,255,255,0.03)}}
        .badge{{display:inline-block;background:rgba(255,255,255,0.03);color:var(--muted);padding:4px 8px;border-radius:999px;font-size:12px;margin-bottom:8px}}
        .card h3{{margin:6px 0 4px 0;font-size:15px}}
        .card h3 a{{color:var(--text);text-decoration:none}}
        .card h3 a:hover{{text-decoration:underline;color:var(--accent)}}
        .fecha{{color:var(--muted);font-size:12px;margin:0 0 8px 0}}
        .desc{{color:var(--muted);font-size:13px;margin:0}}
        footer{{margin-top:18px;color:var(--muted);font-size:13px;display:flex;justify-content:space-between;align-items:center}}
        @media (max-width:900px){{.tabs{{grid-template-columns:1fr}} .counts{{text-align:left}}}}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="title">
                <h1>Resumen AML — Noticias y Actualizaciones</h1>
                <div class="meta">Consulta automática · {fecha_hoy}</div>
            </div>
            <div class="counts">
                <div><strong>{cnt_n}</strong> noticias</div>
                <div><strong>{cnt_a}</strong> actualizaciones</div>
            </div>
        </header>

        <div class="tabs">
            <div class="panel" id="noticias">
                <h2>Noticias recientes</h2>
                {cards_noticias}
            </div>

            <aside class="panel" id="actualizaciones">
                <h2>Actualizaciones normativas</h2>
                {cards_actualizaciones}
            </aside>
        </div>

        <footer>
            <div>Generado por NewsBot/BCCL</div>
            <div style="color:var(--muted)">Máx. {MAX_NOTICIAS} noticias · Últimos {DIAS_NOTICIAS} días</div>
        </footer>
    </div>
</body>
</html>"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(HTML)

print("OK — index.html generado: {} noticias | {} actualizaciones | {}".format(
    cnt_n, cnt_a, fecha_hoy))
