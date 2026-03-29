from __future__ import annotations
from typing import Optional, Union
import datetime
import asyncio
import dataclasses
import re
import discord
from discord.ext import commands
import dc
import common
import mails
import mrowka_data
import mrowka_lib
import logger as logger
import ean_db


@dataclasses.dataclass
class DeliveryResult:
    tracking: str
    sygnatura: Optional[str]   # np. "PV 7/2026" — None gdy nie znaleziono
    order_item_name: Optional[str]
    ticket_name: Optional[str]
    price: float


@dataclasses.dataclass
class DeliverySession:
    user_id: int
    started_at: datetime.datetime
    results: list[DeliveryResult] = dataclasses.field(default_factory=list)

    def accepted(self) -> list[DeliveryResult]:
        return [r for r in self.results if r.sygnatura is not None]

    def failed(self) -> list[DeliveryResult]:
        return [r for r in self.results if r.sygnatura is None]

    def total_price(self) -> float:
        return sum(r.price for r in self.accepted())


# user_id → aktywna sesja dostawy
delivery_sessions: dict[int, DeliverySession] = {}


TICKET_CHANNEL = "tickety"
TICKET_CSV_PATH = "storage/ticket.csv"
MAILS_CSV_PATH = "storage/mails.csv"


intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True
intents.reactions = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.command()
async def biore_ticket(ctx):
    try:
        message = dc.message_from_dc_message(ctx.message)
        await message.delete(bot)
        async with mrowka_data.PisarzMrowka.lock:
            data = await mrowka_data.PisarzMrowka.read(safe=False)
            ticket_name = message.channel.name if message.channel else ""
            if ticket_name not in data.tickets:
                await message.author.send(
                    bot,
                    f"⚠️ Komenda !biore_ticket może być użyta tylko na kanale ticketu ⚠️\n"
                    f"{common.HELP_BIORE_TICKET}",
                )
                return
            ticket = data.tickets[ticket_name]
            ticket.owner = message.author
            ticket.all_potwierdzone_sent = False
            ticket.all_wyslane_sent = False
            ticket.all_zrealizowane_sent = False
            ticket.all_anulowane_sent = False
            await ticket.discord_update(bot)

            await mrowka_data.PisarzMrowka.write(data, safe=False)
    except Exception as e:
        logger.logger.exception(e)


@bot.command()  # type: ignore
async def sukces(ctx):
    try:
        ticket_name = ctx.channel.name
        data = await mrowka_data.PisarzMrowka.read()
        if ticket_name not in data.tickets:
            message = dc.message_from_dc_message(ctx.message)
            await message.delete(bot)
            await message.author.send(
                bot,
                f"⚠️ Komenda !sukces może być użyta tylko na kanale ticketu ⚠️\n"
                f"{common.HELP_SUKCES}",
            )
            return

        ticket = data.tickets[ticket_name]
        await ticket.sukces(bot)
    except Exception as e:
        logger.logger.exception(e)


@bot.command()  # type: ignore
async def porazka(ctx):
    try:
        ticket_name = ctx.channel.name
        data = await mrowka_data.PisarzMrowka.read()
        if ticket_name not in data.tickets:
            message = dc.message_from_dc_message(ctx.message)
            await message.delete(bot)
            await message.author.send(
                bot,
                f"⚠️ Komenda !porazka może być użyta tylko na kanale ticketu ⚠️\n"
                f"{common.HELP_PORAZKA}",
            )
            return

        ticket = data.tickets[ticket_name]
        await ticket.porazka(bot)
    except Exception as e:
        logger.logger.exception(e)


@bot.command()  # type: ignore
async def status(ctx):
    message = dc.message_from_dc_message(ctx.message)
    await message.delete(bot)
    try:
        ticket_name = ctx.channel.name
        data = await mrowka_data.PisarzMrowka.read()

        if ticket_name not in data.tickets:
            await message.author.send(
                bot,
                f"⚠️ Komenda !status może być użyta tylko na kanale ticketu ⚠️\n"
                f"{common.HELP_STATUS}",
            )
            return

        ticket = data.tickets[ticket_name]
        await ticket.send_ticket_csv_status_message(bot)
    except Exception as e:
        logger.logger.exception(e)


