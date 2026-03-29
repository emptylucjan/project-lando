from __future__ import annotations
"""
gmail_imap.py — Zastępuje interia.py
Czyta emaile "Twoja przesyłka zostanie dostarczona" z Gmail przez IMAP.
Obsługuje wiele kont Gmail z App Password.

Konfiguracja w config.json:
  "gmail_accounts": [
    {"email": "...", "app_password": "xxxx xxxx xxxx xxxx", "comment": "..."}
  ]
"""
import imaplib
import email
import re
import socket
import unicodedata
import json
import pathlib
from dataclasses import dataclass
from email.header import decode_header
from typing import Optional, Union

import logger as _logger

IMAP_SERVER = "imap.gmail.com"
IMAP_PORT = 993
SUBJECT_QUERY = "Twoja przesyłka zostanie dostarczona"

# Tematy maili InPost świadczące o nadaniu paczki
_INPOST_DISPATCH_SUBJECTS = [
    "potwierdzenie nadania",
    "nadano przesylke",
    "nadano przesyłkę",
    "przesylka nadana",
    "przesyłka nadana",
    "shipment dispatched",
    "label created",
]



@dataclass
class DeliveryInfo:
    """Info wyciągnięte z maila dostawczego Zalando lub InPost."""
    zalando_account: str       # np. eleatowskiedomeny+fiz10@gmail.com (z headera To:)
    gmail_base: str            # np. eleatowskiedomeny@gmail.com (konto do logowania IMAP)
    order_number: Optional[str]
    tracking: Optional[str]
    delivery_date: Optional[str]
    name_surname: Optional[str]
    shipping_amount: Optional[float] = None  # Kwota przesyłki w PLN (z maila Zalando lub InPost)

    def __str__(self) -> str:
        return (
            f"DeliveryInfo(account={self.zalando_account}, "
            f"order={self.order_number}, tracking={self.tracking}, "
            f"delivery={self.delivery_date}, amount={self.shipping_amount})"
        )



@dataclass
class DelayInfo:
    """Info wyciągnięte z maila opóźnienia dostawy Zalando."""
    zalando_account: str   # np. eleatowskiedomeny+fiz19@gmail.com
    gmail_base: str
    subject: str

    def __str__(self) -> str:
        return f"DelayInfo(account={self.zalando_account}, subject={self.subject[:40]})"


def _load_gmail_accounts() -> list[dict]:
    """Wczytuje konta Gmail z config.json."""
    config_path = pathlib.Path(__file__).parent / "config.json"
    if not config_path.exists():
        _logger.logger.error("Brak config.json!")
        return []
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    return cfg.get("gmail_accounts", [])


def _normalize(text: str) -> str:
    if not text:
        return ""
    text = text.strip().lower()
    text = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def _decode_header_value(value) -> str:
    if not value:
        return ""
    parts = decode_header(value)
    out = ""
    for part, enc in parts:
        if isinstance(part, bytes):
            out += part.decode(enc or "utf-8", errors="ignore")
        else:
            out += part
    return out


def _get_text_from_msg(msg) -> tuple[str, str]:
    """Zwraca (plain_text, html) z emaila."""
    plain = ""
    html = ""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            cdisp = str(part.get("Content-Disposition") or "")
            if "attachment" in cdisp.lower():
                continue
            if ctype == "text/plain" and not plain:
                try:
                    plain = part.get_payload(decode=True).decode(
                        part.get_content_charset() or "utf-8", errors="ignore"
                    )
                except Exception:
                    pass
            elif ctype == "text/html" and not html:
                try:
                    html = part.get_payload(decode=True).decode(
                        part.get_content_charset() or "utf-8", errors="ignore"
                    )
                except Exception:
                    pass
    else:
        try:
            payload = msg.get_payload(decode=True).decode(
                msg.get_content_charset() or "utf-8", errors="ignore"
            )
            if msg.get_content_type() == "text/html":
                html = payload
            else:
                plain = payload
        except Exception:
            pass
    return plain, html


