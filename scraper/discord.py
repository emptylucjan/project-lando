"""
Discord webhook helper — sends rich embed alerts for Zalando deals.
"""

import json
import logging
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)


def send_discord_alert(webhook_url: str, product: dict, buy_eur: float, eur_rate: float) -> bool:
    """
    Send a Discord embed with product deal info.

    Args:
        webhook_url: Discord webhook URL
        product: dict with keys: name, brand, current_price, url, image_url
        buy_eur: calculated buy price in EUR
        eur_rate: EUR/PLN rate used in calculation

    Returns:
        True if sent successfully, False otherwise
    """
    name = product.get("name", "Nieznany produkt")
    brand = product.get("brand", "")
    price_pln = product.get("current_price", 0)
    url = product.get("url", "")
    image_url = product.get("image_url") or product.get("thumbnail_url")

    title = f"{brand} — {name}" if brand else name
    # Trim long titles
    if len(title) > 200:
        title = title[:197] + "..."

    embed = {
        "title": title,
        "url": url,
        "color": 0x57F287,  # Discord green
        "fields": [
            {
                "name": "💰 Cena Zalando",
                "value": f"**{price_pln:.2f} PLN**",
                "inline": True,
            },
            {
                "name": "🛒 Buy price",
                "value": f"**{buy_eur:.2f} EUR**",
                "inline": True,
            },
            {
                "name": "📈 Kurs EUR",
                "value": f"{eur_rate:.4f} PLN",
                "inline": True,
            },
        ],
        "footer": {
            "text": "Zalando Monitor • Shox",
        },
    }

    # Add thumbnail if available
    if image_url:
        embed["thumbnail"] = {"url": image_url}

    payload = json.dumps({"embeds": [embed]}).encode("utf-8")

    try:
        req = urllib.request.Request(
            webhook_url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status in (200, 204):
                logger.info("✅ Discord alert wysłany: %s (%.2f EUR)", name[:50], buy_eur)
                return True
            else:
                logger.warning("Discord webhook zwrócił status %d", resp.status)
                return False
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        logger.error("Discord HTTP error %d: %s", e.code, body[:200])
        return False
    except Exception as e:
        logger.error("Błąd wysyłania Discord webhook: %s", e)
        return False
