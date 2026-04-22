import urllib.request
import xml.etree.ElementTree as ET
import re
import os
import html

rss_url = "https://anchor.fm/s/10f10dc44/podcast/rss"
output_dir = "podcast"

if not os.path.exists(output_dir):
    os.makedirs(output_dir)

def slugify(text):
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')

def clean_description(desc):
    if not desc: return ""
    # Remove "Ve a escucharlo el episodio en este enlace" links
    pattern = r'<p><a href="https://vidaensalud\.es"[^>]*>Ve a escucharlo el episodio en este enlace</a>\s*&lt;</p>'
    desc = re.sub(pattern, '', desc)
    desc = desc.replace('Ve a escucharlo el episodio en este enlace', '')
    return desc

def get_short_description(html_content, length=160):
    if not html_content: return ""
    # Clean HTML tags
    text = re.sub(r'<[^>]+>', '', html_content)
    # Decode HTML entities
    text = html.unescape(text)
    # Remove extra whitespaces
    text = ' '.join(text.split())
    # Truncate
    if len(text) > length:
        return text[:length].rsplit(' ', 1)[0] + "..."
    return text

def get_episodes():
    req = urllib.request.Request(rss_url, headers={'User-Agent': 'Mozilla/5.0'})
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
    if global_image_el is not None:
        global_image = global_image_el.text

    for i, item in enumerate(items):
        title_el = item.find('title')
        title = title_el.text if title_el is not None and title_el.text else "Episodio sin título"
        
        pub_date_el = item.find('pubDate')
        pub_date = pub_date_el.text if pub_date_el is not None and pub_date_el.text else ""
        
        link_el = item.find('link')
        spotify_link = link_el.text if link_el is not None else ""
        
        # Use content:encoded for full description if available, else description
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
        if itunes_image is not None:
            image = itunes_image.get('href')
            
        episode_number = len(items) - i
        slug = str(episode_number)
        
        # Format date
        try:
            from datetime import datetime
            dt = datetime.strptime(pub_date, '%a, %d %b %Y %H:%M:%S %Z')
            formatted_date = dt.strftime('%d de %B, %Y')
            months = {
                'January': 'enero', 'February': 'febrero', 'March': 'marzo', 'April': 'abril',
                'May': 'mayo', 'June': 'junio', 'July': 'julio', 'August': 'agosto',
                'September': 'septiembre', 'October': 'octubre', 'November': 'noviembre', 'December': 'diciembre'
            }
            for eng, esp in months.items():
                formatted_date = formatted_date.replace(eng, esp)
        except:
            formatted_date = pub_date

        episodes.append({
            'title': title,
            'pubDate': formatted_date,
            'description': description,
            'audioUrl': audio_url,
            'image': image,
            'slug': slug,
            'spotifyLink': spotify_link
        })
    return episodes
template = """<!DOCTYPE html>
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
                    <a href="../index.html">☰ Volver al Catálogo</a>
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

episodes = get_episodes()
print(f"Generating {len(episodes)} episodes with Transcriptions...")

for i, ep in enumerate(episodes):
    file_path = os.path.join(output_dir, f"{ep['slug']}.html")
    prev_link = ""
    next_link = ""
    if i < len(episodes) - 1:
        prev_ep = episodes[i+1]
        prev_link = f'<a href="{prev_ep["slug"]}.html">← Episodio Anterior</a>'
    if i > 0:
        next_ep = episodes[i-1]
        next_link = f'<a href="{next_ep["slug"]}.html">Episodio Siguiente →</a>'

    # Check for local transcript
    transcript_path = os.path.join("transcripciones", f"{ep['slug']}.txt")
    if os.path.exists(transcript_path):
        with open(transcript_path, "r", encoding="utf-8") as f:
            raw_text = f.read()
            # Basic formatting: paragraphs
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

    content = template.format(
        title=ep['title'],
        image=ep['image'],
        pubDate=ep['pubDate'],
        audioUrl=ep['audioUrl'],
        description=ep['description'],
        short_description=get_short_description(ep['description']),
        slug=ep['slug'],
        prev_link=prev_link,
        next_link=next_link,
        spotifyLink=ep['spotifyLink'],
        transcript_html=transcript_html
    )
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

# Generate Sitemap
sitemap_content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>https://vidaensalud.es/index.html</loc>
        <priority>1.0</priority>
    </url>
"""

for ep in episodes:
    sitemap_content += f"""    <url>
        <loc>https://vidaensalud.es/podcast/{ep['slug']}.html</loc>
        <priority>0.8</priority>
    </url>
"""

sitemap_content += "</urlset>"

with open("sitemap.xml", "w", encoding="utf-8") as f:
    f.write(sitemap_content)

print("Done! Sitemap generated.")
