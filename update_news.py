import feedparser
import urllib.parse
from bs4 import BeautifulSoup
import socket
from datetime import datetime, timezone, timedelta
import requests

# ── CONFIGURACIÓN TÉCNICA ──
socket.setdefaulttimeout(30)
tz_ar = timezone(timedelta(hours=-3))
now_ar = datetime.now(tz_ar)

# ── 1. DEFINICIÓN DE FILTROS (ELIMINACIÓN DE RUIDO) ──

# Términos que disparan la exclusión inmediata (Cotizaciones y BCRA macro)
BLACK_LIST = [
    'cotiza', 'precio', 'minuto a minuto', 'brecha', 'riesgo país', 
    'reservas', 'compra el bcra', 'ventas del bcra', 'sube', 'baja',
    'volatilidad', 'mercado'
]

# Palabras técnicas que VALIDAN que una noticia es de cumplimiento
STRICT_KEYWORDS = [
    'uif', 'gafi', 'compliance', 'testaferro', 'maniobra', 'causa', 
    'imputado', 'procesado', 'sujeto obligado', 'debida diligencia', 
    'origen de fondos', 'justificación', 'ros', 'operación sospechosa',
    'arrepentido', 'enriquecimiento', 'patrimonio'
]

# Fuentes de Prensa Seleccionadas
SITES_PRENSA = (
    "site:cronista.com OR site:ambito.com OR site:iprofesional.com OR site:infobae.com OR "
    "site:lanacion.com.ar OR site:clarin.com OR site:perfil.com OR site:baenegocios.com"
)

session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0 NewsBot/BCCL-Compliance'})

# ── 2. FUNCIONES DE PROCESAMIENTO ──

def clean_summary(text):
    if not text: return "Sin descripción disponible."
    try:
        # Limpieza de HTML y recorte
        clean = BeautifulSoup(text, "html.parser").get_text()
        return clean[:220] + "..."
    except:
        return str(text)[:220] + "..."

def fetch_aml_news(query, limit=20, check_technical=False):
    # Agregamos operadores negativos directamente a la URL de Google para mayor eficiencia
    excluded_query = " ".join([f"-{word}" for word in BLACK_LIST])
    full_query = f"{query} {excluded_query} when:5d"
    
    url = "https://news.google.com/rss/search?q={}&hl=es-419&gl=AR&ceid=AR:es-419".format(
        urllib.parse.quote(full_query)
    )
    
    try:
        resp = session.get(url, timeout=20)
        entries = feedparser.parse(resp.content).entries
    except:
        return []

    results = []
    seen_titles = set()

    for entry in entries:
        t_low = entry.title.lower()
        s_low = entry.summary.lower() if hasattr(entry, 'summary') else ""

        # Filtro de seguridad extra: Si el título tiene palabras de precio, se ignora
        if any(w in t_low for w in BLACK_LIST):
            continue

        # Si check_technical es True, debe tener al menos una palabra técnica de cumplimiento
        if check_technical:
            if not any(k in t_low or k in s_low for k in STRICT_KEYWORDS):
                continue

        if entry.title not in seen_titles and len(entry.title) > 20:
            results.append({
                "fuente": entry.source.title if hasattr(entry, 'source') else "Medio",
                "titular": entry.title.split(" - ")[0], # Limpia el nombre del medio del título
                "link": entry.link,
                "fecha": entry.get('published', 'Reciente')[:16],
                "resumen": clean_summary(entry.summary if 'summary' in entry else "")
            })
            seen_titles.add(entry.title)
            
    return results[:limit]

# ── 3. EJECUCIÓN DE BÚSQUEDAS ESPECÍFICAS ──

# Solapa 1: Prensa General (Lavado, Rulo, Inocencia Fiscal)
# Buscamos específicamente el "Rulo" o "Inocencia Fiscal" que son los temas de interés 2026
q_prensa = f'("lavado de activos" OR "rulo cambiario" OR "inocencia fiscal" OR "justificación de fondos") AND ({SITES_PRENSA})'
news_noticias = fetch_aml_news(q_prensa, limit=25)

# Solapa 2: Actualizaciones Técnicas (Organismos + Normativa)
q_tecnica = f'("UIF" OR "GAFI" OR "CNV" OR "BCRA cumplimiento" OR "ley de blanqueo")'
news_actualizaciones = fetch_aml_news(q_tecnica, limit=10, check_technical=True)

# ── 4. GENERACIÓN DEL DASHBOARD HTML ──

def make_cards(news_list, type_class):
    if not news_list:
        return '<div class="no-data">No se detectaron movimientos técnicos de interés en las últimas 120 horas.</div>'
    
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
        </div>
        """
    return html

fecha_emision = now_ar.strftime('%d/%m/%Y %H:%M')

HTML_TEMPLATE = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>BCCL - Monitor de Cumplimiento AML</title>
    <style>
        :root {{ --azul: #004a80; --dorado: #b8973d; --bg: #f0f2f5; }}
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: var(--bg); margin: 0; color: #333; }}
        header {{ background: var(--azul); color: white; padding: 20px; text-align: center; border-bottom: 5px solid var(--dorado); }}
        .tabs {{ display: flex; justify-content: center; background: white; position: sticky; top: 0; z-index: 1000; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .tab-btn {{ padding: 15px 30px; border: none; background: none; cursor: pointer; font-weight: bold; color: #666; border-bottom: 3px solid transparent; transition: 0.3s; }}
        .