@bot.command()  # type: ignore
async def info(ctx, text: str = ""):
    message = dc.message_from_dc_message(ctx.message)
    await message.delete(bot)
    try:
        ticket_name = mrowka_data.order_item_name_to_ticket_name(text)
        data = await mrowka_data.PisarzMrowka.read()

        order_item = None

        if ticket_name in data.tickets:
            ticket = data.tickets[ticket_name]
            if text in ticket.divided_orders:
                order_item = ticket.divided_orders[text]
        else:
            order_item = mrowka_lib.info_find_order_item_from_text(data, text)

        if order_item is None:
            await message.author.send(
                bot,
                f'⚠️ Nie znaleziono pozycji zamówienia z informacją dla "{text}" ⚠️\n'
                f"{common.HELP_INFO}",
            )
            return
        else:
            await order_item.info(bot)
    except Exception as e:
        logger.logger.exception(e)


@bot.command()  # type: ignore
async def historia(ctx, order_item_name: str = ""):
    message = dc.message_from_dc_message(ctx.message)
    await message.delete(bot)
    try:
        ticket_name = mrowka_data.order_item_name_to_ticket_name(order_item_name)
        data = await mrowka_data.PisarzMrowka.read()

        if ticket_name not in data.tickets:
            await message.author.send(
                bot,
                f'⚠️ Ticket o nazwie "{ticket_name}" nie istnieje ⚠️\n'
                f"{common.HELP_HISTORIA}",
            )
            return

        ticket = data.tickets[ticket_name]
        if order_item_name not in ticket.divided_orders:
            await message.author.send(
                bot,
                f'⚠️ Pozycja o nazwie "{order_item_name}" nie istnieje w tickecie "{ticket_name}" ⚠️\n'
                f"{common.HELP_HISTORIA}",
            )
            return

        order_item = ticket.divided_orders[order_item_name]
        content = (
            f'📜 Historia zmian statusów dla pozycji ticketu "{order_item_name}":\n'
            f"{order_item.history.to_discord()}"
        )
        await message.author.send(bot, content)
    except Exception as e:
        logger.logger.exception(e)


@bot.command()  # type: ignore
async def cofnij(ctx, order_item_name: str = "", step: Optional[int] = None):
    message = dc.message_from_dc_message(ctx.message)
    try:
        ticket_name = mrowka_data.order_item_name_to_ticket_name(order_item_name)

        async with mrowka_data.PisarzMrowka.lock:
            data = await mrowka_data.PisarzMrowka.read(safe=False)

            if ticket_name not in data.tickets:
                await message.delete(bot)
                await message.author.send(
                    bot,
                    f'⚠️ Ticket o nazwie "{ticket_name}" nie istnieje ⚠️\n'
                    f"{common.HELP_COFNIJ}",
                )
                return

            ticket = data.tickets[ticket_name]
            if order_item_name not in ticket.divided_orders:
                await message.delete(bot)
                await message.author.send(
                    bot,
                    f'⚠️ Pozycja zamówienia o nazwie "{order_item_name}" nie istnieje w tickecie "{ticket_name}" ⚠️\n'
                    f"{common.HELP_COFNIJ}",
                )
                return

            order_item = ticket.divided_orders[order_item_name]
            user = dc.User(
                id=ctx.author.id,
                name=ctx.author.display_name,
            )
            await order_item.cofnij(bot, user, step, data)

            await mrowka_data.PisarzMrowka.write(data, safe=False)
    except Exception as e:
        logger.logger.exception(e)


