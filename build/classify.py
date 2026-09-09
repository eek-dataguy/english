# -*- coding: utf-8 -*-
"""Rule-based grammar-topic classifier + teaching notes.

classify(stem, options) -> category id (see TOPICS).
Content-based: looks mostly at the answer options, which in gap-fill items
are a tight minimal pair that reveals the grammar point being tested.
"""
import re

TOPICS = {
    'prepositions-time': {
        'name': 'Prepositions of time',
        'note': "Use <b>at</b> for clock times, <b>night</b>, <b>the weekend</b> and festivals "
                "(at 6, at night, at Christmas). Use <b>on</b> for days and dates "
                "(on Monday, on 5 June, on my birthday). Use <b>in</b> for months, years, "
                "seasons and parts of the day (in July, in 2020, in winter, in the morning).",
    },
    'prepositions-place': {
        'name': 'Prepositions of place',
        'note': "Use <b>at</b> for a point or a place seen as a point (at the door, at the bus stop, "
                "at school). Use <b>in</b> for enclosed or bounded spaces (in the room, in London, "
                "in a car). Use <b>on</b> for surfaces and lines (on the table, on the wall, on the bus).",
    },
    'prepositions-other': {
        'name': 'Prepositions & dependent prepositions',
        'note': "Many verbs, adjectives and nouns take a fixed preposition: "
                "<b>depend on</b>, <b>good at</b>, <b>interested in</b>, <b>afraid of</b>, "
                "<b>listen to</b>, <b>wait for</b>, <b>arrive at/in</b>. These have to be learned "
                "as whole chunks.",
    },
    'articles': {
        'name': 'Articles (a / an / the / zero)',
        'note': "Use <b>a/an</b> with a singular countable noun mentioned for the first time "
                "(<b>a</b> before a consonant sound, <b>an</b> before a vowel sound). Use <b>the</b> "
                "when it is clear which one you mean, or it is unique. Use <b>no article</b> for "
                "plural or uncountable nouns in general (I like music), and most names.",
    },
    'present-simple-continuous': {
        'name': 'Present simple vs. continuous',
        'note': "<b>Present simple</b> for habits, routines and permanent facts "
                "(I <b>work</b> in a bank; water <b>boils</b> at 100°). "
                "<b>Present continuous</b> (am/is/are + -ing) for things happening now or "
                "around now, and fixed future arrangements (I<b>'m working</b> late today). "
                "Stative verbs (know, like, want, believe) are normally not continuous.",
    },
    'past-simple-continuous': {
        'name': 'Past simple vs. past continuous',
        'note': "<b>Past simple</b> for finished actions and the main events of a story "
                "(she <b>arrived</b>, opened the door). <b>Past continuous</b> (was/were + -ing) "
                "for an action in progress around a past moment, often interrupted by a past "
                "simple action (while I <b>was cooking</b>, the phone <b>rang</b>).",
    },
    'present-perfect': {
        'name': 'Present perfect vs. past simple',
        'note': "<b>Present perfect</b> (have/has + past participle) links the past to now: "
                "experience (I<b>'ve been</b> to Japan), recent news, and unfinished time "
                "(<b>this week</b>, <b>yet</b>, <b>already</b>, <b>since</b>, <b>for</b>). "
                "Use <b>past simple</b> with a finished past time (yesterday, in 2019, ago).",
    },
    'future': {
        'name': 'Talking about the future',
        'note': "<b>will</b> for predictions, decisions made now and offers/promises. "
                "<b>be going to</b> for plans and intentions, and predictions from present "
                "evidence. <b>Present continuous</b> for fixed arrangements with a time/place. "
                "After <b>when/if/before/as soon as</b>, use the present, not <b>will</b>.",
    },
    'conditionals': {
        'name': 'Conditionals',
        'note': "Zero: <b>if + present, present</b> (general truths). "
                "First: <b>if + present, will + verb</b> (real future possibility). "
                "Second: <b>if + past, would + verb</b> (unreal/unlikely present or future). "
                "Third: <b>if + past perfect, would have + participle</b> (unreal past).",
    },
    'modals': {
        'name': 'Modal verbs',
        'note': "Modals are followed by the bare infinitive. "
                "<b>can/could</b> ability & permission, <b>must/have to</b> obligation, "
                "<b>mustn't</b> prohibition vs <b>don't have to</b> = no obligation, "
                "<b>should/ought to</b> advice, <b>might/may/could</b> possibility. "
                "For deduction: <b>must</b> (sure it's true) / <b>can't</b> (sure it's false).",
    },
    'gerund-infinitive': {
        'name': 'Gerund vs. infinitive',
        'note': "Some verbs take <b>-ing</b> (enjoy, finish, avoid, mind, suggest, keep). "
                "Some take <b>to + infinitive</b> (want, decide, hope, promise, offer, agree). "
                "After prepositions always use <b>-ing</b>. A few (stop, remember, try) change "
                "meaning with each form.",
    },
    'comparatives-superlatives': {
        'name': 'Comparatives & superlatives',
        'note': "Short adjectives: <b>-er / -est</b> (cheap → cheaper → the cheapest). "
                "Longer adjectives: <b>more / the most</b> (expensive → more expensive). "
                "Use <b>than</b> after a comparative, and <b>the</b> before a superlative. "
                "Irregular: good → better → best; bad → worse → worst.",
    },
    'quantifiers': {
        'name': 'Quantifiers (some / any / much / many …)',
        'note': "<b>some</b> in positives and offers/requests; <b>any</b> in negatives and questions. "
                "<b>much</b> + uncountable, <b>many</b> + plural countable (both mostly in "
                "negatives/questions); <b>a lot of</b> works everywhere. "
                "<b>a few</b> + countable, <b>a little</b> + uncountable = a small positive amount.",
    },
    'countable-uncountable': {
        'name': 'Countable & uncountable nouns',
        'note': "Uncountable nouns (information, advice, furniture, bread, money) have no plural "
                "and take a singular verb. Count them with a phrase: <b>a piece of</b> advice, "
                "<b>two slices of</b> bread. Use <b>much/little</b> with uncountable, "
                "<b>many/few</b> with countable.",
    },
    'relative-clauses': {
        'name': 'Relative clauses',
        'note': "<b>who</b> for people, <b>which</b> for things, <b>that</b> for either (in "
                "defining clauses), <b>whose</b> for possession, <b>where</b> for places. "
                "You can drop the pronoun when it is the object of the clause "
                "(the film (that) I saw). Don't use <b>what</b> as a relative pronoun.",
    },
    'question-tags': {
        'name': 'Question tags',
        'note': "The tag reverses the main clause: positive statement → negative tag, and vice "
                "versa (You're coming, <b>aren't you</b>? / He didn't call, <b>did he</b>?). "
                "It repeats the auxiliary (or do/does/did), and uses a pronoun.",
    },
    'questions-word-order': {
        'name': 'Questions & word order',
        'note': "Questions invert subject and auxiliary: <b>(Wh-) + auxiliary + subject + verb</b> "
                "(Where <b>do you</b> live? What <b>has she</b> done?). In reported or indirect "
                "questions the word order goes back to normal (I don't know where <b>he lives</b>).",
    },
    'passive': {
        'name': 'The passive',
        'note': "Passive = <b>be</b> (in the right tense) + <b>past participle</b> "
                "(is made, was built, has been sold, will be done). Use it when the doer is "
                "unknown, obvious or unimportant; add the doer with <b>by</b> if needed.",
    },
    'reported-speech': {
        'name': 'Reported speech',
        'note': "Tenses usually shift back one step (am → was, will → would, have done → had done), "
                "and pronouns / time words change (now → then, tomorrow → the next day). "
                "<b>say</b> has no person object; <b>tell</b> needs one (tell <b>me</b>).",
    },
    'pronouns': {
        'name': 'Pronouns & possessives',
        'note': "Subject (I, he, they) vs object (me, him, them) pronouns; "
                "possessive adjectives (my, his, their) come before a noun, possessive pronouns "
                "(mine, his, theirs) stand alone. Reflexives (myself, themselves) = subject and "
                "object are the same.",
    },
    'verb-to-be': {
        'name': "Verb 'to be' and there is / are",
        'note': "Present: I <b>am</b>, he/she/it <b>is</b>, you/we/they <b>are</b>; "
                "negatives add <b>not</b>, questions invert (Is she…?). "
                "<b>There is</b> + singular / uncountable, <b>there are</b> + plural.",
    },
    'irregular-verbs': {
        'name': 'Irregular verb forms',
        'note': "Irregular verbs don't add <b>-ed</b>. Learn the three forms: "
                "base / past simple / past participle — go/went/gone, take/took/taken, "
                "break/broke/broken. The past participle is the one you need after "
                "<b>have</b> and in the passive.",
    },
    'used-to': {
        'name': 'used to / would (past habits)',
        'note': "<b>used to + infinitive</b> for past habits and past states that are no longer "
                "true (I <b>used to</b> smoke; there <b>used to</b> be a shop here). "
                "Questions/negatives: <b>did/didn't use to</b>. <b>be used to + -ing</b> is "
                "different — it means 'be accustomed to'.",
    },
    'so-such-too-enough': {
        'name': 'so / such / too / enough',
        'note': "<b>so</b> + adjective/adverb, <b>such</b> + (a/an) + (adjective) + noun. "
                "<b>too</b> + adjective = more than is wanted (too hot); "
                "adjective + <b>enough</b> / <b>enough</b> + noun = the right amount or more.",
    },
    'phrasal-verbs': {
        'name': 'Phrasal verbs',
        'note': "A verb + particle whose meaning is often idiomatic (give up, put off, look after, "
                "run out of). With many, an object pronoun goes in the middle "
                "(turn <b>it</b> on, not turn on it).",
    },
    'confusing-words': {
        'name': 'Easily confused words',
        'note': "Pairs that learners mix up: make/do, say/tell, borrow/lend, bring/take, "
                "as/like, lie/lay, its/it's, been/gone. Check the exact pattern each one needs.",
    },
    'idioms-collocation': {
        'name': 'Idioms & collocations',
        'note': "These are fixed expressions where the words don't add up literally "
                "(a piece of cake, put up with, top-drawer). The only reliable approach is "
                "to meet them in context and memorise them whole.",
    },
    'vocabulary': {
        'name': 'Vocabulary in context',
        'note': "Choosing the word that fits the meaning and the collocations of the sentence. "
                "Watch the words just before and after the gap — they usually decide the answer.",
    },
    'tenses-verb-forms': {
        'name': 'Verb tenses & forms',
        'note': "The options are forms of one verb, so the sentence is testing <b>tense</b> or "
                "<b>form</b>. Find the time reference (now / yesterday / since 2010 / tomorrow) "
                "and any signal words, then match the tense: -ing for continuous, "
                "have/has + participle for present perfect, will/going to for future.",
    },
    'general': {
        'name': 'Mixed grammar',
        'note': "A mix of points. Read the whole sentence, decide what is being tested "
                "(tense? preposition? word form?), then eliminate options that break that rule.",
    },
}

