import imaplib, email
from email.header import decode_header

conn = imaplib.IMAP4_SSL('imap.gmail.com', 993)
conn.login('eleatowskiedomeny@gmail.com', 'mvjq ljhg vnau kksk')
conn.select('INBOX', readonly=True)

# Pobierz treść emaila ID 1467 — "Twoja przesyłka zostanie dostarczona"
_, data = conn.fetch(b'1511', '(RFC822)')
msg = email.message_from_bytes(data[0][1])

raw_subj = msg.get('Subject', '')
parts = decode_header(raw_subj)
subj = ''.join(p.decode(enc or 'utf-8', errors='ignore') if isinstance(p, bytes) else str(p) for p, enc in parts)
print(f'FROM: {msg.get("From")}')
print(f'TO:   {msg.get("To")}')
print(f'SUBJ: {subj}')
print('=' * 60)

# Treść plain-text
for part in msg.walk():
    if part.get_content_type() == 'text/plain':
        payload = part.get_payload(decode=True)
        charset = part.get_content_charset() or 'utf-8'
        print(payload.decode(charset, errors='ignore')[:4000])
        break

conn.logout()