def _extract_order_info(body: str, html: str, subject: str, to_header: str, gmail_base: str) -> DeliveryInfo:
    txt = body.replace("\r\n", "\n").replace("\r", "\n")
    subj = (subject or "").replace("\xa0", " ")
    full_content = txt + "\n" + html  # szukamy w obu

    # numer zamówienia
    m_order = re.search(r"Numer\s+zam[oó]wienia[:\s]*([0-9]+)", full_content, re.IGNORECASE)
    if not m_order:
        # Zalando umieszcza numer w linku lub jako duży numer 13-cyfrowy
        m_order = re.search(r"\b(1091[0-9]{10})\b", full_content)
    order_number = m_order.group(1).strip() if m_order else None

    # tracking — najpierw z plain text
    tracking = None
    m_track = re.search(r"Numer\s+[śs]ledzenia\s+przesy[łl]ki[:\s]*([0-9A-Z]{8,30})", full_content, re.IGNORECASE)
    if m_track:
        tracking = m_track.group(1).strip()

    # tracking — z linku InPost/DHL/DPD/GLS w HTML
    if not tracking and html:
        track_patterns = [
            r'number=([0-9]{10,30})',                          # InPost: ?number=XXXX
            r'inpost\.pl/[^"<]*?([0-9]{10,30})',              # InPost URL
            r'dhl\.com/[^"<]*?tracking[^"<]*?([0-9]{10,30})', # DHL
            r'dpd\.com/[^"<]*?([0-9]{10,30})',                # DPD
            r'gls-group\.eu/[^"<]*?([0-9]{10,30})',           # GLS
            r'poczta-polska\.pl/[^"<]*?([0-9]{10,30})',       # Poczta Polska
        ]
        for pat in track_patterns:
            m = re.search(pat, html, re.IGNORECASE)
            if m:
                tracking = m.group(1)
                _logger.logger.info("Tracking z HTML (pattern '%s'): %s", pat[:30], tracking)
                break

    # imię i nazwisko (pierwsza linia po "Adres dostawy")
    m_addr = re.search(
        r"Adres\s+dostawy\s*(.+?)\s*(Przewidywana|Data|Zalando:|Twoje)",
        txt, re.IGNORECASE | re.DOTALL
    )
    full_name = None
    if m_addr:
        for line in m_addr.group(1).split("\n"):
            line = line.strip()
            if line:
                full_name = line
                break

    # data dostawy — z tematu maila
    delivery_date = None
    m_between = re.search(
        r"mi[eę]dzy\s+(\d{1,2}\.\d{1,2}(?:\.\d{4})?).{0,10}?(\d{1,2}\.\d{1,2}(?:\.\d{4})?)",
        subj, re.IGNORECASE
    )
    if m_between:
        delivery_date = f"{m_between.group(1)}-{m_between.group(2)}"
    else:
        m_to = re.search(r"\bdo\s+(\d{1,2}\.\d{1,2}(?:\.\d{4})?)", subj, re.IGNORECASE)
        if m_to:
            delivery_date = m_to.group(1)

    # konto Zalando — z headera To:
    zalando_account = gmail_base
    m_to_addr = re.search(r"[\w.+\-]+@[\w.\-]+", to_header or "")
    if m_to_addr:
        zalando_account = m_to_addr.group(0)

    return DeliveryInfo(
        zalando_account=zalando_account,
        gmail_base=gmail_base,
        order_number=order_number,
        tracking=tracking,
        delivery_date=delivery_date,
        name_surname=full_name,
        shipping_amount=_extract_shipping_amount_zalando(txt),
    )


