import feedparser
import urllib.parse
from bs4 import BeautifulSoup
import socket
from datetime import datetime, timezone, timedelta
import requests
import email.utils

socket.setdefaulttimeout(30)

tz_ar = timezone(timedelta(hours=-3))
now_ar = datetime.now(tz_ar)
meses = ['enero','febrero','marzo','abril','mayo','junio',
         'julio','agosto','septiembre','octubre','noviembre','diciembre']
fecha_hoy = "{} de {} de {} - {} hs (ARG)".format(
    now_ar.day, meses[now_ar.month - 1], now_ar.year, now_ar.strftime('%H:%M')
)

NEGATIVE_FILTER = [
    'dental', 'dientes', 'odontologia', 'aguacate', 'receta', 'futbol', 'clima',
    'vinagre', 'almohada', 'mancha', 'jabon', 'limpieza', 'ropa', 'suavizante',
    'lavarropas', 'pelo', 'cutis', 'dieta', 'cocina'
]
ACTUALIZACION_NEG = NEGATIVE_FILTER + [
    'policial', 'crimen', 'asesinato', 'robo', 'detenido', 'allanamiento', 'tiroteo', 'narco', 'banda'
]

SITES_GOV = (
    "site:argentina.gob.ar OR site:afip.gob.ar OR site:bcra.gob.ar OR "
    "site:cnv.gov.ar OR site:fiscales.gob.ar OR site:uif.gob.ar"
)
SITES_AR = (
    "site:cronista.com OR site:ambito.com OR site:iprofesional.com OR site:infobae.com OR "
    "site:lanacion.com.ar OR site:clarin.com OR site:tn.com.ar OR site:perfil.com OR "
    "site:baenegocios.com OR site:eldiarioar.com OR site:pagina12.com.ar OR "
    "site:lapoliticaonline.com OR site:eleconomista.com.ar OR "
    "site:gacetamercantil.com OR site:apertura.com OR site:minutouno.com"
)
SITES_INTL = (
    "site:bloomberg.com OR site:reuters.com OR site:cnnespanol.cnn.com OR "
    "site:elpais.com OR site:bbc.com"
)

DIAS_NOTICIAS = 5
DIAS_ACTUALIZACIONES = 30

session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0 NewsBot/BCCL'})


def clean_summary(text):
    if not text:
        return "Sin descripcion disponible."
    return BeautifulSoup(text, "html.parser").get_text()[:240] + "..."


def fetch_news(query, limit, neg_filter, dias):
    # when: va al final del query codificado para que Google lo respete
    q_encoded = urllib.parse.quote(query) + "+when:" + str(dias) + "d"
    url = "https://news.google.com/rss/search?q={}&hl=es-419&gl=AR&ceid=AR:es-419".format(q_encoded)
    # Fecha limite para filtrar por codigo
    fecha_limite = datetime.now(timezone.utc) - timedelta(days=dias)
    try:
        resp = session.get(url, timeout=15)
        entries = feedparser.parse(resp.content).entries
    except Exception as e:
        print("Error:", e)
        return []

    results = []
    seen_titles = set()
    seen_sources = {}

    for entry in entries:
        t_low = entry.title.lower()
        if len(entry.title) < 15 or entry.link.count('/') < 4:
            continue
        fuente = entry.source.title if hasattr(entry, 'source') else "Medio"
        if seen_sources.get(fuente, 0) >= 3:
            continue
        if entry.title not in seen_titles and not any(w in t_low for w in neg_filter):
            # Filtro de fecha por codigo: descarta noticias mas viejas que 'dias'
            pub_raw = entry.get('published', '')
            if pub_raw:
                try:
                    pub_dt = datetime(*email.utils.parsedate(pub_raw)[:6], tzinfo=timezone.utc)
                    if pub_dt < fecha_limite:
                        continue
                except Exception:
                    pass  # si no se puede parsear la fecha, la incluimos igual
            fecha_fmt = pub_raw[:16] if pub_raw else ''
            results.append({
                "fuente":  fuente,
                "titular": entry.title,
                "link":    entry.link,
                "fecha":   fecha_fmt,
                "resumen": clean_summary(entry.summary if 'summary' in entry else "")
            })
            seen_titles.add(entry.title)
            seen_sources[fuente] = seen_sources.get(fuente, 0) + 1

    return results[:limit]


# TAB 1 - NOTICIAS
q_arg = (
    '("lavado de dinero" OR "lavado de activos" OR "blanqueo de capitales" OR "blanqueamiento de capitales") '
    'AND ("Argentina" OR "argentino" OR "BCRA" OR "UIF" OR "peso argentino") '
    'AND ({})'.format(SITES_AR)
)
q_intl = (
    '("lavado de dinero" OR "lavado de activos" OR "blanqueo de capitales" OR "money laundering") '
    'AND ({})'.format(SITES_INTL)
)
news_arg  = fetch_news(q_arg,  20, NEGATIVE_FILTER, DIAS_NOTICIAS)
news_intl = fetch_news(q_intl,  8, NEGATIVE_FILTER, DIAS_NOTICIAS)
titulares_arg = set(n["titular"] for n in news_arg)
news_intl = [n for n in news_intl if n["titular"] not in titulares_arg]
news_noticias = (news_arg + news_intl)[:25]