PREPS = {'at', 'on', 'in', 'by', 'for', 'to', 'of', 'with', 'from', 'about', 'off', 'into',
         'over', 'under', 'up', 'out', 'through', 'across', 'between', 'among', 'behind',
         'beside', 'near', 'onto', 'towards', 'toward', 'against', 'during', 'since', 'until',
         'till', 'within', 'without', 'along', 'round', 'around', '*', '-', '—'}
TIME_WORDS = re.compile(r'\b(weekend|weekends|monday|tuesday|wednesday|thursday|friday|saturday|'
                        r'sunday|morning|afternoon|evening|night|noon|midnight|christmas|easter|'
                        r'birthday|january|february|march|april|may|june|july|august|september|'
                        r'october|november|december|summer|winter|spring|autumn|fall|'
                        r"o'?clock|\d{4}|new year|the moment|weekdays?)\b", re.I)
ARTS = {'a', 'an', 'the', '*', '-', '—', '', 'no article', 'some', 'any'}
REL = {'who', 'which', 'that', 'whose', 'whom', 'where', 'when', 'what', 'why'}
QUANT = {'some', 'any', 'much', 'many', 'a lot', 'lots', 'a lot of', 'lots of', 'a few', 'few',
         'a little', 'little', 'no', 'none', 'plenty', 'enough', 'several'}
