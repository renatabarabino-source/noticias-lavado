import feedparser
import urllib.parse
from bs4 import BeautifulSoup
import socket
from datetime import datetime, timezone, timedelta
import requests

# --- CONFIGURACIÓN TÉCNICA ---
socket.setdefaulttimeout(30)
tz_ar = timezone(timedelta(hours=-3))
now_ar = datetime.now(tz_ar)

# --- 1. FILTROS DE EXCLUSIÓN TOTAL (LA "LISTA NEGRA") ---
# Si alguna de estas palabras aparece en el título, la noticia se descarta.
BLACK_LIST = [
    # Mercado y Cotizaciones (Lo que ya pediste)
    'cotiza', 'cotización', 'precio', 'minuto a minuto', 'brecha', 'riesgo país', 
    'reservas', 'compra el bcra', 'ventas del bcra', 'sube', 'baja', 'dolar hoy',
    
    # Higiene, Limpieza y Salud (Filtros de "Higiene")
    'jabón', 'detergente', 'limpieza', 'manchas', 'vinagre', 'bicarbonato', 
    'lavarropas', 'suavizante', 'ropa', 'cutis', 'piel', 'dental', 'odontología',
    'dientes', 'almohada', 'colchón', 'truco', 'remedio', 'casero', 'salud',
    
    # Deportes y Espectáculos
    'fútbol', 'partido', 'gol', 'messi', 'campeonato', 'liga', 'copa', 'tenis',
    'básquet', 'romance', 'separación', 'espectáculo', 'chismes', 'famosos',
    
    # Otros ruidos comunes
    'receta', 'cocina', 'clima', 'pronóstico', 'horóscopo', 'tránsito', 
    'vía expresa', 'accidente', 'falleció', 'vtv', 'feriado'
]

# --- 2. VALIDACIÓN TÉCNICA (Compliance) ---
# Términos que confirman que la noticia es de interés para el área
STRICT_KEYWORDS = [
    'uif', 'gafi', 'compliance', 'testaferro', 'maniobra', 'causa', 'justicia',
    'imputado', 'procesado', 'sujeto obligado', 'debida diligencia', 'lavado',
    'origen de fondos', 'justificación', 'ros', 'operación sospechosa',
    'inocencia fiscal', 'blanqueo', 'rulo cambiario', 'embargo'
]

SITES_PRENSA = (
    "site:cronista.com OR site:ambito.com OR site:iprofesional.com OR site:infobae.com OR "
    "site:lanacion.com.ar OR site:clarin.com OR site:perfil.com OR site:baenegocios.com"
)

session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0 Compliance-Monitor-BCCL'})

# --- 3. FUNCIONES ---

def clean_summary(text):
    if not text: return "Sin descripción disponible."
    try:
        # Extraemos solo el texto del resumen que manda Google News
        clean = BeautifulSoup(text, "html.parser").get_text()
        return clean[:220].replace('"', "'") + "..."
    except:
        return str(text)[:220] + "..."

def fetch_refined_news(query, limit=20, tech_only=False):
    # Agregamos los filtros negativos a la query de Google para ahorrar procesamiento
    neg_query = " ".join([f"-{word}" for word in BLACK_LIST[:15]]) # Google limita la cantidad de operadores
    full_query = f"{query} {neg_query} when:5d"
    
    url = "https://news.google.com/rss/search?q={}&hl=es-419&gl=AR&ceid=AR:es-419".format(
        urllib.parse.quote(full_query)
    )
    
    try:
        resp = session.get(url, timeout=20)
        feed = feedparser.parse(resp.content)
    except:
        return []

    results = []
    seen_titles = set()

    for entry in feed.entries:
        t_low = entry.title.lower()
        s_low = entry.summary.lower() if hasattr(entry, 'summary') else ""

        # FILTRO DE SEGURIDAD 1: Lista Negra local
        if any(w in t_low for w in BLACK_LIST):
            continue

        # FILTRO DE SEGURIDAD 2: Relevancia técnica si se solicita
        if tech_only:
            if not any(k in t_low or k in s_low for k in STRICT_KEYWORDS):
                continue

        if entry.title not in seen_titles:
            results.append({
                "fuente": entry.source.title if hasattr(entry, 'source') else "Medio",
                "titular": entry.title.split(" - ")[0], 
                "link": entry.link,
                "fecha": entry.get('published', 'Reciente')[:16],
                "resumen": clean_summary(entry.summary if 'summary' in entry else "")
            })
            seen_titles.add(entry.title)
            
    return results[:limit]

