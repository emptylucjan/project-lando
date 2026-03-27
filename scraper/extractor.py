"""
Product data extractor — scrapes product details from a Zalando product page.
Uses JavaScript execution on the live DOM to extract data reliably.
"""

from typing import Optional, Tuple
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re
import json
import logging
import os
import urllib.request
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


def _is_packshot_bg(image_url: str) -> bool:
    """Check if an image URL is a true packshot (product alone on gray bg).
    Downloads a tiny 100px version and checks corners + center edges.
    Lifestyle/model photos fail because the model's body crosses center edges."""
    try:
        import io
        tiny_url = re.sub(r'imwidth=\d+', 'imwidth=100', image_url)
        if 'imwidth=' not in tiny_url:
            tiny_url += ('&' if '?' in tiny_url else '?') + 'imwidth=100'
        tiny_url = tiny_url.replace('&filter=packshot', '').replace('?filter=packshot', '')

        req = urllib.request.Request(tiny_url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        with urllib.request.urlopen(req, timeout=5) as resp:
            img = Image.open(io.BytesIO(resp.read())).convert('RGB')

        data = np.array(img)
        h, w = data.shape[:2]

        # Check 8 regions: 4 corners + center-left, center-right, center-top, center-bottom
        # Full-body model photos: person's legs/pants are visible at bottom-center
        # Packshots: bottom-center is clean gray background
        regions = [
            data[0:5, 0:5],              # top-left corner
            data[0:5, w-5:w],            # top-right corner
            data[h-5:h, 0:5],            # bottom-left corner
            data[h-5:h, w-5:w],          # bottom-right corner
            data[h//2-3:h//2+3, 0:5],    # center-left edge
            data[h//2-3:h//2+3, w-5:w],  # center-right edge
            data[0:5, w//2-3:w//2+3],    # center-top edge
            data[h-8:h, w//2-5:w//2+5],  # center-bottom edge (catches legs/pants)
        ]

        region_means = []
        for region in regions:
            mean = region.mean(axis=(0, 1))
            # Each region: all channels > 200, nearly neutral (spread < 20)
            if mean.min() < 200 or (mean.max() - mean.min()) > 20:
                return False
            region_means.append(float(mean.mean()))

        # Inter-region uniformity check:
        # Zalando CG packshots have perfectly uniform bg (all regions ≈ same gray).
        # Real studio photos have lighting gradients → regions differ by 10-30 pts.
        inter_range = max(region_means) - min(region_means)
        if inter_range > 12:
            logger.debug("Studio bg detected (inter-region range=%.1f > 12) — odrzucam", inter_range)
            return False

        return True
    except Exception as e:
        logger.debug("Packshot bg check failed for %s: %s", image_url[:60], e)
        return False


def _find_packshot_url(candidate_urls: list) -> Optional[str]:
    """Find the first URL that is a true packshot (uniform gray background).
    Returns high-res URL or None."""
    for url in candidate_urls:
        if _is_packshot_bg(url):
            hi_res = re.sub(r'imwidth=\d+', 'imwidth=1800', url)
            if 'imwidth=' not in hi_res:
                hi_res += ('&' if '?' in hi_res else '?') + 'imwidth=1800'
            logger.info("Packshot znaleziony: %s", hi_res[:80])
            return hi_res
    return None


def remove_background(input_path: str, output_path: str = None, tolerance: int = 18) -> str:
    """Remove gray bg using flood-fill from edges — won't cut into the product.
    Only removes pixels connected to the image border that match background color."""
    from collections import deque

    if output_path is None:
        output_path = os.path.splitext(input_path)[0] + ".png"
    img = Image.open(input_path).convert("RGBA")
    data = np.array(img)
    h, w = data.shape[:2]

    # Detect background color from corners
    corners = [data[0:10, 0:10, :3], data[0:10, w-10:w, :3],
               data[h-10:h, 0:10, :3], data[h-10:h, w-10:w, :3]]
    bg_color = np.median(np.concatenate([c.reshape(-1, 3) for c in corners], axis=0), axis=0)

    # Auto-adjust tolerance for very light backgrounds (white/light gray products)
    if bg_color.min() > 220:
        tolerance = min(tolerance, 15)
        logger.debug("Jasne tło (%s) — zmniejszam tolerancję do %d", bg_color.astype(int), tolerance)

    # Pre-compute color distance to background for every pixel
    diff = np.sqrt(np.sum((data[:, :, :3].astype(float) - bg_color) ** 2, axis=2))

    # Safety check: if product area is too similar to background, skip removal
    # (white product on white/gray bg — can't separate without destroying product)
    # Use 75th percentile: white AF1 stays near 0 everywhere; dark/mixed shoes pass
    center = diff[h//4:3*h//4, w//4:3*w//4]
    p75 = float(np.percentile(center, 75))
    if p75 < 20:
        logger.warning("Produkt zbyt podobny do tła (p75_diff=%.1f) — pomijam usuwanie tła", p75)
        # Save as PNG with opaque alpha (no transparency)
        Image.fromarray(data).save(output_path, "PNG")
        return output_path

    # Flood-fill from all border pixels — only mark pixels as background
    # if they're connected to the edge AND within tolerance
    is_bg = np.zeros((h, w), dtype=bool)
    queue = deque()

    # Seed from all 4 borders
    for x in range(w):
        if diff[0, x] < tolerance:
            is_bg[0, x] = True
            queue.append((0, x))
        if diff[h-1, x] < tolerance:
            is_bg[h-1, x] = True
            queue.append((h-1, x))
    for y in range(h):
        if diff[y, 0] < tolerance:
            is_bg[y, 0] = True
            queue.append((y, 0))
        if diff[y, w-1] < tolerance:
            is_bg[y, w-1] = True
            queue.append((y, w-1))

    # BFS flood-fill
    while queue:
        cy, cx = queue.popleft()
        for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            ny, nx = cy + dy, cx + dx
            if 0 <= ny < h and 0 <= nx < w and not is_bg[ny, nx] and diff[ny, nx] < tolerance:
                is_bg[ny, nx] = True
                queue.append((ny, nx))

    # Build alpha: background=0, product=255, edge zone=gradient
    alpha = np.full((h, w), 255, dtype=np.uint8)
    alpha[is_bg] = 0

    # Smooth edges: pixels near the boundary get partial transparency
    edge_tolerance = tolerance + 15
    edge_candidates = ~is_bg & (diff < edge_tolerance)
    # Manual dilation: find product pixels adjacent to background (numpy-only)
    bg_padded = np.pad(is_bg, 1, mode='constant', constant_values=False)
    bg_border = (
        bg_padded[:-2, 1:-1] | bg_padded[2:, 1:-1] |
        bg_padded[1:-1, :-2] | bg_padded[1:-1, 2:]
    ) & ~is_bg
    edge_zone = bg_border & edge_candidates
    alpha[edge_zone] = ((diff[edge_zone] - tolerance) / 15 * 255).clip(0, 255).astype(np.uint8)

    data[:, :, 3] = alpha
    Image.fromarray(data).save(output_path, "PNG")
    return output_path


def download_product_image(image_url: str, save_path: str) -> dict:
    """Download product image and auto-convert to transparent PNG.
    Returns dict with 'jpg' and 'png' paths, or empty dict on failure."""
    try:
        req = urllib.request.Request(image_url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, 'wb') as f:
                f.write(resp.read())
        # Auto-convert to transparent PNG
        png_path = remove_background(save_path)
        logger.info("Zdjęcie: %s → %s", save_path, png_path)
        return {"jpg": save_path, "png": png_path}
    except Exception as e:
        logger.error("Błąd pobierania zdjęcia: %s", e)
        return {}


def _extract_eans_from_ldjson(driver) -> dict:
    """
    Parsuje JSON-LD strony Zalando i zwraca słownik {rozmiar: {ean, sku, available}}.
    Pole available=True tylko gdy offers.availability zawiera 'InStock'.
    """
    import json as _json
    import re as _re
    try:
        scripts = driver.execute_script("""
            var scripts = document.querySelectorAll('script[type="application/ld+json"]');
            var results = [];
            for (var s of scripts) { results.push(s.textContent); }
            return results;
        """)

        size_ean_map = {}
        for raw in (scripts or []):
            try:
                data = _json.loads(raw)
                items = data if isinstance(data, list) else [data]
                for item in items:
                    variants = item.get("hasVariant", [])
                    if not variants and item.get("@type") == "Product":
                        variants = [item]

                    for variant in variants:
                        sku = variant.get("sku", "")
                        gtin = variant.get("gtin") or variant.get("gtin13") or variant.get("gtin8") or ""
                        offers = variant.get("offers", {})
                        if isinstance(offers, list) and offers:
                            offers = offers[0]
                        gtin = gtin or offers.get("gtin") or offers.get("gtin13") or ""

                        if not gtin:
                            continue

                        # Availability: InStock = dostępny
                        availability = offers.get("availability", "") or variant.get("availability", "")
                        is_in_stock = "InStock" in availability

                        url_val = variant.get("url", "") or offers.get("url", "")
                        m = _re.search(r'[?&]size=([^&]+)', url_val)
                        if m:
                            size = m.group(1)
                            # Dekoduj URL encoding: %2F→/, + lub %20→spacja, %2C→,
                            size = size.replace("%2F", "/").replace("+", " ").replace("%20", " ")
                            size = size.replace("%2C", ",").replace(",", ".")
                        else:
                            size = None

                        if size:
                            ean = gtin.lstrip("0") or gtin
                            size_ean_map[size] = {
                                "ean": ean,
                                "sku": sku,
                                "available": is_in_stock,
                            }

            except Exception:
                continue

        return size_ean_map
    except Exception:
        return {}


def _select_size_in_dropdown(driver, size_str: str) -> bool:
    import time
    try:
        # LAYOUT A: Dropdown (np. Air Max 90) — trigger → listbox → listitem
        has_trigger = driver.execute_script(
            "return !!document.querySelector('[data-testid=\"pdp-size-picker-trigger\"]')"
        )
        if has_trigger:
            # Otwórz dropdown
            driver.execute_script(
                "document.querySelector('[data-testid=\"pdp-size-picker-trigger\"]').click()"
            )
            time.sleep(0.4)

            clicked = driver.execute_script(f"""
                var sizeStr = '{size_str}';
                var listbox = document.querySelector('[role="listbox"]');
                if (!listbox) return false;
                var items = listbox.querySelectorAll('[role="listitem"]');
                for (var i = 0; i < items.length; i++) {{
                    var spans = items[i].querySelectorAll('span');
                    for (var j = 0; j < spans.length; j++) {{
                        if (spans[j].textContent.trim() === sizeStr) {{
                            var label = items[i].querySelector('label');
                            if (label) {{ label.click(); return true; }}
                            var inp = items[i].querySelector('input');
                            if (inp) {{ inp.click(); return true; }}
                            spans[j].click();
                            return true;
                        }}
                    }}
                }}
                return false;
            """)

            if clicked:
                # Zamknij listbox Escape, niech strona przetworzy wybor
                time.sleep(0.2)
                driver.execute_script(
                    "document.dispatchEvent(new KeyboardEvent('keydown', "
                    "{key: 'Escape', code: 'Escape', bubbles: true}));"
                )
                time.sleep(0.2)
            return bool(clicked)

        # LAYOUT B: Standardowe przyciski/label z rozmiarami (Dunk Low, Air Force 1 itp.)
        # Szukamy bezpośrednio w sekcji rozmiarów bez otwierania żadnego dropdown
        clicked = driver.execute_script(f"""
            var sizeStr = '{size_str}';
            // Szukamy label lub button zawierający dokładnie ten rozmiar
            // Limitujemy do sekcji z rozmiarami żeby nie trafić w złe elementy
            var containers = document.querySelectorAll(
                '[data-testid*="size"], [class*="size"], [data-testid*="pdp-size"]'
            );
            for (var c = 0; c < containers.length; c++) {{
                var labels = containers[c].querySelectorAll('label, button');
                for (var i = 0; i < labels.length; i++) {{
                    var text = labels[i].innerText.trim();
                    if (text === sizeStr || text.startsWith(sizeStr + '\\n') || text.startsWith(sizeStr + ' ')) {{
                        labels[i].click();
                        return true;
                    }}
                }}
            }}
            // Fallback: szukamy w całej formie rozmiarów
            var form = document.querySelector('form[name="size-picker-form"]');
            if (form) {{
                var items = form.querySelectorAll('[role="listitem"]');
                for (var i = 0; i < items.length; i++) {{
                    var spans = items[i].querySelectorAll('span');
                    for (var j = 0; j < spans.length; j++) {{
                        if (spans[j].textContent.trim() === sizeStr) {{
                            var label = items[i].querySelector('label');
                            if (label) {{ label.click(); return true; }}
                            spans[j].click(); return true;
                        }}
                    }}
                }}
            }}
            return false;
        """)
        return bool(clicked)

    except Exception:
        return False


def extract_product_data(driver, url: str, max_price: float = None) -> Optional[dict]:
    """
    Navigate to a product URL and extract product data.
    If max_price is provided, EAN/SKU extraction is skipped when price exceeds the limit
    (saves ~15-25 sec per rejected product).
    Returns a dict with product info, or None on failure.
    """
    try:
        logger.info("Otwieram: %s", url)
        driver.get(url)

        # Wait for price to appear (span containing "zł")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'zł')]"))
        )

        import time
        time.sleep(2)

        # Extract everything via JavaScript from the rendered DOM
        data = driver.execute_script("""
            var result = {};
            
            // === NAME ===
            var h1 = document.querySelector('h1');
            result.name = h1 ? h1.innerText.trim() : null;
            
            // === BRAND ===
            var scripts = document.querySelectorAll('script[type="application/ld+json"]');
            for (var i = 0; i < scripts.length; i++) {
                try {
                    var ld = JSON.parse(scripts[i].textContent);
                    if (ld && ld.brand && ld.brand.name) {
                        result.brand = ld.brand.name;
                        break;
                    }
                    if (Array.isArray(ld)) {
                        for (var j = 0; j < ld.length; j++) {
                            if (ld[j] && ld[j].brand && ld[j].brand.name) {
                                result.brand = ld[j].brand.name;
                                break;
                            }
                        }
                    }
                } catch(e) {}
            }
            
            // === PRICES ===
            // Check for "od" prefix — indicates multi-seller product
            // Must be detected NEAR the price element, not in random body text
            result.isFromPrice = false;
            
            var allSpans = document.querySelectorAll('span');
            var priceSpans = [];
            var priceRegex = /^\\d[\\d\\s]*[.,]\\d{2}\\s*zł$/;
            
            for (var i = 0; i < allSpans.length; i++) {
                var text = allSpans[i].innerText.trim().replace(/\\u00a0/g, ' ');
                if (priceRegex.test(text)) {
                    var rect = allSpans[i].getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {
                        var cleaned = text.replace(/[^\\d,.]/g, '').replace(',', '.');
                        var value = parseFloat(cleaned);
                        if (!isNaN(value) && value > 0) {
                            priceSpans.push({
                                value: value,
                                top: rect.top,
                                fontSize: parseFloat(window.getComputedStyle(allSpans[i]).fontSize),
                                text: text,
                                _el: allSpans[i]
                            });
                        }
                    }
                }
            }
            
            // EU-required "Najniższa cena w 30 dniach" disclosure must be excluded
            // from currentPrice candidates (it's the historical low, NOT the current price)
            var bodyText = document.body.innerText;
            var najnizszaMatch = bodyText.match(/[Nn]ajni.{0,15}cen.{0,30}:[\s\u00a0]*([\d\s]+[.,]\d{2})\s*z/);
            var najnizsza = najnizszaMatch ? parseFloat(najnizszaMatch[1].replace(/[\s\u00a0]/g,'').replace(',','.')) : null;
            result.najnizsza = najnizsza;
            // Remove the "30-day lowest" from candidates
            if (najnizsza) {
                priceSpans = priceSpans.filter(function(p) { return Math.abs(p.value - najnizsza) > 0.5; });
            }

            priceSpans.sort(function(a, b) { return a.top - b.top; });
            var mainPrices = priceSpans.filter(function(p) {
                return p.top > 0 && p.top < 800;
            });
            var bigPrices = mainPrices.filter(function(p) { return p.fontSize >= 16; });
            var firstBigPrice = bigPrices.length > 0 ? bigPrices[0] : (mainPrices.length > 0 ? mainPrices[0] : null);
            result.currentPrice = firstBigPrice ? firstBigPrice.value : null;
            
            // Check for "od" prefix near the main price element
            if (firstBigPrice && firstBigPrice._el) {
                var priceEl = firstBigPrice._el;
                // Check parent and grandparent text
                for (var up = 0; up < 3; up++) {
                    var ancestor = priceEl;
                    for (var u = 0; u <= up; u++) { if (ancestor.parentElement) ancestor = ancestor.parentElement; }
                    var ancText = ancestor.innerText.trim().substring(0, 50).toLowerCase();
                    if (/^od\s/.test(ancText) || /\bod\s+\d/.test(ancText)) {
                        result.isFromPrice = true;
                        break;
                    }
                }
                // Check previous sibling
                var prev = priceEl.previousElementSibling;
                if (prev && prev.innerText.trim().toLowerCase() === 'od') {
                    result.isFromPrice = true;
                }
            }
            
            // Remove DOM references before returning (not serializable)
            priceSpans.forEach(function(p) { delete p._el; });
            
            var body = document.body.innerText;
            var regMatch = body.match(/[Cc]ena\\s+regularna[:\\s]+(\\d[\\d\\s]*[.,]\\d{2})\\s*z/);
            result.regularPrice = regMatch ? parseFloat(regMatch[1].replace(',', '.')) : null;
            
            // === IMAGE ===
            // Collect ALL gallery thumbnail URLs as candidates.
            // Python code will check each one's background to find the packshot.
            var galleryCandidates = [];
            var seenHashes = {};
            var galleryImgs = document.querySelectorAll('img[src*="ztat.net"], img[src*="zalando.com"]');
            
            for (var gi = 0; gi < galleryImgs.length; gi++) {
                var src = galleryImgs[gi].src;
                if (!src || !src.includes('spp-media-p1')) continue;
                var rect = galleryImgs[gi].getBoundingClientRect();
                if (rect.width === 0 || rect.height === 0) continue;
                // Gallery thumbs: small images (width < 200) in the upper area (y < 1300)
                if (rect.width > 200 || rect.top > 1300) continue;
                // Deduplicate by hash
                var hashMatch = src.match(/spp-media-p1\/([a-f0-9]+)\//);
                var hash = hashMatch ? hashMatch[1] : src;
                if (seenHashes[hash]) continue;
                seenHashes[hash] = true;
                galleryCandidates.push(src);
            }
            
            result.gallery_candidates = galleryCandidates;
            result.image_url = null;
            result.gallery_images = [];
            
            return result;
        """)

        logger.debug("JS extraction result: %s", data)

        if not data:
            logger.error("JS extraction returned null")
            return None

        # Parse prices
        current_price = data.get("currentPrice")
        original_price = data.get("regularPrice")
        is_multi_seller = data.get("isFromPrice", False)

        # === PACKSHOT DETECTION ===
        # Check each gallery candidate's background to find the real packshot
        gallery_candidates = data.get("gallery_candidates", [])
        packshot_url = None
        if gallery_candidates:
            logger.info("Szukam packshotowego zdjęcia wśród %d kandydatów...", len(gallery_candidates))
            packshot_url = _find_packshot_url(gallery_candidates)
        if not packshot_url:
            # Fallback: use og:image or first candidate
            packshot_url = data.get("image_url")
            if not packshot_url and gallery_candidates:
                packshot_url = re.sub(r'imwidth=\d+', 'imwidth=1800', gallery_candidates[0])
            logger.warning("Nie znaleziono packshotowego tła — używam fallback: %s",
                           (packshot_url or "brak")[:80])

        # Discount
        discount_percent = None
        if current_price and original_price and original_price > current_price:
            discount_percent = round((1 - current_price / original_price) * 100, 1)

        # === SIZE EXTRACTION ===
        sizes = _extract_sizes(driver)

        # === LOW STOCK FILTER ===
        # Sizes with 1-3 remaining are treated as unavailable (too risky)
        for s in sizes:
            if s.get("low_stock"):
                s["available"] = False

        # === MULTI-SELLER CHECK ===
        # If "od X zł" was shown, check each available size's seller by
        # selecting it and reading "Sprzedaż i dostawa przez..." text
        if is_multi_seller and sizes:
            logger.info("Cena 'od' wykryta — sprawdzanie sprzedawcy per rozmiar")

            # PRE-FILTER: wyciągnij JSON-LD żeby oznaczyć OutOfStock rozmiary
            # ZANIM zaczniemy klikać — klik OutOfStock w multi-seller = redirect na login
            _ld_pre = _extract_eans_from_ldjson(driver)
            if _ld_pre:
                for s in sizes:
                    entry = _ld_pre.get(s["size"])
                    if entry:
                        if entry.get("ean"):
                            s["ean"] = entry["ean"]
                        # Oznacz OutOfStock z JSON-LD jako unavailable
                        if entry.get("available") is False:
                            s["available"] = False
                            logger.debug("JSON-LD pre-filter: %s → OutOfStock", s["size"])

            _check_sellers_per_size(driver, sizes)
            for s in sizes:
                if s.get("seller") == "zalando" and s["available"]:
                    s["accepted"] = True
                else:
                    s["accepted"] = False
        else:
            # No "od" = single seller (Zalando), all available sizes are accepted
            for s in sizes:
                s["seller"] = "zalando"
                # If no per-size price was found but size is available, inherit main price
                if s["available"] and s.get("price") is None:
                    s["price"] = current_price
                s["accepted"] = s["available"]

        accepted_sizes = [s for s in sizes if s.get("accepted")]

        # === EARLY PRICE CHECK — skip EAN when product is too expensive ===
        if max_price is not None and current_price is not None and current_price > max_price:
            logger.info("❌ Cena %.2f PLN > limit %.2f PLN — pomijam EAN/SKU", current_price, max_price)
            # Return partial data (no EANs) — caller will reject via price filter
            name = data.get("name")
            brand = data.get("brand")
            return {
                "url": url,
                "name": name,
                "brand": brand,
                "current_price": current_price,
                "original_price": original_price,
                "discount_percent": discount_percent,
                "image_url": packshot_url,
                "gallery_images": [packshot_url] if packshot_url else [],
                "sizes": sizes,
                "is_multi_seller": is_multi_seller,
                "accepted_sizes": [s["size"] for s in accepted_sizes],
            }

        # === EAN/SKU EXTRACTION — dla WSZYSTKICH produktów (single i multi-seller) ===
        # Dla multi-seller: _check_sellers_per_size wyznaczył accepted=True tylko dla Zalando
        # JSON-LD wyciągnie EAN dla wszystkich rozmiarów — marketplace (35.5) dostanie ean
        # ale nie będzie w accepted_sizes, więc PZ go pominie
        if accepted_sizes:
            logger.info("Pobieranie EAN/SKU dla %d zaakceptowanych rozmiarów (is_multi_seller=%s)",
                        len(accepted_sizes), is_multi_seller)

            # === ŚCIEŻKA 1: JSON-LD — EAN + dostępność dla wszystkich rozmiarów ===
            ld_ean_map = _extract_eans_from_ldjson(driver)
            if ld_ean_map:
                logger.info("JSON-LD: znaleziono dane dla %d rozmiarów", len(ld_ean_map))
                for s in sizes:  # Korektuj WSZYSTKIE rozmiary, nie tylko accepted
                    entry = ld_ean_map.get(s["size"])
                    if entry:
                        # Dla single-seller: nadpisz dostępność z JSON-LD
                        # Dla multi-seller: zachowaj accepted wyznaczone przez _check_sellers_per_size
                        if not is_multi_seller:
                            ld_available = entry.get("available", None)
                            if ld_available is not None:
                                s["available"] = ld_available
                                s["accepted"] = ld_available and s.get("seller") == "zalando"
                        # Przypisz EAN dla WSZYSTKICH rozmiarów z JSON-LD (InStock i OutOfStock)
                        if entry.get("ean"):
                            s["ean"] = entry["ean"]

                # === AUTO-DISCOVERY: Dodaj rozmiary z JSON-LD których _extract_sizes nie wykrył ===
                # Zalando JSON-LD zawiera WSZYSTKIE rozmiary w ich dokładnym formacie (128-132,
                # One Size, itd.) — nie musimy dodawać ich do regex, działają automatycznie.
                existing_size_names = {s["size"] for s in sizes}
                for ld_size, ld_entry in ld_ean_map.items():
                    if ld_size not in existing_size_names:
                        ld_available = ld_entry.get("available", False)
                        new_size = {
                            "size": ld_size,
                            "available": ld_available,
                            "price": current_price,
                            "low_stock": False,
                            "price_is_red": False,
                            "ean": ld_entry.get("ean"),
                            "sku": ld_entry.get("sku"),
                            "seller": "zalando",
                            "accepted": ld_available and not is_multi_seller,
                        }
                        sizes.append(new_size)
                        logger.info("JSON-LD auto-discovery: nowy rozmiar '%s' (available=%s)", ld_size, ld_available)

                # Przebuduj accepted_sizes na podstawie zaktualizowanej dostępności
                accepted_sizes = [s for s in sizes if s.get("accepted")]
                logger.info("Po JSON-LD update: %d dostępnych rozmiarów", len(accepted_sizes))

            # === ŚCIEŻKA 1b: SKU Nike — 4 fundamentalnie różne metody ===
            # SKU Nike (np. HV4517-100) jest widoczny po kliknięciu "Wyświetl szczegóły produkcji"
            # Musi być zawsze znalezione.
            nike_sku = None
            sizes_with_ean = [s for s in accepted_sizes if s.get("ean")]


            if sizes_with_ean:
                import time as _t
                from selenium.webdriver.common.action_chains import ActionChains

                def _read_sku_from_page(driver):
                    """Szuka Numer modelu we wszystkich źródłach — DOM, Apollo, NEXT_DATA."""
                    return driver.execute_script("""
                        // 1. innerText DOM
                        var text = document.body.innerText;
                        var patterns = [
                            /Numer modelu[\s:]+([A-Za-z0-9][A-Za-z0-9\-]{4,})/,
                            /Model number[\s:]+([A-Za-z0-9][A-Za-z0-9\-]{4,})/,
                            /Styl[\s:]+([A-Z]{2}[0-9]{4}[-][0-9]{3})/,
                        ];
                        for (var pat of patterns) {
                            var m = text.match(pat); if (m) return m[1];
                        }
                        // 2. innerHTML modelNumber
                        var html = document.body.innerHTML;
                        var m2 = html.match(/\"modelNumber\"\s*:\s*\"([A-Za-z0-9][A-Za-z0-9\\-]{4,})\"/);
                        if (m2) return m2[1];
                        // 3. Apollo/React cache window.__APOLLO_STATE__
                        try {
                            var apolloStr = JSON.stringify(window.__APOLLO_STATE__ || {});
                            var m3 = apolloStr.match(/\"modelNumber\":\"([A-Za-z0-9][A-Za-z0-9\\-]{4,})\"/);
                            if (m3) return m3[1];
                            var m3b = apolloStr.match(/\"style\":\"([A-Z]{2}[0-9]{4}-[0-9]{3})\"/);
                            if (m3b) return m3b[1];
                        } catch(e) {}
                        // 4. window.__NEXT_DATA__
                        try {
                            var ndStr = JSON.stringify(window.__NEXT_DATA__ || {});
                            var m4 = ndStr.match(/\"modelNumber\":\"([A-Za-z0-9][A-Za-z0-9\\-]{4,})\"/);
                            if (m4) return m4[1];
                        } catch(e) {}
                        // 5. JSON-LD additionalProperty
                        var scripts = document.querySelectorAll('script[type="application/ld+json"]');
                        for (var s of scripts) {
                            try {
                                var d = JSON.parse(s.textContent);
                                var items = Array.isArray(d) ? d : [d];
                                for (var item of items) {
                                    var props = item.additionalProperty || [];
                                    for (var p of props) {
                                        var nm = (p.name||'').toLowerCase();
                                        if (nm.includes('model') || nm.includes('style')) {
                                            if (p.value && /^[A-Za-z0-9][A-Za-z0-9\-]{4,}$/.test(p.value)) return p.value;
                                        }
                                    }
                                }
                            } catch(e) {}
                        }
                        return null;
                    """)

                def _click_wyswietl_js(driver):
                    """Klika przycisk Wyświetl przez JS execute_script."""
                    patterns = [
                        "t.includes('wyświetl') && t.includes('produkcji')",
                        "t.includes('wyświetl') && t.includes('produktu')",
                        "t.includes('wyświetl') && t.includes('szczeg')",
                        "t.includes('wyświetl')",
                    ]
                    for pat in patterns:
                        ok = driver.execute_script(f"""
                            var els = document.querySelectorAll('button, span, a, div[role="button"]');
                            for (var e of els) {{
                                var t = (e.innerText || '').trim().toLowerCase();
                                if ({pat}) {{ e.scrollIntoView(); e.click(); return true; }}
                            }}
                            return false;
                        """)
                        if ok:
                            return True
                    return False

                def _open_details_section(driver):
                    """Otwiera sekcję Szczegóły produktu."""
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.6);")
                    _t.sleep(0.2)
                    driver.execute_script("""
                        var buttons = document.querySelectorAll('button');
                        for (var b of buttons) {
                            var t = b.innerText.trim();
                            if (t === 'Szczegóły produktu' || t === 'Product details'
                                || t.toLowerCase().includes('szczeg')) {
                                if (b.getAttribute('aria-expanded') !== 'true') b.click();
                                break;
                            }
                        }
                    """)
                    _t.sleep(0.3)

                def _poll_sku(driver, max_iter=10, interval=0.3):
                    """Polling SKU — max max_iter × interval sekund."""
                    for _ in range(max_iter):
                        sku = _read_sku_from_page(driver)
                        if sku:
                            return sku
                        _t.sleep(interval)
                    return None

                # ─────────────────────────────────────
                # METODA 0: Wyświetl BEZ klikania rozmiaru (dla URL z ?ssku= — rozmiar pre-wybrany przez Zalando)
                # Pomijamy klik rozmiaru, od razu otwieramy szczegóły i klikamy Wyświetl
                # ─────────────────────────────────────
                try:
                    _open_details_section(driver)
                    clicked = _click_wyswietl_js(driver)
                    logger.info("M0: Wyświetl bez klik rozmiaru, clicked=%s", clicked)
                    nike_sku = _poll_sku(driver, max_iter=10, interval=0.3)
                    if nike_sku:
                        logger.info("M0: SKU znalezione: %s", nike_sku)
                except Exception as e:
                    logger.info("M0 wyjątek: %s", e)

                # ─────────────────────────────────────
                # METODA 1: Kliknij rozmiar (dropdown) → Wyświetl (JS) → polling 3s
                # ─────────────────────────────────────
                if not nike_sku:
                    try:
                        first_size = sizes_with_ean[0]["size"]
                        _select_size_in_dropdown(driver, first_size)
                        _t.sleep(0.3)
                        _open_details_section(driver)
                        clicked = _click_wyswietl_js(driver)
                        logger.info("M1: klik rozmiaru %s, Wyświetl=%s", first_size, clicked)
                        nike_sku = _poll_sku(driver, max_iter=10, interval=0.3)
                        if nike_sku:
                            logger.info("M1: SKU znalezione: %s", nike_sku)
                    except Exception as e:
                        logger.info("M1 wyjątek: %s", e)

                # ─────────────────────────────────────
                # METODA 2: Selenium find_element click (inny mechanizm niż JS click)
                # BEZ przeładowania strony — tylko inny klik + polling 3s
                # ─────────────────────────────────────
                if not nike_sku:
                    try:
                        _open_details_section(driver)
                        try:
                            wait = WebDriverWait(driver, 3)
                            btn = wait.until(EC.element_to_be_clickable(
                                (By.XPATH, "//*[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'wyświetl')]")
                            ))
                            btn.click()
                            logger.info("M2: Selenium kliknął Wyświetl")
                        except Exception:
                            logger.info("M2: brak przycisku Wyświetl w DOM")
                        nike_sku = _poll_sku(driver, max_iter=10, interval=0.3)
                        if nike_sku:
                            logger.info("M2: SKU znalezione: %s", nike_sku)
                    except Exception as e:
                        logger.info("M2 wyjątek: %s", e)

                # ─────────────────────────────────────
                # METODA 3: ActionChains hover + click na drugim rozmiarze
                # ─────────────────────────────────────
                if not nike_sku:
                    try:
                        if len(sizes_with_ean) > 1:
                            second_size = sizes_with_ean[1]["size"]
                            _select_size_in_dropdown(driver, second_size)
                            _t.sleep(0.3)
                        _open_details_section(driver)
                        btns = driver.find_elements(By.XPATH,
                            "//*[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'wyświetl')]")
                        wyswietl_btn = next((b for b in btns if b.is_displayed()), None)
                        if wyswietl_btn:
                            ActionChains(driver).move_to_element(wyswietl_btn).click().perform()
                            logger.info("M3: ActionChains kliknął Wyświetl")
                        nike_sku = _poll_sku(driver, max_iter=10, interval=0.3)
                        if nike_sku:
                            logger.info("M3: SKU znalezione: %s", nike_sku)
                    except Exception as e:
                        logger.info("M3 wyjątek: %s", e)

                # ─────────────────────────────────────
                # METODA 4: Fallback z ean_db SQLite
                # ─────────────────────────────────────
                if not nike_sku:
                    try:
                        import os as _os, importlib.util as _ilu, asyncio as _aio
                        for p in __import__("sys").path:
                            candidate = _os.path.join(p, "mrowka", "ean_db.py")
                            if _os.path.exists(candidate):
                                spec = _ilu.spec_from_file_location("ean_db", candidate)
                                _ean_db = _ilu.module_from_spec(spec)
                                spec.loader.exec_module(_ean_db)
                                from urllib.parse import urlparse, urlunparse
                                clean = urlunparse(urlparse(url)._replace(query="", fragment=""))
                                loop = _aio.new_event_loop()
                                existing = loop.run_until_complete(_ean_db.get_eans_for_link(clean))
                                loop.close()
                                db_sku = next((e.sku for e in existing if e.sku), None)
                                if db_sku:
                                    nike_sku = db_sku
                                    logger.info("M4: SKU z ean_db: %s", nike_sku)
                                break
                    except Exception as e:
                        logger.debug("M4 ean_db wyjątek: %s", e)

                if not nike_sku:
                    logger.warning("Nike SKU: WSZYSTKIE METODY ZAWIODŁY dla %s", url)

                try:
                    driver.execute_script(
                        "document.dispatchEvent(new KeyboardEvent('keydown', "
                        "{key: 'Escape', code: 'Escape', bubbles: true}));"
                    )
                except Exception:
                    pass


            # Przypisz Nike SKU do WSZYSTKICH rozmiarów (InStock i OutOfStock) — SKU jest dla modelu, nie rozmiaru
            for s in sizes:
                if nike_sku:
                    s["sku"] = nike_sku
                elif not s.get("sku"):
                    known_sku = next((x.get("sku") for x in sizes if x.get("sku")), None)
                    if known_sku:
                        s["sku"] = known_sku

            # === ŚCIEŻKA 2: UI fallback — dla WSZYSTKICH rozmiarów bez EAN (InStock i OutOfStock) ===
            # OutOfStock rozmiary też potrzebują EAN — zamówienie mogło być złożone gdy były dostępne
            null_ean_sizes = [s for s in sizes if not s.get("ean")]
            if null_ean_sizes:
                logger.info("UI fallback: klikanie dla %d rozmiarów bez EAN z JSON-LD", len(null_ean_sizes))
                sku_value = next((s.get("sku") for s in accepted_sizes if s.get("sku")), None)
                section_expanded = False
                for s in null_ean_sizes:
                    try:
                        if not _select_size_in_dropdown(driver, s["size"]):
                            s["ean"] = None
                            s["sku"] = None
                            continue
                        ean_data = _extract_ean_for_selected_size(
                            driver, section_expanded=section_expanded, known_sku=sku_value)
                        s["ean"] = ean_data.get("ean")
                        s["sku"] = ean_data.get("sku") or sku_value
                        if ean_data.get("sku"):
                            sku_value = ean_data["sku"]
                        section_expanded = True
                    except Exception as e:
                        logger.debug("Błąd EAN dla %s: %s", s["size"], e)
                        s["ean"] = None
                        s["sku"] = sku_value

                # Retry
                still_null = [s for s in null_ean_sizes if s.get("ean") is None]
                if still_null:
                    logger.info("Retry EAN dla %d rozmiarów", len(still_null))
                    for s in still_null:
                        try:
                            if not _select_size_in_dropdown(driver, s["size"]):
                                continue
                            ean_data = _extract_ean_for_selected_size(
                                driver, section_expanded=True, known_sku=sku_value)
                            if ean_data.get("ean"):
                                s["ean"] = ean_data["ean"]
                                s["sku"] = ean_data.get("sku") or sku_value
                        except Exception:
                            pass

        name = data.get("name")
        brand = data.get("brand")

        product = {
            "url": url,
            "name": name,
            "brand": brand,
            "current_price": current_price,
            "original_price": original_price,
            "discount_percent": discount_percent,
            "image_url": packshot_url,
            "gallery_images": [packshot_url] if packshot_url else [],
            "sizes": sizes,
            "is_multi_seller": is_multi_seller,
            "accepted_sizes": [s["size"] for s in accepted_sizes],
        }

        logger.info(
            "Znaleziono: %s | %s | Cena: %.2f PLN%s | Rozmiary: %d zaakceptowanych z %d",
            brand or "?",
            name or "?",
            current_price or 0,
            f" (regularna {original_price:.2f}, -{discount_percent:.0f}%)" if discount_percent else "",
            len(accepted_sizes),
            len(sizes) if sizes else 0,
        )

        return product

    except Exception as e:
        logger.error("Błąd przy scrapowaniu %s: %s", url, e)
        return None


def _extract_ean_for_selected_size(driver, section_expanded=False, known_sku=None) -> dict:
    """
    Extract EAN/GTIN and SKU for the currently selected size.
    Optimized: skip section expansion if already done, skip SKU if known.
    """
    import time

    try:
        if not section_expanded:
            # First call: scroll down and expand "Szczegóły produktu"
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.6);")
            time.sleep(0.2)

            clicked = driver.execute_script("""
                var buttons = document.querySelectorAll('button[aria-expanded], button');
                for (var i = 0; i < buttons.length; i++) {
                    var text = buttons[i].innerText.trim();
                    if (text === 'Szczegóły produktu') {
                        buttons[i].scrollIntoView({behavior: 'instant', block: 'center'});
                        if (buttons[i].getAttribute('aria-expanded') === 'false') {
                            buttons[i].click();
                        }
                        return true;
                    }
                }
                return false;
            """)
            # Nie zwracamy None gdy nie znaleźliśmy przycisku - sekcja może być już otwarta
            time.sleep(0.3)
        
        # Poll for "Wyświetl szczegóły produkcji" and EAN/GTIN
        # Zalando fetches details asynchronously.
        details = None
        max_polls = 6 if section_expanded else 15
        clicked_production = False
        
        for _ in range(max_polls):
            if not clicked_production:
                clicked_production = driver.execute_script("""
                    var allElements = document.querySelectorAll('button, a, span');
                    for (var i = 0; i < allElements.length; i++) {
                        var text = allElements[i].innerText.trim().toLowerCase();
                        if (text.includes('wyświetl') && text.includes('produkcji')) {
                            allElements[i].click();
                            return true; // Clicked!
                        }
                    }
                    return false;
                """)
                
            time.sleep(0.3)
            
            details = driver.execute_script("""
                var text = document.body.innerText;
                var eanMatch = text.match(/EAN\\/GTIN[:\\s]*([0-9]+)/);
                var skuMatch = text.match(/[Nn]umer\\s+modelu[:\\s]*([A-Za-z0-9\\-]+)/);
                return {ean: eanMatch ? eanMatch[1] : null, sku: skuMatch ? skuMatch[1] : null};
            """)
            if details and details.get("ean"):
                # Always format EAN by stripping leading zeros here to check if it's not empty
                break

        if known_sku and details:
            details["sku"] = known_sku

        # Strip leading zeros from EAN (e.g. "0198488602165" → "198488602165")
        if details and details.get("ean"):
            details["ean"] = details["ean"].lstrip("0") or details["ean"]

        return details or {"ean": None, "sku": None}

    except Exception as e:
        logger.debug("Błąd EAN: %s", e)
        return {"ean": None, "sku": None}


    finally:
        # Close modal quickly
        try:
            driver.execute_script("""
                document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', code: 'Escape', bubbles: true}));
            """)
            time.sleep(0.15)
        except:
            pass


def _check_sellers_per_size(driver, sizes: list):
    """
    For multi-seller products, click each available size and check
    who the seller is by reading "Sprzedaż i dostawa przez..." text.
    Also extracts EAN/SKU for Zalando sizes.
    Mutates the sizes list in-place.
    """
    import time

    product_url = driver.current_url.split("?")[0]  # bez query string

    available_sizes = [s for s in sizes if s["available"]]
    if not available_sizes:
        return

    def _ensure_on_product_page():
        """Sprawdza czy nadal na stronie produktu. Jeśli nie (login redirect), wraca."""
        cur = driver.current_url
        if "login" in cur or "accounts" in cur or product_url not in cur:
            logger.info("Wykryto redirect (URL: %s) — wracam na produkt", cur[:60])
            driver.get(product_url)
            time.sleep(3)
            # Re-otwórz dropdown
            driver.execute_script("""
                var btn = document.getElementById('picker-trigger');
                if (btn) { btn.click(); return; }
                var btns = document.querySelectorAll('button');
                for (var b of btns) {
                    if (b.innerText.toLowerCase().includes('rozmiar') || b.innerText.toLowerCase().includes('size')) { b.click(); break; }
                }
            """)
            time.sleep(1.2)
            return True
        return False

    for s in sizes:
        if not s["available"]:
            s["seller"] = "unknown"
            continue

        # Pomiń rozmiary bez ceny — w multi-seller klik na nie często przekierowuje na login
        if s.get("price") is None:
            logger.info("Rozmiar %s → price=None, pomijam klik (zakładam marketplace)", s["size"])
            s["seller"] = "unknown"
            continue

        try:
            _ensure_on_product_page()

            if not _select_size_in_dropdown(driver, s["size"]):
                logger.info("Rozmiar %s → klik nie udał się → zakładam Zalando", s["size"])
                s["seller"] = "zalando"  # zakładamy Zalando jeśli nie można kliknąć
                continue

            time.sleep(1.0)

            # Sprawdź czy nie przekierowało na login
            if _ensure_on_product_page():
                logger.info("Rozmiar %s → redirect po kliku → zakładam marketplace", s["size"])
                s["seller"] = "unknown"
                continue

            # Read seller info
            seller_text = driver.execute_script("""
                var body = document.body.innerText;
                var match = body.match(/[Ss]przedaż i dostawa przez przedsiębiorcę\\s+([^\\n]+)/);
                if (match) return match[1].trim();
                var match2 = body.match(/[Ss]przedaje i wysyła\\s+([^\\n]+)/);
                if (match2) return match2[1].trim();
                return null;
            """)

            if seller_text:
                s["seller"] = seller_text.lower()
                logger.info("Rozmiar %s → marketplace: %s", s["size"], seller_text)
            else:
                s["seller"] = "zalando"
                logger.info("Rozmiar %s → Zalando", s["size"])
                # Extract EAN/SKU for Zalando sizes
                ean_data = _extract_ean_for_selected_size(driver)
                s["ean"] = ean_data.get("ean")
                s["sku"] = ean_data.get("sku")

        except Exception as e:
            logger.info("Błąd przy sprawdzaniu sprzedawcy dla %s: %s — zakładam Zalando", s["size"], e)
            s["seller"] = "zalando"  # zakładamy Zalando przy błędzie



def _extract_sizes(driver) -> list:
    """
    Extract available sizes by clicking the size picker dropdown.
    Returns list of {size, available, price, low_stock} dicts.
    """
    import time

    try:
        # Click the size picker to open dropdown
        picker = driver.execute_script("""
            var btn = document.getElementById('picker-trigger');
            if (btn) { btn.click(); return true; }
            var buttons = document.querySelectorAll('button');
            for (var i = 0; i < buttons.length; i++) {
                var text = buttons[i].innerText.toLowerCase();
                if (text.includes('rozmiar') || text.includes('size')) {
                    buttons[i].click();
                    return true;
                }
            }
            return false;
        """)

        if not picker:
            logger.debug("Nie znaleziono przycisku rozmiarów")
            return []

        time.sleep(1.5)

        # Read sizes from the dropdown - find spans with shoe size text
        sizes_data = driver.execute_script("""
            var sizes = [];
            // Matches: shoe sizes (38, 38.5, 38 1/3), range sizes (128-132, 147-163), clothing (XS-XXXL), One Size
            var sizeRegex = /^\d{2}([.,]\d{1,2})?(\s+\d+\/\d+)?$|^\d{2,3}-\d{2,3}$|^(XXX?L|XXXL|3XL|XXL|XL|XS|L|M|S)$|^[Oo]ne\s*[Ss]ize$|^[Jj]eden\s+[Rr]ozmiar$/;
            var allSpans = document.querySelectorAll('span');
            
            for (var i = 0; i < allSpans.length; i++) {
                // Get direct text content only (not children)
                var directText = '';
                for (var j = 0; j < allSpans[i].childNodes.length; j++) {
                    if (allSpans[i].childNodes[j].nodeType === 3) {
                        directText += allSpans[i].childNodes[j].textContent.trim();
                    }
                }
                directText = directText.trim();
                
                if (!sizeRegex.test(directText)) continue;
                
                // Check visibility
                var rect = allSpans[i].getBoundingClientRect();
                if (rect.width === 0) continue;
                
                // Go up to find the individual SIZE ROW context
                // IMPORTANT: We must NOT go past the row into the list container
                // because that would include "Powiadom mnie" from OTHER sizes
                var contextText = '';
                var el = allSpans[i];
                for (var k = 0; k < 4; k++) {
                    if (el.parentElement) {
                        el = el.parentElement;
                        var txt = el.innerText.trim();
                        
                        // Check if this element contains multiple size numbers
                        // If so, we've gone too far (into the list container)
                        var sizeMatches = txt.match(/\b\d{2}([.,]\d{1,2})?(\s+\d+\/\d+)?\b|\b\d{2,3}-\d{2,3}\b|\b(XXX?L|XXXL|3XL|XXL|XL|XS|L|M|S)\b|One\s*Size|Jeden\s+Rozmiar/gi);
                        if (sizeMatches && sizeMatches.length > 1) {
                            break;  // Stop! We're in the parent list container
                        }
                        
                        // Stop if text is too long (we're in a big container)
                        if (txt.length > 100) break;
                        
                        contextText = txt;
                        
                        // Stop early if we found meaningful context
                        if (txt.includes('Powiadom') || txt.includes('pozosta') || 
                            txt.includes('Pozosta') ||
                            /\\d[\\d\\s]*[.,]\\d{2}\\s*z/.test(txt)) {
                            break;
                        }
                    }
                }
                
                // Remove the size number from context to avoid price concat
                var afterSize = contextText.replace(directText, '').trim();
                var contextLower = contextText.toLowerCase();
                
                var available = true;
                var sizePrice = null;
                var lowStock = false;
                
                // "Powiadom mnie" = sold out (but only if in THIS size's context)
                if (contextLower.includes('powiadom') || contextLower.includes('notify')) {
                    available = false;
                } else {
                    // Extract price from context (after removing size number)
                    var priceMatch = afterSize.match(/(\\d[\\d\\s]*[.,]\\d{2})\\s*z/);
                    if (priceMatch) {
                        sizePrice = parseFloat(priceMatch[1].replace(/\\s/g, '').replace(',', '.'));
                    }
                }
                
                // Detect price color to identify seller
                // RED price (rgb(218,4,16)) = Zalando sale
                // GRAY/BLACK price (rgb(92,97,105)) = partner/Nike
                var priceIsRed = false;
                if (sizePrice !== null) {
                    var priceSpans = el.querySelectorAll('span');
                    for (var p = 0; p < priceSpans.length; p++) {
                        var pt = priceSpans[p].innerText.trim();
                        if (/\\d.*z/.test(pt)) {
                            var color = window.getComputedStyle(priceSpans[p]).color;
                            // Parse rgb(r, g, b) - red channel > 200 = sale/red color
                            var rgbMatch = color.match(/rgb\\((\\d+)/);
                            if (rgbMatch && parseInt(rgbMatch[1]) > 200) {
                                priceIsRed = true;
                            }
                            break;
                        }
                    }
                }
                
                // "Pozostał tylko X" with 1-3 = low stock
                if (/pozosta.*(1|2|3)\s/i.test(contextText)) {
                    lowStock = true;
                    // If no price was found, the size IS available but low stock
                    if (sizePrice === null) available = true;
                }
                
                sizes.push({
                    size: directText,
                    available: available,
                    price: sizePrice,
                    low_stock: lowStock,
                    price_is_red: priceIsRed
                });
            }
            
            return sizes;
        """)

        # Close the dropdown
        driver.execute_script("""
            document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', code: 'Escape', bubbles: true}));
            var overlay = document.querySelector('[class*="Overlay"], [class*="overlay"], [class*="backdrop"]');
            if (overlay) overlay.click();
        """)
        time.sleep(0.5)

        if sizes_data:
            logger.info("RAW sizes_data first 3: %s", sizes_data[:3])
            # Deduplicate (keep first occurrence of each size)
            seen = set()
            unique_sizes = []
            for s in sizes_data:
                if s["size"] not in seen:
                    seen.add(s["size"])
                    unique_sizes.append(s)

            logger.debug("Znaleziono %d rozmiarów", len(unique_sizes))
            return unique_sizes

        return []

    except Exception as e:
        logger.debug("Błąd przy ekstrakcji rozmiarów: %s", e)
        return []
