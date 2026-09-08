# -*- coding: utf-8 -*-
"""Unified extractor for Test Master (Atalay Oguz) - Book 1 grammar, Parts A and E."""
import re, json
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer

PDF = '../GnGozbEwKKuzJeFZwlP44jd4P7XPAoUUz9lMqJEX.pdf'
COL = 290

def clean(t):
    t = (t.replace('�', "'").replace('’', "'").replace('‘', "'")
           .replace('“', '"').replace('”', '"').replace('–', '-')
           .replace('—', '-').replace('…', '...'))
    return re.sub(r'[ \t]+', ' ', t).strip()

def load(pages):
    out = {}
    for pi, pl in enumerate(extract_pages(PDF, page_numbers=pages)):
        rows = []
        for el in pl:
            if isinstance(el, LTTextContainer):
                for ln in el:
                    if hasattr(ln, 'get_text'):
                        t = clean(ln.get_text())
                        if t:
                            rows.append((ln.x0, ln.y0, t))
        out[pages[pi]] = rows
    return out

QSTART = re.compile(r'^(\d{1,3})[.)]\s*(.*)$')
OPT_SPLIT = re.compile(r'(?=(?:^|\s)[A-D]\)\s)')
OPT = re.compile(r'^([A-D])\)\s*(.*)$')
GAP = re.compile(r'_+\(?(\d{1,3})\)?_+')
SKIP = re.compile(r'^(-|•|ELEMENTARY|PRE-?INTERMEDIATE|INTERMEDIATE|UPPER-?INTERMEDIATE|ADVANCED|TEST\s*[-–]|Book 1 Part|Choose |Fill in|Mark the|Find the correct|Only one answer|Complete the|Read the)', re.I)

def reading_order(rows):
    body = [(x, y, t) for x, y, t in rows if 40 < y < 775]
    left = sorted([r for r in body if r[0] < COL], key=lambda r: -r[1])
    right = sorted([r for r in body if r[0] >= COL], key=lambda r: -r[1])
    return [t for _, _, t in left + right]

def _add_opt(q, L, txt):
    q['opts'][L] = ((q['opts'].get(L, '') + ' ' + txt).strip() if q['opts'].get(L) else txt.strip())

def _add_cont(q, txt):
    if not q['opts']:
        q['stem'] = (q['stem'] + ' ' + txt).strip()
    else:
        lastL = list(q['opts'])[-1]
        q['opts'][lastL] = (q['opts'][lastL] + ' ' + txt).strip()

def absorb(q, text):
    text = text.strip()
    if not text:
        return
    if re.search(r'(?:^|\s)[A-D]\)\s', ' ' + text):
        for p in [p.strip() for p in OPT_SPLIT.split(text) if p.strip()]:
            mo = OPT.match(p)
            if mo:
                _add_opt(q, mo.group(1), mo.group(2))
            else:
                _add_cont(q, p)
    else:
        _add_cont(q, text)

def parse_body(lines):
    qs = {}
    cur = None
    passages = []
    for t in lines:
        t = t.strip()
        if not t or re.match(r'^\d+$', t):
            continue
        if SKIP.match(t):
            continue
        m = QSTART.match(t)
        is_new = m and (cur is None or int(m.group(1)) > cur or (int(m.group(1)) == 1 and cur and cur > 5))
        if is_new:
            cur = int(m.group(1))
            qs.setdefault(cur, {'stem': '', 'opts': {}})
            rest = m.group(2).strip()
            if rest:
                absorb(qs[cur], rest)
            continue
        if GAP.search(t) and not OPT.match(t) and (cur is None or not qs.get(cur, {}).get('opts')):
            passages.append(t)
            continue
        if cur is None:
            continue
        absorb(qs[cur], t)
    return qs, ' '.join(passages)

AK_HDR = {
    'A': re.compile(r'^(ELEMENTARY|PRE-?INTERMEDIATE|INTERMEDIATE)\s+Test:?\s+(\d+)', re.I),
    'E': re.compile(r'^(ELEMENTARY|INTERMEDIATE|ADVANCED)\s+test\s+(\d+)', re.I),
}
AK_TOK = re.compile(r'(\d{1,3})\s*-\s*([A-D])')

