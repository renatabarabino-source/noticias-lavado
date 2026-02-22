import feedparser
import urllib.parse
from bs4 import BeautifulSoup
import socket
from datetime import datetime
import requests

socket.setdefaulttimeout(10)

# --- CONFIGURACIÓN ---
BASE_AML = '("lavado de dinero" OR "lavado de activos" OR "blanqueo" OR "blanqueamiento" OR "AML")'

GENERAL_NEG = [
    'dental', 'dientes', 'odontología', 'aguacate', 'receta',
    'fútbol', 'clima', 'vinagre', 'limpieza'
]

ACTUALIZACION_NEG = GENERAL_NEG + [
    'policial', 'crimen', 'asesinato', 'robo', 'detenido',
    'allanamiento', 'tiroteo'
]

PORTALES_PRENSA = (
    "site:infobae.com OR site:clarin.com OR site:lanacion.com.ar OR "
    "site:pagina12.com.ar OR site:minutouno.com OR site:tn.com.ar OR "
    "site:perfil.com OR site:eldestapeweb.com OR site:lapoliticaonline.com OR "
    "site:iprofesional.com OR site:ambito.com OR site:cronista.com OR "
    "site:eleconomista.com.ar OR site:baenegocios.com OR site:reuters.com OR "
    "site:bloomberg.com OR site:eldiarioar.com OR site:prensaobrera.com OR "
    "site:gacetamercantil.com OR site:apertura.com OR site:cnnespanol.cnn.com OR "
    "site:elpais.com"
)

PORTALES_ACTUALIZACIONES = (
    f"{PORTALES_PRENSA} OR site:uif.gob.ar OR site:bcra.gob.ar OR "
    "site:cnv.gob.ar OR site:argentina.gob.ar"
)

DIAS_ATRAS = 5

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 NewsBot/BCCL'
})


# -------------------------------------------------
# UTILIDADES
# -------------------------------------------------

def clean_text(text):
    if not text:
        return "Sin descripción disponible."
    return BeautifulSoup(text, "html.parser").get_text()[:250] + "..."


def fetch_category(query, limit, negative_keywords):

    url = (
        "https://news.google.com/rss/search?"
        f"q={urllib.parse.quote(query)}+when:{DIAS_ATRAS}d"
        "&hl=es-419&gl=AR&ceid=AR:es-419"
    )

    try:
        response = session.get(url, timeout=10)
        entries = feedparser.parse(response.content).entries
    except Exception:
        return []

    news_list = []
    seen_titles = set()

    for entry in entries:

        title_low = entry.title.lower()

        if len(entry.title) < 15:
            continue

        if entry.title in seen_titles:
            continue

        if any(n in title_low for n in negative_keywords):
            continue

        news_list.append({
            "fuente": entry.source.title if hasattr(entry, 'source') else "Medio",
            "titular": entry.title,
            "link": entry.link,
            "resumen": clean_text(entry.summary if 'summary' in entry else ""),
            "fecha": entry.published if 'published' in entry else ""
        })

        seen_titles.add(entry.title)

    return news_list[:limit]


# -------------------------------------------------
# QUERIES
# -------------------------------------------------

# NOTICIAS GENERALES
q_noticias = (
    f'({BASE_AML} OR "dólar blue") AND ("lavado" OR "blanqueo") '
    f'AND ({PORTALES_PRENSA})'
)

news_noticias = fetch_category(
    q_noticias,
    limit=25,
    negative_keywords=GENERAL_NEG
)


# ACTUALIZACIONES REGULATORIAS
q_actualizaciones = (
    f'({BASE_AML}) AND '
    f'("UIF" OR "GAFI" OR "BCRA" OR "ARCA" OR "CNV") AND '
    f'("resolución" OR "comunicado" OR "normativa" OR '
    f'"regulación" OR "circular" OR "ley" OR "decreto") AND '
    f'("Argentina") AND ({PORTALES_ACTUALIZACIONES})'
)

news_actualizaciones = fetch_category(
    q_actualizaciones,
    limit=6,
    negative_keywords=ACTUALIZACION_NEG
)


# -------------------------------------------------
# FECHA
# -------------------------------------------------

fecha_hoy = datetime.now().strftime("%d de %B de %Y · %H:%M hs")


# -------------------------------------------------
# HTML
# -------------------------------------------------

def render_cards(news_list, tab_id):

    if not news_list:
        return '<div class="no-news">No se encontraron noticias.</div>'

    cards = []

    for i, n in enumerate(news_list):

        featured = "featured" if (i == 0 and tab_id == "noticias") else ""

        cards.append(f"""
        <article class="card {featured}">
            <div class="card-meta">
                <span class="badge">{n["fuente"]}</span>
                <span class="card-date">{n["fecha"][:16]}</span>
            </div>

            <h3>
                <a href="{n["link"]}" target="_blank">
                    {n["titular"]}
                </a>
            </h3>

            <p class="desc">{n["resumen"]}</p>

            <a href="{n["link"]}" target="_blank" class="read-more">
                Leer nota →
            </a>
        </article>
        """)

    return "\n".join(cards)


html_output = f"""
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>AML Monitor</title>
<meta name="viewport" content="width=device-width, initial-scale=1">

<style>
body {{
    font-family: Arial, sans-serif;
    background: #f4f1eb;
    margin: 0;
}}

header {{
    background: #0a1628;
    color: white;
    padding: 20px;
}}

h1 span {{
    color: #c9a84c;
}}

nav {{
    background: #102040;
    padding: 10px;
}}

nav button {{
    background: none;
    border: none;
    color: white;
    font-weight: bold;
    margin-right: 20px;
    cursor: pointer;
}}

nav button.active {{
    color: #c9a84c;
}}

.page {{
    display: none;
    padding: 20px;
}}

.page.active {{
    display: block;
}}

.grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px,1fr));
    gap: 15px;
}}

.card {{
    background: white;
    padding: 15px;
    border-top: 3px solid #0a1628;
}}

.card.featured {{
    grid-column: 1 / -1;
}}

footer {{
    background: #0a1628;
    color: #aaa;
    text-align: center;
    padding: 15px;
}}
</style>

</head>

<body>

<header>
<h1>AML<span>·</span>BCCL</h1>
<div>{fecha_hoy}</div>
</header>

<nav>
<button class="tab-btn active" onclick="showTab('noticias',this)">
Noticias ({len(news_noticias)})
</button>

<button class="tab-btn" onclick="showTab('actualizaciones',this)">
Actualizaciones ({len(news_actualizaciones)})
</button>
</nav>

<div id="noticias" class="page active">
<h2>Noticias</h2>
<div class="grid">
{render_cards(news_noticias, "noticias")}
</div>
</div>

<div id="actualizaciones" class="page">
<h2>Actualizaciones</h2>
<div class="grid">
{render_cards(news_actualizaciones, "actualizaciones")}
</div>
</div>

<footer>
Generado automáticamente · AML Monitor
</footer>

<script>

function showTab(id, btn) {{

    document.querySelectorAll('.page')
        .forEach(p => p.classList.remove('active'));

    document.querySelectorAll('.tab-btn')
        .forEach(b => b.classList.remove('active'));

    document.getElementById(id).classList.add('active');

    btn.classList.add('active');
}}

</script>

</body>
</html>
"""


# -------------------------------------------------
# OUTPUT
# -------------------------------------------------

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_output)


print(
    f"✅ index.html generado — "
    f"{len(news_noticias)} noticias · "
    f"{len(news_actualizaciones)} actualizaciones"
)
