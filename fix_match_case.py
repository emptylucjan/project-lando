"""
fix_match_case.py — konwertuje match/case na if/elif dla Python 3.9
"""
import re
import pathlib


def convert_match_case(src: str) -> str:
    """
    Konwertuje bloki match/case w Pythonie 3.10 na if/elif dla 3.9.
    Obsługuje: match self:, match x:, case Y:, case _:
    """
    lines = src.split('\n')
    result = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.rstrip()
        indent = len(line) - len(line.lstrip())
        
        # Znajdź 'match <var>:'
        m = re.match(r'^( *)match (.+):\s*$', stripped)
        if m:
            base_indent = m.group(1)
            var = m.group(2).strip()
            i += 1
            first_case = True
            while i < len(lines):
                case_line = lines[i].rstrip()
                case_stripped = case_line.strip()
                
                # case _ : (default)
                cm_default = re.match(r'^( *)case _:\s*$', case_line)
                # case (X | Y | Z):
                cm_multi = re.match(r'^( *)case \((.+)\):\s*$', case_line)
                # case X:
                cm_single = re.match(r'^( *)case (.+):\s*$', case_line)
                
                if cm_default:
                    kw = 'else'
                    result.append(f'{base_indent}{kw}:')
                    first_case = True  # reset
                    i += 1
                elif cm_multi:
                    pattern = cm_multi.group(2)
                    # Split by | and create list
                    parts = [p.strip() for p in pattern.split('|')]
                    cond = ' or '.join(f'{var} == {p}' for p in parts)
                    kw = 'if' if first_case else 'elif'
                    result.append(f'{base_indent}{kw} {cond}:')
                    first_case = False
                    i += 1
                elif cm_single and case_stripped != 'case:':
                    pattern = cm_single.group(2).strip()
                    # Handle multi-line case with |
                    while i + 1 < len(lines) and lines[i+1].strip().startswith('| '):
                        i += 1
                        extra = lines[i].strip()[2:].strip()
                        pattern = f'({pattern}\n                | {extra})'
                    
                    # Simple single case
                    parts = [p.strip() for p in re.split(r'\s*\|\s*', pattern)]
                    if len(parts) > 1:
                        cond = ' or '.join(f'{var} == {p}' for p in parts)
                    else:
                        cond = f'{var} == {pattern}'
                    kw = 'if' if first_case else 'elif'
                    result.append(f'{base_indent}{kw} {cond}:')
                    first_case = False
                    i += 1
                else:
                    # Czy to wciąż w bloku match? Sprawdź indent
                    if case_line and len(case_line) - len(case_line.lstrip()) <= indent:
                        break
                    result.append(case_line)
                    i += 1
            continue
        
        result.append(line)
        i += 1
    
    return '\n'.join(result)


if __name__ == '__main__':
    files = [
        'mrowka/mrowka_data.py',
        'mrowka/mrowka_bot.py',
        'mrowka/mrowka_lib.py',
    ]
    for fpath in files:
        p = pathlib.Path(fpath)
        if not p.exists():
            continue
        original = p.read_text(encoding='utf-8')
        if 'match ' not in original:
            print(f'No match/case in {fpath}, skipping')
            continue
        converted = convert_match_case(original)
        p.write_text(converted, encoding='utf-8')
        # Count conversions
        n = original.count('\n    match ') + original.count('\nmatch ')
        print(f'Converted {fpath} ({n} match blocks)')
    print('Done')