def _extract_shipping_amount_zalando(text: str) -> Optional[float]:
    """Wyciaga kwote z plain text Zalando: 'Platnosc za przesylke wynosi X,XX zl'"""
    # Przyklad: 'Platnosc za przesylke wynosi 737,60 zl'
    m = re.search(
        r'[Pp][\u015b]a[t\u0142][n\u0144]o[s\u015b][\u0107c][\s\S]{0,30}przesy[\u0142l]k[\u0119e]\s+wynosi\s+([\d\s]+[,\.]\d{2})\s*z[\u0142l]',
        text, re.IGNORECASE
    )
    if not m:
        # Fallback: szukaj po znormalizowanym tekście
        import unicodedata as _ud
        def _norm(s):
            s = _ud.normalize('NFD', s)
            return ''.join(c for c in s if not _ud.combining(c)).lower()
        norm = _norm(text)
        m2 = re.search(r'platnosc za przesylke wynosi\s+([\d\s]+[,\.]\d{2})\s*zl', norm)
        if m2:
            return _parse_amount(m2.group(1))
        return None
    return _parse_amount(m.group(1))


def _parse_amount(amount_str: str) -> Optional[float]:
    """Konwertuje '3 448,00' lub '3448.00' na float."""
    try:
        s = amount_str.strip().replace(' ', '').replace('\u00a0', '')
        s = s.replace(',', '.')
        return float(s)
    except Exception:
        return None


def _extract_inpost_order_info(body: str, html: str, subject: str, to_header: str, gmail_base: str) -> DeliveryInfo:
    """Parsuje maila InPost 'potwierdzenie nadania' — wyciąga tracking i konto Zalando."""
    # Tracking InPost: 24-cyfrowy barcode
    tracking = None
    m_big = re.search(r'\b([0-9]{20,30})\b', body + ' ' + html)
    if m_big:
        tracking = m_big.group(1)
    if not tracking and html:
        for pat in [r'inpost\.pl/[^"<]*?([0-9]{10,30})', r'number=([0-9]{10,30})']:
            m = re.search(pat, html, re.IGNORECASE)
            if m:
                tracking = m.group(1)
                break

    # Konto Zalando z To:
    zalando_account = gmail_base
    m_to = re.search(r"[\w.+\-]+@[\w.\-]+", to_header or "")
    if m_to:
        zalando_account = m_to.group(0)

    return DeliveryInfo(
        zalando_account=zalando_account,
        gmail_base=gmail_base,
        order_number=None,
        tracking=tracking,
        delivery_date=None,
        name_surname=None,
        shipping_amount=_extract_shipping_amount_inpost(body + ' ' + html),
    )


def _extract_shipping_amount_inpost(full_text: str) -> Optional[float]:
    """Wyciaga 'Kwota pobrania' z HTML InPost (po usunieciu tagow)."""
    # HTML stripped zawiera: 'Kwota pobrania \n 3 448,00 zl'
    m = re.search(
        r'Kwota\s+pobrania\s+([\d\s]+[,\.]\d{2})\s*z[\u0142l]',
        full_text, re.IGNORECASE
    )
    if m:
        return _parse_amount(m.group(1))
    return None


