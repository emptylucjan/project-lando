# README2CONFIG — Konfiguracja projektu na nowej maszynie

Plik dokumentuje wszystko co **nie jest w repo** i wymaga ręcznej konfiguracji
przy pierwszym uruchomieniu projektu na nowej maszynie.

---

## 1. Wymagania systemowe

| Co | Wersja | Uwagi |
|----|--------|-------|
| Windows | 10/11 | Sfera SDK działa tylko na Windows |
| SQL Server | 2019+ | Instancja: `.\INSERTNEXO` |
| Subiekt Nexo | aktualna | Z zainstalowaną Sferą |
| .NET SDK | 8.0+ | Do zbudowania `ReflectSfera` |
| Python | 3.9+ | Bot Discord + scraper |
| Chrome | dowolna | Do scrapera Selenium |

---

## 2. Sfera SDK — DLL-e (KRYTYCZNE)

Pliki DLL InsERT Moria **nie są w repo** (prywatne, za duże).
Muszą być skopiowane z instalacji Subiektu Nexo.

### Gdzie są teraz:
```
C:\Users\lukko\Desktop\MODULKURIERSKI_PRODUKCJA\
```

### Jakie DLL-e są potrzebne:
```
InsERT.Moria.Sfera.dll
InsERT.Moria.ModelDanych.dll
InsERT.Moria.Dokumenty.Logistyka.dll
InsERT.Moria.Asortymenty.dll
InsERT.Moria.Klienci.dll
InsERT.Moria.Waluty.dll
InsERT.Mox.dll
InsERT.SNI.dll          ← WAŻNE: kopia z katalogu Subiektu (fix SNI)
```

Zwykle znajdują się w:
```
C:\Program Files (x86)\InsERT\Subiekt Nexo\
```
lub w katalogu instalacyjnym Sfery Nexo.

### Gdzie zmienić ścieżkę w kodzie:
**Plik:** `ReflectSfera/Program.cs`

```csharp
// Linia ~148 (AssemblyResolve) i linia ~196 (ProcessAction):
var dllDir  = @"C:\Users\lukko\Desktop\MODULKURIERSKI_PRODUKCJA";  // ← zmień to
var dllPath = @"C:\Users\lukko\Desktop\MODULKURIERSKI_PRODUKCJA";  // ← i to
```
**Zmień obie ścieżki** na folder gdzie trzymasz DLL-e na nowej maszynie.

### Operator Subiektu (login):
```csharp
// Linia ~201-202:
if (!sfera.ZalogujOperatora("Aleksander PIsiecki", "robocze"))
```
Zmień `"Aleksander PIsiecki"` i `"robocze"` na nazwę i hasło operatora w Subiekcie.

---

## 3. SQL Server — połączenie

### Nazwa instancji (hardcoded w 2 miejscach):

**`mrowka/mrowka_lib.py` linia 24-25:**
```python
_SFERA_DB_NAME   = "Nexo_eleat teesty kurwa"   # ← nazwa bazy danych
_SFERA_DB_SERVER = r".\INSERTNEXO"             # ← instancja SQL Server
```

**`sfera_api.py` linia 16:**
```python
"DbServer": ".\\INSERTNEXO",   # ← instancja SQL Server
```

> Wartości `DbName` i `DbServer` w wywołaniach bota są przekazywane z `mrowka_lib.py` —
> wystarczy zmienić tylko tam.

---

## 4. Pliki konfiguracyjne (NIE SĄ w repo — gitignored)

### `mrowka/config.json`
```json
{
  "discord_token": "...",
  "gmail_accounts": [
    {
      "email": "konto@gmail.com",
      "app_password": "xxxx xxxx xxxx xxxx"
    }
  ]
}
```

### `bot_config.json` (główny Discord bot)
```json
{
  "token": "...",
  "guild_id": 123456789
}
```

### `mrowka/storage/` (dane bota)
Folder z pickle/json persystencji bota — tworzony automatycznie przy pierwszym uruchomieniu.

---

## 5. Baza SQLite — EAN-y

**Plik:** `mrowka/ean_db.sqlite`

Gitignorowany. Tworzony automatycznie przy pierwszym uruchomieniu bota.
Po przeniesieniu na nową maszynę — skopiuj plik jeśli chcesz zachować historię EAN-ów.

---

## 6. Budowanie ReflectSfera (C#)

Po sklonowaniu repo i skonfigurowaniu ścieżek do DLL:

```powershell
cd ReflectSfera
dotnet build -c Release
```

Wykonywalny plik będzie w:
```
ReflectSfera\bin\Release\net8.0-windows\ReflectSfera.exe
```

---

## 7. Instalacja Python dependencies

```bash
pip install discord.py pdfplumber aiofiles aiohttp selenium webdriver-manager pyodbc
```

---

## 8. Kolejność uruchamiania

1. Upewnij się że SQL Server (`.\INSERTNEXO`) działa
2. Upewnij się że Subiekt Nexo jest zalogowany (lub przynajmniej usługa działa)
3. Zbuduj `ReflectSfera`: `dotnet build -c Release`
4. Uzupełnij `mrowka/config.json` i `bot_config.json`
5. Uruchom bota: `python mrowka/run.py`
