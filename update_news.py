import feedparser
import urllib.parse
from bs4 import BeautifulSoup
import socket
from datetime import datetime, timezone, timedelta
import requests

socket.setdefaulttimeout(10)

# ── CONFIGURACIÓN ──────────────────────────────────────────────────────────────
BASE_AML = '("lavado de dinero" OR "lavado de activos" OR "blanqueo" OR "blanqueamiento" OR "AML")'

GENERAL_NEG = ['dental', 'dientes', 'odontología', 'aguacate', 'receta', 'fútbol',
               'clima', 'vinagre', 'limpieza', 'cocina', 'moda', 'belleza']
ACTUALIZACION_NEG = GENERAL_NEG + ['policial', 'crimen', 'asesinato', 'robo',
                                    'detenido', 'allanamiento', 'tiroteo', 'narco', 'banda']

PORTALES_PRENSA = (
    "site:infobae.com OR site:clarin.com OR site:lanacion.com.ar OR site:pagina12.com.ar OR "
    "site:minutouno.com OR site:tn.com.ar OR site:perfil.com OR site:eldestapeweb.com OR "
    "site:lapoliticaonline.com OR site:iprofesional.com OR site:ambito.com OR site:cronista.com OR "
    "site:eleconomista.com.ar OR site:baenegocios.com OR site:reuters.com OR site:bloomberg.com OR "
    "site:eldiarioar.com OR site:gacetamercantil.com OR site:apertura.com OR "
    "site:cnnespanol.cnn.com OR site:elpais.com"
)

PORTALES_ACTUALIZACIONES = (
    PORTALES_PRENSA + " OR site:uif.gob.ar OR site:bcra.gob.ar OR site:cnv.gob.ar OR "
    "site:argentina.gob.ar OR site:cronista.com OR site:baenegocios.com"
)

DIAS_NOTICIAS = 5
DIAS_ACTUALIZACIONES = 30

session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) NewsBot/BCCL'})

# Hora Argentina sin pytz (UTC-3, sin DST)
TZ_AR = timezone(timedelta(hours=-3))
now_ar = datetime.now(TZ_AR)
MESES = ['enero','febrero','marzo','abril','mayo','junio',
         'julio','agosto','septiembre','octubre','noviembre','diciembre']
FECHA_HOY = f"{now_ar.day} de {MESES[now_ar.month-1]} de {now_ar.year} · {now_ar.strftime('%H:%M')} hs (ARG)"

# ── HELPERS ────────────────────────────────────────────────────────────────────
def clean_text(text):
    if not text:
        return "Sin descripción disponible."
    return BeautifulSoup(text, "html.parser").get_text()[:260] + "..."

def fetch_category(query, limit, negative_keywords, dias):
    url = (
        "https://news.google.com/rss/search?q="
        + urllib.parse.quote(query)
        + f"+when:{dias}d&hl=es-419&gl=AR&ceid=AR:es-419"
    )
    try:
        response = session.get(url, timeout=10)
        entries = feedparser.parse(response.content).entries
    except Exception:
        return []

    news_list = []
    seen_titles = set()
    seen_sources = {}

    for entry in entries:
        t_low = entry.title.lower()
        if len(entry.title) < 15 or entry.link.count('/') < 4:
            continue
        fuente = entry.source.title if hasattr(entry, 'source') else "Medio"
        # Máximo 3 por fuente → diversidad
        if seen_sources.get(fuente, 0) >= 3:
            continue
        if entry.title not in seen_titles and not any(n in t_low for n in negative_keywords):
            news_list.append({
                "fuente":  fuente,
                "titular": entry.title,
                "link":    entry.link,
                "resumen": clean_text(entry.get('summary', '')),
                "fecha":   entry.get('published', '')[:16],
            })
            seen_titles.add(entry.title)
            seen_sources[fuente] = seen_sources.get(fuente, 0) + 1

    return news_list[:limit]

# ── FETCH ──────────────────────────────────────────────────────────────────────
q_noticias = (
    f'({BASE_AML} OR "dólar blue") AND ("lavado" OR "blanqueo") AND ({PORTALES_PRENSA})'
)
news_noticias = fetch_category(q_noticias, 24, GENERAL_NEG, DIAS_NOTICIAS)

q_actualizaciones = (
    f'({BASE_AML}) AND '
    '("UIF" OR "GAFI" OR "BCRA" OR "ARCA" OR "CNV") AND '
    '("resolución" OR "comunicado" OR "normativa" OR "regulación" OR "circular" OR '
    '"disposición" OR "actualización" OR "ley" OR "decreto" OR "recomendación" OR "alerta" OR "informe") AND '
    f'"Argentina" AND ({PORTALES_ACTUALIZACIONES})'
)
news_actualizaciones = fetch_category(q_actualizaciones, 6, ACTUALIZACION_NEG, DIAS_ACTUALIZACIONES)

