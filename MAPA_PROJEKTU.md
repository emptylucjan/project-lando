# 🗺️ Vero Sport — Mapa Projektu

## Pełny Flow Zamówienia

```
1. TICKET CSV (przez Discord)
   └─ Mrówka dzieli na order_items wg limitu kwotowego
   
2. Auto-scan Zalando → EAN, cena, rozmiary → ean_db
   EnsureProduct w Subiekt (symbol + EAN)
   CreatePZ → Status: "Odłożone przyjęcie towaru"
              Uwagi: "Zamówienie: {name} | Konto: {email} | Hasło: {pass}"
   
3. IMAP check_interia (co godzinę, tylko UNSEEN)
   └─ Email "zostanie dostarczone" → tracking (InPost/DHL/DPD)
      → POST /api/pz/update-tracking → NumerPrzesylki + Uwagi w PZ

4. IMAP check_imap_invoice (co godzinę)
   └─ Email "Faktura od Zalando" → #magazynierzy
      (login, numer zamówienia, prośba o PDF)
      
5. #magazynierzy — PDF faktury (plik "Invoice*.pdf")
   └─ invoice_parser.py: numer FV, data, SKU, ceny
      → POST /api/pz/update-invoice → NumerZewnetrzny + daty w PZ
      → POST /api/fz/create   → Faktura Zakupu w Subiekcie

6. #magazynierzy LUB DM !start_dostawy
   └─ Magazynier skanuje tracking z paczki
      → POST /api/pz/accept → Status=20 (Przyjęty) + DataMagazynowa=dziś
      → Discord: order_item → ✅ ZAMOWIENIE_ZOSTALO_ZREALIZOWANE
```

---

## ✅ Co jest zrobione

| Moduł | Plik | Status |
|-------|------|--------|
| Scraper Zalando (EAN, cena, rozmiary) | `scraper/extractor.py` | ✅ |
| Lokalna baza EANów | `mrowka/ean_db.py` | ✅ |
| Mrówka: auto-scan + podział ticketu + CreatePZ | `mrowka/mrowka_lib.py` | ✅ |
| EnsureProduct + EAN w Subiekcie | backend `EnsureProductExistsAsync` | ✅ |
| `POST /api/pz/create` — Odłożone, uwagi Discord | backend | ✅ |
| IMAP tracking (UNSEEN, parsowanie HTML, InPost/DHL/DPD) | `mrowka/gmail_imap.py` | ✅ |
| `POST /api/pz/update-tracking` — NumerPrzesylki + Uwagi | backend | ✅ |
| IMAP faktura — powiadomienie na #magazynierzy | `mrowka/mrowka_lib.py` | ✅ |
| Parsowanie PDF faktury Zalando | `mrowka/invoice_parser.py` | ✅ |
| `POST /api/pz/update-invoice` — NumerZewnetrzny + daty | backend | ✅ |
| `POST /api/fz/create` — Faktura Zakupu powiązana z PZ | backend | 🧪 czeka na test DC |
| Handle label na #magazynierzy → PZ przyjęty | `mrowka/mrowka_bot.py` | ✅ |
| `POST /api/pz/accept` — Status=20 + DataMagazynowa | backend | ✅ |
| `!start_dostawy` / `!stop_dostawy` DM — sesja skanowania | `mrowka/mrowka_bot.py` | ✅ |

---

## ❌ Co jeszcze do zrobienia

| Funkcja | Priorytet | Uwagi |
|---------|-----------|-------|
| `POST /api/fz/create` — FZ z poprawną datą, status=21 Odłożone, zapis pz_sygnatura | **wysoki** | ✅ zaimplementowane jako `CreateFZByPz` — **czeka na test DC** |
| WhatsApp → Mrówka bridge | niski | Node.js bot przekazujący do Mrówki |
| B2B Sklep → Mrówka bridge | niski | integracja z istniejącym sklepem |

---

## Endpointy Backend (.NET, port 5051)

| Endpoint | Co robi |
|----------|---------|
| `POST /api/pz/create` | Tworzy PZ (Odłożone, uwagi Discord) |
| `POST /api/pz/update-tracking` | NumerPrzesylki + Uwagi → PZ |
| `POST /api/pz/update-invoice` | NumerZewnetrzny + DataWydania + DataMagazynowa → PZ |
| `POST /api/pz/accept` | StatusDokumentuId=20 + DataMagazynowa=dziś → PZ |
| `POST /api/fz/create` | Tworzy Fakturę Zakupu z danymi z PDF |

---

## Komendy Discord (Mrówka)

| Komenda | Gdzie | Co robi |
|---------|-------|---------|
| `!start_dostawy` | DM | Otwiera sesję skanowania dostaw |
| `!stop_dostawy` | DM | Podsumowanie: przyjęte PZ, suma PLN, gotowe tickety |
| `!zrealizuj <tracking>` | DM | Ręczna zmiana statusu na Zrealizowane |
| `!biore_ticket` | ticket channel | Przypisuje ticket do siebie |
| `!sukces` / `!porazka` | ticket channel | Zmiana statusu ticketu |
| `!status` | ticket channel | Pokaż status pozycji w tickecie |
| `!cofnij <nazwa>` | ticket channel | Cofnij ostatni status |
| `!anuluj <nazwa>` | ticket channel | Anuluj pozycję/cały ticket |
| `!info <nazwa>` | ticket channel | Info o pozycji zamówienia |
| `!bank` | gdziekolwiek | Liczba wolnych kont email |
| `!podmien_mail <nazwa>` | ticket channel | Podmień konto email |
