# -*- coding: utf-8 -*-
"""Merge parsed quizzes -> static-site data files under ../web/data/."""
import json, os, re, hashlib, random
from collections import defaultdict, Counter
from classify import classify, TOPICS

OUT = '../web/data'
os.makedirs(OUT + '/level', exist_ok=True)
os.makedirs(OUT + '/topic', exist_ok=True)

ihk = json.load(open('ihk_quizzes.json', encoding='utf-8'))
tm = json.load(open('tm_quizzes.json', encoding='utf-8'))

LEVELS = ['A1', 'A2', 'B1', 'B2', 'C1']
CHUNK = 12

def slug(s):
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')[:60]

def looks_broken(opts):
    """Detect option text corrupted by column-merge / cloze bleed in the source PDF."""
    for o in opts:
        if len(o) > 45:
            return True
        if '_____' in o or '___' in o:
            return True
        if re.search(r'\bA\s*:\s|\bB\s*:\s|www\.', o):
            return True
        if re.search(r'[a-z]{2}\.[A-Z][a-z]', o):
            return True
    return False

def clean_q(it, hint):
    q = re.sub(r'\s+', ' ', it['q']).strip()
    q = re.sub(r'_{2,}|\.{3,}|…', ' ______ ', q)
    q = re.sub(r'\s+', ' ', q).strip()
    opts = [re.sub(r'\s+', ' ', o).strip() for o in it['options']]
    out = {'q': q, 'options': opts, 'answer': it['answer'], 'k': classify(q, opts, hint)}
    fs = re.sub(r'\s+', ' ', (it.get('full') or '')).strip()
    aw = re.sub(r'\s+', ' ', (it.get('answer_word') or '')).strip()
    if fs and fs.lower() != q.lower() and '______' not in fs and 5 < len(fs) < 320:
        out['fs'] = fs
        if aw:
            out['aw'] = aw
    return out

quizzes = []
seen_ids = set()
for src in (ihk, tm):
    for grp in src:
        hint = ' '.join(str(grp.get(k, '')) for k in ('title', 'topic', 'src_level'))
        items = [clean_q(it, hint) for it in grp['questions']
                 if 0 <= it['answer'] < len(it['options']) and len(it['options']) >= 2
                 and not looks_broken(it['options'])]
        uniq, qseen = [], set()
        for it in items:
            key = it['q'].lower()
            if key in qseen:
                continue
            qseen.add(key); uniq.append(it)
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
            cat = Counter(it['k'] for it in part).most_common(1)[0][0]
            quizzes.append({
                'id': qid, 'cefr': grp['cefr'], 'source': grp['source'],
                'srcLevel': grp.get('src_level', ''), 'title': title,
                'topic': grp.get('topic', ''), 'cat': cat,
                'n': len(part), 'questions': part,
            })

by_level = defaultdict(list)
for q in quizzes:
    by_level[q['cefr']].append(q)

# ---- topic aggregates ----
topic_q = defaultdict(list)   # catid -> list of (level, question)
for q in quizzes:
    for it in q['questions']:
        topic_q[it['k']].append((q['cefr'], it))

topics_meta = []
for cid, meta in TOPICS.items():
    entries = topic_q.get(cid, [])
    if not entries:
        continue
    byl = Counter(lv for lv, _ in entries)
    topics_meta.append({
        'id': cid, 'name': meta['name'], 'note': meta['note'],
        'count': len(entries),
        'byLevel': {lv: byl.get(lv, 0) for lv in LEVELS if byl.get(lv)},
    })
topics_meta.sort(key=lambda t: -t['count'])

# per-topic practice pools (spread across levels, capped)
random.seed(7)
POOL_CAP = 90
for t in topics_meta:
    if t['count'] < 8:
        continue
    ents = topic_q[t['id']][:]
    random.shuffle(ents)
    ents.sort(key=lambda e: LEVELS.index(e[0]))   # keep some level spread by round-robin
    buckets = defaultdict(list)
    for lv, it in ents:
        buckets[lv].append(it)
    pool, i = [], 0
    while len(pool) < POOL_CAP and any(buckets[lv] for lv in LEVELS):
        lv = LEVELS[i % len(LEVELS)]
        if buckets[lv]:
            it = buckets[lv].pop()
            pool.append({**it, 'cefr': lv})
        i += 1
    json.dump({'id': t['id'], 'name': t['name'], 'note': t['note'], 'questions': pool},
              open(f"{OUT}/topic/{t['id']}.json", 'w', encoding='utf-8'),
              ensure_ascii=False, separators=(',', ':'))
    t['pool'] = len(pool)

DESC = {
    'A1': 'Beginner - basic verb "to be", articles, plurals, simple present.',
    'A2': 'Elementary - past simple, comparatives, going to, common prepositions.',
    'B1': 'Intermediate - present perfect, conditionals, phrasal verbs, reported speech.',
    'B2': 'Upper-intermediate - perfect tenses, passives, relative clauses, nuance.',
    'C1': 'Advanced - idioms, inversion, sophisticated vocabulary and collocation.',
}

index = {'levels': [], 'topics': [{'id': t['id'], 'name': t['name'], 'count': t['count'],
                                   'byLevel': t['byLevel'], 'practisable': 'pool' in t}
                                  for t in topics_meta],
         'totalQuizzes': len(quizzes),
         'totalQuestions': sum(q['n'] for q in quizzes),
         'generated': __import__('datetime').date.today().isoformat()}

for lv in LEVELS:
    lst = by_level.get(lv, [])
    lst.sort(key=lambda q: (q['source'], q['title']))
    meta = [{'id': q['id'], 'title': q['title'], 'source': q['source'],
             'srcLevel': q['srcLevel'], 'cat': q['cat'], 'n': q['n']} for q in lst]
    json.dump({'level': lv, 'quizzes': lst}, open(f'{OUT}/level/{lv}.json', 'w', encoding='utf-8'),
              ensure_ascii=False, separators=(',', ':'))
    index['levels'].append({
        'level': lv, 'desc': DESC[lv], 'quizzes': len(lst),
        'questions': sum(q['n'] for q in lst), 'items': meta,
    })

json.dump(index, open(f'{OUT}/index.json', 'w', encoding='utf-8'),
          ensure_ascii=False, separators=(',', ':'))
json.dump({'topics': topics_meta}, open(f'{OUT}/topics.json', 'w', encoding='utf-8'),
          ensure_ascii=False, separators=(',', ':'))

# placement test
random.seed(42)
placement = []
per = {'A1': 4, 'A2': 5, 'B1': 5, 'B2': 4, 'C1': 4}
for lv in LEVELS:
    pool = [it for q in by_level.get(lv, []) for it in q['questions']]
    random.shuffle(pool)
    placement += [{**it, 'cefr': lv} for it in pool[:per[lv]]]
random.shuffle(placement)
json.dump({'questions': placement}, open(f'{OUT}/placement.json', 'w', encoding='utf-8'),
          ensure_ascii=False, separators=(',', ':'))

print('quizzes:', len(quizzes), 'questions:', index['totalQuestions'])
for l in index['levels']:
    print(f"  {l['level']}: {l['quizzes']:4d} quizzes  {l['questions']:5d} questions")
print(f"topics: {len(topics_meta)}  ({sum(1 for t in topics_meta if 'pool' in t)} practisable)")
for t in topics_meta:
    print(f"  {t['count']:5d}  {t['id']:26s} {t['name']}")
sz = sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fs in os.walk(OUT) for f in fs) / 1e6
print(f'total data: {sz:.1f} MB')
