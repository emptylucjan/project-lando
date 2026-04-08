"""
Skrypt jednorazowy: EnsureProducts + CreatePZ dla s3micha01-01 i s3micha01-02.
Te zamowienia mają status POTWIERDZONE ale PZ nie zostało stworzone (błąd logowania).

Uruchom z katalogu projektu: python run_pz_s3micha01.py
"""
import sys, os, pathlib, asyncio, pickle, json, subprocess, tempfile

MROWKA_DIR = pathlib.Path(__file__).parent / "mrowka"
os.chdir(MROWKA_DIR)
sys.path.insert(0, str(MROWKA_DIR))

# Import po chdir
import ean_db

ORDERS_TO_PROCESS = ["s3micha01-01", "s3micha01-02"]
SFERA_EXE = str(pathlib.Path("..") / "ReflectSfera" / "bin" / "Release" / "net8.0-windows" / "ReflectSfera.exe")
SFERA_DB_NAME = "Nexo_sport trade sp.z o.o."
SFERA_DB_SERVER = r"192.168.7.6,1433"
SFERA_PASSWORD = "S2q0L2s024!"


def call_sfera(action: str, data: dict, timeout: int = 180) -> dict:
    """Wywołuje ReflectSfera.exe synchronicznie."""
    req = {
        "Action": action,
        "DbName": SFERA_DB_NAME,
        "DbServer": SFERA_DB_SERVER,
        "SferaPassword": SFERA_PASSWORD,
        **data
    }
    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", encoding="utf-8",
                                     delete=False, dir=".") as f:
        json.dump(req, f, ensure_ascii=False)
        tmp_path = f.name
    try:
        result = subprocess.run(
            [SFERA_EXE, tmp_path],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=timeout
        )
        # Szukaj JSON-a w stdout (może być poprzedzone logami)
        for line in reversed(result.stdout.splitlines()):
            line = line.strip()
            if line.startswith("{") and "Success" in line:
                try:
                    return json.loads(line)
                except Exception:
                    pass
        # Też loguj stderr
        if result.stderr:
            for line in result.stderr.splitlines():
                if line.strip():
                    print(f"  [stderr] {line}")
        print(f"  [WARN] Brak JSON w stdout. Stdout: {result.stdout[:300]}")
        return {"Success": False, "Message": f"Brak odpowiedzi CLI. stdout={result.stdout[:200]}"}
    except subprocess.TimeoutExpired:
        return {"Success": False, "Message": f"Timeout {timeout}s"}
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


async def main():
    # Wczytaj orders.pkl
    orders_pkl = pathlib.Path("storage") / "orders.pkl"
    with open(orders_pkl, "rb") as f:
        data = pickle.load(f)

    ticket = data.tickets.get("s3micha01")
    if not ticket:
        print("BLAD: nie znaleziono ticketu s3micha01")
        return

    for order_name in ORDERS_TO_PROCESS:
        order_item = ticket.divided_orders.get(order_name)
        if not order_item:
            print(f"[SKIP] {order_name} — nie istnieje w tickecie")
            continue

        print(f"\n{'='*60}")
        print(f"Przetwarzam: {order_name}")

        # Pobierz EANy z ean_db
        links = [shoe.link for shoe in order_item.shoes]
        ean_data = await ean_db.get_eans_for_links(links)

        # Zbuduj pz_items (tylko pozycje z EAN)
        pz_items = []
        sfera_entries = []
        for shoe_info in order_item.shoes:
            for size, qty in shoe_info.size_to_quantity.items():
                if qty <= 0:
                    continue
                entries = ean_data.get(shoe_info.link, [])
                entry = next((e for e in entries if e.size == size), None)
                ean = entry.ean if entry else None
                if not ean:
                    print(f"  [WARN] Brak EAN dla {shoe_info.link[:60]} r.{size} — pomijam")
                    continue
                sku = entry.sku if entry else None
                brand = entry.brand if entry else None
                model_name = f"{brand} {sku} \u00b7 {size}" if (brand and sku) else (entry.name if entry else f"\u00b7 {size}")
                pz_items.append({
                    "ean": ean,
                    "symbol": sku,
                    "quantity": qty,
                    "cenaZakupu": round(shoe_info.og_price * 0.8, 2),
                })
                sfera_entries.append({
                    "EAN": ean,
                    "SKU": sku,
                    "Brand": brand,
                    "ModelName": model_name,
                    "Size": size,
                })

        if not pz_items:
            print(f"  [SKIP] Brak pozycji z EAN — nie można stworzyć PZ")
            continue

        print(f"  Pozycje EnsureProducts: {len(sfera_entries)}")
        print(f"  Pozycje PZ: {len(pz_items)}")

        # === ENSURE PRODUCTS ===
        print(f"\n  [1/2] EnsureProducts...")
        ensure_res = call_sfera("EnsureProducts", {"EnsureProducts": sfera_entries}, timeout=180)
        if ensure_res.get("Success"):
            print(f"  [OK] EnsureProducts sukces: {ensure_res.get('EnsureResults', {})}")
        else:
            print(f"  [BLAD] EnsureProducts: {ensure_res.get('Message', '?')[:200]}")
            print(f"  Kontynuuję mimo błędu EnsureProducts (produkty mogą już istnieć)...")

        # === CREATE PZ ===
        mail_email = order_item.mail.mail if order_item.mail else None
        zalando_pass = order_item.mail.zalando_pass if order_item.mail else None
        uwagi = (
            f"Zamówienie: {order_name} | "
            f"Konto: {mail_email or 'nieprzypisane'} | "
            f"Hasło Zalando: {zalando_pass or '—'}"
        )
        payload = {
            "dostawcaEmail": None,
            "dostawcaNip": None,
            "dataOperacji": None,
            "uwagi": uwagi,
            "items": pz_items,
        }

        print(f"\n  [2/2] CreatePZ...")
        pz_res = call_sfera("CreatePZ", {"PzData": payload}, timeout=120)
        if pz_res.get("Success") and pz_res.get("DocumentNumber"):
            doc_num = pz_res["DocumentNumber"]
            print(f"  [OK] PZ utworzone: {doc_num}")
            # Zaktualizuj pz_sygnatura w danych
            order_item.pz_sygnatura = doc_num
        else:
            print(f"  [BLAD] CreatePZ: {pz_res.get('Message', '?')[:300]}")

    # Zapisz zaktualizowane dane (z pz_sygnatura)
    import shutil, datetime
    snapshot_dir = pathlib.Path("storage") / "snapshots"
    snapshot_dir.mkdir(exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    shutil.copy2(orders_pkl, snapshot_dir / f"orders_{ts}_po_pz_s3micha01.pkl")
    with open(orders_pkl, "wb") as f:
        pickle.dump(data, f)
    print(f"\n[OK] Zapisano orders.pkl z zaktualizowanymi pz_sygnatura")
    print("Zrestartuj bota zeby odswiezyl wiadomosci Discord.")

asyncio.run(main())
