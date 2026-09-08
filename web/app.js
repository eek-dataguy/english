"use strict";
const APP = document.getElementById('app');
const LEVELS = ['A1', 'A2', 'B1', 'B2', 'C1'];
const PKEY = 'egg_progress_v1';
const levelCache = {};
let INDEX = null;

/* ---------- progress ---------- */
function loadProgress() {
  try { return JSON.parse(localStorage.getItem(PKEY)) || {}; }
  catch (e) { return {}; }
}
function saveProgress(p) {
  try { localStorage.setItem(PKEY, JSON.stringify(p)); } catch (e) {}
}
function recordAttempt(quizId, cefr, correct, total, perLevelCounts) {
  const p = loadProgress();
  p.attempts = p.attempts || [];
  p.attempts.push({ quizId, cefr, correct, total, ts: Date.now() });
  if (p.attempts.length > 400) p.attempts = p.attempts.slice(-400);
  p.best = p.best || {};
  const pct = total ? correct / total : 0;
  if (!(quizId in p.best) || pct > p.best[quizId]) p.best[quizId] = pct;
  p.lvl = p.lvl || {};
  const add = perLevelCounts || { [cefr]: { c: correct, t: total } };
  for (const k in add) {
    p.lvl[k] = p.lvl[k] || { c: 0, t: 0 };
    p.lvl[k].c += add[k].c; p.lvl[k].t += add[k].t;
  }
  saveProgress(p);
}
function levelAccuracy(lv) {
  const p = loadProgress();
  const s = (p.lvl || {})[lv];
  return s && s.t ? { pct: s.c / s.t, c: s.c, t: s.t } : null;
}

/* ---------- data ---------- */
async function getIndex() {
  if (INDEX) return INDEX;
  INDEX = await fetch('data/index.json').then(r => r.json());
  return INDEX;
}
async function getLevel(lv) {
  if (levelCache[lv]) return levelCache[lv];
  levelCache[lv] = await fetch('data/level/' + lv + '.json').then(r => r.json());
  return levelCache[lv];
}

/* ---------- utils ---------- */
const $ = (tag, attrs, ...kids) => {
  const el = document.createElement(tag);
  if (attrs) for (const k in attrs) {
    if (k === 'class') el.className = attrs[k];
    else if (k === 'html') el.innerHTML = attrs[k];
    else if (k.startsWith('on')) el.addEventListener(k.slice(2), attrs[k]);
    else if (attrs[k] != null) el.setAttribute(k, attrs[k]);
  }
  for (const kid of kids.flat()) if (kid != null) el.append(kid.nodeType ? kid : document.createTextNode(kid));
  return el;
};
function shuffle(a) { a = a.slice(); for (let i = a.length - 1; i > 0; i--) { const j = Math.random() * (i + 1) | 0;[a[i], a[j]] = [a[j], a[i]]; } return a; }
function esc(s) { return String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c])); }
function stemHTML(s) { return esc(s).replace(/ ?_{3,} ?/g, ' <b class="blank">______</b> '); }
function pctClass(p) { return p >= 0.8 ? 'good' : p >= 0.6 ? 'mid' : 'low'; }
function clear() { APP.innerHTML = ''; }

