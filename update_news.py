import feedparser
import urllib.parse
from bs4 import BeautifulSoup
import os
import socket
from datetime import datetime
import requests

socket.setdefaulttimeout(30)

# --- CONFIGURACIÓN DE FILTROS ---
# Filtro negativo extremo para eliminar "ruido" doméstico
NEGATIVE_FILTER = [
    'aguacate', 'salud', 'receta', 'dieta', 'fútbol', 'pronóstico', 'clima', 'vinagre', 
    'almohada', 'mancha', 'jabón', 'limpieza', 'lavarropas', 'ropa', 'tintorería', 
    'suavizante', 'cloro', 'bicarbonato', 'pelo', 'cutis'
]

DIAS_ATRAS = 5
MAX_NOTICIAS = 30

def get_image(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        img = soup.find("meta", property="og:image") or soup.find("meta", property="twitter:image")
        return img.get("content") or img.get("href") if img else ""
    except:
        return ""

def clean_summary(text):
    if not text: return "Sin descripción disponible."
    soup = BeautifulSoup(text, "html.parser")
    return soup.get_text()[:250] + "..."

def fetch_category(query, is_intl=False):
    gl = "US" if is_intl else "AR"
    hl = "en" if is_intl else "es-419"
    
    url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}+when:{DIAS_ATRAS}d&hl={hl}&gl={gl}&ceid={gl}:es-419"
    entries = feedparser.parse(url).entries
    
    news_list = []
    for entry in entries:
        t_low = entry.title.lower()
        if not any(n in t_low for n in NEGATIVE_FILTER):
            news_list.append({
                "fuente": entry.source.title if hasattr(entry, 'source') else "Medio",
                "titular": entry.title,
                "link": entry.link,
                "fecha": entry.get('published', 'Reciente'),
                "resumen": clean_summary(entry.summary if 'summary' in entry else ""),
                "img": get_image(entry.link)
            })
    return news_list[:MAX_NOTICIAS]

# --- ESTRATEGIA DE BÚSQUEDA POR SOLAPA ---

# 1. PRINCIPAL (NORMATIVAS): Foco en entes reguladores argentinos y GAFI
# Incluye ARCA, UIF, BCRA, CNV y leyes específicas.
query_principal = '("lavado de activos" OR "lavado de dinero" OR "AML" OR "blanqueo") AND (UIF OR BCRA OR ARCA OR CNV OR GAFI OR "resolución" OR "normativa")'
news_principal = fetch_category(query_principal)

# 2. ARGENTINA (ESCÁNDALOS Y MOVIMIENTOS): Foco en justicia y ahora incluye DÓLAR BLUE
# Buscamos la relación entre el mercado informal y el lavado.
query_argentina = '("lavado de dinero" OR "lavado de activos") AND ("dólar blue" OR "cuevas" OR "justicia" OR "corrupción" OR "imputado" OR "PROCELAC")'
news_argentina = fetch_category(query_argentina)

# 3. INTERNACIONAL: Foco global, sin entes locales como ARCA.
query_intl = '("money laundering" OR "lavado de activos") AND (FATF OR "Interpol" OR "FinCEN" OR "OFAC" OR "Global") -ARCA -UIF -BCRA'
news_intl = fetch_category(query_intl, is_intl=True)

# --- GENERACIÓN DE HTML ---
# (Mantenemos el diseño de solapas y fondos que pediste)
html_template = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Resumen de Noticias AML - BCCL</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&display=swap" rel="stylesheet">
    <style>
        :root {{ --p-color: #004a80; --a-color: #3498db; --i-color: #d4af37; }}
        body {{ font-family: 'Inter', sans-serif; margin: 0; background: #fdfdfd; }}
        header {{ background: var(--p-color); color: white; text-align: center; padding: 40px 20px; }}
        header h1 {{ margin: 0; font-weight: 900; font-size: 2.2rem; }}
        header p {{ margin: 10px 0 0; font-weight: 700; font-size: 1.2rem; opacity: 0.9; }}
        .tabs {{ display: flex; justify-content: center; background: #fff; position: sticky; top: 0; z-index: 100; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .tab-btn {{ padding: 15px 25px; border: none; background: none; cursor: pointer; font-weight: 700; font-size: 0.9rem; color: #666; border-bottom: 4px solid transparent; }}
        .tab-btn.active {{ color: var(--p-color); border-bottom-color: var(--p-color); }}
        .page {{ display: none; padding: 30px 15px; min-height: 80vh; }}
        .page.active {{ display: block; }}
        
        #principal {{ background: linear-gradient(rgba(255,255,255,0.9), rgba(255,255,255,0.9)), url('https://images.unsplash.com/photo-1554224155-1696413575b3?auto=format&fit=crop&w=1920&q=80'); background-size: cover; }}
        #argentina {{ background: linear-gradient(rgba(240,248,255,0.9), rgba(240,248,255,0.9)), url('
