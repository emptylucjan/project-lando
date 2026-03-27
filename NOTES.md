# NOTES — Zalando Scraper

## Co robi projekt

Scraper automatycznie sprawdza ceny produktów na Zalando.pl.
Wczytuje listę URLi z pliku XLSX, otwiera każdy produkt w przeglądarce
i wyciąga dane. Jeśli cena jest w limicie — zapisuje ofertę do pliku JSON.

---

## Przepływ krok po kroku

### 1. Wczytanie konfiguracji i listy produktów (`main.py`)
- `config.json` określa: nazwę pliku XLSX, opóźnienia między requestami, tryb headless
- `produkty.xlsx` — kolumna A: URL produktu, kolumna B: maksymalna akceptowalna cena
- Każdy wiersz z prawidłowym URL i ceną trafia do listy do sprawdzenia

### 2. Uruchomienie przeglądarki (`scraper/browser.py`)
- Chrome przez Selenium + `webdriver-manager` (auto-pobieranie ChromeDrivera)
- Flagi anti-bot: wyłączone `AutomationControlled`, nadpisany `navigator.webdriver`,
  fałszywe `plugins` i `languages`, User-Agent udający normalnego użytkownika
- Pierwsze wejście na `zalando.pl` + kliknięcie "Akceptuj wszystko" (cookie popup)
- Między produktami: losowe opóźnienie (domyślnie 3–7 sek) żeby nie wpaść w bana

### 3. Scrapowanie danych produktu (`scraper/extractor.py → extract_product_data`)

#### 3a. Ładowanie strony
- `driver.get(url)` — otwiera stronę produktu
- Czeka aż pojawi się element ze słowem "zł" (dowód że strona się załadowała)
- Dodatkowy `sleep(2)` na doładowanie JS

#### 3b. Wyciągnięcie danych przez JavaScript (jeden duży `execute_script`)
- **Nazwa** — `document.querySelector('h1').innerText`
- **Marka** — z `<script type="application/ld+json">` (JSON-LD structured data)
- **Cena bieżąca** — skanowanie wszystkich `<span>` pasujących do formatu `X,XX zł`,
  widocznych na ekranie (rect.width > 0), sortowanie po pozycji Y,
  bierze pierwszy duży (fontSize ≥ 16) w górnej połowie strony (top < 800px)
- **Cena regularna** — regex na `document.body.innerText` szukający "Cena regularna: X,XX"
- **Flaga "od X zł"** — wykrywa czy to produkt multi-seller (kilku sprzedawców),
  czyta kontekst wokół elementu z ceną (parent/sibling) i szuka prefixu "od "
- **Kandydaci na zdjęcie** — wszystkie `<img src*="spp-media-p1">` widoczne jako miniaturki
  (width < 200px, top < 1300px), deduplikowane po hashu z URL

#### 3c. Wykrywanie packshotowego zdjęcia (`_is_packshot_bg` + `_find_packshot_url`)
- Dla każdego kandydata pobiera miniaturę 100px przez HTTP
- Sprawdza 8 regionów: 4 rogi + 4 krawędzie środkowe
- Każdy region musi mieć: wszystkie kanały RGB > 200 i rozpiętość kanałów < 20
  (czyli jasne, neutralne tło = szary Zalando packshot)
- Dodatkowo: inter-region range < 12 (tło musi być jednorodne — odrzuca lifestyle foto
  ze zdjęciami modeli w studio z gradientem oświetlenia)
- Znaleziony packshot skalowany do `imwidth=1800` (high-res)

#### 3d. Wyciągnięcie rozmiarów (`_extract_sizes`)
- Klika przycisk size picker (`#picker-trigger`)
- Czeka 1.5 sek na otwarcie dropdowna
- Skanuje wszystkie `<span>` pasujące do rozmiaru buta (35–52, .5) lub odzieży (XS–3XL)
- Dla każdego rozmiaru idzie w górę drzewa DOM (max 4 poziomy) szukając kontekstu ROW
  — zatrzymuje się gdy znajdzie > 1 rozmiar w tekście (weszliśmy za wysoko w listę)
- Z kontekstu row czyta:
  - "Powiadom mnie" → `available: false` (brak na stanie)
  - Cena w formacie `X,XX zł` → `price`
  - "Pozostał tylko 1/2/3" → `low_stock: true`
  - Kolor ceny: czerwony (RGB.r > 200) → `price_is_red` (wyprzedaż Zalando)
