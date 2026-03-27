import urllib.request, io, numpy as np
from PIL import Image

# Packshot URLs confirmed-working from previous runs
images = [
    # CBF shirt packshot (CG bg, spread=0)
    ('CBF-packshot', 'https://img01.ztat.net/article/spp-media-p1/dc4eb7090ce74c73bd8d87c8ad56a025/23c1fe54c2dd45e3af0f7bb4f002030a.jpg?imwidth=100'),
    # CBF lifestyle-1 (waist-up, should FAIL)
    ('CBF-lifestyle1', 'https://img01.ztat.net/article/spp-media-p1/19fe8b0442b243e0877c80bb9188a4ce/268db501adda4687895a77ddbb807f31.jpg?imwidth=100'),
    # AF1 packshot
    ('AF1-packshot (white)', 'https://img01.ztat.net/article/spp-media-p1/56725b665faa4aa89e0bfba891892741/5aeea2f4893d48fdbb74c59eca218f67.jpg?imwidth=100'),
    # Shox packshot
    ('Shox-packshot', 'https://img01.ztat.net/article/spp-media-p1/70a2b94a7e684b94a7e683919b9f1/3b03b5d82e5a4ee597e4cd8d6d0fa3dc.jpg?imwidth=100'),
    # Adidas jacket packshot
    ('Jacket-packshot', 'https://img01.ztat.net/article/spp-media-p1/1d46e0e6e8824609a16f91e0d4b84b04/cb2de05fc2634cdf9edd56c0bf05c85b.jpg?imwidth=100'),
]

def analyze_spread(url, label):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            img = Image.open(io.BytesIO(r.read())).convert('RGB')
    except Exception as e:
        print(f"\n{label} -> ERROR: {e}")
        return
    d = np.array(img)
    h, w = d.shape[:2]
    regions = {
        'tl': d[0:5, 0:5], 'tr': d[0:5, w-5:w],
        'bl': d[h-5:h, 0:5], 'br': d[h-5:h, w-5:w],
        'ml': d[h//2-3:h//2+3, 0:5], 'mr': d[h//2-3:h//2+3, w-5:w],
        'tc': d[0:5, w//2-3:w//2+3], 'bc': d[h-8:h, w//2-5:w//2+5],
    }
    spreads = []
    for name, region in regions.items():
        m = region.mean(axis=(0,1))
        spreads.append((name, float(m.max()-m.min()), m.astype(int)))
    
    max_spread = max(s[1] for s in spreads)
    all_bright = all(s[2].min() > 200 for s in spreads)
    pass_tight = all_bright and max_spread < 5
    pass_loose = all_bright and max_spread < 20
    
    print(f"\n{label}")
    print(f"  Max spread across regions: {max_spread:.1f}")
    print(f"  All bright (>200): {all_bright}")
    print(f"  PASS with spread<5:  {pass_tight}")
    print(f"  PASS with spread<20: {pass_loose}")
    for name, sp, rgb in spreads:
        print(f"    {name}: spread={sp:.1f} RGB={rgb}")

for label, url in images:
    analyze_spread(url, label)
