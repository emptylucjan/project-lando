"""
ean_db.py — Lokalna baza danych EAN/SKU per link Zalando.
Używa SQLite przez aiosqlite. Unika podwójnego skanowania tych samych URLi.
"""
from __future__ import annotations
import os
import asyncio
import logging
import datetime
from dataclasses import dataclass
from typing import Optional, Union

import aiosqlite

log = logging.getLogger("mrowka.ean_db")

# Ścieżka do pliku bazy danych
_DB_PATH = os.path.join(os.path.dirname(__file__), "storage", "ean_db.sqlite")


@dataclass
class EanEntry:
    link: str
    ean: Optional[str]
    size: str
    sku: Optional[str]
    name: Optional[str]
    brand: Optional[str]
    price: Optional[float]
    scanned_at: str = ""


async def init_db() -> None:
    """Tworzy tabele jeśli nie istnieją."""
    os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
    async with aiosqlite.connect(_DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS ean_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                link TEXT NOT NULL,
                ean TEXT,
                size TEXT NOT NULL,
                sku TEXT,
                name TEXT,
                brand TEXT,
                price REAL,
                scanned_at TEXT NOT NULL,
                UNIQUE(link, size)
            )
        """)
        await db.commit()
    log.info("EAN DB zainicjalizowana: %s", _DB_PATH)


async def save_scan_results(link: str, name: Optional[str], brand: Optional[str],
                             price: Optional[float], size_to_ean: dict[str, Optional[str]],
                             sku: Optional[str] = None) -> None:
    """
    Zapisuje wyniki skanu Selenium dla danego linku.
    Nadpisuje istniejące wpisy (UPSERT per link+size).
    """
    now = datetime.datetime.now().isoformat()
    async with aiosqlite.connect(_DB_PATH) as db:
        for size, ean in size_to_ean.items():
            await db.execute("""
                INSERT INTO ean_entries (link, ean, size, sku, name, brand, price, scanned_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(link, size) DO UPDATE SET
                    ean=excluded.ean,
                    sku=excluded.sku,
                    name=excluded.name,
                    brand=excluded.brand,
                    price=excluded.price,
                    scanned_at=excluded.scanned_at
            """, (link, ean, size, sku, name, brand, price, now))
        await db.commit()
    log.info("Zapisano %d EANów dla: %s", len(size_to_ean), link[:60])


async def get_eans_for_link(link: str) -> list[EanEntry]:
    """Zwraca wszystkie wpisy EAN dla danego linku."""
    async with aiosqlite.connect(_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM ean_entries WHERE link=? ORDER BY size",
            (link,)
        ) as cursor:
            rows = await cursor.fetchall()
    return [EanEntry(
        link=r["link"], ean=r["ean"], size=r["size"], sku=r["sku"],
        name=r["name"], brand=r["brand"], price=r["price"], scanned_at=r["scanned_at"]
    ) for r in rows]


async def get_eans_for_links(links: list[str]) -> dict[str, list[EanEntry]]:
    """Zwraca EANy dla wielu linków naraz. {link: [EanEntry, ...]}"""
    result: dict[str, list[EanEntry]] = {link: [] for link in links}
    if not links:
        return result

    placeholders = ",".join("?" * len(links))
    async with aiosqlite.connect(_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            f"SELECT * FROM ean_entries WHERE link IN ({placeholders}) ORDER BY link, size",
            links
        ) as cursor:
            rows = await cursor.fetchall()

    for r in rows:
        entry = EanEntry(
            link=r["link"], ean=r["ean"], size=r["size"], sku=r["sku"],
            name=r["name"], brand=r["brand"], price=r["price"], scanned_at=r["scanned_at"]
        )
        result[r["link"]].append(entry)
    return result


async def already_scanned(link: str) -> bool:
    """Sprawdza czy link był skanowany i ma co najmniej jeden EAN != NULL."""
    async with aiosqlite.connect(_DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM ean_entries WHERE link=? AND ean IS NOT NULL AND ean != ''", (link,)
        ) as cursor:
            row = await cursor.fetchone()
    return (row[0] if row else 0) > 0