# --- 4. EJECUCIÓN ---

print("🔍 Filtrando ruidos y buscando noticias de AML...")

# Solapa 1: Foco en maniobras y blanqueo
q_noticias = f'("lavado de activos" OR "rulo cambiario" OR "blanqueo" OR "justificación de fondos") AND ({SITES_PRENSA})'
news_noticias = fetch_refined_news(q_noticias, limit=20)

# Solapa 2: Foco en organismos (UIF/GAFI/BCRA)
q_organismos = '("UIF" OR "GAFI" OR "CNV" OR "PROCELAC" OR "BCRA cumplimiento")'
news_actualizaciones = fetch_refined_news(q_organismos, limit=10, tech_only=True)

# --- 5. GENERACIÓN HTML (Dashboard) ---

def make_cards(news_list, type_class):
    if not news_list:
        return '<p style="grid-column:1/-1; text-align:center; padding:50px; color:#666;">No hay noticias técnicas relevantes en este periodo.</p>'
    
    html = ""
    for n in news_list:
        html += f"""
        <div class="card {type_class}">
            <div class="card-header">
                <span class="badge">{n['fuente']}</span>
                <span class="date">{n['fecha']}</span>
            </div>
            <h3><a href="{n['link']}" target="_blank">{n['titular']}</a></h3>
            <p class="desc">{n['resumen']}</p>
        </div>"""
    return html

# Generación del archivo final
fecha_str = now_ar.strftime('%d/%m/%Y %H:%M')
HTML_BODY = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>BCCL - Monitor AML</title>
    <style>
        :root {{ --primary: #004a80; --accent: #d4af37; --bg: #f8f9fa; }}
        body {{ font-family: 'Segoe UI', sans-serif; background: var(--bg); margin: 0; }}
        header {{ background: var(--primary); color: white; padding: 20px; text-align: center; border-bottom: 4px solid var(--accent); }}
        .tabs {{ display: flex; justify-content: center; background: white; sticky: top; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
        .tab-btn {{ padding: 15px 25px; border: none; background: none; cursor: pointer; font-weight: bold; color: #666; transition: 0.2s; }}
        .tab-btn.active {{ color: var(--primary); border-bottom: 3px solid var(--primary); }}
        .container {{ max-width: 1200px; margin: 20px auto; padding: 0 20px; }}
        .page {{ display: none; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 20px; }}
        .active {{ display: grid; }}
        .card {{ background: white; border-radius: 8px; padding: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); border-left: 5px solid #ddd; }}
        .c-news {{ border-left-color: #1a73e8; }}
        .c-tech {{ border-left-color: var(--accent); }}
        .badge {{ background: #f0f0f0; font-size: 0.7rem; padding: 3px 6px; border-radius: 3px; font-weight: 900; color: var(--primary); }}
        .date {{ font-size: 0.75rem; color: #999; float: right; }}
        h3 {{ font-size: 1rem; margin: 12px 0; line-height: 1.4; }}
        h3 a {{ text-decoration: none; color: #111; }}
        .desc {{ font-size: 0.88rem; color: #555; line-height: 1.5; }}
    </style>
</head>
<body>
    <header><h1>Monitor de Cumplimiento AML</h1><p>BCCL | {fecha_str}</p></header>
    <div class="tabs">
        <button class="tab-btn active" onclick="openTab(event, 'noticias')">Noticias Relevantes</button>
        <button class="tab-btn" onclick="openTab(event, 'tecnico')">Organismos y Normativa</button>
    </div>
    <div class="container">
        <div id="noticias" class="page active">{make_cards(news_noticias, 'c-news')}</div>
        <div id="tecnico" class="page">{make_cards(news_actualizaciones, 'c-tech')}</div>
    </div>
    <script>
        function openTab(evt, tabName) {{
            var i, page, tablinks;
            page = document.getElementsByClassName("page");
            for (i = 0; i < page.length; i++) page[i].classList.remove("active");
            tablinks = document.getElementsByClassName("tab-btn");
            for (i = 0; i < tablinks.length; i++) tablinks[i].classList.remove("active");
            document.getElementById(tabName).classList.add("active");
            evt.currentTarget.classList.add("active");
        }}
    </script>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(HTML_BODY)
print("✅ Dashboard generado en 'index.html' sin ruidos de limpieza o deportes.")