# TAB 2 - ACTUALIZACIONES
q_act = (
    '("lavado de dinero" OR "lavado de activos" OR "blanqueo" OR "AML") '
    'AND ("UIF" OR "GAFI" OR "BCRA" OR "ARCA" OR "CNV") '
    'AND ("resolucion" OR "comunicado" OR "normativa" OR "circular" OR '
    '"disposicion" OR "decreto" OR "ley" OR "alerta" OR "informe") '
    'AND "Argentina" '
    'AND (({}) OR ({}))'.format(SITES_GOV, SITES_AR)
)
news_act = fetch_news(q_act, 6, ACTUALIZACION_NEG, DIAS_ACTUALIZACIONES)

print("Noticias: {} | Actualizaciones: {} | {}".format(
    len(news_noticias), len(news_act), fecha_hoy))


def make_cards(news_list):
    if not news_list:
        return '<p class="empty">No se encontraron noticias para este periodo.</p>'
    html = ""
    for n in news_list:
        titular = n["titular"].replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;')
        resumen  = n["resumen"].replace('<', '&lt;').replace('>', '&gt;')
        fuente   = n["fuente"].replace('<', '&lt;').replace('>', '&gt;')
        link     = n["link"]
        fecha    = n["fecha"]
        html += (
            '<div class="card">'
            '<span class="badge">' + fuente + '</span>'
            '<h3><a href="' + link + '" target="_blank" rel="noopener">' + titular + '</a></h3>'
            '<p class="fecha">' + fecha + '</p>'
            '<p class="desc">' + resumen + '</p>'
            '</div>\n'
        )
    return html


cards_not = make_cards(news_noticias)
cards_act = make_cards(news_act)
cnt_n     = str(len(news_noticias))
cnt_a     = str(len(news_act))

css = (
    "<style>\n"
    ":root { --azul: #004a80; --dorado: #d4af37; --celeste: #1a73e8; }\n"
    "* { box-sizing: border-box; margin: 0; padding: 0; }\n"
    "body { font-family: Inter, Arial, sans-serif; background: #f2f4f7; color: #1a1a1a; }\n"
    "header { background: var(--azul); color: white; text-align: center; padding: 36px 20px 28px; border-bottom: 4px solid var(--dorado); }\n"
    "header h1 { font-size: 1.9rem; font-weight: 900; margin-bottom: 4px; }\n"
    "header p { font-size: 0.9rem; font-weight: 600; opacity: 0.8; }\n"
    ".fecha-header { font-size: 0.72rem; opacity: 0.6; margin-top: 6px; font-weight: 400; }\n"
    ".tabs { display: flex; justify-content: center; background: #fff; position: sticky; top: 0; z-index: 100; box-shadow: 0 2px 8px rgba(0,0,0,0.08); border-bottom: 1px solid #e0e0e0; }\n"
    ".tab-btn { padding: 15px 28px; border: none; background: none; cursor: pointer; font-family: inherit; font-weight: 700; font-size: 0.8rem; letter-spacing: 0.05em; text-transform: uppercase; color: #777; border-bottom: 3px solid transparent; transition: all 0.2s; }\n"
    ".tab-btn:hover { color: #333; }\n"
    ".tab-btn.active { color: var(--azul); border-bottom-color: var(--azul); }\n"
    ".tab-count { display: inline-block; background: #eee; color: #555; font-size: 0.6rem; padding: 1px 6px; border-radius: 10px; margin-left: 6px; font-weight: 800; }\n"
    ".tab-btn.active .tab-count { background: var(--azul); color: white; }\n"
    ".page { display: none; padding: 28px 16px 60px; min-height: 80vh; }\n"
    ".page.active { display: block; }\n"
    "#noticias { background: #f0f7ff; }\n"
    "#actualizaciones { background: #fffdf5; }\n"
    ".section-header { max-width: 1100px; margin: 0 auto 20px; padding-bottom: 10px; border-bottom: 2px solid #e0e0e0; display: flex; align-items: baseline; justify-content: space-between; flex-wrap: wrap; gap: 6px; }\n"
    ".section-title { font-size: 0.7rem; font-weight: 800; letter-spacing: 0.12em; text-transform: uppercase; color: #888; }\n"
    ".section-period { font-size: 0.65rem; color: #aaa; font-weight: 600; }\n"
    ".grid { max-width: 1100px; margin: 0 auto; display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 18px; }\n"
    ".card { background: #ffffff; border-radius: 10px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); border-left: 5px solid #ddd; display: flex; flex-direction: column; gap: 8px; transition: transform 0.18s, box-shadow 0.18s; }\n"
    ".card:hover { transform: translateY(-3px); box-shadow: 0 8px 20px rgba(0,0,0,0.1); }\n"
    "#noticias .card { border-left-color: var(--celeste); }\n"
    "#actualizaciones .card { border-left-color: var(--dorado); }\n"
    ".badge { display: inline-block; padding: 3px 8px; border-radius: 4px; font-size: 0.58rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.08em; align-self: flex-start; }\n"
    "#noticias .badge { background: #dbeafe; color: #1e40af; }\n"
    "#actualizaciones .badge { background: #fef3cd; color: #856404; }\n"
    "h3 { font-size: 1.05rem; font-weight: 800; line-height: 1.35; }\n"
    "h3 a { text-decoration: none; color: #111; }\n"
    "h3 a:hover { color: var(--azul); text-decoration: underline; }\n"
    ".fecha { font-size: 0.65rem; color: #aaa; font-weight: 600; }\n"
    ".desc { font-size: 0.85rem; color: #555; line-height: 1.55; flex: 1; }\n"
    ".empty { text-align: center; color: #888; padding: 40px; font-size: 0.9rem; }\n"
    "footer { background: var(--azul); color: rgba(255,255,255,0.5); text-align: center; padding: 18px; font-size: 0.68rem; border-top: 3px solid var(--dorado); }\n"
    "footer strong { color: var(--dorado); }\n"
    "@media (max-width: 600px) { header h1 { font-size: 1.4rem; } .tab-btn { padding: 12px 12px; font-size: 0.7rem; } .grid { grid-template-columns: 1fr; } }\n"
    "</style>\n"
)

