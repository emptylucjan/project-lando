import imaplib, email
from email.header import decode_header
import quopri

MAIL_IDS = [b'1534']  # Faktura mail

conn = imaplib.IMAP4_SSL('imap.gmail.com', 993)
conn.login('eleatowskiedomeny@gmail.com', 'mvjq ljhg vnau kksk')
conn.select('INBOX', readonly=True)

for mid in MAIL_IDS:
    _, data = conn.fetch(mid, '(RFC822)')
    msg = email.message_from_bytes(data[0][1])

    # Temat
    raw_subj = msg.get('Subject', '')
    parts = decode_header(raw_subj)
    subj = ''
    for p, enc in parts:
        if isinstance(p, bytes): subj += p.decode(enc or 'utf-8', errors='ignore')
        else: subj += str(p)

    print(f'FROM: {msg.get("From")}')
    print(f'TO:   {msg.get("To")}')
    print(f'SUBJ: {subj}')
    print(f'DATE: {msg.get("Date")}')
    print('=' * 60)

    # Treść
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == 'text/plain':
                payload = part.get_payload(decode=True)
                charset = part.get_content_charset() or 'utf-8'
                print(payload.decode(charset, errors='ignore')[:3000])
                break
    else:
        payload = msg.get_payload(decode=True)
        charset = msg.get_content_charset() or 'utf-8'
        print(payload.decode(charset, errors='ignore')[:3000])

conn.logout()