/* ---------- views ---------- */
async function viewHome() {
  clear();
  const idx = await getIndex();
  APP.append(
    $('h1', null, 'Find the grammar level you need to work on'),
    $('p', { class: 'lede' },
      `${idx.totalQuestions.toLocaleString()} multiple-choice questions from your PDFs, sorted into CEFR levels A1–C1. ` +
      `Do a few quizzes at each level; the dashboard shows where your accuracy drops.`)
  );

  // weakest-level callout
  const accs = LEVELS.map(lv => ({ lv, a: levelAccuracy(lv) })).filter(x => x.a && x.a.t >= 5);
  if (accs.length >= 2) {
    accs.sort((x, y) => x.a.pct - y.a.pct);
    const w = accs[0];
    APP.append($('div', { class: 'callout warn' },
      $('b', null, `Weakest so far: ${w.lv} `),
      `— ${Math.round(w.a.pct * 100)}% correct over ${w.a.t} questions. Focus your practice here.`));
  } else {
    APP.append($('div', { class: 'callout' },
      'New here? ', $('a', { href: '#/placement' }, 'Take the 22-question placement test'),
      ' for a quick level estimate, or just pick a level below.'));
  }

  const grid = $('div', { class: 'grid' });
  for (const l of idx.levels) {
    const a = levelAccuracy(l.level);
    const card = $('a', { class: 'levelcard card', href: '#/level/' + l.level });
    card.append(
      $('span', { class: 'tag ' + l.level }, l.level),
      $('div', { class: 'desc' }, l.desc),
      $('div', { class: 'meta' }, `${l.quizzes} quizzes · ${l.questions.toLocaleString()} questions`)
    );
    if (a) {
      card.append(
        $('div', { class: 'bar ' + pctClass(a.pct) }, $('i', { style: `width:${Math.round(a.pct * 100)}%` })),
        $('div', { class: 'meta' }, `your accuracy: ${Math.round(a.pct * 100)}% (${a.c}/${a.t})`)
      );
    }
    grid.append(card);
  }
  APP.append(grid);
  APP.append($('div', { class: 'row' },
    $('a', { class: 'btn', href: '#/placement' }, '▶ Placement test'),
    $('a', { class: 'btn ghost', href: '#/progress' }, 'My progress')));
}

async function viewLevel(lv) {
  if (!LEVELS.includes(lv)) return viewHome();
  clear();
  APP.append($('p', null, $('a', { href: '#/' }, '← All levels')));
  const idx = await getIndex();
  const meta = idx.levels.find(x => x.level === lv);
  APP.append(
    $('h1', null, $('span', { class: 'tag ' + lv }, lv), ' ' + (meta ? meta.desc : '')),
    $('div', { class: 'row' },
      $('button', { class: 'btn', onclick: () => startRandom(lv) }, '🎲 Random ' + lv + ' quiz'),
      $('span', { class: 'muted' }, `${meta.quizzes} quizzes · ${meta.questions.toLocaleString()} questions`))
  );
  const p = loadProgress();
  const bySource = {};
  for (const it of meta.items) (bySource[it.source] = bySource[it.source] || []).push(it);
  for (const src in bySource) {
    APP.append($('h2', null, src + ` (${bySource[src].length})`));
    const ul = $('ul', { class: 'quizlist' });
    for (const it of bySource[src]) {
      const best = (p.best || {})[it.id];
      const li = $('li', best != null ? { class: 'done' } : null);
      li.append($('div', null,
        $('div', { class: 't' }, it.title),
        $('div', { class: 's' }, `${it.n} questions${it.srcLevel ? ' · source level: ' + it.srcLevel : ''}`)));
      const right = $('div', { class: 'row' });
      if (best != null) {
        const bc = 'pill score' + (best < 0.6 ? ' low' : '');
        right.append($('span', { class: bc }, 'best ' + Math.round(best * 100) + '%'));
      }
      right.append($('a', { class: 'btn ghost', href: '#/quiz/' + encodeURIComponent(it.id) }, best != null ? 'Retry' : 'Start'));
      li.append(right);
      ul.append(li);
    }
    APP.append(ul);
  }
}

async function startRandom(lv) {
  const data = await getLevel(lv);
  const q = data.quizzes[Math.random() * data.quizzes.length | 0];
  location.hash = '#/quiz/' + encodeURIComponent(q.id);
}

async function viewQuiz(id) {
  clear();
  APP.append($('p', { class: 'muted' }, 'Loading quiz…'));
  let quiz = null, lv = null;
  for (const L of LEVELS) {
    if (id.startsWith(L + '-')) { lv = L; break; }
  }
  const search = lv ? [lv] : LEVELS;
  for (const L of search) {
    const data = await getLevel(L);
    const found = data.quizzes.find(q => q.id === id);
    if (found) { quiz = found; lv = L; break; }
  }
  if (!quiz) { clear(); APP.append($('p', null, 'Quiz not found. ', $('a', { href: '#/' }, 'Home'))); return; }
  runQuiz(quiz, lv, '#/level/' + lv);
}

