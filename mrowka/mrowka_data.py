from __future__ import annotations
from typing import Optional, Union
import datetime
import dc
import mails
import dataclasses
import pprint
import common
import enum
import discord
import aiofiles  # type: ignore
import logger
from discord.ext import commands


class MrowkaMessageType(enum.Enum):
    TICKET_STATUS = 1
    ORDER_ITEM_STATUS = 2
    INTERIA_ERROR = 3
    FAKTURA_STATUS = 4
    EAN_MESSAGE = 5
    ZADANIE = 6


class MrowkaOrderItemStatusStatus(enum.Enum):
    OCZEKUJACE = 1
    POTWIERDZONE = 2
    ANULOWANE = 3

    def get_statuses(self) -> list["MrowkaOrderItemStatus"]:
        return [
            status for status in MrowkaOrderItemStatus if status.get_status() == self
        ]

    def emoji(self) -> str:
        if self == MrowkaOrderItemStatusStatus.OCZEKUJACE:
                return "🕰️"
        elif self == MrowkaOrderItemStatusStatus.POTWIERDZONE:
                return "✅"
        elif self == MrowkaOrderItemStatusStatus.ANULOWANE:
                return "❌"

    def text(self) -> str:
        if self == MrowkaOrderItemStatusStatus.OCZEKUJACE:
                return "Oczekujące"
        elif self == MrowkaOrderItemStatusStatus.POTWIERDZONE:
                return "Potwierdzone"
        elif self == MrowkaOrderItemStatusStatus.ANULOWANE:
                return "Anulowane"

    def __str__(self) -> str:
        return f"{self.emoji()} {self.text()}"

    def __repr__(self) -> str:
        return self.__str__()


class MrowkaOrderItemStatus(enum.Enum):
    OCZEKUJE_NA_ZAMOWIENIE = 1
    W_TRAKCIE_ZAMAWIANIA = 2
    ZAMOWIENIE_POTWIERDZONE = 3
    ZAMOWIENIE_WYSLANE = 4
    ZAMOWIENIE_ZOSTALO_ZREALIZOWANE = 5

    ZAMOWIENIE_ANULOWANE_RECZNIE = 6

    ZAMOWIENIE_ANULOWANE_PRZEZ_ZALANDO_NALEZY_ANULOWAC_1 = 7
    ZAMOWIENIE_ANULOWANE_PRZEZ_ZALANDO_NALEZY_ANULOWAC_2 = 8
    ZAMOWIENIE_ANULOWANE_PRZEZ_ZALANDO = 9

    ZAMOWIENIE_NIE_ODBIERAC_1 = 10
    ZAMOWIENIE_NIE_ODBIERAC_2 = 11

    ZAMOWIENIE_DO_ODESLANIA_1 = 12
    ZAMOWIENIE_DO_ODESLANIA_2 = 13
    ZAMOWIENIE_ODESLANE = 14

    BRAK = 15

    def help_text(self) -> str:
        return f'{self.emoji()} - ustaw status na "{self.text()}"'

    def next_statuses(self) -> list["MrowkaOrderItemStatus"]:
        if self == MrowkaOrderItemStatus.OCZEKUJE_NA_ZAMOWIENIE:
                return [
                    MrowkaOrderItemStatus.W_TRAKCIE_ZAMAWIANIA,
                    MrowkaOrderItemStatus.BRAK,
                ]
        elif self == MrowkaOrderItemStatus.W_TRAKCIE_ZAMAWIANIA:
                return [
                    MrowkaOrderItemStatus.ZAMOWIENIE_POTWIERDZONE,
                    MrowkaOrderItemStatus.BRAK,
                ]
        elif self == MrowkaOrderItemStatus.ZAMOWIENIE_ANULOWANE_PRZEZ_ZALANDO_NALEZY_ANULOWAC_1:
                return [
                    MrowkaOrderItemStatus.ZAMOWIENIE_ANULOWANE_PRZEZ_ZALANDO_NALEZY_ANULOWAC_2
                ]
        elif self == MrowkaOrderItemStatus.ZAMOWIENIE_ANULOWANE_PRZEZ_ZALANDO_NALEZY_ANULOWAC_2:
                return [MrowkaOrderItemStatus.ZAMOWIENIE_ANULOWANE_PRZEZ_ZALANDO]
        elif self == MrowkaOrderItemStatus.ZAMOWIENIE_NIE_ODBIERAC_1:
                return [MrowkaOrderItemStatus.ZAMOWIENIE_NIE_ODBIERAC_2]
        elif self == MrowkaOrderItemStatus.ZAMOWIENIE_DO_ODESLANIA_1:
                return [MrowkaOrderItemStatus.ZAMOWIENIE_DO_ODESLANIA_2]
        elif self == MrowkaOrderItemStatus.ZAMOWIENIE_DO_ODESLANIA_2:
                return [MrowkaOrderItemStatus.ZAMOWIENIE_ODESLANE]
        else:
                return []

    def send_warehouse_message(self) -> bool:
        return self in [
            MrowkaOrderItemStatus.OCZEKUJE_NA_ZAMOWIENIE,
            MrowkaOrderItemStatus.W_TRAKCIE_ZAMAWIANIA,
            MrowkaOrderItemStatus.ZAMOWIENIE_ANULOWANE_PRZEZ_ZALANDO_NALEZY_ANULOWAC_1,
            MrowkaOrderItemStatus.ZAMOWIENIE_ANULOWANE_PRZEZ_ZALANDO_NALEZY_ANULOWAC_2,
            MrowkaOrderItemStatus.ZAMOWIENIE_NIE_ODBIERAC_1,
            MrowkaOrderItemStatus.ZAMOWIENIE_DO_ODESLANIA_1,
            MrowkaOrderItemStatus.ZAMOWIENIE_DO_ODESLANIA_2,
        ]

    def emoji(self) -> str:
        if self == MrowkaOrderItemStatus.OCZEKUJE_NA_ZAMOWIENIE:
                return "⏳"
        elif self == MrowkaOrderItemStatus.W_TRAKCIE_ZAMAWIANIA:
                return "🛒"
        elif self == MrowkaOrderItemStatus.ZAMOWIENIE_POTWIERDZONE:
                return "👏"
        elif self == MrowkaOrderItemStatus.ZAMOWIENIE_WYSLANE:
                return "🚚"
        elif self == MrowkaOrderItemStatus.ZAMOWIENIE_ZOSTALO_ZREALIZOWANE:
                return "✅"
        elif self == MrowkaOrderItemStatus.ZAMOWIENIE_ANULOWANE_RECZNIE:
                return "❌"
        elif self == MrowkaOrderItemStatus.ZAMOWIENIE_ANULOWANE_PRZEZ_ZALANDO_NALEZY_ANULOWAC_1:
                return "❗"
        elif self == MrowkaOrderItemStatus.ZAMOWIENIE_ANULOWANE_PRZEZ_ZALANDO_NALEZY_ANULOWAC_2:
                return "✋"
        elif self == MrowkaOrderItemStatus.ZAMOWIENIE_ANULOWANE_PRZEZ_ZALANDO:
                return "⚠️"
        elif self == MrowkaOrderItemStatus.ZAMOWIENIE_NIE_ODBIERAC_1:
                return "🙅‍♂️"
        elif self == MrowkaOrderItemStatus.ZAMOWIENIE_NIE_ODBIERAC_2:
                return "⛔"
        elif self == MrowkaOrderItemStatus.ZAMOWIENIE_DO_ODESLANIA_1:
                return "📦"
        elif self == MrowkaOrderItemStatus.ZAMOWIENIE_DO_ODESLANIA_2:
                return "🔁"
        elif self == MrowkaOrderItemStatus.ZAMOWIENIE_ODESLANE:
                return "🔄"
        elif self == MrowkaOrderItemStatus.BRAK:
                return "🚫"

    def get_status(self) -> MrowkaOrderItemStatusStatus:
        if self in [
            MrowkaOrderItemStatus.OCZEKUJE_NA_ZAMOWIENIE,
            MrowkaOrderItemStatus.W_TRAKCIE_ZAMAWIANIA,
        ]:
            return MrowkaOrderItemStatusStatus.OCZEKUJACE
        elif self in [
            MrowkaOrderItemStatus.ZAMOWIENIE_POTWIERDZONE,
            MrowkaOrderItemStatus.ZAMOWIENIE_WYSLANE,
            MrowkaOrderItemStatus.ZAMOWIENIE_ZOSTALO_ZREALIZOWANE,
        ]:
            return MrowkaOrderItemStatusStatus.POTWIERDZONE
        else:
            return MrowkaOrderItemStatusStatus.ANULOWANE

    def text(self) -> str:
        if self == MrowkaOrderItemStatus.OCZEKUJE_NA_ZAMOWIENIE:
                return "Oczekuje na zamówienie"
        elif self == MrowkaOrderItemStatus.W_TRAKCIE_ZAMAWIANIA:
                return "W trakcie zamawiania"
        elif self == MrowkaOrderItemStatus.ZAMOWIENIE_POTWIERDZONE:
                return "Zamówienie potwierdzone"
        elif self == MrowkaOrderItemStatus.ZAMOWIENIE_WYSLANE:
                return "Zamówienie wysłane"
        elif self == MrowkaOrderItemStatus.ZAMOWIENIE_ZOSTALO_ZREALIZOWANE:
                return "Zamówienie zostało zrealizowane"
        elif self == MrowkaOrderItemStatus.ZAMOWIENIE_ANULOWANE_RECZNIE:
                return "Zamówienie anulowane ręcznie"
        elif self == MrowkaOrderItemStatus.ZAMOWIENIE_ANULOWANE_PRZEZ_ZALANDO_NALEZY_ANULOWAC_1:
                return "Zamówienie do anulowania"
        elif self == MrowkaOrderItemStatus.ZAMOWIENIE_ANULOWANE_PRZEZ_ZALANDO_NALEZY_ANULOWAC_2:
                return "Zamówienie w trakcie anulowania"
        elif self == MrowkaOrderItemStatus.ZAMOWIENIE_ANULOWANE_PRZEZ_ZALANDO:
                return "Zamówienie anulowane"
        elif self == MrowkaOrderItemStatus.ZAMOWIENIE_NIE_ODBIERAC_1:
                return "Nie odbierać tego zamówienia"
        elif self == MrowkaOrderItemStatus.ZAMOWIENIE_NIE_ODBIERAC_2:
                return "Zamówienie nieodebrane"
        elif self == MrowkaOrderItemStatus.ZAMOWIENIE_DO_ODESLANIA_1:
                return "Zamówienie do odesłania"
        elif self == MrowkaOrderItemStatus.ZAMOWIENIE_DO_ODESLANIA_2:
                return "Zamówienie w trakcie odsyłania"
        elif self == MrowkaOrderItemStatus.ZAMOWIENIE_ODESLANE:
                return "Zamówienie odesłane"
        elif self == MrowkaOrderItemStatus.BRAK:
                return "Brak"

    def anuluj(self) -> "MrowkaOrderItemStatus":
        if self == MrowkaOrderItemStatus.OCZEKUJE_NA_ZAMOWIENIE or self == MrowkaOrderItemStatus.W_TRAKCIE_ZAMAWIANIA:
                return MrowkaOrderItemStatus.ZAMOWIENIE_ANULOWANE_RECZNIE
        elif self == MrowkaOrderItemStatus.ZAMOWIENIE_POTWIERDZONE:
                return (
                    MrowkaOrderItemStatus.ZAMOWIENIE_ANULOWANE_PRZEZ_ZALANDO_NALEZY_ANULOWAC_1
                )
        elif self == MrowkaOrderItemStatus.ZAMOWIENIE_WYSLANE:
                return MrowkaOrderItemStatus.ZAMOWIENIE_NIE_ODBIERAC_1
        elif self == MrowkaOrderItemStatus.ZAMOWIENIE_ZOSTALO_ZREALIZOWANE:
                return MrowkaOrderItemStatus.ZAMOWIENIE_DO_ODESLANIA_1
        else:
                return self

    def __str__(self) -> str:
        return f"{self.emoji()} {self.text()}"

    def __repr__(self) -> str:
        return self.__str__()