@bot.command()  # type: ignore
async def anuluj(ctx, name: str = ""):
    message = dc.message_from_dc_message(ctx.message)
    try:
        user = dc.User(
            id=ctx.author.id,
            name=ctx.author.display_name,
        )
        ticket_name = mrowka_data.order_item_name_to_ticket_name(name)

        if not hasattr(ctx.channel, "name") or ctx.channel.name != ticket_name:
            await message.delete(bot)
            await message.author.send(
                bot,
                f"⚠️ Komenda !anuluj <nazwa> może być użyta tylko na kanale ticketu ⚠️\n"
                f"{common.HELP_ANULUJ}",
            )
            return

        async with mrowka_data.PisarzMrowka.lock:
            data = await mrowka_data.PisarzMrowka.read(safe=False)

            if ticket_name not in data.tickets:
                await message.delete(bot)
                await message.author.send(
                    bot,
                    f'⚠️ Ticket o nazwie "{ticket_name}" nie istnieje ⚠️\n'
                    f"{common.HELP_ANULUJ}",
                )
                return

            ticket = data.tickets[ticket_name]
            if name in ticket.divided_orders:
                order_item = ticket.divided_orders[name]
                await order_item.anuluj(bot, user, data)
            elif name == ticket_name:
                for order_item in ticket.divided_orders.values():
                    await order_item.anuluj(bot, user, data)
            else:
                await message.delete(bot)
                await message.author.send(
                    bot,
                    f'⚠️ Pozycja zamówienia o nazwie "{name}" nie istnieje w tickecie "{ticket_name}" ⚠️\n'
                    f"{common.HELP_ANULUJ}",
                )
                return

            await mrowka_data.PisarzMrowka.write(data, safe=False)
    except Exception as e:
        logger.logger.exception(e)


@bot.command()
async def bank(ctx):
    message = dc.message_from_dc_message(ctx.message)
    await message.delete(bot)

    maile = await mails.get_number_of_unused_mails()
    content = (
        f"📧 Liczba niewykorzystanych kont: {maile} 📧\n"
        f"Aby dodać nowe konta wyślij plik `mails.csv` z kontami zgodny z formatem:"
    )
    await message.author.send(
        bot,
        content=content,
        file=discord.File(MAILS_CSV_PATH),
    )


@bot.command()
async def bank_wyczysc(ctx):
    message = dc.message_from_dc_message(ctx.message)
    await message.delete(bot)

    await mails.clear_mail_bank()
    maile = await mails.get_number_of_unused_mails()
    content = (
        "✅ Bank maili został wyczyszczony ✅\n"
        f"📧 Liczba niewykorzystanych kont: {maile} 📧\n"
        f"Aby dodać nowe konta wyślij plik `mails.csv` z kontami zgodny z formatem:"
    )
    await message.author.send(
        bot,
        content=content,
        file=discord.File(MAILS_CSV_PATH),
    )


@bot.command()  # type: ignore
async def podmien_mail(ctx, order_item_name: str = ""):
    message = dc.message_from_dc_message(ctx.message)
    await message.delete(bot)

    try:
        ticket_name = mrowka_data.order_item_name_to_ticket_name(order_item_name)

        async with mrowka_data.PisarzMrowka.lock:
            data = await mrowka_data.PisarzMrowka.read(safe=False)

            if ticket_name not in data.tickets:
                await message.delete(bot)
                await message.author.send(
                    bot,
                    f'⚠️ Ticket o nazwie "{ticket_name}" nie istnieje ⚠️\n'
                    f"{common.HELP_PODMIEN_MAIL}",
                )
                return

            ticket = data.tickets[ticket_name]
            if order_item_name not in ticket.divided_orders:
                await message.delete(bot)
                await message.author.send(
                    bot,
                    f'⚠️ Pozycja zamówienia o nazwie "{order_item_name}" nie istnieje w tickecie "{ticket_name}" ⚠️\n'
                    f"{common.HELP_PODMIEN_MAIL}",
                )
                return

            order_item = ticket.divided_orders[order_item_name]
            await order_item.podmien_mail(bot, data)
            await mrowka_data.PisarzMrowka.write(data, safe=False)

        await message.author.send(
            bot,
            f"✅ Pomyślnie podmieniono mail dla pozycji zamówienia '{order_item_name}' ✅",
        )
    except Exception as e:
        logger.logger.exception(e)