function runQuiz(quiz, cefr, backHash) {
  clear();
  const items = shuffle(quiz.questions).map(it => {
    const order = shuffle(it.options.map((o, i) => i));
    return { stem: it.q, opts: order.map(i => it.options[i]), correct: order.indexOf(it.answer), cefr: it.cefr || cefr };
  });
  const picks = new Array(items.length).fill(-1);
  let graded = false;

  APP.append($('p', null, $('a', { href: backHash }, '← Back')));
  APP.append($('div', { class: 'spread' },
    $('h1', null, quiz.title),
    $('span', { class: 'tag ' + cefr }, cefr)));
  APP.append($('p', { class: 'muted' }, `${quiz.source} · choose the best option for each gap`));

  const form = $('form', { onsubmit: e => e.preventDefault() });
  const qEls = items.map((it, qi) => {
    const box = $('div', { class: 'q' });
    box.append($('div', { class: 'stem', html: `<span class="n">${qi + 1}.</span>${stemHTML(it.stem)}` }));
    const opts = $('div', { class: 'opts' });
    it.opts.forEach((text, oi) => {
      const lab = $('label', { class: 'opt' });
      const radio = $('input', { type: 'radio', name: 'q' + qi, value: oi });
      radio.addEventListener('change', () => { picks[qi] = oi; updateBar(); });
      lab.append(radio, $('span', null, text), $('span', { class: 'mk' }, ''));
      opts.append(lab);
    });
    box.append(opts);
    form.append(box);
    return box;
  });
  APP.append(form);

  const bar = $('div', { class: 'bar' }, $('i', { style: 'width:0%' }));
  const status = $('span', { class: 'muted' }, '0 / ' + items.length + ' answered');
  function updateBar() {
    const n = picks.filter(x => x >= 0).length;
    bar.firstChild.style.width = Math.round(n / items.length * 100) + '%';
    status.textContent = n + ' / ' + items.length + ' answered';
    checkBtn.disabled = n === 0;
  }
  const checkBtn = $('button', { class: 'btn', disabled: 'disabled', onclick: grade }, 'Check answers');
  const actions = $('div', { class: 'sticky-actions' });
  actions.append(checkBtn, bar, status);
  APP.append(actions);
  updateBar();

  function grade() {
    if (graded) return;
    graded = true;
    let correct = 0;
    const perLevel = {};
    items.forEach((it, qi) => {
      const labs = qEls[qi].querySelectorAll('.opt');
      labs.forEach(l => l.querySelector('input').disabled = true);
      const lvl = it.cefr;
      perLevel[lvl] = perLevel[lvl] || { c: 0, t: 0 };
      perLevel[lvl].t++;
      if (picks[qi] === it.correct) { correct++; perLevel[lvl].c++; }
      if (picks[qi] >= 0 && picks[qi] !== it.correct) {
        labs[picks[qi]].classList.add('wrong');
        labs[picks[qi]].querySelector('.mk').textContent = '✗ your answer';
      }
      labs[it.correct].classList.add('correct');
      labs[it.correct].querySelector('.mk').textContent = '✓ correct';
    });
    recordAttempt(quiz.id, cefr, correct, items.length, perLevel);

    const pct = correct / items.length;
    actions.innerHTML = '';
    actions.append(
      $('span', { class: 'scorebig' }, `${correct} / ${items.length}`),
      $('span', { class: 'pill score' + (pct < 0.6 ? ' low' : '') }, Math.round(pct * 100) + '%'),
      $('button', { class: 'btn', onclick: () => startRandom(cefr) }, 'Another ' + cefr + ' quiz'),
      $('a', { class: 'btn ghost', href: backHash }, 'Back to ' + cefr),
      $('a', { class: 'btn ghost', href: '#/progress' }, 'My progress')
    );
    window.scrollTo({ top: 0, behavior: 'smooth' });
    const msg = pct >= 0.85 ? 'Strong — this level looks comfortable.'
      : pct >= 0.6 ? 'Getting there. A few more quizzes at this level will help.'
        : 'This level needs work. Keep practising here before moving up.';
    APP.querySelector('h1').after($('div', { class: 'callout ' + (pct >= 0.85 ? 'good' : pct >= 0.6 ? '' : 'warn') }, msg));
  }
}

