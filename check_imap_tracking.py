import imaplib, email, re
from email.header import decode_header

conn = imaplib.IMAP4_SSL('imap.gmail.com', 993)
conn.login('eleatowskiedomeny@gmail.com', 'mvjq ljhg vnau kksk')
conn.select('INBOX', readonly=True)

_, data = conn.fetch(b'1511', '(RFC822)')
msg = email.message_from_bytes(data[0][1])

# Pobierz HTML
html_body = None
for part in msg.walk():
    if part.get_content_type() == 'text/html':
        payload = part.get_payload(decode=True)
        charset = part.get_content_charset() or 'utf-8'
        html_body = payload.decode(charset, errors='ignore')
        break

if html_body:
    # Szukaj linków trackingowych (DHL, DPD, InPost, GLS, Poczta Polska)
    track_patterns = [
        r'inpost\.pl[^\s"<]*',
        r'dhl\.com[^\s"<]*',
        r'dpd\.com[^\s"<]*',
        r'gls-group\.eu[^\s"<]*',
        r'paczkownia[^\s"<]*',
        r'tracking[^\s"<]{0,100}',
        r'sledz[^\s"<]{0,100}',
        r'[Śś]led[żź][^\s"<]{0,100}',
        r'numer.*?([0-9]{10,30})',
    ]
    found = set()
    for pat in track_patterns:
        matches = re.findall(pat, html_body, re.IGNORECASE)
        for m in matches:
            if len(m) > 5:
                found.add(m[:120])
    
    print("=== Linki/numery trackingowe ===")
    for f in sorted(found)[:20]:
        print(f)
    
    # Pokaż fragment HTML wokół słowa "śledź" / "tracking"
    print("\n=== Fragment z 'sledz' ===")
    idx = html_body.lower().find('sledz')
    if idx == -1:
        idx = html_body.lower().find('śledź')
    if idx >= 0:
        print(html_body[max(0,idx-100):idx+500])
else:
    print("Brak HTML — może tylko plain text")

conn.logout()