@bot.command()  # type: ignore
async def zrealizuj(ctx, *args):
    message = dc.message_from_dc_message(ctx.message)
    if len(args) == 0:
        await message.delete(bot)
        await message.author.send(
            bot,
            f"⚠️ Podaj przynajmniej jeden tracking ⚠️\n{common.HELP_ZREALIZUJ}",
        )
        return

    fails = []
    async with mrowka_data.PisarzMrowka.lock:
        data = await mrowka_data.PisarzMrowka.read(safe=False)

        for tracking in args:
            if tracking not in data.tracking_to_order_item_name:
                fails.append(tracking)
                continue

            order_item_name = data.tracking_to_order_item_name[tracking]
            order_item = data.get_order_item(order_item_name)
            if order_item is None:
                fails.append(tracking)
                continue

            await order_item.zrealizuj(bot, message.author, data)

        await mrowka_data.PisarzMrowka.write(data, safe=False)

    content = f"✅ Zrealizowano {len(args) - len(fails)} przesyłek ✅"
    if len(fails) > 0:
        content += "\n❗ Nie udało się zrealizować przesyłek dla następujących trackingów: ❗\n"
        for fail in fails:
            content += f"{fail}\n"
    await message.author.send(bot, content=content)


@bot.command()  # type: ignore
async def start_dostawy(ctx):
    """
    DM: !start_dostawy
    Rozpoczyna sesję przyjmowania dostaw. Następnie wysyłaj trackingi
    (jeden lub wiele na raz, oddzielone spacją/enterem/czymkolwiek).
    """
    if not isinstance(ctx.channel, discord.DMChannel):
        await ctx.send("⚠️ Ta komenda działa tylko w wiadomości prywatnej (DM).")
        return

    user_id = ctx.author.id
    delivery_sessions[user_id] = DeliverySession(
        user_id=user_id,
        started_at=datetime.datetime.now(),
    )
    await ctx.send(
        "📦 **Sesja dostawy rozpoczęta!**\n"
        "Skanuj/wpisuj numery tracking (jeden lub wiele na raz — rozdziel spacją, enterem lub czymkolwiek).\n"
        "Wpisz `!stop_dostawy` żeby zakończyć i zobaczyć podsumowanie."
    )


