"""Sprawdza kolumny daty w tabelach SQL Subiekt Nexo"""
import json, pyodbc

c = json.load(open('mrowka/config.json'))
conn = pyodbc.connect('DRIVER={SQL Server};SERVER=' + c['db_server'] +
                      ';DATABASE=' + c['db_name'] + ';UID=sa;PWD=' + c['sfera_password'])

print("=== Dokumenty - kolumny z 'data' ===")
rows = conn.execute(
    "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
    "WHERE TABLE_SCHEMA='ModelDanychContainer' AND TABLE_NAME='Dokumenty' "
    "AND LOWER(COLUMN_NAME) LIKE '%data%' ORDER BY COLUMN_NAME"
).fetchall()
for r in rows:
    print(r[0])

print("\n=== DokumentyPZ - kolumny z 'data' ===")
rows = conn.execute(
    "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
    "WHERE TABLE_SCHEMA='ModelDanychContainer' AND TABLE_NAME='DokumentyPZ' "
    "AND LOWER(COLUMN_NAME) LIKE '%data%' ORDER BY COLUMN_NAME"
).fetchall()
for r in rows:
    print(r[0])
