"""
patch_remaining_cases.py — naprawia pozostałe case( bloki które transpiler pominął
"""
import re, pathlib

p = pathlib.Path('mrowka/mrowka_data.py')
src = p.read_text(encoding='utf-8')
lines = src.splitlines(keepends=True)
out = []
i = 0

def find_var_from_context(lines, case_idx):
    """Znajdź zmienną match patrząc wstecz na if/elif self =="""
    ci = len(lines[case_idx]) - len(lines[case_idx].lstrip())
    for j in range(case_idx - 1, max(0, case_idx - 50), -1):
        l = lines[j].rstrip()
        m = re.match(r'^\s*if (\w+) == .+:\s*$', l)
        if m: return m.group(1)
        m2 = re.match(r'^\s*elif (\w+) == .+:\s*$', l)
        if m2: return m2.group(1)
    return 'self'

while i < len(lines):
    raw = lines[i]
    stripped = raw.rstrip()

    # case (\n
    if re.match(r'^\s*case \(\s*$', stripped):
        var = find_var_from_context(lines, i)
        base_ind = ' ' * (len(stripped) - len(stripped.lstrip()))
        i += 1
        parts = []
        while i < len(lines):
            inner = lines[i].rstrip()
            if re.match(r'^\s*\):\s*$', inner):
                i += 1
                break
            part = inner.strip().lstrip('|').strip()
            if part:
                parts.append(part)
            i += 1
        cond = ' or '.join(f'{var} == {p_}' for p_ in parts)
        out.append(f'{base_ind}elif {cond}:\n')
        continue

    out.append(raw)
    i += 1

result = ''.join(out)
p.write_text(result, encoding='utf-8')
remaining = len(re.findall(r'^\s+case ', result, re.MULTILINE))
print(f'Done. Remaining case lines: {remaining}')
