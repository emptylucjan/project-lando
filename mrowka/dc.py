from __future__ import annotations
from typing import Optional, Union
"""
dc.py — Discord wrappers (port z excelex/boty/dc.py)
Windows-compatible, bez zmian funkcjonalnych.
"""
import asyncio
import dataclasses
import discord
from discord.ext import commands

import logger as _logger

_dc_lock = asyncio.Lock()


@dataclasses.dataclass
class Category:
    id: int
    name: str

    @_logger.async_try_log(None)
    async def get_dc(self, bot: commands.Bot) -> Optional[discord.CategoryChannel]:
        if self.id == -1:
            raise Exception(f'category id is -1 - "{self.name}"')
        async with _dc_lock:
            dc_category = discord.utils.get(bot.guilds[0].categories, id=self.id)
        if dc_category is None:
            raise Exception(f'category "{self.name}" not found')
        return dc_category

    def __str__(self) -> str:
        return f"CategoryChannel(name={self.name}, id={self.id})"
    def __repr__(self) -> str:
        return self.__str__()


@dataclasses.dataclass
class User:
    id: int
    name: str

    @_logger.async_try_log()
    async def send(self, bot: commands.Bot, content: Optional[str] = None, file: Optional[discord.File] = None) -> Optional["Message"]:
        if self.id == -1:
            raise Exception(f"user id is -1 - {self}")
        async with _dc_lock:
            dc_user = bot.get_user(self.id)
        if dc_user is None:
            raise Exception(f"user is None - {self}")
        async with _dc_lock:
            if file is None:
                dc_message = await dc_user.send(content=content)
            else:
                dc_message = await dc_user.send(content=content, file=file)
        return message_from_dc_message(dc_message)

    def mention(self) -> str:
        return f"<@{self.id}>"

    def __str__(self) -> str:
        return f"User(name={self.name}, id={self.id})"
    def __repr__(self) -> str:
        return self.__str__()


@dataclasses.dataclass
class Channel:
    id: int
    name: str

    @_logger.async_try_log()
    async def send(self, bot: commands.Bot, content: Optional[str] = None, file: Optional[discord.File] = None) -> Optional["Message"]:
        if self.id == -1:
            raise Exception(f"channel id is -1 - {self}")
        async with _dc_lock:
            dc_channel = bot.get_channel(self.id)
        if dc_channel is None:
            raise Exception(f"channel is None - {self}")
        if isinstance(dc_channel, (discord.ForumChannel, discord.CategoryChannel, discord.abc.PrivateChannel)):
            raise Exception(f"channel wrong type - {self}")
        async with _dc_lock:
            if file is None:
                dc_message = await dc_channel.send(content=content)
            else:
                dc_message = await dc_channel.send(content=content, file=file)
        return message_from_dc_message(dc_message)

    @_logger.async_try_log()
    async def edit(self, bot: commands.Bot, category: Category):
        if self.id == -1:
            raise Exception(f"channel id is -1 - {self}")
        async with _dc_lock:
            dc_channel = bot.get_channel(self.id)
        if dc_channel is None:
            raise Exception(f"channel is None - {self}")
        dc_category = await category.get_dc(bot)
        async with _dc_lock:
            await dc_channel.edit(category=dc_category)

    @_logger.async_try_log()
    async def fetch_message(self, bot: commands.Bot, message_id: int) -> Optional["Message"]:
        async with _dc_lock:
            dc_channel = bot.get_channel(self.id)
        if dc_channel is None:
            raise Exception(f"channel is None - {self}")
        async with _dc_lock:
            dc_message = await dc_channel.fetch_message(message_id)
        return message_from_dc_message(dc_message)

    def mention(self) -> str:
        return f"<#{self.id}>"

    def __str__(self) -> str:
        return f"Channel(name={self.name}, id={self.id})"
    def __repr__(self) -> str:
        return self.__str__()


