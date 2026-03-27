import urllib.request
import re

url = 'https://www.zalando.pl/nike-sportswear-air-max-90-prm-reflect-sneakersy-niskie-whitemetallic-silver-coloured-ni112p039-a11.html'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'})
try:
    html = urllib.request.urlopen(req).read().decode('utf-8', errors='ignore')
    with open('am90.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("Saved am90.html")
except Exception as e:
    print(e)
