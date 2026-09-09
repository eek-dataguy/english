# -*- coding: utf-8 -*-
"""Per-question explanation generator — STRICT.

explain(stem, options, answer_idx) returns a short question-specific HTML string
only when a rule can *verify* that the answer really is that grammar point
(usually: the whole option set belongs to a known closed class). Otherwise ''.
We accept low coverage in exchange for being right.
"""
import re

def _b(s):
    return '<b>' + s + '</b>'

def _prep(stem):
    s = re.sub(r'[_.]{3,}|…', ' ___ ', stem or '')
    return ' ' + re.sub(r'\s+', ' ', s).strip() + ' '

def _n(o):
    return re.sub(r'\s+', ' ', str(o).strip().lower()).strip(' .!?"’\'')

def _after(s):
    m = re.search(r'___\s+([A-Za-z][A-Za-z\'-]*)', s)
    return m.group(1) if m else ''

def _before(s):
    m = re.search(r'([A-Za-z][A-Za-z\'-]*)\s+___', s)
    return m.group(1).lower() if m else ''

def _same_verb(options):
    """True if the options are inflections of ONE verb (bare / -s / -ing / -ed / to-)."""
    stems = []
    for o in options:
        w = _n(o)
        w = re.sub(r"^(to|not|be|been|being|have|has|had|will|would|is|are|was|were|do|does|"
                   r"did|doesn't|didn't|don't)\s+", '', w)
        w = w.split()[0] if w.split() else ''
        for suf in ('ing', 'ed', 'es', 's', 'en'):
            if w.endswith(suf) and len(w) - len(suf) >= 2:
                w = w[:-len(suf)]
                break
        if w.endswith(('i',)):
            w = w[:-1] + 'y'
        if w:
            stems.append(w)
    return len(stems) >= 2 and len(set(stems)) == 1

ARTS = {'a', 'an', 'the', '*', '-', '', 'no'}
QUANT = {'some', 'any', 'much', 'many', 'a lot of', 'lots of', 'a few', 'few', 'a little',
         'little', 'no', 'none', 'plenty of', 'enough', 'a lot', 'lots'}
MODALS = {'must', "mustn't", 'have to', "don't have to", "doesn't have to", 'had to',
          'should', "shouldn't", 'ought to', 'can', "can't", 'could', "couldn't", 'may',
          'might', 'will', "won't", 'would', "wouldn't", 'need to', "needn't", 'shall',
          'used to', 'be able to'}
MODAL_GLOSS = {
    'must': "obligation or strong necessity",
    "mustn't": "prohibition — not allowed",
    'have to': "obligation, often from an outside rule",
    "don't have to": "no obligation — it isn't necessary",
    "doesn't have to": "no obligation — it isn't necessary",
    'had to': "past obligation",
    'should': "advice — the right thing to do",
    "shouldn't": "advice against doing it",
    'ought to': "advice, like 'should'",
    'can': "ability or permission",
    "can't": "impossibility, or being sure it is not true",
    'could': "past ability, or a polite / less-certain possibility",
    'may': "permission, or possibility",
    'might': "possibility (less sure than 'may')",
    'will': "a decision made now, a prediction, or a promise",
    'would': "an imagined / unreal situation, or politeness",
    'need to': "necessity",
    "needn't": "no necessity",
    'used to': "a past habit or state that is no longer true",
    'be able to': "ability (used where 'can' has no form)",
}
REL = {'who': "for people", 'which': "for things and animals",
       'that': "for people or things in a defining clause (no commas)",
       'whose': "for possession — whose + noun", 'where': "for places", 'when': "for times"}
TAG_RE = re.compile(r'^(is|are|was|were|do|does|did|have|has|had|will|would|can|could|should|'
                    r"isn't|aren't|wasn't|weren't|don't|doesn't|didn't|haven't|hasn't|hadn't|"
                    r"won't|wouldn't|can't|couldn't|shouldn't)\s+(i|you|he|she|it|we|they|there)$")
GI_TRIG_ING = ("enjoy mind finish avoid keep consider suggest admit deny practise practice miss "
               "fancy postpone imagine risk recommend").split()
GI_TRIG_TO = ("want decide hope promise offer agree refuse manage plan expect learn afford "
              "pretend arrange choose ask tell would like").split()


