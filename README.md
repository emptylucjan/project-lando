# Vero Sport — Zalando Integration

## 📋 Notatka: 2026-03-27, 09:04

### ✅ Co działa

- **Scraper Zalando** — EAN, cena, rozmiary butów, odzieży, zakresów wzrostowych (`128-132`, `147-163` itp.), `One Size`; auto-discovery nowych formatów rozmiarów z JSON-LD
- **CSV ticket** — format `LINK;CENA;LIMIT;[rozmiary]`, rozmiary jako dynamiczne kolumny nagłówka; obsługuje dowolny format rozmiaru
- **Tworzenie PZ** (Przyjęcie Zewnętrzne) w Subiekcie Nexo przez Sfera CLI
- **Tworzenie FZ** (Faktura Zakupu) w Subiekcie Nexo przez Sfera CLI
- **Tworzenie ZK** (Zamówienie od Klienta) w Subiekcie Nexo przez Sfera CLI
- **Parsowanie faktur PDF** — wyciąganie numeru FV, daty, SKU, cen z PDF Zalando

---

### ❌ Co nie działa / nie sprawdzone

- **Parsowanie dat z faktury** — update daty w PZ/FZ z faktury PDF nie działa poprawnie
- **Logika podwójnej paczki** — brak implementacji
- **Wysyłanie faktur na Google Docs** — nie zaimplementowane
- **Logika dostaw i odkładania paczek** — nie gotowe
- **Aktualna logika dostaw** — nie sprawdzone czy zmiana statusu PZ/FZ z `O` (odłożone) na `P` (przyjęte) działa

---

### 🗂️ Format CSV ticketu

```
LINK ; CENA ; LIMIT ; 38 ; 39 ; 40 ; 128-132 ; 132-147 ; One Size
https://zalando.pl/... ; 227 ;  ;  ;  2 ;  ;  2 ;
```

- `CENA` — opcjonalna (bot pobiera z Zalando jeśli 0)
- `LIMIT` — opcjonalny limit par na zamówienie
- Reszta kolumn = rozmiary dokładnie jak na Zalando

---

### 📁 Kluczowe pliki

| Plik | Rola |
|------|------|
| `mrowka/mrowka_lib.py` | Główna logika bota: CSV → scan → PZ/FZ/ZK |
| `mrowka/mrowka_bot.py` | Discord bot, komendy, reakcje |
| `mrowka/mrowka_data.py` | Struktury danych (ticket, order item, shoe) |
| `scraper/extractor.py` | Scraping Zalando: EAN, rozmiary, ceny, zdjęcia |
| `mrowka/zalando_scanner.py` | Opakowuje extractor, zwraca `ScanResult` |
| `mrowka/gmail_imap.py` | IMAP: tracking, faktury |
| `mrowka/invoice_parser.py` | Parsowanie PDF faktur Zalando |
| `mrowka/ean_db.py` | SQLite — lokalna baza EANów |
| `ReflectSfera/` | .NET CLI — most do Sfera SDK (Subiekt Nexo) |