AUX = {'do', 'does', 'did', "don't", "doesn't", "didn't", 'have', 'has', 'had', "haven't",
       "hasn't", "hadn't", 'is', 'are', 'was', 'were', 'am', "isn't", "aren't", "wasn't",
       "weren't", 'be', 'been', 'being', 'will', 'would', 'shall', 'should'}
MODALS = {'can', 'could', 'may', 'might', 'must', 'should', 'shall', 'will', 'would',
          'ought to', 'have to', 'has to', 'had to', "mustn't", "can't", "couldn't",
          "shouldn't", "won't", "wouldn't", 'be able to', 'need to', "needn't"}
PRON = {'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them',
        'my', 'your', 'his', 'its', 'our', 'their', 'mine', 'yours', 'hers', 'ours', 'theirs',
        'myself', 'yourself', 'himself', 'herself', 'itself', 'ourselves', 'themselves'}
BE = {'am', 'is', 'are', 'was', 'were', 'be', 'been', 'being', "isn't", "aren't", "wasn't",
      "weren't", "am not", 'there is', 'there are', "there's", 'there was', 'there were'}

def _norm(o):
    return re.sub(r'\s+', ' ', o.strip().lower().strip('.').strip())

def _set(options):
    return {_norm(o) for o in options}

TENSE_MARK = ('was', 'were', 'have', 'has', 'had', 'will', 'is', 'are', 'am', 'been',
              'be', 'being', "doesn't", "didn't", "don't", "won't", "hasn't", "haven't",
              'used', 'going', 'did', 'do', 'does', 'would', 'shall', 'should')

