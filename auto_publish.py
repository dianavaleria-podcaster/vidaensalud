
import urllib.request
import requests
import xml.etree.ElementTree as ET
import re
import os
import html
import time
from datetime import datetime
import google.generativeai as genai
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# --- Configuration ---
RSS_URL = "https://anchor.fm/s/10f10dc44/podcast/rss"
OUTPUT_DIR = "podcast"
TRANSCRIPT_DIR = "transcripciones"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TRANSCRIPTION_LIMIT = 50  # Aumentado para terminar los últimos 42 episodios de una vez

if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)
if not os.path.exists(TRANSCRIPT_DIR): os.makedirs(TRANSCRIPT_DIR)

# --- Helpers ---
def get_short_description(html_content, length=160):
    if not html_content: return ""
    text = re.sub(r'<[^>]+>', '', html_content)
    text = html.unescape(text)
    text = ' '.join(text.split())
    if len(text) > length:
        return text[:length].rsplit(' ', 1)[0] + "..."
    return text

def clean_description(desc):
    if not desc: return ""
    pattern = r'<p><a href="https://vidaensalud\.es"[^>]*>Ve a escucharlo el episodio en este enlace</a>\s*&lt;</p>'
    desc = re.sub(pattern, '', desc)
    desc = desc.replace('Ve a escucharlo el episodio en este enlace', '')
    return desc

