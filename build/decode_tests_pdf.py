# -*- coding: utf-8 -*-
"""
'English Grammar Tests.pdf' (the 853-test english-test.net collection) ships with
subset fonts whose glyphs are mapped into the Unicode Private Use Area with a
simple offset cipher and no ToUnicode map, so a normal text extract yields only
spaces. Each PUA code point U+F0xx decodes to ASCII via  chr(288 - 0xxx),
with U+F020 -> space. This script writes the readable text to tests_dec.txt.
"""
from pdfminer.high_level import extract_text

def decode(s):
    out = []
    for ch in s:
        c = ord(ch)
        if 0xF000 <= c <= 0xF0FF:
            v = c - 0xF000
            if v == 0x20:
                out.append(' ')
            else:
                d = 288 - v
                out.append(chr(d) if 32 <= d < 127 else '?')
        else:
            out.append(ch)
    return ''.join(out)

if __name__ == '__main__':
    raw = extract_text('../English Grammar Tests.pdf')
    open('tests_dec.txt', 'w', encoding='utf-8').write(decode(raw))
    print('wrote tests_dec.txt', len(raw), 'chars')