def _stem(word):
    w = word
    for suf in ('ing', 'ed', 'es', 's', 'en'):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            return w[:-len(suf)]
    return w

def _is_verbish_pair(options):
    """options look like different tense/form variants of the SAME verb."""
    toks = [o for o in (_norm(x) for x in options) if o]
    if len(toks) < 3:
        return False
    # collect the 'main' verb-ish word of each option
    heads = []
    has_marker = False
    for t in toks:
        ws = t.split()
        for w in ws:
            if w in TENSE_MARK:
                has_marker = True
        cand = [w for w in ws if w not in TENSE_MARK and w not in ('to', 'not', 'a', 'the')]
        if cand:
            heads.append(_stem(cand[-1]))
    if not heads:
        return False
    # same base verb across most options?
    from collections import Counter
    common, cnt = Counter(heads).most_common(1)[0]
    same_verb = cnt >= max(2, len(toks) - 1)
    inflected = sum(1 for t in toks if any(x.endswith(('ing', 'ed', 'en')) for x in t.split()))
    return same_verb and (has_marker or inflected >= 2)

CONTENT_WORD = re.compile(r'^[a-z]+(?:ly|ness|tion|ment|ful|less|ous|ive|able|ible|ance|ence)?$')

def _looks_lexical(options):
    """single-word non-grammatical choices => vocabulary, not grammar."""
    toks = [_norm(o) for o in options if _norm(o)]
    if len(toks) < 3:
        return False
    if not all(len(t.split()) == 1 for t in toks):
        return False
    funct = PREPS | ARTS | REL | QUANT | AUX | PRON | BE | {m for m in MODALS}
    return sum(1 for t in toks if t in funct) <= 1

