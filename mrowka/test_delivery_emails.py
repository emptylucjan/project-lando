"""
test_delivery_emails.py — szybki test wyciągania info z maili "Twoja przesyłka"
Używa SUBJECT SEARCH w IMAP (serwerowe filtrowanie — bez pobierania wszystkich maili)
"""
import imaplib
import email
import json
import pathlib
import sys
from email.header import decode_header

IMAP_SERVER = "imap.gmail.com"
IMAP_PORT = 993

def decode_val(value):
    if not value:
        return ""
    parts = decode_header(value)
    out = ""
    for part, enc in parts:
        if isinstance(part, bytes):
            out += part.decode(enc or "utf-8", errors="ignore")
        else:
            out += str(part)
    return out

config = json.loads(pathlib.Path("config.json").read_text(encoding="utf-8"))
account = config["gmail_accounts"][0]
email_addr = account["email"]
app_password = account["app_password"]

print(f"Łączę z {email_addr}...")
mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
mail.login(email_addr, app_password)
mail.select("INBOX", readonly=True)

# Szukaj po nadawcy Zalando — pomijamy problem z polskimi znakami w IMAP
_, data = mail.search(None, 'FROM "zalando"')
ids = data[0].split()
print(f"Znaleziono {len(ids)} maili od Zalando")

# Pobierz ostatnie 20 i szukaj "dostarczona" w temacie
found = 0
for num in ids[-20:]:
    _, msg_data = mail.fetch(num, "(RFC822.HEADER)")
    msg = email.message_from_bytes(msg_data[0][1])
    
    subject = decode_val(msg.get("Subject", ""))
    to = decode_val(msg.get("To", ""))
    date = decode_val(msg.get("Date", ""))
    
    if "dostarczona" in subject.lower() or "przesyk" in subject.lower() or "przesy" in subject.lower():
        print(f"\n✅ MAIL DOSTAWCZY:")
        print(f"   Temat: {subject[:80]}")
        print(f"   Do:    {to}")
        print(f"   Data:  {date}")
        found += 1
    else:
        # Pokaż pierwsze kilka tematów żeby zobaczyć co mamy
        if num == ids[-1]:
            print(f"\nOstatni mail od Zalando:")
            print(f"   Temat: {subject[:80]}")
            print(f"   Do:    {to}")

print(f"\nŁącznie znaleziono: {found} maili dostawczych")
mail.logout()