def parse_ak(pagemap, part):
    hdr = AK_HDR[part]
    res = {}
    for p in sorted(pagemap):
        rows = pagemap[p]
        for side in ('L', 'R'):
            col = sorted([r for r in rows if (r[0] < COL) == (side == 'L')], key=lambda r: -r[1])
            cur = None
            for x, y, t in col:
                mh = hdr.match(t)
                if mh:
                    cur = (mh.group(1).title(), int(mh.group(2)))
                    res.setdefault(cur, {})
                    continue
                if cur is None:
                    continue
                for mt in AK_TOK.finditer(t):
                    res[cur].setdefault(int(mt.group(1)), mt.group(2))
    return res

FOOT = {
    'A': re.compile(r'^(Elementary|Pre-Intermediate|Intermediate)\s+Test\s+(\d+)$', re.I),
    'E': re.compile(r'^(Elementary|Intermediate|Advanced)\s+test\s+(\d+)$', re.I),
}

def build(part, qpages, akpages, levelmap, title_prefix, do_cloze=True):
    QP = load(qpages)
    AP = load(akpages)
    footre = FOOT[part]
    tests = {}
    order = []
    for p in qpages:
        rows = QP[p]
        tid = None
        for x, y, t in rows:
            if y < 36:
                mm = footre.match(t)
                if mm:
                    tid = (mm.group(1).title(), int(mm.group(2)))
        if not tid:
            continue
        if tid not in tests:
            tests[tid] = []
            order.append(tid)
        tests[tid] += reading_order(rows)
    ak = parse_ak(AP, part)
    quizzes = []
    st = {'tests': 0, 'seen': 0, 'kept': 0, 'd_key': 0, 'd_opts': 0, 'd_stem': 0, 'cloze_fixed': 0}
    for tid in order:
        lvl, n = tid
        st['tests'] += 1
        qs, passage = parse_body(tests[tid])
        akk = ak.get((lvl, n), {})
        for qn in sorted(qs):
            st['seen'] += 1
            q = qs[qn]
            opts = [q['opts'].get(L, '').strip() for L in 'ABCD']
            opts = [o for o in opts if o]
            letter = akk.get(qn)
            stem = re.sub(r'\s+', ' ', q['stem']).strip()
            if not stem and do_cloze and passage and GAP.search(passage):
                s = passage
                for g in set(int(x) for x in GAP.findall(passage)):
                    if g == qn:
                        continue
                    gl = akk.get(g)
                    gq = qs.get(g, {})
                    fill = gq.get('opts', {}).get(gl) if gl else None
                    s = re.sub(r'_+\(?' + str(g) + r'\)?_+', fill if fill else '___', s)
                s = re.sub(r'_+\(?' + str(qn) + r'\)?_+', ' _____ ', s)
                stem = re.sub(r'\s+', ' ', s).strip()
                if stem:
                    st['cloze_fixed'] += 1
            if not letter:
                st['d_key'] += 1
                continue
            if len(opts) < 4:
                st['d_opts'] += 1
                continue
            if len(stem) < 4 or len(stem) > 500 or not re.search(r'[A-Za-z]', stem):
                st['d_stem'] += 1
                continue
            ai = ord(letter) - 65
            if ai >= len(opts):
                st['d_key'] += 1
                continue
            q['_item'] = {'q': stem, 'options': opts, 'answer': ai}
        items = [qs[qn]['_item'] for qn in sorted(qs) if '_item' in qs[qn]]
        st['kept'] += len(items)
        if items:
            quizzes.append({'source': 'Test Master (Atalay Oguz)', 'part': part, 'src_level': lvl,
                            'cefr': levelmap[lvl], 'title': f'{title_prefix} - {lvl} Test {n}',
                            'num': n, 'questions': items})
    return quizzes, st

