from __future__ import annotations
from typing import Optional, Union
"""
common.py — port z excelex/boty/common.py, Windows-compatible
"""
import datetime
import asyncio
import pathlib
import time
import typing
import re
import json

import aiofiles  # type: ignore

import logger as _logger

PRICE_LIMIT_PER_ORDER_ITEM = 4000
SHOE_LIMIT_PER_SHOE_SIZE = 10


def split_coma_semicolon(s: str) -> list[str]:
    return re.split(r"[;,]", s)


T = typing.TypeVar("T")


def fix_price(price: float) -> float:
    return (price * 0.8) / 1.23


def get_random_filename() -> str:
    storage = pathlib.Path("storage") / "vars"
    storage.mkdir(parents=True, exist_ok=True)
    return str(storage / f"file_{int(time.time()*1000) % 100:02d}")


async def save_str_to_file(content: str) -> str:
    file_path = get_random_filename()
    async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
        await f.write(content)
    return file_path


async def command_start(ctx):
    await ctx.message.add_reaction("⏳")


async def command_ok(ctx):
    await ctx.message.add_reaction("✅")
    await ctx.message.clear_reaction("⏳")


async def command_fail(ctx):
    await ctx.message.add_reaction("❌")
    await ctx.message.clear_reaction("⏳")


def sorted_sizes(sizes: typing.Iterable[str]) -> list[str]:
    def size_key(size: str) -> float:
        if size == "XXS":
            return 100
        if size == "XS":
            return 101
        if size == "S":
            return 102
        if size == "M":
            return 103
        if size == "L":
            return 104
        if size == "XL":
            return 105
        if size == "XXL":
            return 106
        # Range sizes like "128-132", "132-147", "147-163" — sort by first number
        range_match = re.match(r'^(\d+)-(\d+)$', size)
        if range_match:
            return float(range_match.group(1)) + 200  # offset > clothing letters (106), below 9999
        # One Size products
        if re.match(r'^[Oo]ne\s*[Ss]ize$|^[Jj]eden\s+[Rr]ozmiar$', size):
            return 500
        try:
            return float(size.replace(" 1/3", ".3").replace(" 2/3", ".6"))
        except Exception as e:
            _logger.logger.exception(f"Error parsing size '{size}': {e}")
            return 9999

    return sorted(sizes, key=size_key)


class AsyncJsonFileMonitor(typing.Generic[T]):
    def __init__(self, obj_type: typing.Type[T], file_path: str):
        self._lock: Optional[asyncio.Lock] = None  # lazy — tworzone w event loop Discorda
        self.obj_type = obj_type
        self.file_path = pathlib.Path(file_path)

    @property
    def lock(self) -> asyncio.Lock:
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock


    @_logger.async_try_log()
    async def read(self, safe: bool = True) -> T:
        if safe:
            async with self.lock:
                return await self.read(safe=False)
        else:
            try:
                if not self.file_path.exists():
                    return self.obj_type()
                async with aiofiles.open(self.file_path, "rb") as f:
                    raw = await f.read()
                if not raw:
                    return self.obj_type()
                import pickle
                return pickle.loads(raw)
            except Exception as e:
                _logger.logger.exception(f"Error reading pkl file {self.file_path}: {e}")
                return self.obj_type()

    @_logger.async_try_log()
    async def write(self, data: T, safe: bool = True):
        if safe:
            async with self.lock:
                await self.write(data, safe=False)
        else:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = self.file_path.parent / f"temp_{self.file_path.name}"
            import pickle
            async with aiofiles.open(temp_path, "wb") as f:
                await f.write(pickle.dumps(data))
            temp_path.replace(self.file_path)

    @_logger.async_try_log()
    async def update(self, update_fn: typing.Callable[[T], T], safe: bool = True):
        if safe:
            async with self.lock:
                await self.update(update_fn, safe=False)
        else:
            data = await self.read(safe=False)
            data = update_fn(data)
            await self.write(data, safe=False)

    @_logger.async_try_log()
    async def clear(self, safe: bool = True):
        if safe:
            async with self.lock:
                await self.clear(safe=False)
        else:
            if self.file_path.exists():
                self.file_path.unlink()

    @_logger.async_try_log()
    async def snapshot(self):
        async with self.lock:
            now = datetime.datetime.now()
            snapshot_path = (
                self.file_path.parent
                / "snapshots"
                / f"{self.file_path.stem}_{now.strftime('%Y-%m-%d_%H-%M-%S')}{self.file_path.suffix}"
            )
            snapshot_path.parent.mkdir(parents=True, exist_ok=True)
            if self.file_path.exists():
                import shutil
                shutil.copy2(self.file_path, snapshot_path)


# Helpy do komend
HELP_BIORE_TICKET = "!biore_ticket - przypisuje ticket do siebie"
HELP_SUKCES = "!sukces - przenosi kanał ticketu do Archiwum Sukcesu"
HELP_PORAZKA = "!porazka - przenosi kanał ticketu do Archiwum Porażki"
HELP_STATUS = "!status - pokazuje status ticketu"
HELP_HISTORIA = "!historia <nazwa_pozycji_ticketu> - pokazuje historię zmian danej pozycji ticketu"
HELP_INFO = (
    "!info <coś> - wysyła na kanał ticketu informacje o danej pozycji ticketu\n"
    "\tbot znajduje pozycję ticketu na podstawie <coś>\n"
    "\t<coś> może być: nazwa pozycji ticketu, tracking, mail, kod, numer zamówienia"
)
HELP_COFNIJ = (
    "!cofnij <nazwa_pozycji_ticketu> - cofa stan danej pozycji ticketu\n"
    "!cofnij <nazwa_pozycji_ticketu> <krok> - cofa stan danej pozycji ticketu do podanego kroku"
)
HELP_ANULUJ = (
    "!anuluj <nazwa_ticketu> - anuluje cały ticket\n"
    "!anuluj <nazwa_pozycji_ticketu> - anuluje daną pozycję ticketu"
)
HELP_BANK = '!bank - pokazuje liczbę niewykorzystanych maili oraz przesyła plik "mails.csv"'
HELP_BANK_WYCZYSC = "!bank_wyczysc - czyści bank maili"
HELP_PODMIEN_MAIL = "!podmien_mail <nazwa_pozycji_ticketu> - podmienia maila na niewykorzystany z banku maili"
HELP_ZREALIZUJ = "!zrealizuj <tracking1> <tracking2> ... - oznacza pozycje ticketów z podanymi trackingami jako zrealizowane"
HELP_TICKET = '!ticket <nazwa_ticketu> - tworzy nowy ticket o podanej nazwie oraz przesyła plik "<nazwa_ticketu>.csv"'
HELP_TICKET_CSV = 'Aby dodać buty do ticketu - prześlij plik "<nazwa_ticketu>.csv" na kanał ticketu'
HELP_TRACKING_CSV = 'Aby dodać trackingi do pozycji ticketów - prześlij plik "trackings.csv"'
HELP_MAILS_CSV = 'Aby dodać maile - prześlij plik "mails.csv"'
