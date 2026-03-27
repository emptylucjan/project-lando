from __future__ import annotations
"""
logger.py — port z excelex/boty/logger.py, kompatybilny z Windows
"""
import logging
import functools
import traceback
import json
import pathlib
import threading
import urllib.request
import urllib.error

logger = logging.getLogger("mrowka")


def _load_webhook_url() -> str | None:
    try:
        config_path = pathlib.Path(__file__).parent / "config.json"
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        url = cfg.get("error_webhook_url", "")
        return url if url and not url.startswith("WKLEJ") else None
    except Exception:
        return None


class DiscordWebhookHandler(logging.Handler):
    """Wysyła logi ERROR/CRITICAL na Discord webhook (synchronicznie w wątku)."""

    def __init__(self):
        super().__init__(level=logging.ERROR)
        self.webhook_url: str | None = _load_webhook_url()

    def emit(self, record: logging.LogRecord):
        if not self.webhook_url:
            return
        try:
            msg = self.format(record)
            # Utnij do 1900 znaków (Discord limit 2000)
            if len(msg) > 1900:
                msg = msg[:1900] + "\n…(obcięto)"
            level_emoji = "🔴" if record.levelno >= logging.CRITICAL else "⚠️"
            payload = json.dumps({
                "content": f"{level_emoji} **[{record.levelname}]** `{record.name}`\n```\n{msg}\n```"
            }).encode("utf-8")
            req = urllib.request.Request(
                self.webhook_url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            # Wyślij w osobnym wątku żeby nie blokować asyncio
            threading.Thread(target=self._send, args=(req,), daemon=True).start()
        except Exception:
            pass  # nigdy nie crashuj przez logger

    @staticmethod
    def _send(req):
        try:
            urllib.request.urlopen(req, timeout=5)
        except Exception:
            pass


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    # Podepnij Discord webhook handler
    webhook_handler = DiscordWebhookHandler()
    webhook_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    ))
    logging.getLogger().addHandler(webhook_handler)


def try_log(default=None):
    """Dekorator synchroniczny — łapie wyjątki i loguje je."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.exception(f"{func.__name__}: {e}")
                return default
        return wrapper
    return decorator


def async_try_log(default=None):
    """Dekorator asynchroniczny — łapie wyjątki i loguje je."""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.exception(f"{func.__name__}: {e}")
                return default
        return wrapper
    return decorator
