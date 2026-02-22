import feedparser
import urllib.parse
from bs4 import BeautifulSoup
import socket
from datetime import datetime
import pytz
import requests

socket.setdefaulttimeout(10)

BASE_AML = '("lavado de dinero" OR "lavado de activos" OR "blanqueo" OR "blanqueamiento" OR "AML")'

GENERAL_NEG = ['dental', 'dientes', 'odontología', 'aguacate', 'receta', 'fútbol', 'clima', 'vinagre', 'limpieza']
ACTUALIZACION_NEG = GENERAL_NEG + ['policial', 'crimen', 'asesinato', 'robo', 'detenido', 'allanamiento', 'tiroteo']

PORTALES_PRENSA = (
    "site:infobae.com OR site:clarin.com OR site:lanacion.com.ar OR site:pagina12.com.ar OR "
    "site:minutouno.com OR site:tn.com.ar OR site:perfil.com OR site:eldestapeweb.com OR "
    "site:lapoliticaonline.com OR site:iprofesional.com OR site:ambito.com OR site:cronista.com OR "
    "site:eleconomista.com.ar OR site:baenegocios.com OR site:reuters.com OR site:bloomberg.com OR "
    "site:eldiarioar.com OR site:gacetamercantil.com OR site:apertura.com OR "
    "site:cnnespanol.cnn.com OR site:elpais.com"
)

PORTALES_ACTUALIZACIONES = (
    f"{PORTALES_PRENSA} OR site:uif.gob.ar OR site:bcra.gob.ar OR site:cnv.gob.ar OR "
    "site:argentina.gob.ar OR site:cronista.com OR site:baenegocios.com"
)

DIAS_NOTICIAS = 5
DIAS_ACTUALIZACIONES = 30

session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) NewsBot/BCCL'})

tz_ar = pytz.timezone('America/Argentina/Buenos_Aires')
now_ar = datetime.now(tz_ar)
meses = ['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre']
fecha_hoy = f"{now_ar.day} de {meses[now_ar.month-1]} de {now_ar.year} · {now_ar.strftime('%H:%M')} hs (ARG)"

def clean_text(text):
    if not text: return "Sin descripción disponible."
    return BeautifulSoup(text, "html.parser").get_text()[:260] + "..."

def fetch_category(query, limit, negative_keywords, dias):
    url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}+when:{dias}d&hl=es-419&gl=AR&ceid=AR:es-419"
    try:
        response = session.get(url, timeout=10)
        entries = feedparser.parse(response.content).entries
    except:
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
                "resumen": clean_text(entry.summary if 'summary' in entry else ""),
                "fecha": entry.published[:16] if 'published' in entry else ""
            })
            seen_titles.add(entry.title)
            seen_sources[fuente] = seen_sources.get(fuente, 0) + 1

    return news_list[:limit]

q_noticias = f'({BASE_AML} OR "dólar blue") AND ("lavado" OR "blanqueo") AND ({PORTALES_PRENSA})'
news_noticias = fetch_category(q_noticias, limit=24, negative_keywords=GENERAL_NEG, dias=DIAS_NOTICIAS)

q_actualizaciones = (
    f'({BASE_AML}) AND '
    f'("UIF" OR "GAFI" OR "BCRA" OR "ARCA" OR "CNV") AND '
    f'("resolución" OR "comunicado" OR "normativa" OR "regulación" OR "circular" OR '
    f'"disposición" OR "actualización" OR "ley" OR "decreto" OR "recomendación" OR "alerta" OR "informe") AND '
    f'("Argentina") AND ({PORTALES_ACTUALIZACIONES})'
)
news_actualizaciones = fetch_category(q_actualizaciones, limit=6, negative_keywords=ACTUALIZACION_NEG, dias=DIAS_ACTUALIZACIONES)

