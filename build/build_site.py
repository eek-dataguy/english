# -*- coding: utf-8 -*-
"""Merge parsed quizzes -> static-site data files under ../web/data/."""
import json, os, re, hashlib
from collections import defaultdict

OUT = '../web/data'
os.makedirs(OUT + '/level', exist_ok=True)

ihk = json.load(open('ihk_quizzes.json', encoding='utf-8'))
tm = json.load(open('tm_quizzes.json', encoding='utf-8'))

LEVELS = ['A1', 'A2', 'B1', 'B2', 'C1']
CHUNK = 12

def slug(s):
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')[:60]

def looks_broken(opts):
    """Detect option text corrupted by column-merge / cloze bleed in the source PDF."""
    for o in opts:
        if len(o) > 45:            # options in these books are short; long => merged text
            return True
        if '_____' in o or '___' in o:   # a blank inside an option = bleed from another gap
            return True
        if re.search(r'\bA\s*:\s|\bB\s*:\s|www\.', o):  # dialogue markers pulled in
            return True
        if re.search(r'[a-z]{2}\.[A-Z][a-z]', o):       # "sentence.Next" run-together
            return True
    return False

def clean_q(it):
    q = re.sub(r'\s+', ' ', it['q']).strip()
    # normalise the blank to a single style
    q = re.sub(r'_{2,}|\.{3,}|…', ' ______ ', q)
    q = re.sub(r'\s+', ' ', q).strip()
    opts = [re.sub(r'\s+', ' ', o).strip() for o in it['options']]
    return {'q': q, 'options': opts, 'answer': it['answer']}

quizzes = []
seen_ids = set()
for src in (ihk, tm):
    for grp in src:
        items = [clean_q(it) for it in grp['questions']
                 if 0 <= it['answer'] < len(it['options']) and len(it['options']) >= 2
                 and not looks_broken(it['options'])]
        # dedupe questions inside a group
        uniq, qseen = [], set()
        for it in items:
            k = it['q'].lower()
            if k in qseen:
                continue
            qseen.add(k); uniq.append(it)
        items = uniq
        if not items:
            continue
        nchunks = (len(items) + CHUNK - 1) // CHUNK
        for ci in range(nchunks):
            part = items[ci * CHUNK:(ci + 1) * CHUNK]
            base = f"{grp['cefr']}-{slug(grp['source'])}-{slug(grp['title'])}"
            qid = base + (f"-{ci+1}" if nchunks > 1 else "")
            if qid in seen_ids:
                qid += '-' + hashlib.md5(json.dumps(part).encode()).hexdigest()[:4]
            seen_ids.add(qid)
            title = grp['title'] + (f" (part {ci+1}/{nchunks})" if nchunks > 1 else "")
            quizzes.append({
                'id': qid,
                'cefr': grp['cefr'],
                'source': grp['source'],
                'srcLevel': grp.get('src_level', ''),
                'title': title,
                'n': len(part),
                'questions': part,
            })

by_level = defaultdict(list)
for q in quizzes:
    by_level[q['cefr']].append(q)

index = {'levels': [], 'totalQuizzes': len(quizzes),
         'totalQuestions': sum(q['n'] for q in quizzes),
         'generated': __import__('datetime').date.today().isoformat()}

DESC = {
    'A1': 'Beginner - basic verb "to be", articles, plurals, simple present.',
    'A2': 'Elementary - past simple, comparatives, going to, common prepositions.',
    'B1': 'Intermediate - present perfect, conditionals, phrasal verbs, reported speech.',
    'B2': 'Upper-intermediate - perfect tenses, passives, relative clauses, nuance.',
    'C1': 'Advanced - idioms, inversion, sophisticated vocabulary and collocation.',
}

for lv in LEVELS:
    lst = by_level.get(lv, [])
    # stable order: source then title
    lst.sort(key=lambda q: (q['source'], q['title']))
    meta = [{'id': q['id'], 'title': q['title'], 'source': q['source'],
             'srcLevel': q['srcLevel'], 'n': q['n']} for q in lst]
    json.dump({'level': lv, 'quizzes': lst}, open(f'{OUT}/level/{lv}.json', 'w', encoding='utf-8'),
              ensure_ascii=False, separators=(',', ':'))
    index['levels'].append({
        'level': lv, 'desc': DESC[lv],
        'quizzes': len(lst),
        'questions': sum(q['n'] for q in lst),
        'items': meta,
    })

json.dump(index, open(f'{OUT}/index.json', 'w', encoding='utf-8'),
          ensure_ascii=False, separators=(',', ':'))

# placement test: sample questions spread across levels
import random
random.seed(42)
placement = []
per = {'A1': 4, 'A2': 5, 'B1': 5, 'B2': 4, 'C1': 4}
for lv in LEVELS:
    pool = [it for q in by_level.get(lv, []) for it in q['questions']]
    random.shuffle(pool)
    for it in pool[:per[lv]]:
        placement.append({**it, 'cefr': lv})
random.shuffle(placement)
json.dump({'questions': placement}, open(f'{OUT}/placement.json', 'w', encoding='utf-8'),
          ensure_ascii=False, separators=(',', ':'))

print('quizzes:', len(quizzes), 'questions:', index['totalQuestions'])
for l in index['levels']:
    print(f"  {l['level']}: {l['quizzes']:4d} quizzes  {l['questions']:5d} questions")
sz = sum(os.path.getsize(f'{OUT}/level/{lv}.json') for lv in LEVELS) / 1e6
print(f'data size: {sz:.1f} MB across level files')