@dataclasses.dataclass
class Message:
    id: int
    content: Optional[str]
    author: User
    channel: Optional[Channel]

    @_logger.async_try_log()
    async def delete(self, bot: commands.Bot):
        if self.id == -1 or self.channel is None:
            return
        async with _dc_lock:
            dc_channel = bot.get_channel(self.channel.id)
        if dc_channel is None:
            return
        async with _dc_lock:
            message = await dc_channel.fetch_message(self.id)
            await message.delete()

    @_logger.async_try_log()
    async def edit(self, bot: commands.Bot, content: Optional[str] = None, file: Optional[discord.File] = None):
        if self.id == -1 or self.channel is None:
            return
        async with _dc_lock:
            dc_channel = bot.get_channel(self.channel.id)
        if dc_channel is None:
            return
        async with _dc_lock:
            dc_message = await dc_channel.fetch_message(self.id)
            if file is None:
                await dc_message.edit(content=content)
            else:
                await dc_message.edit(content=content, attachments=[file])

    @_logger.async_try_log()
    async def add_reaction(self, bot: commands.Bot, emoji: str):
        if self.id == -1 or self.channel is None:
            return
        async with _dc_lock:
            dc_channel = bot.get_channel(self.channel.id)
        if dc_channel is None:
            return
        async with _dc_lock:
            dc_message = await dc_channel.fetch_message(self.id)
            await dc_message.add_reaction(emoji)

    @_logger.async_try_log()
    async def clear_reactions(self, bot: commands.Bot):
        if self.id == -1 or self.channel is None:
            return
        async with _dc_lock:
            dc_channel = bot.get_channel(self.channel.id)
        if dc_channel is None:
            return
        async with _dc_lock:
            dc_message = await dc_channel.fetch_message(self.id)
            await dc_message.clear_reactions()

    def __str__(self) -> str:
        return f"Message(id={self.id}, author={self.author}, channel={self.channel}, content={self.content})"
    def __repr__(self) -> str:
        return self.__str__()


# ── Factory functions ──────────────────────────────────

@_logger.async_try_log(User(id=-1, name="unknown"))
async def user_from_id(bot: commands.Bot, user_id: int) -> User:
    async with _dc_lock:
        dc_user = discord.utils.get(bot.get_all_members(), id=user_id)
    if dc_user is None:
        raise Exception(f"user with id {user_id} not found")
    return User(id=dc_user.id, name=dc_user.display_name)


@_logger.async_try_log(Channel(id=-1, name="unknown"))
async def channel_from_name(bot: commands.Bot, channel_name: str) -> Channel:
    async with _dc_lock:
        dc_channel = discord.utils.get(bot.get_all_channels(), name=channel_name)
    if dc_channel is None:
        async with _dc_lock:
            dc_channel = await bot.guilds[0].create_text_channel(channel_name)
    return Channel(id=dc_channel.id, name=dc_channel.name)


@_logger.try_log(Channel(id=-1, name="unknown"))
def channel_from_dc_channel(dc_channel: discord.abc.GuildChannel) -> Channel:
    return Channel(id=dc_channel.id, name=dc_channel.name)


@_logger.try_log(Message(id=-1, content=None, author=User(id=-1, name=""), channel=None))
def message_from_dc_message(dc_message: discord.Message) -> Message:
    author = User(id=dc_message.author.id, name=dc_message.author.display_name)
    if isinstance(dc_message.channel, (discord.DMChannel, discord.PartialMessageable)):
        channel = None
    elif not hasattr(dc_message.channel, "name") or dc_message.channel.name is None:
        channel = None
    else:
        channel = Channel(id=dc_message.channel.id, name=dc_message.channel.name)
    return Message(id=dc_message.id, content=dc_message.content, author=author, channel=channel)


@_logger.async_try_log(Category(id=-1, name="unknown"))
async def category_from_name(bot: commands.Bot, category_name: str) -> Category:
    async with _dc_lock:
        dc_category = discord.utils.get(bot.guilds[0].categories, name=category_name)
    if dc_category is None:
        async with _dc_lock:
            dc_category = await bot.guilds[0].create_category(category_name)
    return Category(id=dc_category.id, name=dc_category.name)


# ── Stałe kanałów/kategorii ────────────────────────────

def CHANNEL_MAGAZYNIERZY(bot): return channel_from_name(bot, "magazynierzy")
def CHANNEL_TICKETY(bot): return channel_from_name(bot, "tickety")
def CHANNEL_DOSTAWY(bot): return channel_from_name(bot, "zalando-dostawy")
def CATEGORY_SUKCES(bot): return category_from_name(bot, "Archiwum Sukcesu")
def CATEGORY_PORAZKA(bot): return category_from_name(bot, "Archiwum Porażki")


def get_daily_message_users(bot: commands.Bot) -> list:
    """
    Zwraca listę coroutine user_from_id dla użytkowników skonfigurowanych
    jako odbiorcy dziennych podsumowań zamówień.
    Konfiguracja: config.json -> "daily_message_user_ids": [123456789, ...]
    Jeśli lista pusta — ciche pominięcie, bez błędu.
    """
    import json as _json
    import pathlib as _pathlib
    try:
        config_path = _pathlib.Path(__file__).parent / "config.json"
        config = _json.loads(config_path.read_text(encoding="utf-8"))
        user_ids: list[int] = config.get("daily_message_user_ids", [])
        return [user_from_id(bot, uid) for uid in user_ids]
    except Exception:
        return []