- Rozmiary z `low_stock` są traktowane jako niedostępne (za ryzykowne)

#### 3e. Obsługa multi-seller (`_check_sellers_per_size`)
- Tylko gdy wykryto "od X zł"
- Dla każdego dostępnego rozmiaru: klika rozmiar w dropdownie i czyta
  "Sprzedaż i dostawa przez przedsiębiorcę X" — jeśli brak tego tekstu = Zalando
- Tylko rozmiary sprzedawane przez Zalando są `accepted: true`

#### 3f. Pobranie EAN/SKU (`_extract_ean_for_selected_size`)
- Dla każdego zaakceptowanego rozmiaru: wybiera rozmiar w dropdownie
- Scrolluje w dół, klika "Szczegóły produktu" (aria-expanded)
- Klika "Wyświetl szczegóły produkcji" (modal z danymi technicznymi)
- Polluje body.innerText do 12x co 250ms szukając:
  - `EAN/GTIN: XXXXXXXXXXXXX` → EAN (strip wiodących zer, np. `0198...` → `198...`)
  - `Numer modelu: XXXXX` → SKU (ten sam dla wszystkich rozmiarów)
- Zamyka modal przez `KeyboardEvent('keydown', Escape)`

### 4. Filtr ceny (`scraper/price_filter.py`)
- Jeśli `current_price <= max_price` → produkt przechodzi
- Jeśli brak ceny → odrzucony z logiem WARNING

### 5. Zapis oferty (`offers/storage.py`)
- Oferty trzymane w `data/offers.json`
- Deduplication po URL — duplikaty nie są nadpisywane
- Do każdej oferty dodaje: `max_price_threshold` (limit z XLSX) i `added_at` (timestamp)

### 6. Pobieranie i obróbka zdjęcia (`extractor.py → download_product_image + remove_background`)
- Pobiera JPG packshotem przez urllib (z User-Agentem)
- Zapisuje do `images/{SKU}.jpg`
- `remove_background`: flood-fill od krawędzi obrazu → usuwa tło połączone z brzegiem
  o kolorze zbliżonym do narożników (bg_color z mediany 4 rogów, tolerancja 18)
- Biały/jasny produkt na jasnym tle: pomija usuwanie (p75 centralnego diff < 20)
- Wygładza krawędzie: partial transparency dla pikseli na granicy tło/produkt
- Zapisuje do `images/{SKU}.png` z kanałem alpha (przezroczyste tło)

---

## Pliki i ich role

| Plik | Rola |
|------|------|
| `main.py` | Punkt wejścia — pętla po produktach z XLSX |
| `config.json` | Konfiguracja (plik XLSX, delay, headless) |
| `produkty.xlsx` | Lista URL + max ceny (wejście) |
| `scraper/browser.py` | Chrome + stealth setup + cookie handling |
| `scraper/extractor.py` | Cała logika wyciągania danych ze strony |
| `scraper/price_filter.py` | Prosty filtr cena ≤ max |
| `offers/storage.py` | Zapis/odczyt ofert do `data/offers.json` |
| `images/` | Pobrane zdjęcia JPG + PNG (transparent bg) |
| `test_scrape.py` | Szybki test jednego URL bez XLSX |
| `test_batch.py` | Test kilku URLi naraz |
| `data/offers.json` | Wynik działania — zaakceptowane oferty |

---

## Ważne detale / edge cases

- **EAN ze stron Zalando zawierają wiodące zero** (format EAN-14 → 13 cyfr po stripowaniu)
  → zawsze `lstrip("0")`
- **Rozmiary low_stock (1–3 szt)** są oznaczane `available: false` — za ryzykowne do oferty
- **Multi-seller ("od X zł")** — każdy rozmiar może mieć innego sprzedawcę;
  akceptujemy tylko Zalando (nie partnerów)
- **Packshot detection** opiera się na pixel analysis a nie URL — bo URL nie zawsze
  wskazuje na typ zdjęcia; lifestyle foto z modelem też ma "czysty" URL
- **remove_background** używa flood-fill (nie prostego color-replace) żeby nie wyciąć
  białych elementów produku (np. podeszwa białego buta)
