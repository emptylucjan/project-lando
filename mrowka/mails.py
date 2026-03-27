from __future__ import annotations
"""
mails.py — bank kont Zalando (Gmail)
Format CSV:  mail;zalando_pass;code
"""
import asyncio
import dataclasses
import pathlib
import pprint
import re
import json
from typing import Optional, Union

import aiofiles  # type: ignore
import logger as _logger


MAILS_CSV_PATH = pathlib.Path("storage") / "mails.csv"
MAILS_JSON_PATH = pathlib.Path("storage") / "mails.json"

_lock = asyncio.Lock()


@dataclasses.dataclass
class MailData:
    mail: str
    zalando_pass: str
    code: str
    used: bool = False

    def to_discord(self) -> str:
        return f"```{self.mail}``````{self.zalando_pass}``````{self.code}```"

    def __str__(self) -> str:
        return pprint.pformat(dataclasses.asdict(self), indent=4)

    def __repr__(self) -> str:
        return self.__str__()


@dataclasses.dataclass
class MailDataCollection:
    mails: list[MailData] = dataclasses.field(default_factory=list)

    def to_dict(self) -> dict:
        return {"mails": [dataclasses.asdict(m) for m in self.mails]}

    @classmethod
    def from_dict(cls, d: dict) -> "MailDataCollection":
        col = cls()
        for m in d.get("mails", []):
            col.mails.append(MailData(**m))
        return col


# ── Persistence ──────────────────────────────────────

async def _read() -> MailDataCollection:
    MAILS_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not MAILS_JSON_PATH.exists():
        return MailDataCollection()
    try:
        async with aiofiles.open(MAILS_JSON_PATH, "r", encoding="utf-8") as f:
            raw = await f.read()
        return MailDataCollection.from_dict(json.loads(raw))
    except Exception as e:
        _logger.logger.exception(f"mails._read: {e}")
        return MailDataCollection()


async def _write(col: MailDataCollection):
    MAILS_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp = MAILS_JSON_PATH.parent / f"temp_{MAILS_JSON_PATH.name}"
    async with aiofiles.open(temp, "w", encoding="utf-8") as f:
        await f.write(json.dumps(col.to_dict(), ensure_ascii=False, indent=4))
    temp.replace(MAILS_JSON_PATH)


# ── Public API ────────────────────────────────────────

@_logger.async_try_log(None)
async def get_unused_mail() -> Optional[MailData]:
    async with _lock:
        col = await _read()
        for mail in col.mails:
            if not mail.used:
                mail.used = True
                await _write(col)
                return mail
    return None


@_logger.async_try_log()
async def add_new_mails(new_mails: list[MailData]):
    async with _lock:
        col = await _read()
        existing = {m.mail for m in col.mails}
        for mail in new_mails:
            if mail.mail not in existing:
                col.mails.append(mail)
                existing.add(mail.mail)
        await _write(col)


@_logger.async_try_log(0)
async def get_number_of_unused_mails() -> int:
    col = await _read()
    return sum(1 for m in col.mails if not m.used)


@_logger.async_try_log()
async def clear_mail_bank():
    async with _lock:
        col = await _read()
        for m in col.mails:
            m.used = True
        await _write(col)


async def mails_csv_to_mails(file_path: str) -> list[MailData]:
    # utf-8-sig obsługuje BOM (np. pliki z Excela)
    async with aiofiles.open(file_path, "r", encoding="utf-8-sig") as f:
        lines = await f.readlines()

    result: list[MailData] = []
    for line in lines[1:]:  # pomijamy nagłówek
        parts = re.split(r"[;,]", line.strip())
        if len(parts) < 3:
            continue
        mail = parts[0].strip()
        zalando_pass = parts[1].strip()
        code = parts[2].strip()
        # 4. kolumna (interia_haslo) — ignorujemy, ale akceptujemy taki format
        if mail:
            result.append(MailData(mail=mail, zalando_pass=zalando_pass, code=code))
    return result


def generate_mails_csv_template() -> str:
    """Generuje przykładowy plik CSV z bankiem maili."""
    return (
        "mail;zalando_pass;code\n"
        "eleatowskiedomeny+fiz7@gmail.com;Luki6720;1234\n"
        "eleatowskiedomeny+fiz10@gmail.com;Luki6720;5678\n"
    )
