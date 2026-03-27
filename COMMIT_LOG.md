# COMMIT LOG — projekt zalando

Dokument śledzi wszystkie commity do repozytorium.
**Zasada: commit na GitHub tylko po potwierdzeniu przez właściciela projektu.**

---

## Legenda
- ✅ **Zatwierdzone** — właściciel potwierdził działanie
- ⚠️ **Niesprawdzone** — commit poszedł bez testu (błąd)
- 🧪 **Przetestowane lokalnie** — działa lokalnie, czeka na potwierdzenie

---

## Historia commitów

| Hash | Czas | Opis | Status |
|------|------|------|--------|
| `3a41ad4` | 2026-03-27 02:13 | `init: Vero Sport Zalando integration — scraper, Discord bot (Mrowka), ReflectSfera C# bridge` | ✅ Zatwierdzone (ok. 09:00) |
| `1119791` | 2026-03-27 09:09 | `feat: discord_bot.py + .gitignore + README (token z bot_config.json)` | ✅ Zatwierdzone (ok. 09:00) |
| `06a4cae` | 2026-03-27 09:50 | `fix: UpdateInvoice - data przez SQL (DataWydaniaWystawienia) zamiast SDK` | ✅ Zatwierdzone — właściciel potwierdził działanie ("działa, zajebiscie") |
| `60e0c83` | 2026-03-27 10:02 | `fix: CreateFZ - daty po Przelicz(), status PZ+FZ=Odlozone po zapisie` | ⚠️ Niesprawdzone — commit poszedł bez testu właściciela |

| `d13bb75` | 2026-03-27 18:xx | `fix(FZ): poprawny status 21 dla FZ, reset daty DataWydaniaWystawienia` | ⚠️ Niesprawdzone — commit bez potwierdzenia właściciela |
| `(local)` | 2026-03-27 20:xx | `feat: CreateFZByPz — produkycjna akcja z pz_sygnatura + fallback po Uwagi, podmiana w handle_faktura_pdf` | 🧪 Przetestowane lokalnie — czeka na test DC |

---

## Zasady na przyszłość

1. Implementuję zmiany lokalnie i buduję (`dotnet build`)
2. Informuję właściciela o gotowości do testu
3. **Czekam na potwierdzenie działania**
4. Dopiero wtedy commit + push na GitHub
