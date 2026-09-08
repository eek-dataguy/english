# English Grammar Gym

A static website for practising English grammar by CEFR level (A1–C1) and finding
out which level your accuracy drops at. ~13,000 multiple-choice questions.

- **`web/`** – the site itself (vanilla HTML/CSS/JS, no build step). Deploy this
  folder to Vercel / Netlify / GitHub Pages. See [`web/README.md`](web/README.md).
- **`build/`** – the pipeline that extracts questions from the source PDFs into
  `web/data/*.json`. See [`build/README.md`](build/README.md).

## Quick start

```bash
cd web
python -m http.server 8080      # http://localhost:8080
```

## Deploy to Vercel

Import the repo, set **Root Directory = `web`**, framework "Other", no build
command. Or:

```bash
cd web && vercel --prod
```

## Content note

Questions are extracted from grammar-test books the site owner holds copies of
(the english-test.net "Incomplete Sentences" collection and *Test Master* by
Atalay Oguz). The source PDFs are **not** committed (`.gitignore`). The CEFR
levels are approximate mappings of each book's own difficulty labels; every quiz
shows its original label. Consider keeping this repository private.
