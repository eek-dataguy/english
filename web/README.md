# English Grammar Gym

A static site to practise English grammar by CEFR level (A1–C1) and see which
level your accuracy drops at. ~13,000 multiple-choice questions extracted from
your own grammar-test PDFs.

## What's here

```
web/
  index.html  style.css  app.js      # the whole app (vanilla JS, no build step)
  vercel.json                         # static config (clean URLs + cache headers)
  data/
    index.json        # level list + every quiz's title/size  (loaded on home)
    placement.json     # 22 mixed questions for the placement test
    level/A1.json … C1.json   # full quizzes per level (loaded when you open one)
```

Progress (per-quiz best score, accuracy per level, recent attempts) is stored in
the browser's `localStorage` – nothing is sent anywhere.

## Run locally

Any static server, e.g.:

```
cd web
python -m http.server 8080
# open http://localhost:8080
```

(Opening `index.html` via `file://` won't work – the app `fetch`es the JSON.)

## Deploy to Vercel

The site is fully static; the project root is this `web/` folder.

```
cd web
vercel            # first run: link/create the project, accept defaults
vercel --prod     # promote to production
```

Or in the Vercel dashboard: **New Project → import the repo → set "Root Directory"
to `web` → Framework preset: Other → Deploy.** No build command, no environment
variables.

## Levels are approximate

Questions come from two collections with their own difficulty labels
(Elementary / Intermediate / Advanced, and Elementary → Advanced). Those are
mapped onto A1–C1 as best they can be; each quiz still shows its original source
label. B1 is by far the largest bucket because the english-test.net "Intermediate"
set is huge and spans B1–B2. See `../build/README.md` for the mapping table.

## Regenerating the data

See `../build/README.md`.
