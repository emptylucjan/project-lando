import pdfplumber, re

pdf_path = r"C:\Users\lukko\Desktop\projekt zalando\Invoice-10910151062396.pdf"

all_text = ""
with pdfplumber.open(pdf_path) as pdf:
    for i, page in enumerate(pdf.pages):
        # Extract words with positions sorted by Y then X
        words = page.extract_words(x_tolerance=5, y_tolerance=5)
        # Group by Y position (row)
        rows = {}
        for w in words:
            y = round(w['top'] / 5) * 5  # bucket by 5px
            rows.setdefault(y, []).append(w['text'])
        
        text_lines = []
        for y in sorted(rows.keys()):
            text_lines.append(' '.join(rows[y]))
        
        page_text = '\n'.join(text_lines)
        all_text += page_text + '\n'
        print(f"\n{'='*60}")
        print(f"STRONA {i+1}:")
        print(f"{'='*60}")
        print(page_text)

print("\n\n" + "="*60)
print("SZUKAM KLUCZOWYCH DANYCH:")
print("="*60)

# Numer zamówienia
m = re.search(r'Numer\s+zam[oó]wienia\s*[:\s]+(\d+)', all_text, re.IGNORECASE)
print(f"Numer zam: {m.group(1) if m else 'NIE ZNALEZIONO'}")

# Numer faktury (różne formaty Zalando)
for pat in [
    r'Numer\s+rachunku\s*[:\s]+([A-Z0-9/-]+)',
    r'Faktura\s+VAT\s+([A-Z0-9/-]+)',
    r'Nr\s+faktury\s*[:\s]+([A-Z0-9/-]+)',
    r'[A-Z]{2,}\d{4,}',  # np. PL100401677550
]:
    m = re.search(pat, all_text, re.IGNORECASE)
    if m:
        print(f"Numer FV ({pat[:20]}): {m.group(1) if m.lastindex else m.group(0)}")

# Data
for pat in [
    r'(\d{1,2}[./]\d{1,2}[./]\d{2,4})',
    r'(\d{4}-\d{2}-\d{2})',
    r'Data\s+wystawienia\s*[:\s]+(\S+)',
]:
    m = re.search(pat, all_text, re.IGNORECASE)
    if m:
        print(f"Data ({pat[:20]}): {m.group(1)}")
        break
