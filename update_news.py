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
        ...
    </style>
</head>
<body>
...
</html>"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(HTML)

print("OK — index.html generado: {} noticias | {} actualizaciones | {}".format(
    cnt_n, cnt_a, fecha_hoy))
