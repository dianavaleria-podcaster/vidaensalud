
import urllib.request
import xml.etree.ElementTree as ET
import re
import os
import html

rss_url = "https://anchor.fm/s/10f10dc44/podcast/rss"
output_dir = "episodios"

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

    for item in items:
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
            
        slug = slugify(title)
        
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
    <style>
        body {{ padding: 20px; }}
        .main-wrapper {{
            max-width: 800px;
            margin: 0 auto;
            background: #ffffff;
            padding: 60px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }}
        .breadcrumbs {{
            font-family: var(--fuente-texto);
            font-size: 0.9rem;
            margin-bottom: 30px;
            color: #666;
        }}
        .breadcrumbs a {{
            color: var(--verde-salud);
            text-decoration: none;
        }}
        .episode-header {{
            text-align: center;
            margin-bottom: 40px;
        }}
        .episode-image {{
            width: 100%;
            max-width: 180px;
            height: auto;
            border-radius: 12px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            margin-bottom: 25px;
        }}
        .episode-title {{
            font-size: 2.2rem;
            margin: 10px 0;
            line-height: 1.2;
        }}
        .episode-date {{
            font-family: var(--fuente-texto);
            color: #888;
            font-size: 1rem;
            margin-bottom: 20px;
        }}
        .player-container {{
            background: #121212;
            padding: 20px;
            border-radius: 12px;
            margin: 30px 0;
        }}
        .player-container audio {{
            width: 100%;
        }}
        .episode-description {{
            font-family: var(--fuente-texto);
            line-height: 1.7;
            color: #333;
            font-size: 1.1rem;
            margin-bottom: 40px;
        }}
        .transcript-section {{
            margin-top: 50px;
            padding-top: 30px;
            border-top: 1px solid #eee;
        }}
        .transcript-section h2 {{
            color: var(--verde-salud);
            font-size: 1.5rem;
            margin-bottom: 20px;
        }}
        .transcript-placeholder {{
            background: #f9f9f9;
            padding: 20px;
            border-radius: 8px;
            border: 1px dashed #ccc;
            font-family: var(--fuente-texto);
            text-align: center;
        }}
        .episode-nav {{
            display: flex;
            justify-content: space-between;
            margin-top: 50px;
            padding-top: 30px;
            border-top: 1px solid #eee;
            font-family: var(--fuente-texto);
        }}
        .episode-nav a {{
            color: var(--verde-salud);
            text-decoration: none;
            font-weight: bold;
            transition: opacity 0.2s;
        }}
        .episode-nav a:hover {{
            opacity: 0.7;
        }}
        .back-link {{
            display: block;
            text-align: center;
            margin-top: 40px;
            color: var(--rojo);
            text-decoration: none;
            font-weight: bold;
            font-family: var(--fuente-texto);
        }}
        .back-link:hover {{ text-decoration: underline; }}
        @media (max-width: 768px) {{
            .main-wrapper {{ padding: 30px; }}
            .episode-title {{ font-size: 1.8rem; }}
        }}
    </style>
</head>
<body>
    <div class="main-wrapper">
        <nav class="header-nav">
            <a href="../suscripcion/index.html" class="btn-rojo">Suscríbete</a>
        </nav>

        <div class="breadcrumbs">
            <a href="../index.html">Inicio</a> &gt; Episodios &gt; {title}
        </div>

        <article class="episode-content">
            <header class="episode-header">
                <img src="{image}" alt="{title}" class="episode-image">
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
                <h2>Transcripción</h2>
                <div class="transcript-placeholder">
                    <p>La transcripción automática está disponible en la plataforma de Spotify.</p>
                    <a href="{spotifyLink}" target="_blank" class="btn-rojo" style="display: inline-block; margin-top: 10px;">Ver transcripción en Spotify</a>
                </div>
            </section>

            <nav class="episode-nav">
                <div class="prev-ep">
                    {prev_link}
                </div>
                <div class="next-ep">
                    {next_link}
                </div>
            </nav>

            <a href="../index.html" class="back-link">← Volver al catálogo</a>
        </article>

        <footer style="margin-top: 60px; border-top: 1px solid #eee; padding-top: 40px; text-align: center;">
            <img src="../logo.jpg" alt="Vida En Salud" class="logo" style="max-width: 80px;">
            <p style="font-size: 0.9rem; color: #666;">&copy; 2026 Vida En Salud - Diana Valeria</p>
        </footer>
    </div>
</body>
</html>
"""

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

    content = template.format(
        title=ep['title'],
        image=ep['image'],
        pubDate=ep['pubDate'],
        audioUrl=ep['audioUrl'],
        description=ep['description'],
        prev_link=prev_link,
        next_link=next_link,
        spotifyLink=ep['spotifyLink']
    )
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

print("Done!")
