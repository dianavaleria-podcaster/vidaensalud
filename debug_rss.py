
import urllib.request
import xml.etree.ElementTree as ET

rss_url = "https://anchor.fm/s/10f10dc44/podcast/rss"

def debug_rss():
    try:
        req = urllib.request.Request(rss_url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(req)
        xml_data = response.read()
        root = ET.fromstring(xml_data)
        print(f"Root tag: {root.tag}")
        
        channel = root.find('channel')
        if channel is None:
            print("Channel not found")
            return
            
        items = channel.findall('item')
        print(f"Found {len(items)} items")
        
        if len(items) > 0:
            first_item = items[0]
            for elem in first_item:
                print(f"  Element: {elem.tag}, text: {elem.text[:50] if elem.text else 'None'}")
                
    except Exception as e:
        print(f"Error: {e}")

debug_rss()
