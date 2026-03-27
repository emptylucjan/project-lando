"""Debug: test SKU extraction from URL and check if it matches HTML"""
import re

url = "https://www.zalando.pl/nike-sportswear-air-force-1-07-sneakersy-niskie-white-ni112n022-a11.html"

# Test URL regex
sku_match = re.search(r'-([\w]+)\.html$', url)
print(f"sku_suffix: {sku_match.group(1).upper() if sku_match else 'None'}")

full_sku_match = re.search(r'-(\w+-\w+)\.html$', url)
print(f"full_sku: {full_sku_match.group(1).upper() if full_sku_match else 'None'}")

# What we need: NI112N022-A11
# URL ends with: ni112n022-a11.html
# So full_sku should be: NI112N022-A11 ✓

with open("debug_page.html", "r", encoding="utf-8") as f:
    html = f.read()

full_sku = "NI112N022-A11"
print(f"\nSearching for '{full_sku}' in HTML:")
count = 0
for m in re.finditer(re.escape(full_sku), html, re.IGNORECASE):
    count += 1
    start = max(0, m.start() - 50)
    end = min(len(html), m.end() + 200)
    context = html[start:end]
    amounts = re.findall(r'"amount"\s*:\s*(\d+)', context)
    price_match = re.search(
        r'"current"\s*:\s*\{"amount"\s*:\s*(\d+)\}.*?"original"\s*:\s*\{"amount"\s*:\s*(\d+)\}',
        context
    )
    print(f"  Match {count} at pos {m.start()}")
    print(f"    amounts in context: {amounts}")
    print(f"    price_match: {price_match.groups() if price_match else 'None'}")
    if count >= 5:
        break

print(f"\nTotal matches: {html.lower().count(full_sku.lower())}")

# Try also just the product code without variant
code = "NI112N022"
print(f"\nSearching for '{code}':")
for m in list(re.finditer(re.escape(code), html, re.IGNORECASE))[:3]:
    start = max(0, m.start() - 30)
    end = min(len(html), m.end() + 300)
    context = html[start:end]
    price_match = re.search(
        r'"current"\s*:\s*\{"amount"\s*:\s*(\d+)\}.*?"original"\s*:\s*\{"amount"\s*:\s*(\d+)\}',
        context
    )
    print(f"  pos {m.start()}: price_match={price_match.groups() if price_match else 'None'}")
