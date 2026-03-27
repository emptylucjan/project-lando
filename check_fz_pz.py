"""
Pokazuje wszystkie FZ powiązane z PZ w bazie Subiekt.
Uruchom: python check_fz_pz.py
"""
import pymssql

conn = pymssql.connect(
    server="SZEFAKOMP\\INSERTNEXO",
    database="Nexo_eleat teesty kurwa",
    user="sa",
    password="",
)
cursor = conn.cursor()

print("=" * 70)
print("FZ ↔ PZ — powiązania (tabela Powiazania)")
print("=" * 70)

cursor.execute("""
    SELECT
        d1.NumerWewnetrzny_PelnaSygnatura  AS PZ,
        d1.NumerZewnetrzny                 AS PZ_NrZew,
        d2.NumerWewnetrzny_PelnaSygnatura  AS FZ,
        d2.NumerZewnetrzny                 AS FZ_NrZew,
        d1.Uwagi                           AS PZ_Uwagi
    FROM ModelDanychContainer.Powiazania p
    JOIN ModelDanychContainer.Dokumenty d1 ON d1.Id = p.Id1
    JOIN ModelDanychContainer.Dokumenty d2 ON d2.Id = p.Id2
    WHERE p.Zbior1 = 'Dokumenty' AND p.Zbior2 = 'Dokumenty'
    ORDER BY p.Id1 DESC
""")
rows = cursor.fetchall()
if not rows:
    print("Brak powiązań FZ↔PZ w tabeli Powiazania.")
    print()
    # Pokaż co jest w Powiazania
    cursor.execute("SELECT TOP 10 Id1, Zbior1, Id2, Zbior2, Typ1, Typ2 FROM ModelDanychContainer.Powiazania")
    sample = cursor.fetchall()
    if sample:
        print("Przykładowe wiersze w Powiazania:")
        for r in sample:
            print(f"  Id1={r[0]} Zbior1={r[1]} Id2={r[2]} Zbior2={r[3]} Typ1={r[4]} Typ2={r[5]}")
else:
    for r in rows:
        pz = r[0] or "?"
        pz_nr = r[1] or "—"
        fz = r[2] or "?"
        fz_nr = r[3] or "—"
        print(f"  PZ: {pz:20} (NrZew: {pz_nr:20}) → FZ: {fz} (NrZew: {fz_nr})")
        if r[4]:
            print(f"      Uwagi PZ: {str(r[4])[:80]}")
        print()

print()
print("=" * 70)
print("Wszystkie FZ w bazie (ostatnie 20):")
print("=" * 70)
cursor.execute("""
    SELECT TOP 20
        NumerWewnetrzny_PelnaSygnatura,
        NumerZewnetrzny,
        NumerWewnetrzny_SygnaturaPrzedNr
    FROM ModelDanychContainer.Dokumenty
    WHERE NumerWewnetrzny_PelnaSygnatura LIKE '%FZ%'
       OR NumerWewnetrzny_SygnaturaPrzedNr LIKE '%FZ%'
    ORDER BY Id DESC
""")
rows = cursor.fetchall()
if not rows:
    print("Brak FZ w bazie.")
else:
    for r in rows:
        print(f"  {str(r[0]):25}  NrZew: {str(r[1] or '—'):20}  Prefix: {r[2]}")

conn.close()