BG_IMGS = [
    "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=800&auto=format",
    "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=600&auto=format",
    "https://images.unsplash.com/photo-1559526324-4b87b5e36e44?w=600&auto=format",
    "https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?w=600&auto=format",
    "https://images.unsplash.com/photo-1526304640581-d334cdbbf45e?w=600&auto=format",
    "https://images.unsplash.com/photo-1642543492481-44e81e3914a7?w=600&auto=format",
    "https://images.unsplash.com/photo-1518186285589-2f7649de83e0?w=600&auto=format",
    "https://images.unsplash.com/photo-1601597111158-2fceff292cdc?w=600&auto=format",
    "https://images.unsplash.com/photo-1543286386-713bdd548da4?w=600&auto=format",
    "https://images.unsplash.com/photo-1507679799987-c73779587ccf?w=600&auto=format",
    "https://images.unsplash.com/photo-1553729459-efe14ef6055d?w=600&auto=format",
    "https://images.unsplash.com/photo-1590283603385-17ffb3a7f29f?w=600&auto=format",
    "https://images.unsplash.com/photo-1565372195458-9de0b320ef04?w=600&auto=format",
    "https://images.unsplash.com/photo-1464375117522-1311d6a5b81f?w=600&auto=format",
    "https://images.unsplash.com/photo-1621761191319-c6fb62004040?w=600&auto=format",
]

def render_cards_noticias(news_list):
    if not news_list:
        return '<div class="no-news">No se encontraron noticias para este período.</div>'
    cards = []
    for i, n in enumerate(news_list):
        if i == 0:
            size_class = "card-large"
        elif i < 3:
            size_class = "card-medium"
        else:
            size_class = "card-small"
        bg = BG_IMGS[i % len(BG_IMGS)]
        cards.append(f'''
        <article class="card {size_class}" style="background-image:url('{bg}')" onclick="window.open('{n["link"]}','_blank')">
            <div class="card-overlay"></div>
            <div class="card-content">
                <div class="card-top">
                    <span class="badge">{n["fuente"]}</span>
                    <span class="card-date">{n["fecha"]}</span>
                </div>
                <h3>{n["titular"]}</h3>
                <p class="desc">{n["resumen"]}</p>
                <span class="read-more">Leer nota →</span>
            </div>
        </article>''')
    return "\n".join(cards)

def render_cards_actualizaciones(news_list):
    if not news_list:
        return '<div class="no-news">No se encontraron actualizaciones en los últimos 30 días.</div>'
    cards = []
    reg_imgs = [
        "https://images.unsplash.com/photo-1521791136064-7986c2920216?w=600&auto=format",
        "https://images.unsplash.com/photo-1554224154-26032ffc0d07?w=600&auto=format",
        "https://images.unsplash.com/photo-1450101499163-c8848c66ca85?w=600&auto=format",
        "https://images.unsplash.com/photo-1507679799987-c73779587ccf?w=600&auto=format",
        "https://images.unsplash.com/photo-1590283603385-17ffb3a7f29f?w=600&auto=format",
        "https://images.unsplash.com/photo-1436491865332-7a61a109cc05?w=600&auto=format",
    ]
    for i, n in enumerate(news_list):
        bg = reg_imgs[i % len(reg_imgs)]
        cards.append(f'''
        <article class="card card-reg" style="background-image:url('{bg}')" onclick="window.open('{n["link"]}','_blank')">
            <div class="card-overlay"></div>
            <div class="card-content">
                <div class="card-top">
                    <span class="badge badge-gold">{n["fuente"]}</span>
                    <span class="card-date">{n["fecha"]}</span>
                </div>
                <h3>{n["titular"]}</h3>
                <p class="desc">{n["resumen"]}</p>
                <span class="read-more gold-link">Ver resolución →</span>
            </div>
        </article>''')
    return "\n".join(cards)

