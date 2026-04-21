
import urllib.request
import xml.etree.ElementTree as ET
import re
import os

rss_url = "https://anchor.fm/s/10f10dc44/podcast/rss"

def get_episodes():
    try:
        response = urllib.request.urlopen(rss_url)
        xml_data = response.read()
        root = ET.fromstring(xml_data)
        channel = root.find('channel')
        items = channel.findall('item')
        
        episodes = []
        for item in items:
            title = item.find('title').text
            pub_date = item.find('pubDate').text
            description = item.find('description').text
            link = item.find('link').text
            enclosure = item.find('enclosure')
            audio_url = enclosure.get('url') if enclosure is not None else ""
            
            # Extract image from itunes namespace
            image = ""
            itunes_ns = {'itunes': 'http://www.itunes.com/dtds/podcast-1.0.dtd'}
            itunes_image = item.find('itunes:image', itunes_ns)
            if itunes_image is not None:
                image = itunes_image.get('href')
            
            episodes.append({
                'title': title,
                'pubDate': pub_date,
                'description': description,
                'audioUrl': audio_url,
                'image': image
            })
        return episodes
    except Exception as e:
        print(f"Error: {e}")
        return []

episodes = get_episodes()
print(f"Found {len(episodes)} episodes.")
for ep in episodes[:5]:
    print(f"- {ep['title']} ({ep['pubDate']})")
