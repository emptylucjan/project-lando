"""
fix_case_multiline.py
Naprawia wieloliniowe 'case (\n    X\n):' → eliminuje je i podmienia na elif.
Plik wejściowy: mrowka/mrowka_data.py
"""
import re
import pathlib


def find_match_var(lines, case_idx):
    """Znajdź zmienną 'match var:' dla danego case (szukaj wstecz)."""
    ci = lines[case_idx]
    case_indent = len(ci) - len(ci.lstrip())
    for j in range(case_idx - 1, -1, -1):
        l = lines[j].rstrip()
        if not l.strip():
            continue
        li = len(l) - len(l.lstrip())
        if li < case_indent:
            m = re.match(r'^\s*match (.+):\s*$', l)
            if m:
                return m.group(1).strip()
            # Może to if/elif zamiennionych przez poprzedni pass
            m2 = re.match(r'^\s*if (.+) == .+:\s*$', l)
            if m2:
                return m2.group(1).strip()
            m3 = re.match(r'^\s*elif (.+) == .+:\s*$', l)
            if m3:
                return m3.group(1).strip()
            break
    return 'self'


def process(src: str) -> str:
    lines = src.splitlines(keepends=True)
    i = 0
    out = []

    while i < len(lines):
        raw = lines[i]
        stripped = raw.rstrip()

        # match <var>:
        mm = re.match(r'^(\s*)match (.+):\s*$', stripped)
        if mm:
            base_ind = mm.group(1)
            var = mm.group(2).strip()
            i += 1
            first = True

            while i < len(lines):
                cr = lines[i]
                cs = cr.rstrip()

                # Zakończenie bloku match: linia o tym samym lub mniejszym indencie
                # która NIE jest case/else
                ci2 = len(cs) - len(cs.lstrip()) if cs.strip() else 999
                is_case = bool(re.match(r'^\s*case ', cs))
                is_empty = not cs.strip()

                if not is_case and not is_empty and ci2 <= len(base_ind) and cs.strip():
                    break

                # case _:
                if re.match(r'^\s*case _:\s*$', cs):
                    out.append(base_ind + 'else:\n')
                    i += 1
                    continue

                # case (\n...\n):  — wieloliniowe z nawiasem
                if re.match(r'^\s*case \(\s*$', cs):
                    # Zbierz zawartość do zamknięcia nawiasu
                    parts_raw = []
                    i += 1
                    while i < len(lines):
                        inner = lines[i].rstrip()
                        if re.match(r'^\s*\):\s*$', inner):
                            i += 1
                            break
                        # Może być "  | ..." albo "  X"
                        part = inner.strip().lstrip('| ').strip()
                        if part:
                            parts_raw.append(part)
                        i += 1
                    cond = ' or '.join(f'{var} == {p}' for p in parts_raw)
                    kw = 'if' if first else 'elif'
                    out.append(f'{base_ind}{kw} {cond}:\n')
                    first = False
                    continue

                # case X | Y: (single line z|)  lub  case X:
                cm = re.match(r'^\s*case (.+):\s*$', cs)
                if cm:
                    pattern = cm.group(1).strip()
                    parts = [p.strip() for p in re.split(r'\s*\|\s*', pattern)]
                    cond = ' or '.join(f'{var} == {p}' for p in parts)
                    kw = 'if' if first else 'elif'
                    out.append(f'{base_ind}{kw} {cond}:\n')
                    first = False
                    i += 1
                    continue

                # Ciało case
                out.append(cr)
                i += 1
            continue

        out.append(raw)
        i += 1

    return ''.join(out)


if __name__ == '__main__':
    p = pathlib.Path('mrowka/mrowka_data.py')
    src = p.read_text(encoding='utf-8')
    result = process(src)
    p.write_text(result, encoding='utf-8')
    # Count remaining 'case' lines
    remaining = len(re.findall(r'^\s+case ', result, re.MULTILINE))
    print(f'Done. Remaining "case" lines: {remaining}')
