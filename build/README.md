# Extraction pipeline

Turns the three source PDFs into the JSON the website loads (`../web/data/`).

## Sources

| PDF | What it is | Used |
|---|---|---|
| `English Grammar Tests.pdf` | english-test.net "Incomplete Sentences", 853 tests × 10 Q, with answer keys. Levels: Elementary / Intermediate / Advanced. | ✅ all of it |
| `English Grammar Tests (useful).pdf` | Older subset of the same collection, worse text layer. | ❌ redundant |
| `GnGozbEwKKuzJeFZwlP44jd4P7XPAoUUz9lMqJEX.pdf` | "Test Master" (Atalay Oguz). Book 1 = grammar (~9 200 Q). Book 2 = vocabulary, Book 3 = reading. | ✅ Book 1 Parts A, B, E |

Test Master Parts C and D ("multi-level" tests) are skipped – they carry no clean
per-question level label. Books 2–3 are vocabulary/reading, out of scope.

## Steps

```
pip install pdfminer.six
python decode_tests_pdf.py     # -> tests_dec.txt   (de-obfuscates the font cipher)
python parse_ihk.py            # -> ihk_quizzes.json (english-test.net)
python parse_tm.py             # -> tm_quizzes.json  (Test Master A/B/E, via pdfminer coords)
python build_site.py           # -> ../web/data/*.json  (uses classify.py)
```

`classify.py` tags every question with a grammar topic (prepositions of time,
conditionals, gerund/infinitive, …) from the option shape + the source test's
topic label, and holds the short teaching note shown after each answer. The
english-test.net set is mostly idioms / word-choice, so a large share lands in
the `idioms-collocation` and `vocabulary` buckets — those are real topics too.

`build_site.py` also drops questions whose options were corrupted by column-merge
in the scanned PDF (long option strings, stray blanks, dialogue markers) – about
1.5 % of Test Master items.

## CEFR mapping (approximate)

| Source label | CEFR |
|---|---|
| Test Master Elementary (Part A) | A1 |
| Test Master Pre-Intermediate / Part E Elementary / Part B "(Elem/Pre-Int)" | A2 |
| english-test.net Elementary | A2 |
| Test Master Intermediate / english-test.net Intermediate | B1 |
| Test Master Part B "(Int/Upper-Int)" | B2 |
| english-test.net Advanced / Test Master Part E Advanced | C1 |

These are best-effort. english-test.net "Intermediate" in particular spans B1–B2
(its idiom/phrasal-verb tests lean harder); each quiz shows its original source
label so you can judge.