js = (
    "<script>\n"
    "function showTab(tabId, btn) {\n"
    "  document.querySelectorAll('.page').forEach(function(p) { p.classList.remove('active'); });\n"
    "  document.querySelectorAll('.tab-btn').forEach(function(b) { b.classList.remove('active'); });\n"
    "  document.getElementById(tabId).classList.add('active');\n"
    "  btn.classList.add('active');\n"
    "  window.scrollTo({ top: 0, behavior: 'smooth' });\n"
    "}\n"
    "</script>\n"
)

html = (
    "<!DOCTYPE html>\n"
    "<html lang='es'>\n"
    "<head>\n"
    "<meta charset='UTF-8'>\n"
    "<meta name='viewport' content='width=device-width, initial-scale=1.0'>\n"
    "<title>Resumen AML - BCCL</title>\n"
    "<link href='https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&display=swap' rel='stylesheet'>\n"
    + css +
    "</head>\n"
    "<body>\n"
    "<header>\n"
    "  <h1>Resumen de Noticias AML</h1>\n"
    "  <p>Monitor de Cumplimiento &middot; BCCL</p>\n"
    "  <p class='fecha-header'>" + fecha_hoy + "</p>\n"
    "</header>\n"
    "<div class='tabs'>\n"
    "  <button class='tab-btn active' onclick=\"showTab('noticias', this)\">\n"
    "    Noticias <span class='tab-count'>" + cnt_n + "</span>\n"
    "  </button>\n"
    "  <button class='tab-btn' onclick=\"showTab('actualizaciones', this)\">\n"
    "    Actualizaciones Normativas <span class='tab-count'>" + cnt_a + "</span>\n"
    "  </button>\n"
    "</div>\n"
    "<div id='noticias' class='page active'>\n"
    "  <div class='section-header'>\n"
    "    <span class='section-title'>Argentina &amp; Internacional &middot; Lavado &middot; Blanqueo</span>\n"
    "    <span class='section-period'>Ultimos 5 dias</span>\n"
    "  </div>\n"
    "  <div class='grid'>\n"
    + cards_not +
    "  </div>\n"
    "</div>\n"
    "<div id='actualizaciones' class='page'>\n"
    "  <div class='section-header'>\n"
    "    <span class='section-title'>UIF &middot; GAFI &middot; BCRA &middot; ARCA &middot; CNV &mdash; Resoluciones y Normativas</span>\n"
    "    <span class='section-period'>Ultimos 30 dias</span>\n"
    "  </div>\n"
    "  <div class='grid'>\n"
    + cards_act +
    "  </div>\n"
    "</div>\n"
    "<footer>\n"
    "  Generado para <strong>AML &middot; BCCL</strong> &nbsp;&middot;&nbsp; "
    "Fuente: Google News &nbsp;&middot;&nbsp; " + fecha_hoy + "\n"
    "</footer>\n"
    + js +
    "</body>\n"
    "</html>\n"
)

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("LISTO - index.html generado.")