@bot.command()  # type: ignore
async def stop_dostawy(ctx):
    """
    DM: !stop_dostawy
    Kończy sesję dostawy i wysyła podsumowanie:
    - ile paczek przyjęto
    - suma PLN
    - gotowe tickety (wszystkie order_items zrealizowane)
    - nieznalezione trackingi
    """
    if not isinstance(ctx.channel, discord.DMChannel):
        await ctx.send("⚠️ Ta komenda działa tylko w wiadomości prywatnej (DM).")
        return

    user_id = ctx.author.id
    session = delivery_sessions.pop(user_id, None)
    if session is None:
        await ctx.send("⚠️ Nie masz aktywnej sesji. Wpisz `!start_dostawy` żeby zacząć.")
        return

    accepted = session.accepted()
    failed = session.failed()
    elapsed = datetime.datetime.now() - session.started_at
    minutes = int(elapsed.total_seconds() // 60)
    seconds = int(elapsed.total_seconds() % 60)

    # Sprawdź gotowe tickety (wszystkie order_items zrealizowane)
    data = await mrowka_data.PisarzMrowka.read()
    gotowe_tickets: list[str] = []
    for ticket_name, ticket in data.tickets.items():
        if not ticket.divided_orders:
            continue
        all_done = all(
            oi.history.get_status().status == mrowka_data.MrowkaOrderItemStatus.ZAMOWIENIE_ZOSTALO_ZREALIZOWANE
            for oi in ticket.divided_orders.values()
        )
        done_count = sum(
            1 for oi in ticket.divided_orders.values()
            if oi.history.get_status().status == mrowka_data.MrowkaOrderItemStatus.ZAMOWIENIE_ZOSTALO_ZREALIZOWANE
        )
        total_count = len(ticket.divided_orders)
        if all_done:
            total_val = sum(oi.price_total() for oi in ticket.divided_orders.values())
            gotowe_tickets.append(f"✅ **{ticket_name}** — {done_count}/{total_count} paczek | {total_val:.2f} PLN")

    # === Buduj odpowiedź ===
    lines = [
        f"📦 **Podsumowanie dostawy** ({minutes}m {seconds}s)",
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"✅ Przyjęte: **{len(accepted)}** paczek | 💰 Suma: **{session.total_price():.2f} PLN**",
    ]

    if accepted:
        lines.append("\n**Przyjęte PZ:**")
        for r in accepted:
            ticket_info = f" | ticket: {r.ticket_name}" if r.ticket_name else ""
            lines.append(f"  📦 `{r.tracking[:12]}...` → **{r.sygnatura}**{ticket_info}")

    if failed:
        lines.append(f"\n❌ **Nie znalezione ({len(failed)}):**")
        for r in failed:
            lines.append(f"  ❓ `{r.tracking}`")

    if gotowe_tickets:
        lines.append(f"\n🎉 **Gotowe tickety ({len(gotowe_tickets)}):**")
        lines.extend(gotowe_tickets)
    else:
        lines.append("\n⏳ Brak ticketów z wszystkimi paczkami dostarczonymi.")

    await ctx.send("\n".join(lines))


@bot.command()  # type: ignore
async def ticket(ctx):
    try:
        message = dc.message_from_dc_message(ctx.message)
        await message.delete(bot)

        if not hasattr(ctx.channel, 'name') or ctx.channel.name != TICKET_CHANNEL:
            await message.author.send(
                bot,
                f"⚠️ Komenda !ticket może być użyta tylko na kanale '{TICKET_CHANNEL}' ⚠️\n"
                f"{common.HELP_TICKET}",
            )
            return

        now = datetime.datetime.now()
        month_num = now.month
        
        # Oczyszczenie nazwy uzytkownika (tylko litery i cyfry)
        raw_name = ctx.author.display_name.lower()
        import re
        clean_name = re.sub(r'[^a-z0-9]', '', raw_name)
        if not clean_name:
            clean_name = "user"
            
        prefix = f"s{month_num}{clean_name}"

        async with mrowka_data.PisarzMrowka.lock:
            data = await mrowka_data.PisarzMrowka.read(safe=False)
            
            # Policz tickety tego uzytkownika w tym miesiacu
            user_tickets_this_month = 0
            for t in data.tickets.values():
                ticket_created = getattr(t, 'created_at', None)
                if getattr(t, 'owner', None) and t.owner.id == ctx.author.id:
                    if ticket_created and ticket_created.month == month_num and ticket_created.year == now.year:
                        user_tickets_this_month += 1
                        
            ticket_number = user_tickets_this_month + 1
            nazwa_ticketu = f"{prefix}{ticket_number:02d}"
            
            # Upewnij sie ze kanal o tej nazwie nie istnieje (np. po usunieciu z jsona)
            while discord.utils.get(ctx.guild.channels, name=nazwa_ticketu) or nazwa_ticketu in data.tickets:
                ticket_number += 1
                nazwa_ticketu = f"{prefix}{ticket_number:02d}"

        channel = await dc.channel_from_name(bot, nazwa_ticketu)
        content = (
            "📋 Pobierz plik, wypełnij go i odeślij spowrotem 📋\n"
            "Przydatne komendy:\n"
            f"{common.HELP_BIORE_TICKET}\n"
            f"{common.HELP_SUKCES}\n"
            f"{common.HELP_PORAZKA}\n"
            f"{common.HELP_STATUS}\n"
            f"{common.HELP_HISTORIA}\n"
            f"{common.HELP_INFO}\n"
            f"{common.HELP_COFNIJ}\n"
            f"{common.HELP_ANULUJ}\n"
            f"{common.HELP_BANK}\n"
            f"{common.HELP_BANK_WYCZYSC}\n"
            f"{common.HELP_PODMIEN_MAIL}\n"
            f"{common.HELP_ZREALIZUJ}\n"
            f"{common.HELP_TICKET}\n"
            f"{common.HELP_TICKET_CSV}\n"
            f"{common.HELP_TRACKING_CSV}\n"
            f"{common.HELP_MAILS_CSV}\n"
        )
        await channel.send(
            bot,
            content=content,
            file=discord.File(TICKET_CSV_PATH, filename=f"{nazwa_ticketu}.csv"),
        )

        ticket = mrowka_data.MrowkaTicket(
            name=nazwa_ticketu,
            owner=message.author,
            divided_orders={},
            created_at=datetime.datetime.now(),
            ticket_channel_id=channel.id,
            guild_id=ctx.guild.id,
        )

        async with mrowka_data.PisarzMrowka.lock:
            data = await mrowka_data.PisarzMrowka.read(safe=False)
            data.tickets[nazwa_ticketu] = ticket
            data.daily_messages_to_send.add(ticket.created_at.date())
            await ticket.discord_update(bot)
            await mrowka_data.PisarzMrowka.write(data, safe=False)

    except Exception as e:
        logger.logger.exception(f"!ticket error: {e}")
        try:
            await ctx.send(f"❌ Błąd tworzenia ticketu: `{e}`")
        except Exception:
            pass


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    await bot.process_commands(message)

    # === Sesja dostawy (DM) — przetwarzaj trackingi ===
    if isinstance(message.channel, discord.DMChannel):
        user_id = message.author.id
        session = delivery_sessions.get(user_id)
        if session is not None and not message.content.startswith("!"):
            # Wyciągnij trackingi — szukaj w każdym tokenie osobno (nie usuwaj newlines!)
            # Inaczej dwa numery w osobnych liniach zleją się w jeden fałszywy tracking
            tokens = re.split(r"[\s,;|]+", message.content)
            trackings = []
            for token in tokens:
                # Wyciągnij ciąg 15–30 cyfr z tokena
                m = re.search(r"\d{15,30}", token)
                if m:
                    trackings.append(m.group(0))
            trackings = list(dict.fromkeys(trackings))  # deduplikacja, zachowaj kolejność
            if trackings:
                data = await mrowka_data.PisarzMrowka.read()
                for tracking in trackings:
                    # Wywołaj /api/pz/accept
                    result = await mrowka_lib._subiekt_post(
                        "/api/pz/accept", {"tracking": tracking}, timeout=30
                    )
                    sygnatura = result.get("sygnatura") if result else None

                    # Znajdź order_item i ticket
                    order_item_name = None
                    ticket_name = None
                    price = 0.0
                    for tname, ticket in data.tickets.items():
                        for oi in ticket.divided_orders.values():
                            if oi.tracking == tracking:
                                order_item_name = oi.name
                                ticket_name = tname
                                price = oi.price_total()
                                break
                        if order_item_name:
                            break

                    session.results.append(DeliveryResult(
                        tracking=tracking,
                        sygnatura=sygnatura,
                        order_item_name=order_item_name,
                        ticket_name=ticket_name,
                        price=price,
                    ))

                # Zaktualizuj statusy Discord async
                async with mrowka_data.PisarzMrowka.lock:
                    data_w = await mrowka_data.PisarzMrowka.read(safe=False)
                    changed = False
                    for tracking in trackings:
                        for ticket in data_w.tickets.values():
                            for oi in ticket.divided_orders.values():
                                if oi.tracking != tracking:
                                    continue
                                cur = oi.history.get_status()
                                if (
                                    mrowka_data.MrowkaOrderItemStatus.ZAMOWIENIE_ZOSTALO_ZREALIZOWANE
                                    in cur.status.next_statuses()
                                ):
                                    await oi.change_status(
                                        bot,
                                        mrowka_data.MrowkaOrderItemStatus.ZAMOWIENIE_ZOSTALO_ZREALIZOWANE,
                                        cur.user,
                                        data_w,
                                    )
                                    changed = True
                    if changed:
                        await mrowka_data.PisarzMrowka.write(data_w, safe=False)

    await mrowka_lib.ticket_update_csv(bot, message)
    await mrowka_lib.order_item_update_csv(bot, message)
    await mrowka_lib.tracking_update_csv(bot, message)
    await mrowka_lib.mails_update_csv(bot, message)
    await mrowka_lib.handle_faktura_pdf(bot, message)
    await mrowka_lib.handle_label(bot, message)


@bot.event
async def on_raw_reaction_add(rrae: discord.RawReactionActionEvent):
    try:
        if rrae.guild_id is None:
            return
        guild = bot.get_guild(rrae.guild_id)
        if guild is None:
            return

        emoji = str(discord.utils.get(guild.emojis, id=rrae.emoji.id) or rrae.emoji)
        channel = guild.get_channel(rrae.channel_id)
        if channel is None or not isinstance(channel, discord.TextChannel):
            return

        member = guild.get_member(rrae.user_id)
        if member is None:
            return
        if member.bot:
            return

        dc_message = await channel.fetch_message(rrae.message_id)
        message = dc.message_from_dc_message(dc_message)

        data = await mrowka_data.PisarzMrowka.read()
        message_type = data.message_id_to_message_type.get(dc_message.id, None)

        if message_type == mrowka_data.MrowkaMessageType.ORDER_ITEM_STATUS:
            await mrowka_lib.handle_order_item_reaction(
                bot, dc_message, message.author, emoji
            )
        if message_type == mrowka_data.MrowkaMessageType.FAKTURA_STATUS:
            await mrowka_lib.handle_faktura_status_reaction(bot, message, emoji)
        if message_type == mrowka_data.MrowkaMessageType.EAN_MESSAGE:
            await mrowka_lib.handle_ean_message_reaction(bot, message)
        if message_type == mrowka_data.MrowkaMessageType.ZADANIE and emoji == "✅":
            # Dismiss zadania wiadomości
            try:
                await dc_message.delete()
            except Exception:
                pass
            async with mrowka_data.PisarzMrowka.lock:
                data_w = await mrowka_data.PisarzMrowka.read(safe=False)
                data_w.message_id_to_message_type.pop(dc_message.id, None)
                await mrowka_data.PisarzMrowka.write(data_w, safe=False)

    except Exception as e:
        logger.logger.exception(e)


@bot.command()  # type: ignore
async def test_delivery(ctx, mail: str, tracking: str = "TEST-TRACKING-0001", order_number: str = None):
    """
    TEST: symuluje mail dostawczy od Zalando dla podanego konta.
    Użycie: !test_delivery eleatowskiedomeny+fiz46@gmail.com [tracking] [nr_zamowienia]
    """
    from gmail_imap import DeliveryInfo
    import datetime

    fake_info = DeliveryInfo(
        zalando_account=mail,
        gmail_base="eleatowskiedomeny@gmail.com",
        order_number=order_number,
        tracking=tracking,
        delivery_date=(datetime.date.today() + datetime.timedelta(days=2)).strftime("%d.%m.%Y"),
        name_surname=None,
    )

    await ctx.send(f"🧪 Symulacja maila dostawczego dla **{mail}**\nTracking: `{tracking}`")

    # Wywołaj wewnętrzną logikę check_gmail_delivery z fake danymi
    async with mrowka_data.PisarzMrowka.lock:
        data = await mrowka_data.PisarzMrowka.read(safe=False)
        mail_to_order = {}
        for ticket in data.tickets.values():
            for oi in ticket.divided_orders.values():
                if oi.mail:
                    mail_to_order[oi.mail.mail.lower()] = oi

        oi = mail_to_order.get(mail.lower())
        if not oi:
            await ctx.send(f"❌ Nie znaleziono order_item dla konta `{mail}`")
            return

        oi.tracking = tracking
        oi.delivery_date = fake_info.delivery_date
        if order_number:
            oi.order_number = order_number

        # Update tracking w PZ
        if oi.pz_sygnatura or oi.name:
            result = await mrowka_lib._subiekt_post("/api/pz/update-tracking", {
                "orderName": oi.name,
                "tracking": tracking,
            })
            track_ok = result and result.get("Success") if result else False
            await ctx.send(f"📦 Update-tracking PZ: {'✅' if track_ok else '⚠️ Błąd (pomijam)'}")

        # Zmień status na ZAMOWIENIE_WYSLANE
        user = dc.message_from_dc_message(ctx.message).author
        wyslane = mrowka_data.MrowkaOrderItemStatus.ZAMOWIENIE_WYSLANE
        zrealizowane = mrowka_data.MrowkaOrderItemStatus.ZAMOWIENIE_ZOSTALO_ZREALIZOWANE
        cur = oi.history.get_status()
        if cur.status not in (wyslane, zrealizowane):
            await oi.change_status(bot, wyslane, user, data)
            await ctx.send(f"✅ Status → **ZAMOWIENIE_WYSLANE** dla `{oi.name}`")
        else:
            await ctx.send(f"ℹ️ Status już: `{cur.status.name}`")

        await mrowka_data.PisarzMrowka.write(data, safe=False)


@bot.event
async def on_ready():
    logger.logger.info(f"Zalogowano jako {bot.user}")
    await ean_db.init_db()  # inicjalizuj lokalną bazę EAN
    create_task(every_1_minute())
    create_task(every_1_day())
    create_task(every_1_hour())


@bot.command()
async def setup(ctx):
    """Tworzy wymagane kanały i kategorie jeśli nie istnieją."""
    REQUIRED_CHANNELS = ["tickety", "magazynierzy", "zalando-dostawy"]
    REQUIRED_CATEGORIES = ["Archiwum Sukcesu", "Archiwum Porażki"]
    guild = ctx.guild
    existing_channels = [ch.name for ch in guild.channels]
    existing_categories = [cat.name for cat in guild.categories]
    created = []

    for name in REQUIRED_CHANNELS:
        if name not in existing_channels:
            await guild.create_text_channel(name)
            created.append(f"📢 #{name}")

    for name in REQUIRED_CATEGORIES:
        if name not in existing_categories:
            await guild.create_category(name)
            created.append(f"📁 {name}")

    if created:
        await ctx.send("✅ **Setup zakończony! Utworzono:**\n" + "\n".join(created))
    else:
        await ctx.send("ℹ️ Wszystkie wymagane kanały i kategorie już istnieją.")


@bot.command()
async def set_webhook(ctx, url: str = ""):
    """Zmienia URL webhooka bledow. Uzycie: !set_webhook <url>"""
    if not url.startswith("https://discord.com/api/webhooks/"):
        await ctx.send(
            "❌ Nieprawidłowy URL.\n"
            "Skopiuj webhook z: Ustawienia kanału → Integracje → Utwórz Webhook → Kopiuj URL\n"
            "Użycie: `!set_webhook https://discord.com/api/webhooks/...`"
        )
        return

    import json as _json
    import pathlib as _pathlib
    config_path = _pathlib.Path(__file__).parent / "config.json"
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = _json.load(f)
    cfg["error_webhook_url"] = url
    with open(config_path, "w", encoding="utf-8") as f:
        _json.dump(cfg, f, ensure_ascii=False, indent=2)

    # Odswiez URL w aktywnym handlerze (bez restartu)
    for handler in logging.getLogger().handlers:
        if hasattr(handler, "webhook_url"):
            handler.webhook_url = url

    await ctx.send(f"✅ Webhook błędów zaktualizowany i aktywny!")


def create_task(coro):
    return bot.loop.create_task(coro)


async def every_1_minute():
    while True:
        try:
            create_task(mrowka_data.PisarzMrowka.snapshot())

            async with mrowka_data.PisarzMrowka.lock:
                data = await mrowka_data.PisarzMrowka.read(safe=False)
                await data.send_daily_messages(bot)
                await data.send_reminders(bot)
                await mrowka_data.PisarzMrowka.write(data, safe=False)

            await asyncio.sleep(60)
        except Exception as e:
            logger.logger.exception(f"every_1_minute: {e}")


async def every_1_hour():
    while True:
        try:
            await mrowka_lib.check_gmail_delivery(bot)            # tracking z maili wysyłkowych
            await mrowka_lib.check_gmail_delivery_confirmed(bot)  # "Cyfrowy dowód dostawy" → ZREALIZOWANE
            await mrowka_lib.check_gmail_delay(bot)               # opóźnienia dostawy
            await mrowka_lib.check_imap_invoice(bot)              # faktury do pobrania
            await asyncio.sleep(3600)
        except Exception as e:
            logger.logger.exception(f"every_1_hour: {e}")


async def every_6_hours():
    try:
        create_task(mrowka_lib.update_everything(bot))
    except Exception as e:
        logger.logger.exception(f"every_6_hours: {e}")
    # while True:
    #    try:
    #        create_task(mrowka_lib.update_everything(bot))

    #        await asyncio.sleep(3600 * 6)
    #    except Exception as e:
    #        logger.logger.exception(f"every_6_hours: {e}")


async def every_1_day():
    while True:
        try:
            await asyncio.sleep(3600 * 24)
        except Exception as e:
            logger.logger.exception(f"every_1_day: {e}")


if __name__ == "__main__":
    import json as _json, pathlib as _pathlib, logging
    _config = _json.loads((_pathlib.Path(__file__).parent / "config.json").read_text(encoding="utf-8"))
    _token = _config.get("discord_token", "")
    if not _token:
        print("BŁĄD: Brak tokena w config.json!")
    else:
        bot.run(_token)
