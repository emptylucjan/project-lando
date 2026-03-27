import pyodbc

conn = pyodbc.connect(
    'DRIVER={SQL Server};SERVER=SZEFAKOMP\\INSERTNEXO;DATABASE=Nexo_eleat teesty kurwa;Trusted_Connection=yes'
)
cur = conn.cursor()

# Sprawdź kolumny kluczowych tabel
cur.execute("""
SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA='ModelDanychContainer'
  AND TABLE_NAME IN ('Asortymenty','JednostkiMiarAsortymentow','KodyKreskowe')
ORDER BY TABLE_NAME, ORDINAL_POSITION
""")

print("=== SCHEMAT TABEL ===")
for row in cur.fetchall():
    print(row)

# Sprawdź przykładowy rekord żeby widzieć realne wartości
cur.execute("""
SELECT TOP 1 * FROM ModelDanychContainer.Asortymenty ORDER BY Id DESC
""")
print("\n=== PRZYKŁADOWY ASORTYMENT (kolumny) ===")
cols = [col[0] for col in cur.description]
print(cols)
row = cur.fetchone()
if row:
    for c, v in zip(cols, row):
        print(f"  {c}: {v}")

# Sprawdź JMA dla tego produktu
if row:
    aid = row[0]  # Id
    cur.execute(f"""
    SELECT TOP 1 * FROM ModelDanychContainer.JednostkiMiarAsortymentow WHERE Asortyment_Id = {aid}
    """)
    print("\n=== PRZYKŁADOWY JMA ===")
    cols2 = [col[0] for col in cur.description]
    print(cols2)
    jma = cur.fetchone()
    if jma:
        for c, v in zip(cols2, jma):
            print(f"  {c}: {v}")
    
    # KodyKreskowe
    if jma:
        jma_id = jma[0]
        cur.execute(f"""
        SELECT TOP 1 * FROM ModelDanychContainer.KodyKreskowe WHERE JednostkaMiaryAsortymentu_Id = {jma_id}
        """)
        print("\n=== PRZYKŁADOWY KOD KRESKOWY ===")
        cols3 = [col[0] for col in cur.description]
        print(cols3)
        kk = cur.fetchone()
        if kk:
            for c, v in zip(cols3, kk):
                print(f"  {c}: {v}")

conn.close()
print("\nGotowe!")