@_logger.try_log([])
def get_new_delivery_emails(gmail_account: dict, only_unseen: bool = True) -> list[DeliveryInfo]:
    """
    Loguje się na IMAP konta Gmail i zwraca listę DeliveryInfo
    dla emaili "Twoja przesyłka zostanie dostarczona".
    
    gmail_account: {"email": "...", "app_password": "..."}
    only_unseen: True = tylko nieprzeczytane, False = wszystkie
    """
    email_addr = gmail_account["email"]
    app_password = gmail_account["app_password"]
    result: list[DeliveryInfo] = []

    try:
        socket.setdefaulttimeout(20)
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        mail.login(email_addr, app_password)
        mail.select("INBOX", readonly=False)

        # Szukaj tylko maili od Zalando (IMAP filtrowanie po stronie serwera)
        # Omijamy problem z polskimi znakami w IMAP SUBJECT search
        if only_unseen:
            search_criteria = '(UNSEEN FROM "zalando")'
        else:
            search_criteria = 'FROM "zalando"'
        _, data = mail.search(None, search_criteria)
        ids = data[0].split()

        # Filtruj lokalnie po temacie (unicode OK tutaj)
        norm_query = _normalize(SUBJECT_QUERY)

        for num in ids:
            _, msg_data = mail.fetch(num, "(RFC822)")
            msg = email.message_from_bytes(msg_data[0][1])

            subject = _decode_header_value(msg.get("Subject"))
            if norm_query not in _normalize(subject):
                continue

            to_header = _decode_header_value(msg.get("To") or "")
            plain, html = _get_text_from_msg(msg)
            info = _extract_order_info(plain, html, subject, to_header, email_addr)
            result.append(info)

            # Oznacz jako przeczytany
            if only_unseen:
                mail.store(num, "+FLAGS", "\\Seen")

        # ─── InPost: potwierdzenie nadania przesyłki ───
        # Gmail IMAP nie obsługuje FROM "paczkomaty" jako substring — szukamy UNSEEN i filtrujemy w Python
        try:
            inpost_crit = "UNSEEN" if only_unseen else "ALL"
            _, id2 = mail.search(None, inpost_crit)
            all_unseen_ids = id2[0].split()
        except Exception:
            all_unseen_ids = []

        for num in all_unseen_ids:
            try:
                # Pobierz tylko nagłówki (szybko) — RFC822.HEADER zamiast pełnego RFC822
                _, hdr_data = mail.fetch(num, "(RFC822.HEADER)")
                hdr_msg = email.message_from_bytes(hdr_data[0][1])
                frm = _decode_header_value(hdr_msg.get("From", "")).lower()

                # Filtruj po nadawcy InPost
                if "inpost" not in frm and "paczkomat" not in frm:
                    continue

                subject = _decode_header_value(hdr_msg.get("Subject", ""))
                if not any(_normalize(s) in _normalize(subject) for s in _INPOST_DISPATCH_SUBJECTS):
                    if only_unseen:
                        mail.store(num, "+FLAGS", "\\Seen")
                    continue

                # Dopiero teraz pobierz pełną treść
                _, msg_data = mail.fetch(num, "(RFC822)")
                msg = email.message_from_bytes(msg_data[0][1])
                to_header = _decode_header_value(msg.get("To") or "")
                plain, html = _get_text_from_msg(msg)
                info = _extract_inpost_order_info(plain, html, subject, to_header, email_addr)
                _logger.logger.info("InPost nadanie: tracking=%s, order=%s, konto=%s",
                                    info.tracking, info.order_number, info.zalando_account)
                result.append(info)
                if only_unseen:
                    mail.store(num, "+FLAGS", "\\Seen")
            except Exception as ex:
                _logger.logger.warning("Błąd parsowania maila InPost: %s", ex)

        mail.logout()
        _logger.logger.info(f"Gmail IMAP [{email_addr}]: znaleziono {len(result)} nowych maili dostawczych")

    except Exception as e:
        _logger.logger.exception(f"get_new_delivery_emails({email_addr}): {e}")

    return result


def get_all_new_delivery_emails() -> list[DeliveryInfo]:
    """Sprawdza wszystkie konta z config.json i zwraca połączoną listę."""
    accounts = _load_gmail_accounts()
    all_results: list[DeliveryInfo] = []
    for account in accounts:
        results = get_new_delivery_emails(account)
        all_results.extend(results)
    return all_results


# Frazy w temacie maila opóźnienia
_DELAY_SUBJECTS = ["aktualizacja dotycząca twojej dostawy", "delivery update"]
# Frazy w treści potwierdzające opóźnienie
_DELAY_BODY_PHRASES = [
    "może zająć nieco dłużej",
    "moze zajac nieco dluzej",
    "delivery may take a little longer",
    "dostawa może zostać opóźniona",
]


