import imaplib, email
from email.header import decode_header

conn = imaplib.IMAP4_SSL('imap.gmail.com', 993)
conn.login('eleatowskiedomeny@gmail.com', 'mvjq ljhg vnau kksk')
conn.select('INBOX', readonly=True)

_, ids = conn.search(None, 'FROM "zalando"')
all_ids = ids[0].split()

# Szukaj maili z "dostarczone" w temacie
hits = []
for num in all_ids:
    _, data = conn.fetch(num, '(RFC822.HEADER)')
    msg = email.message_from_bytes(data[0][1])
    raw_subj = msg.get('Subject', '')
    parts = decode_header(raw_subj)
    subj = ''
    for p, enc in parts:
        if isinstance(p, bytes): subj += p.decode(enc or 'utf-8', errors='ignore')
        else: subj += str(p)
    if any(kw in subj.lower() for kw in ['dostarczon', 'deliver', 'wyslan', 'shipped', 'wyslane']):
        hits.append((num, subj, msg.get('To', ''), msg.get('Date', '')))

print(f'Znaleziono: {len(hits)} maili')
for num, subj, to, date in hits[-5:]:
    print(f'--- ID {num.decode()} ---')
    print(f'TO:   {to}')
    print(f'SUBJ: {subj}')
    print(f'DATE: {date}')

conn.logout()