async function viewPlacement() {
  clear();
  APP.append($('p', null, $('a', { href: '#/' }, '← Home')), $('h1', null, 'Placement test'));
  APP.append($('p', { class: 'lede' }, 'About 22 questions spread across A1–C1. Your score at each level gives a rough estimate of where you stand.'));
  const data = await fetch('data/placement.json').then(r => r.json());
  const quiz = { id: '__placement__', title: 'Placement test', source: 'Mixed levels', questions: data.questions };
  runPlacement(quiz);
}

function runPlacement(quiz) {
  clear();
  const items = shuffle(quiz.questions).map(it => {
    const order = shuffle(it.options.map((o, i) => i));
    return { stem: it.q, opts: order.map(i => it.options[i]), correct: order.indexOf(it.answer), cefr: it.cefr };
  });
  const picks = new Array(items.length).fill(-1);
  APP.append($('h1', null, 'Placement test'));
  const form = $('form', { onsubmit: e => e.preventDefault() });
  const qEls = items.map((it, qi) => {
    const box = $('div', { class: 'q' });
    box.append($('div', { class: 'stem', html: `<span class="n">${qi + 1}.</span>${stemHTML(it.stem)}` }));
    const opts = $('div', { class: 'opts' });
    it.opts.forEach((text, oi) => {
      const lab = $('label', { class: 'opt' });
      const radio = $('input', { type: 'radio', name: 'q' + qi, value: oi });
      radio.addEventListener('change', () => { picks[qi] = oi; update(); });
      lab.append(radio, $('span', null, text), $('span', { class: 'mk' }, ''));
      opts.append(lab);
    });
    box.append(opts); form.append(box); return box;
  });
  APP.append(form);
  const status = $('span', { class: 'muted' }, '0 / ' + items.length);
  const btn = $('button', { class: 'btn', disabled: 'disabled', onclick: grade }, 'See my level');
  const actions = $('div', { class: 'sticky-actions' }, btn, status);
  APP.append(actions);
  function update() {
    const n = picks.filter(x => x >= 0).length;
    status.textContent = n + ' / ' + items.length;
    btn.disabled = n < items.length;
    btn.textContent = n < items.length ? `Answer all (${items.length - n} left)` : 'See my level';
  }
  function grade() {
    const per = {};
    items.forEach((it, qi) => {
      const labs = qEls[qi].querySelectorAll('.opt');
      labs.forEach(l => l.querySelector('input').disabled = true);
      per[it.cefr] = per[it.cefr] || { c: 0, t: 0 };
      per[it.cefr].t++;
      if (picks[qi] === it.correct) per[it.cefr].c++;
      if (picks[qi] >= 0 && picks[qi] !== it.correct) { labs[picks[qi]].classList.add('wrong'); labs[picks[qi]].querySelector('.mk').textContent = '✗'; }
      labs[it.correct].classList.add('correct'); labs[it.correct].querySelector('.mk').textContent = '✓';
    });
    let totalC = 0, totalT = 0;
    for (const k in per) { totalC += per[k].c; totalT += per[k].t; }
    recordAttempt('__placement__', 'B1', totalC, totalT, per);
    // estimate: highest level where accuracy >= 70%
    let est = 'A1';
    for (const lv of LEVELS) { const s = per[lv]; if (s && s.c / s.t >= 0.7) est = lv; }
    actions.innerHTML = '';
    actions.append($('span', { class: 'scorebig' }, 'Estimated level: ' + est),
      $('a', { class: 'btn', href: '#/level/' + est }, 'Practise ' + est),
      $('a', { class: 'btn ghost', href: '#/progress' }, 'Details'));
    const tbl = $('table', { class: 'stats' });
    tbl.append($('tr', null, $('th', null, 'Level'), $('th', { class: 'num' }, 'Score'), $('th', { class: 'num' }, '%')));
    for (const lv of LEVELS) {
      const s = per[lv]; if (!s) continue;
      tbl.append($('tr', null, $('td', null, lv), $('td', { class: 'num' }, `${s.c}/${s.t}`),
        $('td', { class: 'num' }, Math.round(s.c / s.t * 100) + '%')));
    }
    APP.querySelector('h1').after(tbl);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }
  update();
}