def classify(stem, options, hint=''):
    s = (stem or '').lower()
    opts = _set(options)
    hint = (hint or '').lower()

    # ---- strong hint from source title / topic label ----
    H = [
        ('question tag', 'question-tags'), ('tag', 'question-tags'),
        ('conditional', 'conditionals'), ('relative', 'relative-clauses'),
        ('gerund', 'gerund-infinitive'), ('infinitive', 'gerund-infinitive'),
        ('passive', 'passive'), ('reported', 'reported-speech'),
        ('phrasal', 'phrasal-verbs'), ('irregular verb', 'irregular-verbs'),
        ('present perfect', 'present-perfect'), ('past perfect', 'present-perfect'),
        ('comparative', 'comparatives-superlatives'), ('superlative', 'comparatives-superlatives'),
        ('preposition', 'prepositions-other'), ('article', 'articles'),
        ('modal', 'modals'), ('pronoun', 'pronouns'), ('possessive', 'pronouns'),
        ('countable', 'countable-uncountable'), ('much, many', 'quantifiers'),
        ('some, any', 'quantifiers'), ('used to', 'used-to'),
        ('make and do', 'confusing-words'), ('make, do', 'confusing-words'),
        ('confusing', 'confusing-words'), ('slang', 'idioms-collocation'),
        ('idiom', 'idioms-collocation'), ('question', 'questions-word-order'),
        ('present simple', 'present-simple-continuous'),
        ('present continuous', 'present-simple-continuous'),
        ('past simple', 'past-simple-continuous'), ('past continuous', 'past-simple-continuous'),
        ('tense', 'general'), ('verb to be', 'verb-to-be'),
    ]
    for k, v in H:
        if k in hint:
            return v

    # ---- content rules on the options ----
    if opts and opts <= ARTS and ({'a', 'an'} & opts or 'the' in opts):
        return 'articles'

    if opts and opts <= (PREPS | {''}):
        # preposition item — time vs place vs other
        if TIME_WORDS.search(s):
            return 'prepositions-time'
        if re.search(r'\b(in|at|on)\b.*\b(house|room|street|city|town|station|airport|school|'
                     r'work|home|table|wall|floor|door|corner|shop|office|country|world|park|'
                     r'bus|train|car|kitchen|garden|beach|mountain)s?\b', s):
            return 'prepositions-place'
        return 'prepositions-other'

    if opts and opts <= REL and len(opts) >= 2:
        return 'relative-clauses'

    if opts and opts <= QUANT and len(opts) >= 2:
        return 'quantifiers'

    if opts and opts <= MODALS and len(opts) >= 2:
        return 'modals'

    if opts and opts <= PRON and len(opts) >= 2:
        return 'pronouns'

    if opts and opts <= BE and len(opts) >= 2:
        return 'verb-to-be'

    if opts and opts <= AUX and len(opts) >= 2:
        return 'questions-word-order'

    # question tag shape:  ... , ___ ?    with aux+pronoun options
    if re.search(r',\s*_{2,}\s*\?\s*$', stem or '') or re.search(r',\s*______\s*\?', stem or ''):
        return 'question-tags'
    if all(re.match(r"^(is|are|was|were|do|does|did|have|has|will|won't|isn't|aren't|wasn't|"
                    r"weren't|don't|doesn't|didn't|haven't|hasn't|can|can't|would|wouldn't)\s+"
                    r"(i|you|he|she|it|we|they)$", _norm(o)) for o in options if _norm(o)) and options:
        return 'question-tags'

    if 'than' in s and any(w in s for w in (' more ', ' less ')) or \
       any(_norm(o).endswith('er') for o in options) and 'than' in s:
        return 'comparatives-superlatives'
    if any(x in _norm(o) for o in options for x in ('more ', 'most ', ' -er', 'est')) and \
       re.search(r'\bthan\b|\bthe\b.*\b(in|of)\b', s):
        return 'comparatives-superlatives'

    if {'used to', "didn't use to", 'use to', 'would use to'} & opts:
        return 'used-to'

    # gerund / infinitive minimal pair:  to X / X-ing / X
    gi = 0
    for o in (_norm(x) for x in options):
        if o.startswith('to ') or o.endswith('ing') or ' ' not in o:
            gi += 1
    if gi >= 3 and any(_norm(o).endswith('ing') for o in options) and \
       any(_norm(o).startswith('to ') for o in options):
        return 'gerund-infinitive'

    if re.search(r'\b(am|is|are|was|were|be|been|being)\b', s) and \
       any(_norm(o).endswith(('ed', 'en', 't')) for o in options) and _is_verbish_pair(options):
        # crude passive vs active
        if re.search(r'\bby\b', s) or ' by ' in s:
            return 'passive'

    if 'if ' in s or s.startswith('if') or re.search(r'\bunless\b|\bwould\b', s):
        if _is_verbish_pair(options):
            return 'conditionals'

    if re.search(r'\b(yesterday|last night|last week|last year|ago|this morning|just now)\b', s) and \
       _is_verbish_pair(options):
        return 'past-simple-continuous'
    if re.search(r'\b(yet|already|ever|never|since|for years|so far|recently|just)\b', s) and \
       any('have' in _norm(o) or 'has' in _norm(o) or _norm(o).endswith(('ed', 'en')) for o in options):
        return 'present-perfect'
    if re.search(r"\b(will|going to|tomorrow|next week|next year|soon|tonight)\b", s) and _is_verbish_pair(options):
        return 'future'
    if re.search(r'\b(usually|every day|always|often|never|sometimes)\b', s) and _is_verbish_pair(options):
        return 'present-simple-continuous'

    if _is_verbish_pair(options):
        return 'tenses-verb-forms'  # tense/verb-form contrast, point unspecified

    if 'idiom' in hint or 'slang' in hint:
        return 'idioms-collocation'

    if _looks_lexical(options):
        return 'vocabulary'

    # short phrase choices that aren't a clean grammar shape -> word choice
    if all(len(_norm(o).split()) <= 3 for o in options if _norm(o)):
        return 'vocabulary'

    return 'general'
