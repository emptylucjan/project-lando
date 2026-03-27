import asyncio, sys
sys.path.append('C:\\Users\\lukko\\Desktop\\projekt zalando')
import mrowka.zalando_scanner as sz

async def test():
    urls = ['https://www.zalando.pl/nike-sportswear-air-max-90-prm-reflect-sneakersy-niskie-whitemetallic-silver-coloured-ni112p039-a11.html']
    res = await sz.scan_urls(urls)
    for r in res:
        print('SKU:', r.sku)
        count = sum(1 for e in r.size_to_ean.values() if e)
        print(f'EANy: {count} z {len(r.size_to_ean)} rozmiarów')
        for s, e in list(r.size_to_ean.items())[:5]:
            print(f'  {s} -> {e}')

asyncio.run(test())