async function viewProgress() {
  clear();
  const idx = await getIndex();
  const p = loadProgress();
  APP.append($('p', null, $('a', { href: '#/' }, '← Home')), $('h1', null, 'My progress'));
  const attempts = p.attempts || [];
  if (!attempts.length) {
    APP.append($('p', { class: 'lede' }, 'No quizzes done yet. Pick a level from the home page to begin.'));
    return;
  }
  APP.append($('p', { class: 'muted' }, `${attempts.length} quiz attempts recorded on this device.`));

  const tbl = $('table', { class: 'stats' });
  tbl.append($('tr', null, $('th', null, 'Level'), $('th', null, ''), $('th', { class: 'num' }, 'Questions'), $('th', { class: 'num' }, 'Accuracy')));
  const rows = [];
  for (const lv of LEVELS) {
    const a = levelAccuracy(lv);
    const barWrap = $('div', { class: 'bar ' + (a ? pctClass(a.pct) : '') }, $('i', { style: `width:${a ? Math.round(a.pct * 100) : 0}%` }));
    tbl.append($('tr', null,
      $('td', null, $('span', { class: 'tag ' + lv }, lv)),
      $('td', { style: 'width:45%' }, barWrap),
      $('td', { class: 'num' }, a ? a.t : '—'),
      $('td', { class: 'num' }, a ? Math.round(a.pct * 100) + '%' : '—')));
    if (a && a.t >= 5) rows.push({ lv, pct: a.pct });
  }
  APP.append($('h2', null, 'Accuracy by level'), tbl);

  if (rows.length >= 2) {
    rows.sort((x, y) => x.pct - y.pct);
    APP.append($('div', { class: 'callout warn' },
      $('b', null, 'Priority: '),
      rows.filter(r => r.pct < 0.75).map(r => `${r.lv} (${Math.round(r.pct * 100)}%)`).join(', ') ||
      'You are above 75% everywhere — try the next level up.'));
  }

  APP.append($('h2', null, 'Recent attempts'));
  const ul = $('ul', { class: 'quizlist' });
  for (const at of attempts.slice(-25).reverse()) {
    const pct = at.total ? at.correct / at.total : 0;
    ul.append($('li', null,
      $('div', null, $('div', { class: 't' }, at.quizId === '__placement__' ? 'Placement test' : at.quizId),
        $('div', { class: 's' }, new Date(at.ts).toLocaleString())),
      $('span', { class: 'pill score' + (pct < 0.6 ? ' low' : '') }, `${at.correct}/${at.total}`)));
  }
  APP.append(ul);
  APP.append($('div', { class: 'row', style: 'margin-top:20px' },
    $('button', {
      class: 'btn ghost', onclick: () => {
        if (confirm('Erase all progress on this device?')) { localStorage.removeItem(PKEY); route(); }
      }
    }, 'Reset all progress')));
}

/* ---------- theme ---------- */
function initTheme() {
  const saved = localStorage.getItem('egg_theme');
  if (saved) document.documentElement.dataset.theme = saved;
  document.getElementById('themeBtn').addEventListener('click', () => {
    const cur = document.documentElement.dataset.theme || 'auto';
    const next = cur === 'auto' ? 'light' : cur === 'light' ? 'dark' : 'auto';
    document.documentElement.dataset.theme = next;
    localStorage.setItem('egg_theme', next);
  });
}

/* ---------- router ---------- */
function route() {
  const h = location.hash.replace(/^#\/?/, '');
  const [seg, arg] = h.split('/');
  window.scrollTo(0, 0);
  if (!seg) return viewHome();
  if (seg === 'level') return viewLevel(arg);
  if (seg === 'quiz') return viewQuiz(decodeURIComponent(arg || ''));
  if (seg === 'placement') return viewPlacement();
  if (seg === 'progress') return viewProgress();
  return viewHome();
}
window.addEventListener('hashchange', route);
initTheme();
route();