HTML = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AML Monitor · BCCL</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --navy: #050d1a; --navy2: #0b1a2e; --navy3: #0f2040;
            --gold: #d4a843; --gold2: #f0c96a;
            --white: #f0eee8; --muted: rgba(240,238,232,0.5);
            --serif: 'DM Serif Display', Georgia, serif;
            --sans: 'DM Sans', system-ui, sans-serif;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: var(--sans); background: var(--navy); color: var(--white); min-height: 100vh; }}

        .hero {{ position: relative; min-height: 400px; display: flex; flex-direction: column; justify-content: flex-end; overflow: hidden; }}
        .hero-bg {{
            position: absolute; inset: 0;
            background-image: linear-gradient(to bottom, rgba(5,13,26,0.3) 0%, rgba(5,13,26,0.85) 70%, rgba(5,13,26,1) 100%), url('https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=1400&auto=format&fit=crop');
            background-size: cover; background-position: center;
            animation: slowzoom 20s ease-in-out infinite alternate;
        }}
        @keyframes slowzoom {{ from{{transform:scale(1)}} to{{transform:scale(1.06)}} }}
        .hero-content {{ position: relative; z-index: 2; max-width: 1200px; margin: 0 auto; width: 100%; padding: 0 24px 40px; }}
        .hero-eyebrow {{ font-size: 0.65rem; font-weight: 700; letter-spacing: 0.25em; text-transform: uppercase; color: var(--gold); margin-bottom: 10px; }}
        .hero-title {{ font-family: var(--serif); font-size: clamp(2.2rem, 5vw, 3.8rem); font-weight: 400; line-height: 1.1; color: #fff; margin-bottom: 10px; }}
        .hero-title em {{ font-style: italic; color: var(--gold2); }}
        .hero-sub {{ font-size: 0.82rem; color: var(--muted); font-weight: 500; }}

        .ticker-bar {{ background: var(--gold); overflow: hidden; white-space: nowrap; padding: 7px 0; }}
        .ticker-inner {{ display: inline-block; animation: ticker 40s linear infinite; }}
        .ticker-inner span {{ font-size: 0.68rem; font-weight: 700; color: var(--navy); letter-spacing: 0.08em; text-transform: uppercase; padding: 0 48px; }}
        @keyframes ticker {{ 0%{{transform:translateX(60vw)}} 100%{{transform:translateX(-100%)}} }}

        .nav-bar {{ background: rgba(5,13,26,0.97); backdrop-filter: blur(8px); position: sticky; top: 0; z-index: 100; border-bottom: 1px solid rgba(212,168,67,0.2); }}
        .nav-inner {{ max-width: 1200px; margin: 0 auto; padding: 0 24px; display: flex; align-items: center; }}
        .tab-btn {{ padding: 15px 22px; border: none; background: none; cursor: pointer; font-family: var(--sans); font-size: 0.7rem; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; color: var(--muted); border-bottom: 2px solid transparent; transition: all 0.25s; position: relative; top: 1px; }}
        .tab-btn:hover {{ color: var(--white); }}
        .tab-btn.active {{ color: var(--gold); border-bottom-color: var(--gold); }}
        .tab-count {{ display: inline-flex; align-items: center; justify-content: center; width: 17px; height: 17px; background: rgba(212,168,67,0.15); color: var(--gold); font-size: 0.57rem; border-radius: 50%; margin-left: 6px; }}
        .tab-btn.active .tab-count {{ background: var(--gold); color: var(--navy); }}

        .page {{ display: none; padding: 28px 24px 60px; }}
        .page.active {{ display: block; }}

        .section-label {{ max-width: 1200px; margin: 0 auto 18px; display: flex; align-items: center; gap: 12px; }}
        .section-label-line {{ flex: 1; height: 1px; background: rgba(212,168,67,0.18); }}
        .section-label-text {{ font-size: 0.62rem; font-weight: 700; letter-spacing: 0.18em; text-transform: uppercase; color: var(--gold); white-space: nowrap; }}

        .news-grid {{ max-width: 1200px; margin: 0 auto; display: grid; grid-template-columns: repeat(12, 1fr); grid-auto-rows: 185px; gap: 10px; }}

        .card {{ cursor: pointer; position: relative; border-radius: 6px; overflow: hidden; background-size: cover; background-position: center; transition: transform 0.3s, box-shadow 0.3s; }}
        .card:hover {{ transform: translateY(-4px) scale(1.01); box-shadow: 0 20px 50px rgba(0,0,0,0.6); }}
        .card-overlay {{ position: absolute; inset: 0; background: linear-gradient(to top, rgba(5,13,26,0.97) 0%, rgba(5,13,26,0.55) 55%, rgba(5,13,26,0.15) 100%); }}
        .card-content {{ position: relative; z-index: 2; height: 100%; display: flex; flex-direction: column; justify-content: flex-end; padding: 14px 16px; }}
        .card-top {{ display: flex; align-items: center; gap: 8px; margin-bottom: 5px; }}
        .badge {{ font-size: 0.53rem; font-weight: 800; letter-spacing: 0.1em; text-transform: uppercase; color: var(--white); background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.18); padding: 2px 7px; border-radius: 3px; }}
        .badge-gold {{ color: var(--navy); background: var(--gold); border-color: var(--gold); }}
        .card-date {{ font-size: 0.56rem; color: var(--muted); }}
        .card h3 {{ font-family: var(--serif); font-weight: 400; line-height: 1.3; color: #fff; margin-bottom: 4px; }}
        .card .desc {{ font-size: 0.74rem; color: rgba(240,238,232,0.62); line-height: 1.45; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }}
        .read-more {{ display: inline-block; margin-top: 6px; font-size: 0.63rem; font-weight: 700; letter-spacing: 0.08em; color: var(--gold2); text-transform: uppercase; }}
        .gold-link {{ color: var(--gold); }}

        .card-large  {{ grid-column: span 7; grid-row: span 3; }}
        .card-large h3 {{ font-size: 1.5rem; }}
        .card-large .desc {{ -webkit-line-clamp: 3; }}
        .card-medium {{ grid-column: span 5; grid-row: span 2; }}
        .card-medium h3 {{ font-size: 1.05rem; }}
        .card-small  {{ grid-column: span 4; grid-row: span 2; }}
        .card-small h3 {{ font-size: 0.88rem; }}
        .card-small .desc {{ display: none; }}

        .reg-grid {{ max-width: 1200px; margin: 0 auto; display: grid; grid-template-columns: repeat(auto-fill, minmax(330px, 1fr)); gap: 12px; }}
        .card-reg {{ min-height: 220px; }}
        .card-reg h3 {{ font-size: 1rem; }}
        .card-reg .desc {{ -webkit-line-clamp: 3; }}

        .no-news {{ text-align: center; color: var(--muted); padding: 60px 20px; font-size: 0.9rem; }}

        footer {{ background: #020810; border-top: 1px solid rgba(212,168,67,0.15); text-align: center; padding: 20px; font-size: 0.66rem; color: var(--muted); }}
        footer strong {{ color: var(--gold); }}

        @media (max-width: 800px) {{
            .card-large, .card-medium, .card-small {{ grid-column: span 12; grid-row: span 2; }}
            .card-small .desc {{ display: block; }}
        }}
        @media (max-width: 500px) {{
            .tab-btn {{ padding: 12px 10px; font-size: 0.63rem; }}
            .page {{ padding: 18px 12px 50px; }}
        }}
    </style>
</head>
<body>

<header class="hero">
    <div class="hero-bg"></div>
    <div class="hero-content">
        <p class="hero-eyebrow">● Monitor de Cumplimiento · AML · Argentina</p>
        <h1 class="hero-title">Prevención del<br><em>Lavado de Activos</em></h1>
        <p class="hero-sub">Actualizado: {fecha_hoy}</p>
    </div>
</header>

<div class="ticker-bar">
    <div class="ticker-inner">
        <span>UIF · Unidad de Información Financiera</span>
        <span>BCRA · Banco Central de la República Argentina</span>
        <span>CNV · Comisión Nacional de Valores</span>
        <span>GAFI · Grupo de Acción Financiera Internacional</span>
        <span>ARCA · Agencia de Recaudación y Control Aduanero</span>
        <span>PLA/FT · Prevención del Lavado de Activos y Financiamiento del Terrorismo</span>
    </div>
</div>

<nav class="nav-bar">
    <div class="nav-inner">
        <button class="tab-btn active" onclick="showTab('noticias', this)">
            Noticias <span class="tab-count">{len(news_noticias)}</span>
        </button>
        <button class="tab-btn" onclick="showTab('actualizaciones', this)">
            Actualizaciones Normativas <span class="tab-count">{len(news_actualizaciones)}</span>
        </button>
    </div>
</nav>

<div id="noticias" class="page active">
    <div class="section-label">
        <span class="section-label-text">Últimos {DIAS_NOTICIAS} días · AML · Lavado · Blanqueo</span>
        <div class="section-label-line"></div>
    </div>
    <div class="news-grid">
        {render_cards_noticias(news_noticias)}
    </div>
</div>

<div id="actualizaciones" class="page">
    <div class="section-label">
        <span class="section-label-text">Últimos 30 días · Resoluciones · Circulares · Normativas · UIF · GAFI · BCRA · ARCA · CNV</span>
        <div class="section-label-line"></div>
    </div>
    <div class="reg-grid">
        {render_cards_actualizaciones(news_actualizaciones)}
    </div>
</div>

<footer>
    Generado automáticamente para <strong>AML · BCCL</strong> &nbsp;·&nbsp; Fuente: Google News &nbsp;·&nbsp; {fecha_hoy}
</footer>

<script>
    function showTab(tabId, btn) {{
        document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.getElementById(tabId).classList.add('active');
        btn.classList.add('active');
        window.scrollTo({{top: 0, behavior: 'smooth'}});
    }}
</script>
</body>
</html>"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(HTML)

print(f"OK: {len(news_noticias)} noticias · {len(news_actualizaciones)} actualizaciones · {fecha_hoy}")
