import feedparser
import urllib.parse
from bs4 import BeautifulSoup
import socket
from datetime import datetime, timezone, timedelta
import requests
import email.utils

# Configuración técnica
socket.setdefaulttimeout(30)
tz_ar = timezone(timedelta(hours=-3))
now_ar = datetime.now(tz_ar)
meses = ['enero','febrero','marzo','abril','mayo','junio',
         'julio','agosto','septiembre','octubre','noviembre','diciembre']
fecha_hoy = "{} de {} de {} - {} hs (ARG)".format(
    now_ar.day, meses[now_ar.month - 1], now_ar.year, now_ar.strftime('%H:%M')
)

# 1. FILTROS NEGATIVOS (Cero limpieza, historia o policial común)
NEGATIVE_FILTER = [
    'dental', 'dientes', 'odontologia', 'aguacate', 'receta', 'futbol', 'clima',
    'vinagre', 'almohada', 'mancha', 'jabon', 'limpieza', 'ropa', 'suavizante',
    'lavarropas', 'pelo', 'cutis', 'dieta', 'cocina', 'hace 100 años', 'efemerides',
    'tiroteo', 'asesinato', 'sicario', 'homicidio', 'choque', 'accidente', 'herido',
    'sangre', 'fallecio', 'muerto', 'cadaver', 'victima', 'vecinos', 'persecucion'
]

# 2. KEYWORDS TÉCNICAS (La noticia DEBE tener algo de esto para ser válida)
TECHNICAL_KEYWORDS = [
    'uif', 'gafi', 'bcra', 'cnv', 'arca', 'procelac', 'testaferro', 'financiero', 
    'capitales', 'maniobra', 'empresa', 'sociedad', 'trama', 'judicial', 'causa', 
    'imputado', 'procesado', 'lavado', 'activos', 'dinero', 'blanqueo', 'aml', 'compliance'
]

SITES_AR = (
    "site:cronista.com OR site:ambito.com OR site:iprofesional.com OR site:infobae.com OR "
    "site:lanacion.com.ar OR site:clarin.com OR site:tn.com.ar OR site:perfil.com OR "
    "site:baenegocios.com OR site:eldiarioar.com OR site:pagina12.com.ar OR "
    "site:lapoliticaonline.com OR site:eleconomista.com.ar OR site:gacetamercantil.com"
)

SITES_INTL = "site:bloomberg.com OR site:reuters.com OR site:cnnespanol.cnn.com OR site:elpais.com"

DIAS_NOTICIAS = 5
MAX_NOTICIAS = 25 # Tope solicitado

session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0 NewsBot/BCCL'})

def clean_summary(text):
    if not text: return "Sin descripcion disponible."
    return BeautifulSoup(text, "html.parser").get_text()[:240] + "..."

def fetch_news_strict(query, limit, neg_filter, dias):
    q_encoded = urllib.parse.quote(query) + "+when:" + str(dias) + "d"
    url = "https://news.google.com/rss/search?q={}&hl=es-419&gl=AR&ceid=AR:es-419".format(q_encoded)
    fecha_limite = datetime.now(timezone.utc) - timedelta(days=dias)
    
    try:
        resp = session.get(url, timeout=15)
        entries = feedparser.parse(resp.content).entries
    except:
        return []

    results = []
    seen_titles = set()
    
    for entry in entries:
        t_low = entry.title.lower()
        s_low = entry.summary.lower() if hasattr(entry, 'summary') else ""
        
        # --- FILTRADO DE RELEVANCIA ---
        # 1. Longitud y links basura
        if len(entry.title) < 20 or entry.link.count('/') < 4: continue
        
        # 2. Filtro negativo
        if any(w in t_low for w in neg_filter): continue
        
        # 3. VALIDACIÓN TÉCNICA (Blindaje contra policiales/limpieza)
        if not any(k in t_low or k in s_low for k in TECHNICAL_KEYWORDS): continue

        if entry.title not in seen_titles:
            # Filtro de fecha
            pub_raw = entry.get('published', '')
            if pub_raw:
                try:
                    pub_dt = datetime(*email.utils.parsedate(pub_raw)[:6], tzinfo=timezone.utc)
                    if pub_dt < fecha_limite: continue
                except: pass
            
            results.append({
                "fuente":  entry.source.title if hasattr(entry, 'source') else "Medio",
                "titular": entry.title.replace('"', '&quot;'),
                "link":    entry.link,
                "fecha":   pub_raw[:16] if pub_raw else 'Reciente',
                "resumen": clean_summary(entry.summary if 'summary' in entry else "")
            })
            seen_titles.add(entry.title)

    return results[:limit]

# --- PROCESAMIENTO ---
# Buscamos noticias con frases exactas para mayor precisión
q_arg = '("lavado de activos" OR "lavado de dinero" OR "blanqueo de capitales") AND ({})'.format(SITES_AR)
q_intl = '("money laundering" OR "lavado de activos") AND ({})'.format(SITES_INTL)

news_arg = fetch_news_strict(q_arg, 20, NEGATIVE_FILTER, DIAS_NOTICIAS)
news_intl = fetch_news_strict(q_intl, 10, NEGATIVE_FILTER, DIAS_NOTICIAS)

# Unir y limitar a 25
titulares_arg = set(n["titular"] for n in news_arg)
news_intl = [n for n in news_intl if n["titular"] not in titulares_arg]
news_noticias = (news_arg + news_intl)[:MAX_NOTICIAS]

# Actualizaciones (30 días)
q_act = '("uif" OR "gafi" OR "bcra" OR "cnv" OR "arca") AND ("normativa" OR "resolucion" OR "ley")'
news_act = fetch_news_strict(q_act, 6, NEGATIVE_FILTER + ['policial'], 30)

# (Aquí se mantiene tu código de generación de HTML igual al anterior)