def transcribe_with_gemini(audio_url, slug):
    if not GEMINI_API_KEY:
        print(f"Skipping transcription for {slug}: GEMINI_API_KEY not set.")
        return None
    
    print(f"Transcribing {slug} with Gemini 3 Flash...")
    genai.configure(api_key=GEMINI_API_KEY)
    
    # Download audio
    audio_path = f"temp_{slug}.mp3"
    try:
        r = requests.get(audio_url, stream=True)
        with open(audio_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # Upload to Gemini
        model = genai.GenerativeModel("gemini-3-flash-preview")
        audio_file = genai.upload_file(path=audio_path)
        
        # Wait for file to process
        while audio_file.state.name == "PROCESSING":
            time.sleep(2)
            audio_file = genai.get_file(audio_file.name)
            
        # Generate transcription
        prompt = "Transcripción literal de este audio en español. Por favor, divide el texto en párrafos para que sea fácil de leer."
        response = model.generate_content([audio_file, prompt])
        
        # Cleanup
        os.remove(audio_path)
        genai.delete_file(audio_file.name)
        
        return response.text
    except Exception as e:
        print(f"Error transcribing {slug}: {e}")
        if os.path.exists(audio_path): os.remove(audio_path)
        return None

# --- Main Logic ---
def run():
    print(f"Fetching RSS: {RSS_URL}")
    req = urllib.request.Request(RSS_URL, headers={'User-Agent': 'Mozilla/5.0'})
    response = urllib.request.urlopen(req)
    xml_data = response.read()
    root = ET.fromstring(xml_data)
    channel = root.find('channel')
    items = channel.findall('item')
    
    episodes = []
    ns = {
        'itunes': 'http://www.itunes.com/dtds/podcast-1.0.dtd',
        'content': 'http://purl.org/rss/1.0/modules/content/'
    }
    
    global_image = ""
    global_image_el = channel.find('image/url')
    if global_image_el is not None: global_image = global_image_el.text

    # Parse episodes
    for i, item in enumerate(items):
        title_el = item.find('title')
        title = title_el.text if title_el is not None and title_el.text else "Episodio sin título"
        pub_date_el = item.find('pubDate')
        pub_date = pub_date_el.text if pub_date_el is not None and pub_date_el.text else ""
        link_el = item.find('link')
        spotify_link = link_el.text if link_el is not None else ""
        
        description_el = item.find('content:encoded', ns)
        if description_el is not None and description_el.text:
            description = description_el.text
        else:
            desc_el = item.find('description')
            description = desc_el.text if desc_el is not None and desc_el.text else ""
            
        description = clean_description(description)
        enclosure = item.find('enclosure')
        audio_url = enclosure.get('url') if enclosure is not None else ""
        
        image = global_image
        itunes_image = item.find('itunes:image', ns)
        if itunes_image is not None: image = itunes_image.get('href')
            
        slug = str(len(items) - i)
        
        # Handle Date
        try:
            dt = datetime.strptime(pub_date, '%a, %d %b %Y %H:%M:%S %Z')
            formatted_date = dt.strftime('%d de %B, %Y')
            months = {'January': 'enero', 'February': 'febrero', 'March': 'marzo', 'April': 'abril', 'May': 'mayo', 'June': 'junio', 'July': 'julio', 'August': 'agosto', 'September': 'septiembre', 'October': 'octubre', 'November': 'noviembre', 'December': 'diciembre'}
            for eng, esp in months.items(): formatted_date = formatted_date.replace(eng, esp)
        except:
            formatted_date = pub_date

        episodes.append({
            'title': title, 'pubDate': formatted_date, 'description': description,
            'audioUrl': audio_url, 'image': image, 'slug': slug, 'spotifyLink': spotify_link
        })

    # Step-by-step processing
    transcribed_count = 0
    for i, ep in enumerate(episodes):
        slug = ep['slug']
        transcript_path = os.path.join(TRANSCRIPT_DIR, f"{slug}.txt")
        
        # Auto-transcribe if missing, API key exists, and limit not reached
        if not os.path.exists(transcript_path) and GEMINI_API_KEY and transcribed_count < TRANSCRIPTION_LIMIT:
            text = transcribe_with_gemini(ep['audioUrl'], slug)
            if text:
                with open(transcript_path, "w", encoding="utf-8") as f:
                    f.write(text)
                print(f"Transcript saved for {slug}")
                transcribed_count += 1

        # Check for local transcript again
        transcript_html = ""
        if os.path.exists(transcript_path):
            with open(transcript_path, "r", encoding="utf-8") as f:
                raw_text = f.read()
                formatted_text = "".join([f"<p>{p.strip()}</p>" for p in raw_text.split("\n") if p.strip()])
                transcript_html = f"""
                    <details class="transcript-accordion">
                        <summary>Leer transcripción completa</summary>
                        <div class="transcript-content">
                            <button class="copy-btn" onclick="navigator.clipboard.writeText(this.parentElement.innerText); alert('Copiado');">Copiar texto</button>
                            {formatted_text}
                        </div>
                    </details>
                """
        else:
            transcript_html = f"""
                <div class="transcript-placeholder">
                    <p>La transcripción automática está disponible en la plataforma de Spotify.</p>
                    <a href="{ep['spotifyLink']}" target="_blank" class="btn-rojo" style="display: inline-block; margin-top: 10px;">Ver transcripción en Spotify</a>
                </div>
            """

        # Generate HTML
        template = open("generate_episodes.py", "r", encoding="utf-8").read()
        # Extract template string (dirty hack or just redefine it)
        # Redefining is safer
        HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Vida En Salud</title>
    <link rel="stylesheet" href="../estilos.css">
    
    <!-- SEO & Social Media -->
    <link rel="canonical" href="https://vidaensalud.es/podcast/{slug}.html">
    <meta name="description" content="{short_description}">
    <meta property="og:title" content="{title} - Vida En Salud">
    <meta property="og:description" content="{short_description}">
    <meta property="og:image" content="{image}">
    <meta property="og:url" content="https://vidaensalud.es/podcast/{slug}.html">
    <meta property="og:type" content="article">
    <meta name="twitter:card" content="summary_large_image">
</head>
<body>
    <div class="main-wrapper">
        <header class="header-nav">
            <a href="../index.html" class="logo-link">
                <img src="../logo.jpg" alt="Vida En Salud" class="logo-header">
            </a>
            <a href="../suscripcion/index.html" class="btn-rojo">Suscríbete a la Newsletter y obtén ofertas especiales</a>
        </header>

        <article class="episode-content">
            <header class="episode-header">
                <h1 class="episode-title">{title}</h1>
                <p class="episode-date">{pubDate}</p>
            </header>

            <div class="player-container">
                <audio controls src="{audioUrl}">
                    Tu navegador no soporta el elemento de audio.
                </audio>
            </div>

            <div class="episode-description">
                {description}
            </div>

            <section class="transcript-section">
                <h2>Transcripción del episodio</h2>
                {transcript_html}
            </section>

            <nav class="episode-nav">
                <div class="prev-ep">
                    {prev_link}
                </div>
                <div class="catalog-link">
                    <a href="../index.html">☰ Ver Catálogo</a>
                </div>
                <div class="next-ep">
                    {next_link}
                </div>
            </nav>
        </article>

        <footer>
            <p>&copy; 2026 Vida En Salud - Diana Valeria</p>
        </footer>
    </div>
</body>
</html>"""

        prev_link = ""
        next_link = ""
        if i < len(episodes) - 1:
            prev_ep = episodes[i+1]
            prev_link = f'<a href="{prev_ep["slug"]}.html">← Episodio Anterior</a>'
        if i > 0:
            next_ep = episodes[i-1]
            next_link = f'<a href="{next_ep["slug"]}.html">Episodio Siguiente →</a>'

        page_content = HTML_TEMPLATE.format(
            title=ep['title'], image=ep['image'], pubDate=ep['pubDate'],
            audioUrl=ep['audioUrl'], description=ep['description'],
            short_description=get_short_description(ep['description']),
            slug=ep['slug'], prev_link=prev_link, next_link=next_link,
            spotifyLink=ep['spotifyLink'], transcript_html=transcript_html
        )
        
        with open(os.path.join(OUTPUT_DIR, f"{slug}.html"), "w", encoding="utf-8") as f:
            f.write(page_content)

    # Generate Sitemap
    sitemap = '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://vidaensalud.es/index.html</loc><priority>1.0</priority></url>'
    for ep in episodes:
        sitemap += f'<url><loc>https://vidaensalud.es/podcast/{ep["slug"]}.html</loc><priority>0.8</priority></url>'
    sitemap += '</urlset>'
    with open("sitemap.xml", "w", encoding="utf-8") as f: f.write(sitemap)
    
    print("Done! Everything updated.")

if __name__ == "__main__":
    run()