PARTB_FOOT = re.compile(r'\((Elementary|Intermediate)\s*[\\/]\s*(Pre-Intermediate|Upper-Intermediate)\)', re.I)
PARTB_AKH = re.compile(r'\((Elementary|Intermediate)\s*/\s*(Pre-Intermediate|Upper-Intermediate)\)\s*(\d{1,2})\b', re.I)

def build_partB(qpages, akpages):
    QP = load(qpages)
    AP = load(akpages)
    # ---- questions: group by footer text, in encounter order ----
    tests = []           # list of (footer, [lines])
    seen = {}
    for p in qpages:
        rows = QP[p]
        foot = None
        for x, y, t in rows:
            if y < 36 and PARTB_FOOT.search(t):
                foot = re.sub(r'\s+', ' ', t).strip()
        if not foot:
            continue
        if foot not in seen:
            seen[foot] = len(tests)
            tests.append([foot, []])
        tests[seen[foot]][1] += reading_order(rows)
    # ---- answer keys: index -> {qn: letter} ----
    ak = {}
    for p in sorted(akpages):
        rows = AP[p]
        for side in ('L', 'R'):
            col = sorted([r for r in rows if (r[0] < COL) == (side == 'L')], key=lambda r: -r[1])
            cur = None
            for x, y, t in col:
                mh = PARTB_AKH.search(t)
                if mh:
                    cur = int(mh.group(3))
                    ak.setdefault(cur, {})
                    continue
                if cur is None:
                    continue
                for mt in AK_TOK.finditer(t):
                    ak[cur].setdefault(int(mt.group(1)), mt.group(2))
    quizzes = []
    st = {'tests': 0, 'seen': 0, 'kept': 0, 'd_key': 0, 'd_opts': 0, 'd_stem': 0}
    for idx, (foot, lines) in enumerate(tests, start=1):
        st['tests'] += 1
        band = PARTB_FOOT.search(foot)
        cefr = 'A2' if band.group(1).lower() == 'elementary' else 'B2'
        topic = foot.split('(')[0].strip(' -')
        qs, _ = parse_body(lines)
        akk = ak.get(idx, {})
        items = []
        for qn in sorted(qs):
            st['seen'] += 1
            q = qs[qn]
            opts = [o for o in (q['opts'].get(L, '').strip() for L in 'ABCD') if o]
            letter = akk.get(qn)
            stem = re.sub(r'\s+', ' ', q['stem']).strip()
            if not letter:
                st['d_key'] += 1; continue
            if len(opts) < 4:
                st['d_opts'] += 1; continue
            if len(stem) < 4 or len(stem) > 400 or not re.search(r'[A-Za-z]', stem):
                st['d_stem'] += 1; continue
            ai = ord(letter) - 65
            if ai >= len(opts):
                st['d_key'] += 1; continue
            items.append({'q': stem, 'options': opts, 'answer': ai})
        st['kept'] += len(items)
        if items:
            quizzes.append({'source': 'Test Master (Atalay Oguz)', 'part': 'B', 'src_level': band.group(0),
                            'cefr': cefr, 'title': f'Grammar B - {topic} ({cefr})', 'num': idx,
                            'questions': items})
    return quizzes, st

if __name__ == '__main__':
    allq = []
    qa, sa = build('A', list(range(7, 56)), [408, 409, 410],
                   {'Elementary': 'A1', 'Pre-Intermediate': 'A2', 'Intermediate': 'B1'}, 'Grammar A',
                   do_cloze=False)
    print('PART A', json.dumps(sa))
    allq += qa
    qe, se = build('E', list(range(196, 224)), [419, 420],
                   {'Elementary': 'A2', 'Intermediate': 'B1', 'Advanced': 'C1'}, 'Grammar E',
                   do_cloze=False)
    print('PART E', json.dumps(se))
    allq += qe
    qb, sb = build_partB(list(range(56, 108)), [411, 412, 413])
    print('PART B', json.dumps(sb))
    allq += qb
    json.dump(allq, open('tm_quizzes.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    from collections import Counter
    print('TOTAL quizzes', len(allq), Counter(q['cefr'] for q in allq))
    print('TOTAL questions', sum(len(q['questions']) for q in allq))
