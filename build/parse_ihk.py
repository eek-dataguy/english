# Parser for english-test.net "English Grammar Tests" (decoded) -> tests_dec.txt
import re, json, sys
LINES = open('tests_dec.txt', encoding='utf-8').read().split('\n')

def norm(s):
    s = s.replace('\x0c','').replace('\ufffd',"'")
    s = s.replace('\u2019',"'").replace('\u2018',"'").replace('\u201c','"').replace('\u201d','"')
    s = re.sub(r'\s+',' ',s).strip()
    return s

qh_re = re.compile(r'Incomplete Sentences / (Elementary|Intermediate|Advanced) level # (\d+)\s*$')
ak_re = re.compile(r'Incomplete Sentences / (Elementary|Intermediate|Advanced) level # (\d+) \(Answer Keys\)\s*$')

def blocks(rx):
    idx = [i for i,l in enumerate(LINES) if rx.search(l)]
    out = []
    for k,i in enumerate(idx):
        j = idx[k+1] if k+1 < len(idx) else len(LINES)
        m = rx.search(LINES[i])
        out.append((m.group(1), int(m.group(2)), LINES[i+1:j]))
    return out

opt_re = re.compile(r'^\(([a-d])\)\s*(.*)$')
qn_re  = re.compile(r'^Q(\d+)\b\s*(.*)$')

def parse_questions(body):
    # returns dict qnum -> {stem, options{letter:text}}
    qs = {}
    cur = None
    pending_opts = []  # leftover options (letter,text) pooled at page end
    lines = [norm(x) for x in body]
    lines = [x for x in lines if x and not x.startswith('PHOTOCOPIABLE') and not re.match(r'^\d+$',x)]
    for ln in lines:
        mq = qn_re.match(ln)
        if mq:
            cur = int(mq.group(1))
            qs[cur] = {'stem': mq.group(2).strip(), 'options': {}}
            continue
        mo = opt_re.match(ln)
        if mo and cur is not None:
            letter, txt = mo.group(1), mo.group(2).strip()
            if letter in qs[cur]['options']:
                # duplicate letter -> belongs to a later question (pooled). stash.
                pending_opts.append((letter, txt))
            else:
                qs[cur]['options'][letter] = txt
            continue
        if cur is not None and not qs[cur]['options']:
            # still building stem
            qs[cur]['stem'] = (qs[cur]['stem'] + ' ' + ln).strip()
    # distribute pooled options to questions missing them, in order
    if pending_opts:
        missing = [n for n in sorted(qs) if len(qs[n]['options']) < 4]
        pi = 0
        for n in missing:
            for letter in ['a','b','c','d']:
                if letter not in qs[n]['options'] and pi < len(pending_opts):
                    # find next pooled with this letter
                    for k in range(pi, len(pending_opts)):
                        if pending_opts[k][0] == letter:
                            qs[n]['options'][letter] = pending_opts[k][1]
                            pending_opts.pop(k)
                            break
    return qs

ans_re = re.compile(r'^answer:\s*\(([a-d])\)\s*(.*)$')
an_re  = re.compile(r'^A(\d+)\b\s*(.*)$')

def parse_answers(body):
    res = {}
    cur = None
    lines = [norm(x) for x in body]
    lines = [x for x in lines if x and not x.startswith('PHOTOCOPIABLE') and not re.match(r'^\d+$',x)]
    sent = []
    for ln in lines:
        ma = an_re.match(ln)
        if ma:
            cur = int(ma.group(1)); sent=[]
            rest = ma.group(2).strip()
            if rest: sent.append(rest)
            res[cur] = {'letter':None,'word':None,'full':''}
            continue
        mr = ans_re.match(ln)
        if mr and cur is not None:
            res[cur]['letter'] = mr.group(1)
            res[cur]['word'] = mr.group(2).strip()
            res[cur]['full'] = ' '.join(sent).strip()
            sent=[]
            continue
        if cur is not None:
            sent.append(ln)
    return res

Q = blocks(qh_re)
A = blocks(ak_re)
akey = {}
for lvl,num,body in A:
    akey[(lvl,num)] = parse_answers(body)

LEVELMAP = {'Elementary':'A2','Intermediate':'B1','Advanced':'C1'}
quizzes = []
stats = {'tests':0,'q_total':0,'q_kept':0,'q_drop_noopt':0,'q_drop_nokey':0}
titles = {}
# grab titles from question headers' following line
qtitle = {}
idx = [i for i,l in enumerate(LINES) if qh_re.search(l)]
for i in idx:
    m = qh_re.search(LINES[i])
    qtitle[(m.group(1),int(m.group(2)))] = norm(LINES[i+1]) if i+1 < len(LINES) else ''

for lvl,num,body in Q:
    stats['tests']+=1
    qs = parse_questions(body)
    ak = akey.get((lvl,num),{})
    items = []
    for n in sorted(qs):
        stats['q_total']+=1
        opts = qs[n]['options']
        key = ak.get(n)
        if not key or not key['letter']:
            stats['q_drop_nokey']+=1; continue
        # ensure 4 options and correct word present
        cl = key['letter']; cw = key['word']
        if cl not in opts or not opts.get(cl):
            opts[cl] = cw
        if len([v for v in opts.values() if v]) < 2:
            stats['q_drop_noopt']+=1; continue
        stem = qs[n]['stem']
        if not stem or len(stem) < 3:
            stem = re.sub(re.escape(cw), '_____', key['full'], count=1) if key['full'] else stem
        if not stem or len(stem) < 3:
            stats['q_drop_noopt']+=1; continue
        ordered = [(l, opts[l]) for l in ['a','b','c','d'] if opts.get(l)]
        items.append({
            'q': stem,
            'options': [t for _,t in ordered],
            'answer': [i for i,(l,_) in enumerate(ordered) if l==cl][0],
            'answer_word': cw,
            'full': key['full'],
        })
        stats['q_kept']+=1
    if items:
        quizzes.append({
            'source': 'english-test.net',
            'src_level': lvl,
            'cefr': LEVELMAP[lvl],
            'title': qtitle.get((lvl,num),'') or f'{lvl} #{num}',
            'num': num,
            'questions': items,
        })

json.dump(quizzes, open('ihk_quizzes.json','w',encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps(stats, indent=2))
print('quizzes:', len(quizzes))
from collections import Counter
print(Counter(q['cefr'] for q in quizzes))
print(Counter(sum(len(q['questions']) for q in quizzes if q['cefr']==c) for c in ['A2','B1','C1']))