@dataclasses.dataclass
class MrowkaOrderItemStatusHistoryEntry:
    status: MrowkaOrderItemStatus
    user: dc.User
    timestamp: datetime.datetime

    def to_discord(self) -> str:
        return f"Status: {self.status} (**{self.user.name}** - {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')})"

    def __str__(self) -> str:
        return pprint.pformat(dataclasses.asdict(self), indent=4)

    def __repr__(self) -> str:
        return self.__str__()


@dataclasses.dataclass
class MrowkaOrderItemStatusHistory:
    entries: list[MrowkaOrderItemStatusHistoryEntry] = dataclasses.field(
        default_factory=list
    )

    def to_discord(self) -> str:
        lines = [
            f" {id+1}. {e.timestamp.strftime('%Y-%m-%d %H:%M:%S')} - {e.status} (**{e.user.name}**)"
            for id, e in enumerate(self.entries)
        ]
        return "\n".join(lines)

    def change_status(self, user: dc.User, status: MrowkaOrderItemStatus):
        entry = MrowkaOrderItemStatusHistoryEntry(
            status=status,
            user=user,
            timestamp=datetime.datetime.now(),
        )
        self.entries.append(entry)

    def new(self) -> bool:
        return len(self.entries) == 0

    def get_status(self) -> MrowkaOrderItemStatusHistoryEntry:
        if len(self.entries) == 0:
            raise Exception("No status in history")
        return self.entries[-1]

    def __str__(self) -> str:
        return pprint.pformat(dataclasses.asdict(self), indent=4)

    def __repr__(self) -> str:
        return self.__str__()


@dataclasses.dataclass
class MrowkaShoeInfo:
    link: str
    price: float
    og_price: float
    size_to_quantity: dict[str, int]
    limit_per_shoe: int
    limit_per_size: int = common.SHOE_LIMIT_PER_SHOE_SIZE

    def max_size_length(self) -> int:
        return max(len(size) for size in self.size_to_quantity)

    def to_discord(self) -> str:
        size_quantity_lines = [
            f"{size.ljust(self.max_size_length())} : {self.size_to_quantity[size]}"
            for size in common.sorted_sizes(self.size_to_quantity.keys())
        ]
        _sep = '\n'
        return (
            f"```{self.link}```"
            f"Cena: {self.price:.2f}zł, Limit na but: {self.limit_per_shoe}, Limit na rozmiar: {self.limit_per_size}"
            f"```{_sep.join(size_quantity_lines)}```"
        )

    def price_total(self) -> float:
        return sum(quantity * self.price for quantity in self.size_to_quantity.values())

    def amount_total(self) -> int:
        return sum(quantity for quantity in self.size_to_quantity.values())

    def clean(self):
        self.size_to_quantity = {
            size: quantity
            for size, quantity in self.size_to_quantity.items()
            if quantity > 0
        }

    def deepcopy(self) -> "MrowkaShoeInfo":
        return MrowkaShoeInfo(
            link=self.link,
            price=self.price,
            og_price=self.og_price,
            size_to_quantity=self.size_to_quantity.copy(),
            limit_per_shoe=self.limit_per_shoe,
            limit_per_size=self.limit_per_size,
        )

    def minus(self, other: "MrowkaShoeInfo") -> "MrowkaShoeInfo":
        ret = self.deepcopy()
        ret.size_to_quantity = {}
        for size in self.size_to_quantity.keys() | other.size_to_quantity.keys():
            self_quantity = self.size_to_quantity.get(size, 0)
            other_quantity = other.size_to_quantity.get(size, 0)
            new_quantity = self_quantity - other_quantity

            if new_quantity > 0:
                ret.size_to_quantity[size] = new_quantity
            elif new_quantity == 0:
                continue
            else:
                raise Exception("Subtracting more shoes than available")

        return ret

    def plus(self, other: "MrowkaShoeInfo") -> "MrowkaShoeInfo":
        ret = self.deepcopy()
        for size, quantity in other.size_to_quantity.items():
            current_quantity = ret.size_to_quantity.get(size, 0)
            ret.size_to_quantity[size] = current_quantity + quantity
        return ret

    def leq(self, other: "MrowkaShoeInfo") -> bool:
        for size in self.size_to_quantity.keys() | other.size_to_quantity.keys():
            self_quantity = self.size_to_quantity.get(size, 0)
            other_quantity = other.size_to_quantity.get(size, 0)
            if self_quantity > other_quantity:
                return False
        return True

    def __str__(self) -> str:
        return pprint.pformat(dataclasses.asdict(self), indent=4)

    def __repr__(self) -> str:
        return self.__str__()


