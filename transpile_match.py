"""
transpile_match.py — zamienia match/case Python 3.10 na if/elif dla Python 3.9
Uruchamiaj z katalogu głównego projektu: python transpile_match.py
"""
import re
import pathlib


def transpile(src: str) -> str:
    """Linia po linii zastępuje match/case na if/elif."""
    lines = src.splitlines(keepends=True)
    out = []
    i = 0

    while i < len(lines):
        raw = lines[i]
        stripped = raw.rstrip('\n\r')

        # Dopasuj: <indent>match <expr>:
        m = re.match(r'^(\s*)match (.+):\s*$', stripped)
        if m:
            base_indent = m.group(1)
            var = m.group(2).strip()
            i += 1
            first = True

            # Przetwarzaj kolejne wiersze dopóki są case'y
            while i < len(lines):
                craw = lines[i]
                cs = craw.rstrip('\n\r')

                # case _: (default / else)
                if re.match(r'^\s*case _:\s*$', cs):
                    out.append(base_indent + 'else:\n')
                    i += 1
                    continue

                # case (<A> | <B> | ...): — wieloliniowy case z nawiasem
                cm = re.match(r'^(\s*)case \((.+?)\):\s*$', cs)
                if cm:
                    parts = [p.strip() for p in cm.group(2).split('|')]
                    cond = ' or '.join(f'{var} == {p}' for p in parts)
                    kw = 'if' if first else 'elif'
                    out.append(f'{base_indent}{kw} {cond}:\n')
                    first = False
                    i += 1
                    continue

                # case X: (einzelner Wert)
                cm2 = re.match(r'^(\s*)case (.+):\s*$', cs)
                if cm2:
                    pattern = cm2.group(2).strip()
                    # Połącz wieloliniowe (| na końcu)
                    while pattern.endswith('|'):
                        i += 1
                        nxt = lines[i].rstrip('\n\r').strip()
                        pattern += ' ' + nxt

                    # Split po | (poza nawiasami)
                    parts = [p.strip() for p in re.split(r'\s*\|\s*', pattern)]
                    parts = [p for p in parts if p]
                    if len(parts) == 1:
                        cond = f'{var} == {parts[0]}'
                    else:
                        cond = ' or '.join(f'{var} == {p}' for p in parts)
                    kw = 'if' if first else 'elif'
                    out.append(f'{base_indent}{kw} {cond}:\n')
                    first = False
                    i += 1
                    continue

                # Jeśli linia nie jest case → to ciało case lub koniec bloku
                # Sprawdź indent — jeśli ≤ match indent → koniec match
                line_indent = len(cs) - len(cs.lstrip())
                if cs.strip() == '' or line_indent > len(base_indent):
                    out.append(craw)
                    i += 1
                else:
                    # Koniec bloku match
                    break
            continue

        out.append(raw)
        i += 1

    return ''.join(out)


if __name__ == '__main__':
    targets = [
        pathlib.Path('mrowka/mrowka_data.py'),
    ]
    for p in targets:
        if not p.exists():
            print(f'Skip {p}')
            continue
        src = p.read_text(encoding='utf-8')
        before = src.count('\n    match ') + src.count('\nmatch ')
        result = transpile(src)
        after = result.count('\n    match ') + result.count('\nmatch ')
        p.write_text(result, encoding='utf-8')
        print(f'{p}: {before} match blocks -> {after} remaining')
    print('DONE')