@_logger.try_log([])
def get_new_delay_emails(gmail_account: dict, only_unseen: bool = True) -> list[DelayInfo]:
    """
    Wykrywa maile Zalando informujące o opóźnieniu dostawy.
    Temat: 'Aktualizacja dotycząca Twojej dostawy'
    Treść: zawiera frazę o opóźnieniu ('może zająć nieco dłużej').
    """
    email_addr = gmail_account["email"]
    app_password = gmail_account["app_password"]
    result: list[DelayInfo] = []

    try:
        socket.setdefaulttimeout(20)
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        mail.login(email_addr, app_password)
        mail.select("INBOX", readonly=False)

        criteria = '(UNSEEN FROM "zalando")' if only_unseen else 'FROM "zalando"'
        _, data = mail.search(None, criteria)
        ids = data[0].split()

        for num in ids:
            _, msg_data = mail.fetch(num, "(RFC822)")
            msg = email.message_from_bytes(msg_data[0][1])

            subject = _decode_header_value(msg.get("Subject", ""))
            subj_norm = _normalize(subject)

            # Sprawdź temat
            if not any(_normalize(s) in subj_norm for s in _DELAY_SUBJECTS):
                continue

            # Sprawdź treść — musi zawierać frazę o opóźnieniu
            plain, html = _get_text_from_msg(msg)
            body_norm = _normalize(plain + " " + html)
            if not any(_normalize(phrase) in body_norm for phrase in _DELAY_BODY_PHRASES):
                continue

            to_header = _decode_header_value(msg.get("To") or "")
            m_to = re.search(r"[\w.+\-]+@[\w.\-]+", to_header)
            zalando_account = m_to.group(0) if m_to else email_addr

            result.append(DelayInfo(
                zalando_account=zalando_account,
                gmail_base=email_addr,
                subject=subject,
            ))

            if only_unseen:
                mail.store(num, "+FLAGS", "\\Seen")

        mail.logout()
        _logger.logger.info("Gmail IMAP [%s]: znaleziono %d maili opóźnienia", email_addr, len(result))

    except Exception as e:
        _logger.logger.exception("get_new_delay_emails(%s): %s", email_addr, e)

    return result


def get_all_new_delay_emails() -> list[DelayInfo]:
    """Sprawdza wszystkie konta Gmail w poszukiwaniu maili o opóźnieniu dostawy."""
    accounts = _load_gmail_accounts()
    all_results: list[DelayInfo] = []
    for account in accounts:
        all_results.extend(get_new_delay_emails(account))
    return all_results


def test_connection():
    """Test połączenia IMAP — wywołaj ręcznie do weryfikacji."""
    accounts = _load_gmail_accounts()
    for account in accounts:
        email_addr = account["email"]
        app_password = account["app_password"]
        print(f"\n--- Testowanie konta: {email_addr} ---")
        try:
            mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
            mail.login(email_addr, app_password)
            print(f"✅ Połączono!")
            mail.select("INBOX")
            _, data = mail.search(None, "ALL")
            count = len(data[0].split())
            print(f"📬 Emaili w skrzynce: {count}")

            # Szukaj maili dostawczych
            deliveries = get_new_delivery_emails(account, only_unseen=False)
            print(f"📦 Maile 'zostanie dostarczona': {len(deliveries)}")
            for d in deliveries[:3]:
                print(f"  → {d}")
            mail.logout()
        except Exception as e:
            print(f"❌ Błąd: {e}")


def get_delivery_info_for_mail(konto) -> Optional["DeliveryInfo"]:
    """
    Kompatybilna zamiana za interia.get_info_from_interia().
    konto: mails.MailData — sprawdza WSZYSTKIE konta Gmail z configu
    szukając maila przypisanego do zalando_account == konto.mail
    """
    all_infos = get_all_new_delivery_emails()
    for info in all_infos:
        if info.zalando_account == konto.mail:
            return info
    # Nie znaleziono — zwróć pusty obiekt (nie None) żeby nie blokować pętli
    return DeliveryInfo(
        zalando_account=konto.mail,
        gmail_base="",
        order_number=None,
        tracking=None,
        delivery_date=None,
        name_surname=None,
    )


if __name__ == "__main__":
    test_connection()
