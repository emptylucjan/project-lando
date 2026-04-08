"""
Skrypt jednorazowy: usuwa s3micha01-05 z ticketu s3micha01
i zwraca jego konto do banku maili.

Uruchom z katalogu projektu:  python fix_s3micha01.py
"""
import sys, os, pickle, shutil, datetime, pathlib

# Uruchom logike z katalogu mrowka/ zeby pickle znalazl mrowka_data i inne klasy
MROWKA_DIR = pathlib.Path(__file__).parent / "mrowka"
os.chdir(MROWKA_DIR)
sys.path.insert(0, str(MROWKA_DIR))

# Uruchom z katalogu projektu lub mrowka/
storage = pathlib.Path("mrowka/storage")
if not storage.exists():
    storage = pathlib.Path("storage")
if not storage.exists():
    print("BLAD: nie znaleziono katalogu storage/ ani mrowka/storage/")
    sys.exit(1)

orders_pkl  = storage / "orders.pkl"
mails_json  = storage / "mails.json"
snapshot_dir = storage / "snapshots"
snapshot_dir.mkdir(exist_ok=True)

# === 1. Backup ===
ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
backup_path = snapshot_dir / f"orders_{ts}_przed_fix_s3micha01.pkl"
shutil.copy2(orders_pkl, backup_path)
print(f"[OK] Backup zapisany: {backup_path}")

# === 2. Wczytaj dane ===
with open(orders_pkl, "rb") as f:
    data = pickle.load(f)

# === 3. Znajdz ticket s3micha01 ===
TICKET_NAME = "s3micha01"
ORDER_TO_REMOVE = "s3micha01-05"

if not hasattr(data, "tickets") or TICKET_NAME not in data.tickets:
    print(f"BLAD: nie znaleziono ticketu '{TICKET_NAME}'")
    print("Dostepne tickety:", list(getattr(data, "tickets", {}).keys()))
    sys.exit(1)

ticket = data.tickets[TICKET_NAME]
print(f"\n[INFO] Znaleziono ticket: {TICKET_NAME}")
print(f"[INFO] Podzielone zamowienia: {list(ticket.divided_orders.keys())}")

# === 4. Sprawdz czy s3micha01-05 istnieje ===
if ORDER_TO_REMOVE not in ticket.divided_orders:
    print(f"[WARN] Zamowienie '{ORDER_TO_REMOVE}' nie istnieje w tickecie. Koniec.")
    sys.exit(0)

order_05 = ticket.divided_orders[ORDER_TO_REMOVE]
print(f"\n[INFO] Zamowienie do usuniecia: {ORDER_TO_REMOVE}")

# Wyswietl info o mailu
mail_obj = getattr(order_05, "mail", None)
mail_addr = None
if mail_obj:
    mail_addr = getattr(mail_obj, "mail", None) or getattr(mail_obj, "email", None) or str(mail_obj)
    print(f"[INFO] Mail przypisany: {mail_addr}")
else:
    print("[INFO] Brak przypisanego maila")

# === 5. Usun zamowienie ===
del ticket.divided_orders[ORDER_TO_REMOVE]
print(f"[OK] Usunieto '{ORDER_TO_REMOVE}' z ticket.divided_orders")

# === 6. Zwroc mail do banku ===
if mail_addr:
    import json
    with open(mails_json, "r", encoding="utf-8") as f:
        mails_root = json.load(f)

    mails_list = mails_root["mails"]  # lista slownikow

    print(f"\n[INFO] Stan banku przed:")
    used   = [m for m in mails_list if m.get("used")]
    unused = [m for m in mails_list if not m.get("used")]
    print(f"  uzyte: {len(used)}, wolne: {len(unused)}")

    # Znajdz mail w banku i oznacz jako wolny
    found = False
    for m in mails_list:
        m_addr = m.get("mail") or m.get("email") or ""
        if m_addr.strip().lower() == mail_addr.strip().lower():
            m["used"] = False
            found = True
            print(f"[OK] Mail '{mail_addr}' oznaczony jako wolny w banku")
            break

    if not found:
        print(f"[WARN] Mail '{mail_addr}' nie znaleziony w mails.json — moze juz jest wolny lub nie byl w banku")

    with open(mails_json, "w", encoding="utf-8") as f:
        json.dump(mails_root, f, ensure_ascii=False, indent=4)

    used2   = [m for m in mails_list if m.get("used")]
    unused2 = [m for m in mails_list if not m.get("used")]
    print(f"\n[INFO] Stan banku po:")
    print(f"  uzyte: {len(used2)}, wolne: {len(unused2)}")

# === 7. Zapisz zmodyfikowane dane ===
with open(orders_pkl, "wb") as f:
    pickle.dump(data, f)
print(f"\n[OK] Zapisano orders.pkl")
print(f"[OK] Pozostale zamowienia w {TICKET_NAME}: {list(ticket.divided_orders.keys())}")
print("\nGotowe! Zrestartuj bota zeby zaladowal nowe dane.")
