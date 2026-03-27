"""
invoice_parser.py — Parser faktury PDF Zalando
Wyciąga: numer faktury (NumerRachunku), datę wystawienia, numer zamówienia, pozycje.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Optional, Union

try:
    import pdfplumber
    _PDFPLUMBER_OK = True
except ImportError:
    _PDFPLUMBER_OK = False

import logger as _logger


@dataclass
class InvoiceItem:
    sku: str
    name: str
    quantity: int
    price_netto: float
    vat_pln: float
    vat_pct: int


@dataclass
class InvoiceData:
    """Dane wyciągnięte z faktury Zalando PDF."""
    order_number: Optional[str] = None      # np. 10910151062396
    invoice_number: Optional[str] = None    # np. PL100401677550
    invoice_date: Optional[str] = None      # np. 2026-03-17
    items: list[InvoiceItem] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return bool(self.invoice_number and self.invoice_date)

    def __str__(self) -> str:
        return (
            f"InvoiceData(order={self.order_number}, "
            f"fv={self.invoice_number}, date={self.invoice_date}, "
            f"items={len(self.items)})"
        )


def _extract_text_from_pdf(pdf_path: str) -> str:
    """Wyciąga cały tekst z PDF przez pdfplumber z sortowaniem per-wiersz."""
    if not _PDFPLUMBER_OK:
        raise ImportError("pdfplumber nie jest zainstalowany. Uruchom: pip install pdfplumber")

    all_text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            words = page.extract_words(x_tolerance=5, y_tolerance=5)
            rows: dict[int, list[str]] = {}
            for w in words:
                y = round(w["top"] / 5) * 5
                rows.setdefault(y, []).append(w["text"])
            for y in sorted(rows.keys()):
                all_text += " ".join(rows[y]) + "\n"
    return all_text


def parse_invoice_pdf(pdf_path: str) -> InvoiceData:
    """
    Parsuje fakturę Zalando z pliku PDF.
    Zwraca InvoiceData z numerem FV, datą i pozycjami.
    """
    try:
        text = _extract_text_from_pdf(pdf_path)
    except Exception as e:
        _logger.logger.error("invoice_parser: błąd odczytu PDF %s: %s", pdf_path, e)
        return InvoiceData()

    data = InvoiceData()

    # Numer zamówienia Zalando
    m = re.search(r"Numer\s+zam[oó]wienia\s*[:\s]+(\d{10,20})", text, re.IGNORECASE)
    if m:
        data.order_number = m.group(1).strip()

    # Numer faktury (Numer rachunku w Zalando = numer FV VAT)
    m = re.search(r"Numer\s+rachunku\s*[:\s]+([A-Z]{2}[0-9A-Z/-]{4,30})", text, re.IGNORECASE)
    if m:
        data.invoice_number = m.group(1).strip()

    # Data wystawienia — format YYYY-MM-DD lub DD.MM.YYYY
    m = re.search(r"(\d{4}-\d{2}-\d{2})", text)
    if m:
        data.invoice_date = m.group(1)
    else:
        m = re.search(r"(\d{1,2}[./]\d{1,2}[./]\d{4})", text)
        if m:
            raw = m.group(1)
            # Normalize to YYYY-MM-DD
            parts = re.split(r"[./]", raw)
            if len(parts[2]) == 4:  # DD.MM.YYYY
                data.invoice_date = f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
            else:
                data.invoice_date = raw

    # Pozycje faktury — pattern: SKU ... Cena_netto VAT_pln VAT%
    # Np: "NI122S0SE-Q11000L000 - Kurtka przejściowa - L 200,81 46,19 23 %"
    item_pattern = re.compile(
        r"(\d+)\s+"                              # ilość
        r"([A-Z0-9]{6,20}-[A-Z0-9]{8,20})"      # SKU
        r"\s+-\s+"
        r"(.+?)"                                 # nazwa
        r"\s+([\d,]+)\s+([\d,]+)\s+(\d+)\s*%",  # cena netto, VAT PLN, VAT%
        re.MULTILINE
    )
    for m in item_pattern.finditer(text):
        try:
            item = InvoiceItem(
                sku=m.group(2),
                name=m.group(3).strip(),
                quantity=int(m.group(1)),
                price_netto=float(m.group(4).replace(",", ".")),
                vat_pln=float(m.group(5).replace(",", ".")),
                vat_pct=int(m.group(6)),
            )
            data.items.append(item)
        except Exception:
            pass

    _logger.logger.info("invoice_parser: %s", data)
    return data


def parse_invoice_bytes(pdf_bytes: bytes, tmp_path: str = "/tmp/invoice_tmp.pdf") -> InvoiceData:
    """Parsuje fakturę z bytes (np. z Discord attachment)."""
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(pdf_bytes)
        tmp = f.name
    try:
        return parse_invoice_pdf(tmp)
    finally:
        try:
            os.unlink(tmp)
        except Exception:
            pass


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\lukko\Desktop\projekt zalando\Invoice-10910151062396.pdf"
    result = parse_invoice_pdf(path)
    print(f"Numer zamówienia: {result.order_number}")
    print(f"Numer faktury:    {result.invoice_number}")
    print(f"Data wystawienia: {result.invoice_date}")
    print(f"Pozycje ({len(result.items)}):")
    for item in result.items:
        print(f"  SKU={item.sku} | {item.name} | ilość={item.quantity} | netto={item.price_netto} | VAT={item.vat_pct}%")
    print(f"\nStatus: {'OK ✅' if result.ok else 'NIEKOMPLETNE ❌'}")