@dataclasses.dataclass
class MrowkaShoeCollection:
    shoes: dict[str, MrowkaShoeInfo] = dataclasses.field(default_factory=dict)

    @staticmethod
    async def from_csv(file_path: str) -> "MrowkaShoeCollection":
        async with aiofiles.open(file_path, "r", encoding="utf-8-sig") as f:
            lines = await f.readlines()

        header = lines[0].strip().split(";")
        header_upper = [h.strip().upper() for h in header]

        # Wykryj format:
        # Stary: LINK ; CENA ; LIMIT ; 38 ; 39 ...
        # Nowy:  LINK ; LIMIT ; 38 ; 39 ...    ← bot sam pobiera cenę
        has_price_col = len(header_upper) > 1 and header_upper[1] in ("CENA", "PRICE", "OG_PRICE")

        if has_price_col:
            sizes_names = [h.strip() for h in header[3:]]
        else:
            sizes_names = [h.strip() for h in header[2:]]

        def line_to_product_order(line: str) -> Optional["MrowkaShoeInfo"]:
            splitted_line = line.strip().split(";")
            if not splitted_line[0].strip():
                return None
            link = splitted_line[0].strip()

            if has_price_col:
                og_price = (
                    float(splitted_line[1].strip())
                    if splitted_line[1].strip() != ""
                    else 0.0
                )
                price = og_price * 0.8
                limit_per_shoe = (
                    int(splitted_line[2].strip())
                    if len(splitted_line) > 2 and splitted_line[2].strip() != ""
                    else 1000
                )
                qty_start = 3
            else:
                # Nowy format — cena placeholder 0 (wypełni scanner)
                og_price = 0.0
                price = 0.0
                limit_per_shoe = (
                    int(splitted_line[1].strip())
                    if len(splitted_line) > 1 and splitted_line[1].strip().isdigit()
                    else 1000
                )
                qty_start = 2

            quantities = [
                int(q.strip() if q.strip() != "" else "0") for q in splitted_line[qty_start:]
            ]
            size_to_quantity: dict[str, int] = {}
            for size_name, size_quantity in zip(sizes_names, quantities):
                if size_quantity > 0:
                    size_to_quantity[size_name] = size_quantity

            if len(size_to_quantity) == 0:
                return None
            return MrowkaShoeInfo(
                link=link,
                price=price,
                og_price=og_price,
                limit_per_shoe=limit_per_shoe,
                size_to_quantity=size_to_quantity,
            )

        ret = MrowkaShoeCollection()

        for line in lines[1:]:
            if not line.strip():
                continue
            product_order = line_to_product_order(line)
            if product_order is not None:
                ret.add_shoe(product_order)

        return ret


    def deepcopy(self) -> "MrowkaShoeCollection":
        new_sc = MrowkaShoeCollection()
        for shoe in self.shoes.values():
            new_sc.add_shoe(shoe.deepcopy())
        return new_sc

    def add_shoe(self, shoe: MrowkaShoeInfo):
        if shoe.link in self.shoes:
            existing_shoe = self.shoes[shoe.link]
            new_shoe = existing_shoe.plus(shoe)
            self.shoes[shoe.link] = new_shoe
        else:
            self.shoes[shoe.link] = shoe.deepcopy()

    def add_sc(self, other: "MrowkaShoeCollection"):
        for shoe in other.shoes.values():
            self.add_shoe(shoe)

    def max_size_length(self) -> int:
        return max(shoe.max_size_length() for shoe in self.shoes.values())

    def sizes(self) -> set[str]:
        sizes: set[str] = set()
        for shoe in self.shoes.values():
            for size in shoe.size_to_quantity.keys():
                sizes.add(size)
        return sizes

    def price_total(self) -> float:
        return sum(shoe.price_total() for shoe in self.shoes.values())

    def amount_total(self) -> int:
        return sum(shoe.amount_total() for shoe in self.shoes.values())

    def minus(self, shoe: MrowkaShoeInfo):
        if shoe.link not in self.shoes:
            raise Exception("Subtracting shoe that does not exist")

        existing_shoe = self.shoes[shoe.link]
        new_shoe = existing_shoe.minus(shoe)
        if new_shoe.amount_total() > 0:
            self.shoes[shoe.link] = new_shoe
        elif new_shoe.amount_total() == 0:
            del self.shoes[shoe.link]
        else:
            raise Exception("Subtracting more shoes than available")

    def plus(self, other: "MrowkaShoeCollection"):
        for shoe in other.shoes.values():
            self.add_shoe(shoe)

    @logger.async_try_log(None)
    async def take_one_order_item(
        self,
        name: str,
        ticket_name: str,
        guild_id: int,
        ticket_channel_id: int,
        user: dc.User,
    ) -> Optional["MrowkaOrderItem"]:
        if self.amount_total() == 0:
            return None

        mail = await mails.get_unused_mail()
        status: MrowkaOrderItemStatusHistoryEntry = MrowkaOrderItemStatusHistoryEntry(
            status=MrowkaOrderItemStatus.OCZEKUJE_NA_ZAMOWIENIE,
            user=user,
            timestamp=datetime.datetime.now(),
        )
        order_item = MrowkaOrderItem(
            name=name,
            ticket_name=ticket_name,
            shoes=[],
            cancelled_shoes=[],
            history=MrowkaOrderItemStatusHistory(entries=[status]),
            mail=mail,
            guild_id=guild_id,
            ticket_channel_id=ticket_channel_id,
        )

        price = 0.0
        for link in list(self.shoes.keys()):
            per_shoe = 0
            shoe = self.shoes[link].deepcopy()
            shoe.size_to_quantity = {}

            for size, quantity in self.shoes[link].size_to_quantity.items():
                quantity_to_take = min(
                    quantity,
                    shoe.limit_per_shoe - per_shoe,
                    shoe.limit_per_size,
                    int((common.PRICE_LIMIT_PER_ORDER_ITEM - price) // shoe.price),
                )
                if quantity_to_take > 0:
                    shoe.size_to_quantity[size] = quantity_to_take
                    price += quantity_to_take * shoe.price
                    per_shoe += quantity_to_take

            if shoe.amount_total() > 0:
                order_item.shoes.append(shoe)
                self.minus(shoe)

        return order_item

    def __str__(self) -> str:
        return pprint.pformat(dataclasses.asdict(self), indent=4)

    def __repr__(self) -> str:
        return self.__str__()

    def __iter__(self):
        return iter(self.shoes.values())


@dataclasses.dataclass
class ShipmentInfo:
    """Informacje o jednej nadanej paczce (może być max 2 na zamówienie)."""
    tracking: str
    amount_pln: Optional[float]   # Kwota pobrania tej paczki
    date_sent: Optional[str]      # Data nadania (z headera maila)
    source_mail: str              # Konto gmail z którego przyszedł mail

    def to_str(self) -> str:
        amount_str = f"{self.amount_pln:.2f} PLN" if self.amount_pln else "?"
        return f"[{self.tracking}] {amount_str}"


@dataclasses.dataclass
class MrowkaOrderItem:
    name: str
    ticket_name: str
    shoes: list[MrowkaShoeInfo]
    cancelled_shoes: list[MrowkaShoeInfo]
    history: MrowkaOrderItemStatusHistory
    mail: Optional[mails.MailData]
    guild_id: int
    ticket_channel_id: int
    warehouse_message_id: Optional[int] = None
    faktura_message_id: Optional[int] = None
    ticket_message_id: Optional[int] = None
    tracking: Optional[str] = None
    delivery_date: Optional[str] = None
    order_number: Optional[str] = None
    name_surname: Optional[str] = None
    faktura: Optional[bool] = None
    pz_sygnatura: Optional[str] = None  # Sygnatura PZ w Subiekcie (np. PZ 7/2026)
    shipments: list[ShipmentInfo] = dataclasses.field(default_factory=list)  # Lista nadanych przesyłek

    def shipments_uwagi(self) -> str:
        """Buduje tekst do pola Uwagi PZ opisujący nadane przesyłki."""
        if not self.shipments:
            return ""
        n = len(self.shipments)
        parts = " | ".join(s.to_str() for s in self.shipments)
        return f"{n} przesylk{'a' if n == 1 else 'i'}: {parts}"

    def shipped_amount_str(self) -> str:
        """Zwraca string z kwotą wysłaną vs. wartość zamówienia np. '3100.00/3900.00 zł'.
        Puste jeśli brak przesyłek."""
        if not self.shipments:
            return ""
        sent = sum(s.amount_pln for s in self.shipments if s.amount_pln is not None)
        total = self.price_total()
        if sent == 0:
            return ""
        return f"{sent:.2f}/{total:.2f} zł"

    def shoe_collection(self) -> MrowkaShoeCollection:
        sc = MrowkaShoeCollection()
        for shoe in self.shoes:
            sc.add_shoe(shoe)
        return sc

    def cancelled_shoe_collection(self) -> MrowkaShoeCollection:
        sc = MrowkaShoeCollection()
        for shoe in self.cancelled_shoes:
            sc.add_shoe(shoe)
        return sc

    def max_size_length(self) -> int:
        return max(shoe.max_size_length() for shoe in self.shoes)

    def to_discord_ticket(self) -> str:
        status = self.history.get_status()
        _mail_part = (" | `" + self.mail.mail + "`") if self.mail else " | `BRAK MAILA`"
        _track_part = (" | `" + self.tracking + "`") if self.tracking else ""
        _date_part = (" | " + str(self.delivery_date)) if self.delivery_date else ""
        _pz_part = (" | 📦 `" + self.pz_sygnatura + "`") if self.pz_sygnatura else ""
        _shipped = self.shipped_amount_str()
        _shipped_part = (" | 🚚 " + _shipped) if _shipped else ""
        return (
            f"{status.status.emoji()} **{self.name}** | {self.price_total():.2f}z\u0142 | {status.status.text()} "
            f"({status.user.name} - {status.timestamp.strftime('%Y-%m-%d %H:%M:%S')})"
            + _mail_part + _track_part + _date_part + _pz_part + _shipped_part
        )

    def to_discord_warehouse(self) -> str:
        shoes_str = "\n".join(shoe.to_discord() for shoe in self.shoes)
        _tracking = ("```" + self.tracking + "```") if self.tracking else "\n"
        _mail = self.mail.to_discord() if self.mail else "Brak wolnych maili"
        _pz = (f"📦 PZ: **{self.pz_sygnatura}**\n") if self.pz_sygnatura else ""
        _shipped = self.shipped_amount_str()
        _shipped_line = (f"🚚 Wyslano: **{_shipped}**\n") if _shipped else ""
        return (
            f"\U0001f6cd\ufe0f Zam\u00f3wienie: **{self.name}**"
            + _tracking
            + f"Cena: **{self.price_total():.2f}z\u0142**\n"
            + _pz
            + _shipped_line
            + f"{self.history.get_status().to_discord()}\n"
            + _mail + "\n"
            + "\n"
            + shoes_str
        )

    def price_total(self) -> float:
        return sum(shoe.price_total() for shoe in self.shoes)

    @logger.async_try_log("")
    async def to_csv(self) -> str:
        sizes: set[str] = set()
        for shoe in self.shoes:
            for size in shoe.size_to_quantity.keys():
                sizes.add(size)

        header: list[str] = ["LINK", "CENA", "LIMIT"] + common.sorted_sizes(sizes)

        lines: list[list[str]] = [header]
        for shoe in self.shoes:
            line: list[str] = [
                shoe.link,
                f"{shoe.og_price:.2f}",
                str(shoe.limit_per_shoe) if shoe.limit_per_shoe < 1000 else "",
            ]

            for size in common.sorted_sizes(sizes):
                quantity = shoe.size_to_quantity.get(size, 0)
                line.append(str(quantity) if quantity > 0 else "")
            lines.append(line)

        widths = [max(len(row[i]) for row in lines) for i in range(len(header))]
        csv_lines: list[str] = [
            " ; ".join(lines[0][i].ljust(widths[i]) for i in range(len(lines[0])))
        ]
        for line in lines[1:]:
            padded_cells = [line[0].ljust(widths[0])]
            padded_cells.extend(line[i].rjust(widths[i]) for i in range(1, len(line)))
            csv_lines.append(" ; ".join(padded_cells))

        csv = "\n".join(csv_lines)
        return await common.save_str_to_file(csv)

    @logger.async_try_log()
    async def _send_warehouse_message(self, bot: commands.Bot, data: "MrowkaData"):
        if self.warehouse_message_id is not None:
            return await self._update_warehouse_message(bot, data)
        status = self.history.get_status()

        if status.status.send_warehouse_message() is False:
            return

        warehouse_channel = await get_warehouse_channel(bot)

        content = self.to_discord_warehouse()
        if len(content) > 1990:
            content = content[:1987] + "..."
        file_path = await self.to_csv()
        file = discord.File(file_path, filename=f"{self.name}.csv")
        message = await warehouse_channel.send(
            bot,
            content=content,
            file=file,
        )
        if message is None:
            raise Exception("message is None")

        self.warehouse_message_id = message.id
        data.message_id_to_order_item_name[message.id] = self.name
        data.message_id_to_ticket_name[message.id] = self.ticket_name
        data.message_id_to_message_type[message.id] = (
            MrowkaMessageType.ORDER_ITEM_STATUS
        )

        await message.add_reaction(bot, "❔")
        for next_status in status.status.next_statuses():
            await message.add_reaction(bot, next_status.emoji())

    @logger.async_try_log()
    async def _update_warehouse_message(self, bot: commands.Bot, data: "MrowkaData"):
        if self.warehouse_message_id is None:
            return await self._send_warehouse_message(bot, data)

        status = self.history.get_status()
        if status.status.send_warehouse_message() is False:
            await self.delete_warehouse_message(bot)
            return

        warehouse_message = await self.get_warehouse_message(bot)

        content = self.to_discord_warehouse()
        file_path = await self.to_csv()
        file = discord.File(file_path, filename=f"{self.name}.csv")
        await warehouse_message.edit(
            bot,
            content=content,
            file=file,
        )

        await warehouse_message.clear_reactions(bot)
        await warehouse_message.add_reaction(bot, "❔")
        for next_status in status.status.next_statuses():
            await warehouse_message.add_reaction(bot, next_status.emoji())

    @logger.async_try_log()
    async def _send_ticket_message(self, bot: commands.Bot, data: "MrowkaData"):
        if self.ticket_message_id is not None:
            return

        ticket_channel = await self.get_ticket_channel(bot)
        message_content = self.to_discord_ticket()
        message = await ticket_channel.send(bot, content=message_content)
        if message is None:
            raise Exception("message is None")

        self.ticket_message_id = message.id
        data.message_id_to_order_item_name[message.id] = self.name
        data.message_id_to_ticket_name[message.id] = self.ticket_name
        data.message_id_to_message_type[message.id] = MrowkaMessageType.TICKET_STATUS

    @logger.async_try_log()
    async def _update_ticket_message(self, bot: commands.Bot, data: "MrowkaData"):
        if self.ticket_message_id is None:
            return await self._send_ticket_message(bot, data)

        ticket_message = await self.get_ticket_message(bot)
        content = self.to_discord_ticket()
        await ticket_message.edit(bot, content=content)

    @logger.try_log()
    def get_faktura_message_content(self) -> str:
        _mail_part = self.mail.to_discord() if self.mail else " | Brak maila"
        return f"\U0001f4c4 {self.name}" + _mail_part

    @logger.async_try_log()
    async def _send_faktura_message(self, bot: commands.Bot, data: "MrowkaData"):
        if self.faktura_message_id is not None:
            await self._update_faktura_message(bot, data)
            return

        status = self.history.get_status()
        if (
            self.faktura is not None
            or status.status != MrowkaOrderItemStatus.ZAMOWIENIE_WYSLANE
        ):
            return

        content = self.get_faktura_message_content()
        faktura_channel = await self.get_faktura_channel(bot)
        message = await faktura_channel.send(bot, content)
        if message is None:
            raise Exception("message is None")

        await message.add_reaction(bot, "👍🏿")
        await message.add_reaction(bot, "👎🏿")
        self.faktura_message_id = message.id
        data.message_id_to_order_item_name[message.id] = self.name
        data.message_id_to_ticket_name[message.id] = self.ticket_name
        data.message_id_to_message_type[message.id] = MrowkaMessageType.FAKTURA_STATUS

    @logger.async_try_log()
    async def _update_faktura_message(
        self,
        bot: commands.Bot,
        data: "MrowkaData",
    ):
        if self.faktura_message_id is None:
            await self._send_faktura_message(bot, data)
            return

        status = self.history.get_status()
        if (
            self.faktura is not None
            or status.status != MrowkaOrderItemStatus.ZAMOWIENIE_WYSLANE
        ):
            faktura_message = await self.get_faktura_message(bot)
            await faktura_message.delete(bot)
            self.faktura_message_id = None
            return

        faktura_message = await self.get_faktura_message(bot)
        content = self.get_faktura_message_content()
        await faktura_message.edit(bot, content)

    @logger.async_try_log()
    async def info(self, bot: commands.Bot):
        ticket_channel = await self.get_ticket_channel(bot)
        content = self.to_discord_warehouse()
        file_path = await self.to_csv()
        file = discord.File(file_path, filename=f"{self.name}.csv")
        await ticket_channel.send(
            bot,
            content=content,
            file=file,
        )

    @logger.async_try_log()
    async def discord_update(self, bot: commands.Bot, data: "MrowkaData"):
        logger.logger.info(
            f"Updating Discord messages for order item {self.name} in ticket {self.ticket_name}"
        )
        ticket = self.get_ticket(data)
        await self._update_ticket_message(bot, data)
        await self._update_warehouse_message(bot, data)
        await self._update_faktura_message(bot, data)
        await ticket.discord_update(bot)

    @logger.async_try_log()
    async def change_status(
        self,
        bot: commands.Bot,
        status: MrowkaOrderItemStatus,
        user: dc.User,
        data: "MrowkaData",
    ):
        self.history.change_status(user, status)
        await self.discord_update(bot, data)

        # Gdy zamówienie potwierdzone → stwórz PZ z potwierdzonymi sztukami
        if status == MrowkaOrderItemStatus.ZAMOWIENIE_POTWIERDZONE:
            import asyncio as _asyncio
            import mrowka_lib as _ml
            _oi = self
            _bot = bot

            async def _on_potwierdzone():
                try:
                    # 1. Odejmij anulowane z PZ jeśli PZ już istnieje (nadzwyczajny przypadek)
                    if _oi.pz_sygnatura:
                        await _ml.remove_cancelled_from_pz(_oi)
                    else:
                        # 2. Stwórz PZ z potwierdzonymi sztukami (self.shoes już bez anulowanych)
                        # Pobierz kanał ticketu przez discord.py
                        ticket_dc_channel = None
                        for guild in _bot.guilds:
                            ticket_dc_channel = guild.get_channel(_oi.ticket_channel_id)
                            if ticket_dc_channel:
                                break
                        if ticket_dc_channel:
                            ticket_channel = dc.channel_from_dc_channel(ticket_dc_channel)
                        else:
                            ticket_channel = None
                        await _ml._create_pz_for_order_item(_bot, ticket_channel, _oi)

                except Exception as _e:
                    logger.logger.warning("on_potwierdzone PZ error: %s", _e)

            _asyncio.create_task(_on_potwierdzone())



    def get_ticket(self, data: "MrowkaData") -> "MrowkaTicket":
        return data.tickets[self.ticket_name]

    @logger.async_try_log(
        dc.Message(id=-1, content=None, author=dc.User(id=-1, name=""), channel=None)
    )
    async def get_warehouse_message(self, bot: commands.Bot) -> dc.Message:
        if self.warehouse_message_id is None:
            raise Exception("self.warehouse_message_id is None")

        warehouse_channel = await get_warehouse_channel(bot)
        message = await warehouse_channel.fetch_message(bot, self.warehouse_message_id)
        if message is None:
            raise Exception("warehouse_message is None")
        return message

    @logger.async_try_log(dc.Channel(id=-1, name=""))
    async def get_faktura_channel(self, bot: commands.Bot) -> dc.Channel:
        return await dc.channel_from_name(bot, "faktury")

    @logger.async_try_log(
        dc.Message(id=-1, content=None, author=dc.User(id=-1, name=""), channel=None)
    )
    async def get_faktura_message(self, bot: commands.Bot) -> dc.Message:
        if self.faktura_message_id is None:
            raise Exception("self.faktura_message_id is None")

        faktura_channel = await self.get_faktura_channel(bot)
        faktura_message = await faktura_channel.fetch_message(
            bot, self.faktura_message_id
        )
        if faktura_message is None:
            raise Exception("faktura_message is None")
        return faktura_message

    @logger.async_try_log(
        dc.Message(id=-1, content=None, author=dc.User(id=-1, name=""), channel=None)
    )
    async def get_ticket_message(self, bot: commands.Bot) -> dc.Message:
        if self.ticket_message_id is None:
            raise Exception("self.ticket_message_id is None")

        target_channel = await self.get_ticket_channel(bot)
        ticket_message = await target_channel.fetch_message(bot, self.ticket_message_id)
        if ticket_message is None:
            raise Exception("ticket_message is None")
        return ticket_message

    @logger.async_try_log(dc.Channel(id=-1, name=""))
    async def get_ticket_channel(self, bot: commands.Bot) -> dc.Channel:
        return await dc.channel_from_name(bot, self.ticket_name)

    @logger.async_try_log()
    async def delete_warehouse_message(self, bot: commands.Bot):
        if self.warehouse_message_id is None:
            return

        warehouse_message = await self.get_warehouse_message(bot)
        await warehouse_message.delete(bot)
        self.warehouse_message_id = None

    async def anuluj(
        self,
        bot: commands.Bot,
        user: dc.User,
        data: "MrowkaData",
    ):
        current_status = self.history.get_status()
        if current_status.status == MrowkaOrderItemStatus.W_TRAKCIE_ZAMAWIANIA:
            content = (
                f"⚠️ Zamówienie {self.name} zostało anulowane, przestań je zamawiać ⚠️"
            )
            await current_status.user.send(bot, content)

        await self.change_status(
            bot,
            current_status.status.anuluj(),
            user,
            data,
        )

    @logger.async_try_log()
    async def cofnij(
        self,
        bot: commands.Bot,
        user: dc.User,
        step: Optional[int],
        data: "MrowkaData",
    ):
        if step is None:
            step = len(self.history.entries) - 2
        else:
            step -= 1
        if step < 0 or step >= len(self.history.entries):
            await user.send(
                bot,
                f"⚠️ Nie można cofnąć zamówienia {self.name} do kroku {step+1} ⚠️\n"
                f"{common.HELP_COFNIJ}",
            )
            return

        new_status = self.history.entries[step].status
        await self.change_status(bot, new_status, user, data)

    async def zrealizuj(self, bot: commands.Bot, user: dc.User, data: "MrowkaData"):
        await self.change_status(
            bot,
            MrowkaOrderItemStatus.ZAMOWIENIE_ZOSTALO_ZREALIZOWANE,
            user,
            data,
        )

    @logger.async_try_log()
    async def update_shoes(
        self,
        bot: commands.Bot,
        shoe_collection: MrowkaShoeCollection,
        user: dc.User,
        data: "MrowkaData",
    ) -> Optional[str]:
        old_shoes_to_cancelled = self.shoe_collection()
        for shoe in shoe_collection:
            if shoe.link not in old_shoes_to_cancelled.shoes:
                return (
                    f"⚠️ But o linku {shoe.link} nie istnieje w zamówieniu {self.name}."
                )
            if not shoe.leq(old_shoes_to_cancelled.shoes[shoe.link]):
                return f"⚠️ Nie można zwiększyć ilości butów o linku {shoe.link} w zamówieniu {self.name}."
            old_shoes_to_cancelled.minus(shoe)

        self.shoes = list(shoe_collection.shoes.values())
        old_shoes_to_cancelled.plus(self.cancelled_shoe_collection())
        self.cancelled_shoes = list(old_shoes_to_cancelled.shoes.values())

        await self.discord_update(bot, data)
        return None

    @logger.async_try_log()
    async def podmien_mail(self, bot: commands.Bot, data: "MrowkaData"):
        self.mail = await mails.get_unused_mail()
        await self.discord_update(bot, data)

    def __str__(self) -> str:
        return pprint.pformat(dataclasses.asdict(self), indent=4)

    def __repr__(self) -> str:
        return self.__str__()


@dataclasses.dataclass
class MrowkaTicket:
    name: str
    owner: dc.User
    divided_orders: dict[str, MrowkaOrderItem]
    created_at: datetime.datetime
    guild_id: int
    ticket_channel_id: int
    remainder_14_day_sent: bool = False
    remainder_21_day_sent: bool = False
    all_potwierdzone_sent: bool = False
    all_wyslane_sent: bool = False
    all_zrealizowane_sent: bool = False
    all_anulowane_sent: bool = False

    async def discord_update(self, bot: commands.Bot):
        await self.oczekujace(bot)
        await self.potwierdzone(bot)
        await self.wyslane(bot)
        await self.zrealizowane(bot)
        await self.anulowane(bot)

    def shoe_collection(self) -> MrowkaShoeCollection:
        sc = MrowkaShoeCollection()
        for order_item in self.divided_orders.values():
            sc.add_sc(order_item.shoe_collection())
        return sc

    def cancelled_shoe_collection(self) -> MrowkaShoeCollection:
        sc = MrowkaShoeCollection()
        for order_item in self.divided_orders.values():
            sc.add_sc(order_item.cancelled_shoe_collection())
        return sc

    def max_size_length(self) -> int:
        return self.shoe_collection().max_size_length()

    def price_total(self) -> float:
        return self.shoe_collection().price_total()

    def get_oczekujace(self, shoe: MrowkaShoeInfo) -> MrowkaShoeInfo:
        oczekujace = shoe.deepcopy()
        oczekujace.size_to_quantity = {}
        for order_item in self.divided_orders.values():
            if (
                order_item.history.get_status().status.get_status()
                != MrowkaOrderItemStatusStatus.OCZEKUJACE
            ):
                continue
            for order_item_shoe in order_item.shoes:
                if order_item_shoe.link != shoe.link:
                    continue
                oczekujace = oczekujace.plus(order_item_shoe)
        return oczekujace

    def get_potwierdzone(self, shoe: MrowkaShoeInfo) -> MrowkaShoeInfo:
        potwierdzone = shoe.deepcopy()
        potwierdzone.size_to_quantity = {}
        for order_item in self.divided_orders.values():
            if (
                order_item.history.get_status().status.get_status()
                != MrowkaOrderItemStatusStatus.POTWIERDZONE
            ):
                continue
            for order_item_shoe in order_item.shoes:
                if order_item_shoe.link != shoe.link:
                    continue
                potwierdzone = potwierdzone.plus(order_item_shoe)
        return potwierdzone

    def get_anulowane(self, shoe: MrowkaShoeInfo) -> MrowkaShoeInfo:
        oczekujace = self.get_oczekujace(shoe)
        potwierdzone = self.get_potwierdzone(shoe)
        anulowane = shoe.minus(oczekujace).minus(potwierdzone)
        return anulowane

    @logger.async_try_log("")
    async def to_csv(self) -> str:
        sc = self.shoe_collection()
        sizes = sc.sizes()

        header: list[str] = ["LINK", "CENA", "LIMIT"] + common.sorted_sizes(sizes)

        lines: list[list[str]] = [header]
        for shoe in sc:
            line: list[str] = [
                shoe.link,
                f"{shoe.og_price:.2f}",
                str(shoe.limit_per_shoe) if shoe.limit_per_shoe < 1000 else "",
            ]

            for size in common.sorted_sizes(sizes):
                quantity = shoe.size_to_quantity.get(size, 0)
                line.append(str(quantity) if quantity > 0 else "")
            lines.append(line)

        widths = [max(len(row[i]) for row in lines) for i in range(len(header))]
        csv_lines: list[str] = [
            " ; ".join(lines[0][i].ljust(widths[i]) for i in range(len(lines[0])))
        ]
        for line in lines[1:]:
            padded_cells = [line[0].ljust(widths[0])]
            padded_cells.extend(line[i].rjust(widths[i]) for i in range(1, len(line)))
            csv_lines.append(" ; ".join(padded_cells))

        csv = "\n".join(csv_lines)
        return await common.save_str_to_file(csv)

    @logger.async_try_log("")
    async def to_status_csv(self) -> str:
        sc = self.shoe_collection()
        sc.plus(self.cancelled_shoe_collection())
        sizes = sc.sizes()

        header: list[str] = ["LINK / STATUS"] + common.sorted_sizes(sizes)
        lines: list[list[str]] = [header]
        for shoe in sc:
            line: list[str] = [shoe.link]
            for size in common.sorted_sizes(sizes):
                quantity = shoe.size_to_quantity.get(size, 0)
                line.append(str(quantity) if quantity > 0 else "")
            lines.append(line)

            oczekujace = self.get_oczekujace(shoe)
            line = ["Oczekujące"]
            for size in common.sorted_sizes(sizes):
                quantity = oczekujace.size_to_quantity.get(size, 0)
                line.append(str(quantity) if quantity > 0 else "")
            lines.append(line)

            potwierdzone = self.get_potwierdzone(shoe)
            line = ["Potwierdzone"]
            for size in common.sorted_sizes(sizes):
                quantity = potwierdzone.size_to_quantity.get(size, 0)
                line.append(str(quantity) if quantity > 0 else "")
            lines.append(line)

            anulowane = self.get_anulowane(shoe)
            line = ["Anulowane"]
            for size in common.sorted_sizes(sizes):
                quantity = anulowane.size_to_quantity.get(size, 0)
                line.append(str(quantity) if quantity > 0 else "")
            lines.append(line)

        widths = [max(len(row[i]) for row in lines) for i in range(len(header))]
        csv_lines: list[str] = [
            " ; ".join(lines[0][i].ljust(widths[i]) for i in range(len(lines[0])))
        ]
        for line in lines[1:]:
            padded_cells = [line[0].ljust(widths[0])]
            padded_cells.extend(line[i].rjust(widths[i]) for i in range(1, len(line)))
            csv_lines.append(" ; ".join(padded_cells))
        csv = "\n".join(csv_lines)
        return await common.save_str_to_file(csv)

    @logger.async_try_log()
    async def update_divided_orders(
        self,
        bot: commands.Bot,
        shoe_collection: MrowkaShoeCollection,
        user: dc.User,
        data: "MrowkaData",
    ):
        while True:
            new_order_item = await shoe_collection.take_one_order_item(
                name=f"{self.name}-{len(self.divided_orders) + 1:02d}",
                ticket_name=self.name,
                ticket_channel_id=self.ticket_channel_id,
                guild_id=self.guild_id,
                user=user,
            )
            if new_order_item is None:
                break
            self.divided_orders[new_order_item.name] = new_order_item
            await new_order_item.discord_update(bot, data)

    @logger.async_try_log()
    async def send_ticket_csv_message(self, bot: commands.Bot):
        file_path = await self.to_csv()
        file = discord.File(file_path, filename=f"{self.name}.csv")

        channel = await self.get_ticket_channel(bot)
        await channel.send(bot, file=file)

    @logger.async_try_log()
    async def send_ticket_csv_status_message(self, bot: commands.Bot):
        file_path = await self.to_status_csv()
        file = discord.File(file_path, filename=f"{self.name}_status.csv")

        channel = await self.get_ticket_channel(bot)
        await channel.send(bot, file=file)

    @logger.async_try_log()
    async def send_ean_message(
        self, bot: commands.Bot, data: "MrowkaData", file_path: str
    ):
        file = discord.File(file_path, filename=f"{self.name}.xlsx")
        channel = await dc.channel_from_name(bot, "importy-do-subiekta")

        message = await channel.send(
            bot, content="💾 Wgraj ten plik do Subiekta i dodaj reakcję 👍", file=file
        )
        if message is None:
            raise Exception("message is None")
        await message.add_reaction(bot, "👍")

        data.message_id_to_ticket_name[message.id] = self.name
        data.message_id_to_message_type[message.id] = MrowkaMessageType.EAN_MESSAGE

    @logger.async_try_log()
    async def send_ean_plik_wgrany(self, bot: commands.Bot):
        channel = await self.get_ticket_channel(bot)
        await channel.send(
            bot,
            content=f"💾 Plik z EANami został wgrany do Subiekta 💾",
        )

    @logger.async_try_log(dc.Channel(id=-1, name=""))
    async def get_ticket_channel(self, bot: commands.Bot) -> dc.Channel:
        return await dc.channel_from_name(bot, self.name)

    @logger.async_try_log()
    async def send_14_day_reminder(self, bot: commands.Bot):
        if self.remainder_14_day_sent:
            return
        if (datetime.datetime.now() - self.created_at).days < 14:
            return
        if all(
            order_item.history.get_status().status.get_status()
            in [
                MrowkaOrderItemStatusStatus.POTWIERDZONE,
                MrowkaOrderItemStatusStatus.ANULOWANE,
            ]
            for order_item in self.divided_orders.values()
        ):
            return

        channel = await self.get_ticket_channel(bot)
        await channel.send(
            bot,
            content=f"⏰ Przypomnienie: Minęło 14 dni od utworzenia ticketu, a nadal są oczekujące zamówienia. {self.owner.mention()}",
        )
        self.remainder_14_day_sent = True

    @logger.async_try_log()
    async def send_21_day_reminder(self, bot: commands.Bot):
        if self.remainder_21_day_sent:
            return
        if (datetime.datetime.now() - self.created_at).days < 21:
            return
        if all(
            order_item.history.get_status().status.get_status()
            in [
                MrowkaOrderItemStatusStatus.POTWIERDZONE,
                MrowkaOrderItemStatusStatus.ANULOWANE,
            ]
            for order_item in self.divided_orders.values()
        ):
            return

        channel = await self.get_ticket_channel(bot)
        await channel.send(
            bot,
            content=f"⏰ Przypomnienie: Minęło 21 dni od utworzenia ticketu, a nadal są oczekujące zamówienia. {self.owner.mention()}",
        )
        self.remainder_21_day_sent = True

    @logger.async_try_log()
    async def oczekujace(self, bot: commands.Bot):
        if len(self.divided_orders) != 0 and all(
            order_item.history.get_status().status.get_status()
            != MrowkaOrderItemStatusStatus.OCZEKUJACE
            for order_item in self.divided_orders.values()
        ):
            return

        channel = await self.get_ticket_channel(bot)
        category = await dc.category_from_name(bot, f"Oczekujące - {self.owner.name}")
        await channel.edit(bot, category=category)

    @logger.async_try_log()
    async def potwierdzone(self, bot: commands.Bot):
        if self.all_potwierdzone_sent:
            return
        if any(
            order_item.history.get_status().status.get_status()
            == MrowkaOrderItemStatusStatus.OCZEKUJACE
            for order_item in self.divided_orders.values()
        ):
            return
        if all(
            order_item.history.get_status().status.get_status()
            == MrowkaOrderItemStatusStatus.ANULOWANE
            for order_item in self.divided_orders.values()
        ):
            return

        channel = await self.get_ticket_channel(bot)
        category = await dc.category_from_name(bot, f"Potwierdzone - {self.owner.name}")
        await channel.edit(bot, category=category)
        await channel.send(
            bot,
            content=f"{MrowkaOrderItemStatus.ZAMOWIENIE_POTWIERDZONE.emoji()} Wszystkie zamówienia zostały potwierdzone! {self.owner.mention()}",
        )
        self.all_potwierdzone_sent = True

        # Automatycznie utwórz ZK (Zamówienie od Klienta) w Subiekcie
        async def _create_zk_task():
            import mrowka_lib as _ml
            zk_num = None
            zk_error = None
            try:
                zk_num = await _ml.create_zk_for_ticket(self)
                if channel:
                    await channel.send(
                        bot,
                        f"📋 ZK **{zk_num}** utworzone w Subiekcie (klient: `zmien_nazwe`, waluta: EUR)",
                    )
                logger.logger.info("ZK created for ticket %s: %s", self.name, zk_num)
            except Exception as e:
                zk_error = str(e)
                logger.logger.warning("CreateZK failed for ticket %s: %s", self.name, e)
                if channel:
                    await channel.send(
                        bot,
                        f"⚠️ Nie udało się automatycznie stworzyć ZK: `{e}`\nUtwórz ręcznie.",
                    )
            # Wyślij zadanie do kanału zadania-{owner}
            try:
                await _ml.send_zadanie_potwierdzenie(bot, self, zk_num, zk_error)
            except Exception as e2:
                logger.logger.warning("send_zadanie failed for ticket %s: %s", self.name, e2)

        import asyncio as _asyncio
        _asyncio.create_task(_create_zk_task())

    @logger.async_try_log()
    async def wyslane(self, bot: commands.Bot):
        if self.all_wyslane_sent:
            return
        if any(
            order_item.history.get_status().status.get_status()
            == MrowkaOrderItemStatusStatus.OCZEKUJACE
            for order_item in self.divided_orders.values()
        ):
            return
        if all(
            order_item.history.get_status().status.get_status()
            == MrowkaOrderItemStatusStatus.ANULOWANE
            for order_item in self.divided_orders.values()
        ):
            return
        if any(
            order_item.history.get_status().status
            == MrowkaOrderItemStatus.ZAMOWIENIE_POTWIERDZONE
            for order_item in self.divided_orders.values()
        ):
            return

        channel = await self.get_ticket_channel(bot)
        category = await dc.category_from_name(bot, f"Wysłane - {self.owner.name}")
        await channel.edit(bot, category=category)
        await channel.send(
            bot,
            content=f"{MrowkaOrderItemStatus.ZAMOWIENIE_WYSLANE.emoji()} Wszystkie zamówienia zostały wysłane! {self.owner.mention()}",
        )
        self.all_wyslane_sent = True

    @logger.async_try_log()
    async def zrealizowane(self, bot: commands.Bot):
        if self.all_zrealizowane_sent:
            return
        if any(
            order_item.history.get_status().status.get_status()
            == MrowkaOrderItemStatusStatus.OCZEKUJACE
            for order_item in self.divided_orders.values()
        ):
            return
        if all(
            order_item.history.get_status().status.get_status()
            == MrowkaOrderItemStatusStatus.ANULOWANE
            for order_item in self.divided_orders.values()
        ):
            return
        if any(
            order_item.history.get_status().status
            == MrowkaOrderItemStatus.ZAMOWIENIE_POTWIERDZONE
            for order_item in self.divided_orders.values()
        ):
            return
        if any(
            order_item.history.get_status().status
            == MrowkaOrderItemStatus.ZAMOWIENIE_WYSLANE
            for order_item in self.divided_orders.values()
        ):
            return

        channel = await self.get_ticket_channel(bot)
        category = await dc.category_from_name(bot, f"Zrealizowane - {self.owner.name}")
        await channel.edit(bot, category=category)
        await channel.send(
            bot,
            content=f"{MrowkaOrderItemStatus.ZAMOWIENIE_ZOSTALO_ZREALIZOWANE.emoji()} Wszystkie zamówienia zostały zrealizowane! {self.owner.mention()}",
        )
        self.all_zrealizowane_sent = True
        await self.sukces(bot)  # → archiwum sukcesu (CATEGORY_SUKCES)

    @logger.async_try_log()
    async def anulowane(self, bot: commands.Bot):
        if self.all_anulowane_sent:
            return
        if len(self.divided_orders) == 0 or any(
            order_item.history.get_status().status.get_status()
            != MrowkaOrderItemStatusStatus.ANULOWANE
            for order_item in self.divided_orders.values()
        ):
            return

        channel = await self.get_ticket_channel(bot)
        category = await dc.category_from_name(bot, f"Anulowane - {self.owner.name}")
        await channel.edit(bot, category=category)
        await channel.send(
            bot,
            content=f"{MrowkaOrderItemStatus.ZAMOWIENIE_ANULOWANE_RECZNIE.emoji()} Wszystkie zamówienia zostały anulowane! {self.owner.mention()}",
        )
        self.all_anulowane_sent = True

    @logger.async_try_log()
    async def sukces(self, bot: commands.Bot):
        channel = await self.get_ticket_channel(bot)
        sukces_category = await dc.CATEGORY_SUKCES(bot)
        await channel.edit(bot, category=sukces_category)

    @logger.async_try_log()
    async def porazka(self, bot: commands.Bot):
        channel = await self.get_ticket_channel(bot)
        porazka_category = await dc.CATEGORY_PORAZKA(bot)
        await channel.edit(bot, category=porazka_category)

    def __str__(self) -> str:
        return pprint.pformat(dataclasses.asdict(self), indent=4)

    def __repr__(self) -> str:
        return self.__str__()


@dataclasses.dataclass
class MrowkaData:
    tickets: dict[str, MrowkaTicket] = dataclasses.field(default_factory=dict)
    message_id_to_ticket_name: dict[int, str] = dataclasses.field(default_factory=dict)
    message_id_to_order_item_name: dict[int, str] = dataclasses.field(
        default_factory=dict
    )
    message_id_to_message_type: dict[int, MrowkaMessageType] = dataclasses.field(
        default_factory=dict
    )
    daily_messages_sent: set[datetime.date] = dataclasses.field(default_factory=set)
    daily_messages_to_send: set[datetime.date] = dataclasses.field(default_factory=set)
    tracking_to_order_item_name: dict[str, str] = dataclasses.field(
        default_factory=dict
    )
    interia_error_message_id_to_mail: dict[int, str] = dataclasses.field(
        default_factory=dict
    )

    def __post_init__(self):
        def parse_date_set(val) -> set[datetime.date]:
            if isinstance(val, set):
                return val
            if isinstance(val, list):
                ret = set()
                for v in val:
                    if isinstance(v, str):
                        try:
                            ret.add(datetime.date.fromisoformat(v))
                        except ValueError:
                            pass
                return ret
            if isinstance(val, str):
                if val == "set()":
                    return set()
                import re
                dates = re.findall(r"datetime\.date\((\d+),\s*(\d+),\s*(\d+)\)", val)
                ret = set()
                for y, m, d in dates:
                    ret.add(datetime.date(int(y), int(m), int(d)))
                return ret
            return set()

        self.daily_messages_sent = parse_date_set(self.daily_messages_sent)
        self.daily_messages_to_send = parse_date_set(self.daily_messages_to_send)

    async def update_trackings_from_csv(
        self,
        bot: commands.Bot,
        file_path: str,
        user: dc.User,
    ) -> tuple[int, list[str]]:
        tracking_map = await order_item_name_to_tracking_from_csv(file_path)

        updated_count = 0
        fails = []
        for order_item_name, tracking in tracking_map.items():
            order_item = self.get_order_item(order_item_name)
            if order_item is None:
                fails.append(order_item_name)
                continue

            order_item.tracking = tracking
            await order_item.change_status(
                bot,
                MrowkaOrderItemStatus.ZAMOWIENIE_WYSLANE,
                user,
                self,
            )
            self.tracking_to_order_item_name[tracking] = order_item_name
            updated_count += 1
        return updated_count, fails

    @logger.try_log(None)
    def get_order_item(self, order_item_name: str) -> Optional[MrowkaOrderItem]:
        ticket_name = order_item_name_to_ticket_name(order_item_name)
        ticket = self.tickets[ticket_name]
        order_item = ticket.divided_orders[order_item_name]
        return order_item

    @logger.try_log("Błąd podczas generowania podsumowania dnia.")
    def daily_message_str(
        self,
        date: datetime.date,
    ) -> str:
        prices: dict[MrowkaOrderItemStatusStatus, float] = {
            MrowkaOrderItemStatusStatus.OCZEKUJACE: 0.0,
            MrowkaOrderItemStatusStatus.POTWIERDZONE: 0.0,
            MrowkaOrderItemStatusStatus.ANULOWANE: 0.0,
        }

        for ticket in self.tickets.values():
            if ticket.created_at.date() != date:
                continue

            for order_item in ticket.divided_orders.values():
                status = order_item.history.get_status().status.get_status()
                prices[status] += order_item.price_total()

        content = f"📆 Podsumowanie dnia: {date.strftime('%Y-%m-%d')}\n"
        content += "💰 Ceny zamówień rozpoczętych tego dnia według statusów:\n"
        for status in sorted(prices.keys(), key=lambda s: s.value):
            content += f"{status.emoji()} {status.text()}: {prices[status]:.2f}zł\n"
        return content

    @logger.async_try_log("")
    async def to_daily_csv(self, date: datetime.date) -> str:
        header: list[str] = [
            "MAIL",
            "HASŁO ZALANDO",
            "KOD",
            "CENA",
            "TRACKING",
            "NAZWA ZAMÓWIENIA",
        ]
        lines: list[list[str]] = [header]
        for ticket in self.tickets.values():
            if ticket.created_at.date() != date:
                continue

            for order_item in ticket.divided_orders.values():
                line: list[str] = [
                    order_item.mail.mail if order_item.mail else "",
                    order_item.mail.zalando_pass if order_item.mail else "",
                    order_item.mail.code if order_item.mail else "",
                    f"{order_item.price_total():.2f} zł",
                    order_item.tracking if order_item.tracking else "",
                    order_item.name,
                ]
                lines.append(line)


        csv_lines: list[str] = []
        for line in lines:
            csv_lines.append(";".join(line))

        csv = "\n".join(csv_lines)
        return await common.save_str_to_file(csv)

    @logger.async_try_log()
    async def send_daily_messages(
        self,
        bot: commands.Bot,
    ):
        today = datetime.date.today()
        for date in sorted(self.daily_messages_to_send - self.daily_messages_sent):
            if date >= today:
                continue

            content = self.daily_message_str(date)
            for co_user in dc.get_daily_message_users(bot):
                user = await co_user
                file_path = await self.to_daily_csv(date)
                file = discord.File(file_path, filename=f"trackings_{date}.csv")
                await user.send(bot, content=content, file=file)

            self.daily_messages_sent.add(date)

    @logger.async_try_log()
    async def send_reminders(self, bot: commands.Bot):
        for ticket in self.tickets.values():
            await ticket.send_14_day_reminder(bot)
            await ticket.send_21_day_reminder(bot)

    def __str__(self) -> str:
        return pprint.pformat(dataclasses.asdict(self), indent=4)

    def __repr__(self) -> str:
        return self.__str__()


@logger.try_log("")
def order_item_name_to_ticket_name(order_item_name: str) -> str:
    return order_item_name.split("-")[0]


@logger.async_try_log({})
async def order_item_name_to_tracking_from_csv(file_path: str) -> dict[str, str]:
    async with aiofiles.open(file_path, "r") as f:
        lines = await f.readlines()

    tracking_map: dict[str, str] = {}
    for line in lines[1:]:
        splitted_line = line.strip().split(";")
        order_item_name = splitted_line[5].strip()
        tracking = splitted_line[4].strip()
        if order_item_name != "" and tracking != "":
            tracking_map[order_item_name] = tracking

    return tracking_map


@logger.async_try_log(dc.Channel(id=-1, name=""))
async def get_warehouse_channel(bot: commands.Bot) -> dc.Channel:
    return await dc.channel_from_name(bot, "magazynierzy")


PisarzMrowka = common.AsyncJsonFileMonitor(MrowkaData, "storage/orders.pkl")