def explain(stem, options, ans):
    s = _prep(stem)
    sl = s.lower()
    opts = [_n(o) for o in options]
    if not (0 <= ans < len(opts)) or not opts[ans]:
        return ''
    a = opts[ans]
    A = set(opts)
    nxt = _after(s)
    trig = _before(s)
    multi = bool(re.search(r' [/-] ', a))   # two-gap answer -> skip single-point rules
    BE_FORMS = {'am', 'is', 'are', 'was', 'were', 'be', 'been', 'being', "'m", "'s", "'re"}
    DET = {'a', 'an', 'the', 'this', 'that', 'these', 'those', 'my', 'your', 'his', 'her',
           'its', 'our', 'their', 'no', 'some', 'any'}

    # ---- articles: whole option set is articles ----
    if A <= ARTS and a in ('a', 'an', 'the'):
        if a == 'an':
            return f"{_b('an')} before a {_b('vowel sound')}" + (f" — “{nxt}”." if nxt else ".")
        if a == 'a':
            return f"{_b('a')} before a {_b('consonant sound')}" + (f" (“{nxt}”)" if nxt else "") + \
                   " — singular countable noun, first mention."
        return f"{_b('the')} — it is clear which one is meant (already mentioned, unique, " \
               f"or made specific here)."

    # ---- some / any ----
    if A <= QUANT and a in ('some', 'any'):
        neg = bool(re.search(r"\b(not|n't|never|no|without|hardly)\b", sl))
        qm = s.strip().endswith('?')
        if a == 'some' and not neg and not qm:
            return f"{_b('some')} in positive statements (and in offers / requests)."
        if a == 'any' and (neg or qm):
            return f"{_b('any')} in negatives and questions."
        return ''
    # ---- much / many / a few / a little ----
    if A <= QUANT and a in ('much', 'many', 'a few', 'a little', 'few', 'little'):
        plural = a in ('many', 'a few', 'few')
        return f"{_b(a)} + {_b('plural countable' if plural else 'uncountable')} noun" + \
               (f" (“{nxt}”)." if nxt else ".")

    # ---- modals: whole option set is modals ----
    if A <= MODALS and a in MODAL_GLOSS:
        tail = "" if a in ('used to', 'be able to', 'have to', 'had to', "don't have to",
                           "doesn't have to", 'need to', 'ought to') else \
               " Followed by the bare infinitive (no 'to')."
        return f"{_b(a)} = {MODAL_GLOSS[a]}.{tail}"

    # ---- question tag: ", ___ ?" and options are aux+pronoun ----
    if re.search(r',\s*___\s*\?\s*$', s) and all(TAG_RE.match(o) for o in opts if o):
        first = sl.split(',')[0]
        pos = not re.search(r"\b(not|n't|never|no|nobody|nothing|hardly|little)\b", first)
        return f"A {'positive' if pos else 'negative'} statement takes a " \
               f"{_b('negative' if pos else 'positive')} question tag, repeating the auxiliary: {_b(a)}."

    # ---- relative pronoun: options are a subset of relatives ----
    if A <= (set(REL) | {'what', 'whom'}) and a in REL and len(A) >= 2:
        extra = ""
        if a == 'which' and re.search(r',\s*___', s):
            extra = " Here it refers back to the whole idea before the comma."
        return f"{_b(a)} — {REL[a]}.{extra}"

    # ---- comparative + than / superlative ----
    NOT_COMP = {'over', 'under', 'after', 'ever', 'never', 'other', 'rather', 'either', 'neither',
                'together', 'whether', 'however', 'moreover', 'there', 'here', 'where', 'their',
                'her', 'per', 'super', 'order', 'later', 'water', 'father', 'mother', 'brother',
                'summer', 'winter', 'dinner', 'corner', 'answer', 'number', 'member', 'paper',
                'matter', 'letter', 'butter', 'cover', 'power', 'flower', 'quarter', 'character',
                'computer', 'teacher', 'manager', 'passenger', 'customer', 'consumer', 'lawyer'}
    is_comp = (a not in NOT_COMP) and (
        a.startswith(('more ', 'less ')) or a in ('better', 'worse', 'further', 'farther', 'older',
        'elder') or (a.endswith('er') and len(a.split()) == 1 and len(a) >= 5))
    # the gap (the comparative) and 'than' must be close together
    if not multi and is_comp and re.search(r'___(\s+\S+){0,4}\s+than\b', sl):
        return f"Use {_b('than')} after a comparative ({_b(a)})."
    if (a.startswith('the ') and (a.endswith('est') or ' most ' in a)) or \
       (a in ('best', 'worst') and ' the ' in sl):
        return f"Superlative: {_b('the')} + …est / most … — one out of three or more."

    # ---- gerund / infinitive: options are forms of ONE verb, incl. -ing and to- ----
    has_ing = any(o.endswith('ing') and o.split()[0] not in BE_FORMS for o in opts)
    has_to = any(o.startswith('to ') for o in opts)
    cont = a.split()[0] in BE_FORMS or trig in BE_FORMS      # continuous tense, not a gerund
    noun_mod = a.endswith('ing') and nxt and trig in DET     # "a reading lamp" -> compound noun
    if not multi and not cont and not noun_mod and _same_verb(options) and has_ing and \
       (has_to or any(len(o.split()) == 1 for o in opts)):
        if a.endswith('ing'):
            if re.search(r"\b(of|about|in|on|at|by|for|after|before|without|instead of)\s+___", sl):
                return f"After a {_b('preposition')} use the {_b('-ing')} form: {_b(a)}."
            if trig in GI_TRIG_ING:
                return f"After {_b(trig)} use the {_b('-ing')} form: {_b(a)}."
            return f"This verb takes the {_b('-ing')} form here: {_b(a)}."
        if a.startswith('to '):
            if trig in GI_TRIG_TO:
                return f"After {_b(trig)} use {_b('to + infinitive')}: {_b(a)}."
            return f"This verb is followed by {_b('to + infinitive')}: {_b(a)}."

    # ---- been vs gone (both present) ----
    if {'been', 'gone'} <= A and a in ('been', 'gone'):
        if a == 'been':
            return f"{_b('been')} = went there and {_b('came back')}. (‘gone’ = went and is still away.)"
        return f"{_b('gone')} = went there and {_b('is still away')}. (‘been’ = went and came back.)"

    # ---- verb 'to be' ----
    BE = {'am', 'is', 'are', "'m", "'s", "'re", "isn't", "aren't", "am not", 'be'}
    if A <= BE and a in ('am', 'is', 'are', "isn't", "aren't"):
        return f"Present of {_b('be')}: I {_b('am')}, he/she/it {_b('is')}, you/we/they {_b('are')}."

    # ---- so / such / too / enough ----
    SST = {'so', 'such', 'such a', 'such an', 'so many', 'so much', 'too', 'enough'}
    if A <= SST and a in SST:
        return {
            'so': f"{_b('so')} + adjective/adverb on its own (so tired).",
            'so many': f"{_b('so many')} + plural countable noun.",
            'so much': f"{_b('so much')} + uncountable noun.",
            'such': f"{_b('such')} (+ adjective) + noun (such nice people).",
            'such a': f"{_b('such a')} (+ adjective) + singular noun (such a good day).",
            'such an': f"{_b('such an')} before a vowel sound (such an old car).",
            'too': f"{_b('too')} + adjective = more than is wanted (too heavy).",
            'enough': f"adjective + {_b('enough')} / {_b('enough')} + noun = the right amount.",
        }[a]

    # ---- prepositions of time: options are only at/on/in ----
    if A <= {'at', 'on', 'in'} and a in ('at', 'on', 'in'):
        AT = re.search(r"\b(night|midnight|noon|\d+ ?[ap]?\.?m?\.?|\d o'?clock|the weekend|"
                       r"weekends?|christmas|easter|the moment|lunchtime)\b", sl)
        ON = re.search(r"\b((next |last |this )?(mon|tues|wednes|thurs|fri|satur|sun)day|"
                       r"my birthday|christmas day|\d{1,2}(st|nd|rd|th)?\s+(of\s+)?(jan|feb|mar|apr|"
                       r"may|jun|jul|aug|sep|oct|nov|dec))\b", sl)
        IN = re.search(r"\b(january|february|march|april|may|june|july|august|september|october|"
                       r"november|december|(19|20)\d\d|the morning|the afternoon|the evening|"
                       r"summer|winter|spring|autumn)\b", sl)
        if a == 'at' and AT:
            return f"{_b('at')} for clock times, night and holiday periods — “{AT.group(0).strip()}”."
        if a == 'on' and ON:
            return f"{_b('on')} for days and dates — “{ON.group(0).strip()}”."
        if a == 'in' and IN:
            return f"{_b('in')} for months, years, seasons and parts of the day — “{IN.group(0).strip()}”."

    # ---- present perfect vs past simple: options are forms of ONE verb + a signal word ----
    if _same_verb(options) and not multi:
        PP = re.search(r"\b(yet|already|ever|never|so far|just|recently|lately|since \w+|"
                       r"for \w+ (years|months|weeks|days)|this (week|month|year))\b", sl)
        PS = re.search(r"\b(yesterday|last (night|week|month|year|summer)|"
                       r"\d+ (days?|weeks?|months?|years?) ago|in (19|20)\d\d|when i was)\b", sl)
        pp_ans = a.split()[0] in ('have', 'has', "haven't", "hasn't", "'ve", "'s") or \
            a in ('been', 'gone', 'done', 'seen')
        ps_ans = bool(re.search(r"(ed$|went|saw|did|didn't|was|were|had|got|came|took|made|"
                                r"bought|left|found|knew|gave)", a)) and not pp_ans
        if PP and pp_ans:
            return f"“{PP.group(0).strip()}” goes with the {_b('present perfect')} " \
                   f"(have/has + past participle): {_b(a)}."
        if PS and ps_ans:
            return f"A finished past time (“{PS.group(0).strip()}”) needs the {_b('past simple')}: {_b(a)}."

    # ---- conditionals: 'if'/'wish' present and options are verb forms ----
    if _same_verb(options) and not multi and 'as if' not in sl and \
       re.search(r"(^|\s)if\s|\bunless\b|\bi wish\b|\bwish (i|he|she|we|they|you)\b|\bif only\b", sl):
        if 'would have' in a or a.startswith('had ') or re.search(r"had \w+(ed|en)\b", a):
            return f"Third conditional (unreal past): {_b('if + past perfect, would have + participle')}."
        if 'would' in a:
            return f"Second conditional (unreal / unlikely now): {_b('if + past simple, would + verb')}."
        if 'will' in a or "'ll" in a:
            return f"First conditional (real future): {_b('if + present simple, will + verb')}."

    # ---- subject vs object pronoun / possessives: whole set is pronouns ----
    SUBJ = {'i', 'you', 'he', 'she', 'it', 'we', 'they'}
    OBJ = {'me', 'you', 'him', 'her', 'it', 'us', 'them'}
    PADJ = {'my', 'your', 'his', 'her', 'its', 'our', 'their'}
    PPRN = {'mine', 'yours', 'his', 'hers', 'ours', 'theirs'}
    REFL = {'myself', 'yourself', 'himself', 'herself', 'itself', 'ourselves', 'yourselves', 'themselves'}
    allpr = SUBJ | OBJ | PADJ | PPRN | REFL
    if A <= allpr and len(A) >= 2:
        if a in REFL:
            return f"{_b(a)} — a {_b('reflexive pronoun')}: the subject and object are the same."
        if a in PADJ and a not in PPRN and nxt:
            return f"{_b(a)} — a {_b('possessive adjective')}, used before a noun (“{a} {nxt}”)."
        if a in PPRN and a not in PADJ:
            return f"{_b(a)} — a {_b('possessive pronoun')}: it stands alone, no noun after it."
        if a in OBJ and a not in SUBJ and re.search(r"\b(to|for|with|at|about|of|from)\s+___|"
                                                    r"\b(see|help|tell|give|ask|meet|like|know|love|"
                                                    r"call|thank|show|send)\s+___", sl):
            return f"{_b(a)} — an {_b('object pronoun')}: it comes after a verb or preposition."
        if a in SUBJ and a not in OBJ and re.search(r"^\s*___\s+(am|is|are|was|were|do|does|did|have|"
                                                    r"has|had|will|can|could|would|should|\w+s)\b", sl):
            return f"{_b(a)} — a {_b('subject pronoun')}: it goes before the verb."

    return ''