# ── IMÁGENES DE FONDO (economía / finanzas) ────────────────────────────────────
BG_NEWS = [
    "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=900&auto=format",
    "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=700&auto=format",
    "https://images.unsplash.com/photo-1559526324-4b87b5e36e44?w=700&auto=format",
    "https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?w=700&auto=format",
    "https://images.unsplash.com/photo-1526304640581-d334cdbbf45e?w=700&auto=format",
    "https://images.unsplash.com/photo-1642543492481-44e81e3914a7?w=700&auto=format",
    "https://images.unsplash.com/photo-1518186285589-2f7649de83e0?w=700&auto=format",
    "https://images.unsplash.com/photo-1601597111158-2fceff292cdc?w=700&auto=format",
    "https://images.unsplash.com/photo-1543286386-713bdd548da4?w=700&auto=format",
    "https://images.unsplash.com/photo-1507679799987-c73779587ccf?w=700&auto=format",
    "https://images.unsplash.com/photo-1553729459-efe14ef6055d?w=700&auto=format",
    "https://images.unsplash.com/photo-1590283603385-17ffb3a7f29f?w=700&auto=format",
    "https://images.unsplash.com/photo-1565372195458-9de0b320ef04?w=700&auto=format",
    "https://images.unsplash.com/photo-1464375117522-1311d6a5b81f?w=700&auto=format",
    "https://images.unsplash.com/photo-1621761191319-c6fb62004040?w=700&auto=format",
]

BG_REG = [
    "https://images.unsplash.com/photo-1521791136064-7986c2920216?w=700&auto=format",
    "https://images.unsplash.com/photo-1554224154-26032ffc0d07?w=700&auto=format",
    "https://images.unsplash.com/photo-1450101499163-c8848c66ca85?w=700&auto=format",
    "https://images.unsplash.com/photo-1507679799987-c73779587ccf?w=700&auto=format",
    "https://images.unsplash.com/photo-1590283603385-17ffb3a7f29f?w=700&auto=format",
    "https://images.unsplash.com/photo-1436491865332-7a61a109cc05?w=700&auto=format",
]

# ── RENDER ──────────────────────────────────────────────────────────────────────
def card_noticias(news_list):
    if not news_list:
        return '<div class="no-news">No se encontraron noticias para este período.</div>'
    out = []
    for i, n in enumerate(news_list):
        if i == 0:
            cls = "card-large"
        elif i < 3:
            cls = "card-medium"
        else:
            cls = "card-small"
        bg = BG_NEWS[i % len(BG_NEWS)]
        out.append(
            '<article class="card ' + cls + '" '
            'style="background-image:url(\'' + bg + '\')" '
            'onclick="window.open(\'' + n["link"] + '\',\'_blank\')">'
            '<div class="card-overlay"></div>'
            '<div class="card-content">'
            '<div class="card-top">'
            '<span class="badge">' + n["fuente"] + '</span>'
            '<span class="card-date">' + n["fecha"] + '</span>'
            '</div>'
            '<h3>' + n["titular"] + '</h3>'
            '<p class="desc">' + n["resumen"] + '</p>'
            '<span class="read-more">Leer nota &rarr;</span>'
            '</div></article>'
        )
    return "\n".join(out)

def card_actualizaciones(news_list):
    if not news_list:
        return '<div class="no-news">No se encontraron actualizaciones en los últimos 30 días.</div>'
    out = []
    for i, n in enumerate(news_list):
        bg = BG_REG[i % len(BG_REG)]
        out.append(
            '<article class="card card-reg" '
            'style="background-image:url(\'' + bg + '\')" '
            'onclick="window.open(\'' + n["link"] + '\',\'_blank\')">'
            '<div class="card-overlay"></div>'
            '<div class="card-content">'
            '<div class="card-top">'
            '<span class="badge badge-gold">' + n["fuente"] + '</span>'
            '<span class="card-date">' + n["fecha"] + '</span>'
            '</div>'
            '<h3>' + n["titular"] + '</h3>'
            '<p class="desc">' + n["resumen"] + '</p>'
            '<span class="read-more gold-link">Ver resolución &rarr;</span>'
            '</div></article>'
        )
    return "\n".join(out)

# ── HTML ───────────────────────────────────────────────────────────────────────
COUNT_N = str(len(news_noticias))
COUNT_A = str(len(news_actualizaciones))

HTML_PARTS = [
"""<!DOCTYPE html>
<html lang="es">
<head>
...
</html>""",
]

html_final = "".join(HTML_PARTS)

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_final)

print("OK: " + COUNT_N + " noticias · " + COUNT_A + " actualizaciones · " + FECHA_HOY)
