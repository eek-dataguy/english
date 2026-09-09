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
function recordAttempt(quizId, cefr, correct, total, perLevelCounts, title, perCatCounts) {
  const p = loadProgress();
  p.attempts = p.attempts || [];
  p.attempts.push({ quizId, cefr, correct, total, ts: Date.now(), title: title || '' });
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
  p.cat = p.cat || {};
  for (const k in (perCatCounts || {})) {
    p.cat[k] = p.cat[k] || { c: 0, t: 0 };
    p.cat[k].c += perCatCounts[k].c; p.cat[k].t += perCatCounts[k].t;
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
let TOPICS = null;
async function getTopics() {
  if (TOPICS) return TOPICS;
  const j = await fetch('data/topics.json').then(r => r.json());
  TOPICS = {};
  for (const t of j.topics) TOPICS[t.id] = t;
  return TOPICS;
}
const topicCache = {};
async function getTopicPool(id) {
  if (topicCache[id]) return topicCache[id];
  topicCache[id] = await fetch('data/topic/' + id + '.json').then(r => r.json());
  return topicCache[id];
}
function catAccuracy(id) {
  const s = (loadProgress().cat || {})[id];
  return s && s.t ? { pct: s.c / s.t, c: s.c, t: s.t } : null;
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
function sentencePart(it) {
  if (it.fs) {
    let h = esc(it.fs);
    if (it.aw) {
      const re = new RegExp('(' + it.aw.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')', 'i');
      h = h.replace(re, '<b class="blank">$1</b>');
    }
    return '<span class="lbl">Completed sentence</span>' + h;
  }
  return '<span class="lbl">Correct answer</span><b class="blank">' + esc(it.answerText || '') + '</b>';
}
function explainHTML(it) {
  let html = '<div class="ex-answer">' + sentencePart(it) + '</div>';
  if (it.x) {
    html += '<div class="ex-rule"><span class="lbl">Why</span>' + it.x + '</div>';
  }
  return html;
}
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

  // weakest-level + weakest-topic callout
  const accs = LEVELS.map(lv => ({ lv, a: levelAccuracy(lv) })).filter(x => x.a && x.a.t >= 5);
  let weakTopic = null;
  try {
    await getTopics();
    const p = loadProgress();
    const cr = Object.keys(p.cat || {}).map(id => ({ id, s: p.cat[id] }))
      .filter(x => x.s.t >= 5 && TOPICS[x.id]).map(x => ({ id: x.id, pct: x.s.c / x.s.t }));
    cr.sort((a, b) => a.pct - b.pct);
    if (cr.length) weakTopic = cr[0];
  } catch (e) {}
  if (accs.length >= 2) {
    accs.sort((x, y) => x.a.pct - y.a.pct);
    const w = accs[0];
    const c = $('div', { class: 'callout warn' },
      $('b', null, `Weakest level: ${w.lv} `),
      `— ${Math.round(w.a.pct * 100)}% over ${w.a.t} questions.`);
    if (weakTopic) c.append($('br'), $('b', null, 'Weakest topic: '),
      $('a', { href: '#/topic/' + weakTopic.id }, TOPICS[weakTopic.id].name),
      ` (${Math.round(weakTopic.pct * 100)}%).`);
    APP.append(c);
  } else {
    APP.append($('div', { class: 'callout' },
      'New here? ', $('a', { href: '#/placement' }, 'Take the placement test'),
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
    $('a', { class: 'btn ghost', href: '#/topics' }, '📚 Practise by topic'),
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
  await getTopics();
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
  runQuiz(quiz, lv, '#/level/' + lv, () => startRandom(lv));
}

async function viewTopics() {
  clear();
  const [tp] = await Promise.all([getTopics()]);
  APP.append($('p', null, $('a', { href: '#/' }, '← Home')), $('h1', null, 'Practise by grammar topic'));
  APP.append($('p', { class: 'lede' }, 'Every question is tagged with a grammar point. Drill a single point, or check the table on ' +
    'your progress page to see which points you get wrong most.'));
  const list = Object.values(TOPICS).slice().sort((a, b) => b.count - a.count);
  const ul = $('ul', { class: 'quizlist' });
  for (const t of list) {
    const a = catAccuracy(t.id);
    const li = $('li', null);
    li.append($('div', null,
      $('div', { class: 't' }, t.name),
      $('div', { class: 's' }, `${t.count.toLocaleString()} questions` +
        (a ? ` · your accuracy ${Math.round(a.pct * 100)}% (${a.c}/${a.t})` : ''))));
    const right = $('div', { class: 'row' });
    if (a) right.append($('span', { class: 'pill score' + (a.pct < 0.6 ? ' low' : '') }, Math.round(a.pct * 100) + '%'));
    right.append($('a', { class: 'btn ghost', href: '#/topic/' + t.id }, 'Practise'));
    li.append(right);
    ul.append(li);
  }
  APP.append(ul);
}

async function viewTopic(id) {
  clear();
  await getTopics();
  const t = TOPICS[id];
  if (!t) { APP.append($('p', null, 'Unknown topic. ', $('a', { href: '#/topics' }, 'All topics'))); return; }
  APP.append($('p', null, $('a', { href: '#/topics' }, '← All topics')));
  APP.append($('h1', null, t.name));
  APP.append($('div', { class: 'callout', html: t.note }));
  const a = catAccuracy(id);
  if (a) APP.append($('p', { class: 'muted' }, `So far: ${Math.round(a.pct * 100)}% correct over ${a.t} questions on this topic.`));
  let pool;
  try { pool = await getTopicPool(id); }
  catch (e) { APP.append($('p', { class: 'muted' }, 'Not enough questions to build a focused set for this topic.')); return; }
  APP.append($('div', { class: 'row' },
    $('button', { class: 'btn', onclick: () => startTopic(id) }, '▶ Start ' + Math.min(12, pool.questions.length) + '-question set'),
    $('span', { class: 'muted' }, `${pool.questions.length} questions in the pool, mixed levels`)));
}

async function startTopic(id) {
  await getTopics();
  const pool = await getTopicPool(id);
  const qs = shuffle(pool.questions).slice(0, 12);
  const quiz = { id: '__topic_' + id + '__', title: 'Topic: ' + pool.name, source: 'Grammar topic drill',
    cat: id, questions: qs };
  runQuiz(quiz, qs[0] && qs[0].cefr || 'B1', '#/topic/' + id, () => startTopic(id));
}

function runQuiz(quiz, cefr, backHash, nextFn) {
  clear();
  nextFn = nextFn || (() => startRandom(cefr));
  const items = shuffle(quiz.questions).map(it => {
    const order = shuffle(it.options.map((o, i) => i));
    return {
      stem: it.q, opts: order.map(i => it.options[i]),
      correct: order.indexOf(it.answer), cefr: it.cefr || cefr, k: it.k || quiz.cat || 'general',
      fs: it.fs || '', aw: it.aw || '', answerText: it.options[it.answer]
    };
  });
  const picks = new Array(items.length).fill(-1);
  let graded = false;

  APP.append($('p', null, $('a', { href: backHash }, '← Back')));
  APP.append($('div', { class: 'spread' },
    $('h1', null, quiz.title),
    $('span', { class: 'tag ' + cefr }, cefr)));
  APP.append($('p', { class: 'muted' }, `${quiz.source} · choose the best option for each gap`));

  const tip = TOPICS && TOPICS[quiz.cat];
  if (tip && tip.specific) {
    const d = $('details', { class: 'tip' });
    d.append($('summary', null, '💡 Grammar tip · ' + tip.name),
      $('div', { class: 'tip-body', html: tip.note }));
    APP.append(d);
  }

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
    const perLevel = {}, perCat = {};
    items.forEach((it, qi) => {
      const labs = qEls[qi].querySelectorAll('.opt');
      labs.forEach(l => l.querySelector('input').disabled = true);
      const lvl = it.cefr;
      perLevel[lvl] = perLevel[lvl] || { c: 0, t: 0 };
      perLevel[lvl].t++;
      perCat[it.k] = perCat[it.k] || { c: 0, t: 0 };
      perCat[it.k].t++;
      if (picks[qi] === it.correct) { correct++; perLevel[lvl].c++; perCat[it.k].c++; }
      if (picks[qi] >= 0 && picks[qi] !== it.correct) {
        labs[picks[qi]].classList.add('wrong');
        labs[picks[qi]].querySelector('.mk').textContent = '✗ your answer';
      }
      labs[it.correct].classList.add('correct');
      labs[it.correct].querySelector('.mk').textContent = '✓ correct';
      qEls[qi].append($('div', { class: 'explain' + (picks[qi] !== it.correct ? ' miss' : ''), html: explainHTML(it) }));
    });
    recordAttempt(quiz.id, cefr, correct, items.length, perLevel, cefr + ' · ' + quiz.title, perCat);

    const pct = correct / items.length;
    actions.innerHTML = '';
    actions.append(
      $('span', { class: 'scorebig' }, `${correct} / ${items.length}`),
      $('span', { class: 'pill score' + (pct < 0.6 ? ' low' : '') }, Math.round(pct * 100) + '%'),
      $('button', { class: 'btn', onclick: nextFn }, 'Another quiz'),
      $('a', { class: 'btn ghost', href: backHash }, 'Back'),
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
  await getTopics();
  const data = await fetch('data/placement.json').then(r => r.json());
  const quiz = { id: '__placement__', title: 'Placement test', source: 'Mixed levels', questions: data.questions };
  runPlacement(quiz);
}

function runPlacement(quiz) {
  clear();
  const items = shuffle(quiz.questions).map(it => {
    const order = shuffle(it.options.map((o, i) => i));
    return {
      stem: it.q, opts: order.map(i => it.options[i]),
      correct: order.indexOf(it.answer), cefr: it.cefr, k: it.k || 'general',
      fs: it.fs || '', aw: it.aw || '', answerText: it.options[it.answer]
    };
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
    const per = {}, perCat = {};
    items.forEach((it, qi) => {
      const labs = qEls[qi].querySelectorAll('.opt');
      labs.forEach(l => l.querySelector('input').disabled = true);
      per[it.cefr] = per[it.cefr] || { c: 0, t: 0 };
      per[it.cefr].t++;
      perCat[it.k] = perCat[it.k] || { c: 0, t: 0 };
      perCat[it.k].t++;
      if (picks[qi] === it.correct) { per[it.cefr].c++; perCat[it.k].c++; }
      if (picks[qi] >= 0 && picks[qi] !== it.correct) { labs[picks[qi]].classList.add('wrong'); labs[picks[qi]].querySelector('.mk').textContent = '✗'; }
      labs[it.correct].classList.add('correct'); labs[it.correct].querySelector('.mk').textContent = '✓';
      qEls[qi].append($('div', { class: 'explain' + (picks[qi] !== it.correct ? ' miss' : ''), html: explainHTML(it) }));
    });
    let totalC = 0, totalT = 0;
    for (const k in per) { totalC += per[k].c; totalT += per[k].t; }
    recordAttempt('__placement__', 'B1', totalC, totalT, per, 'Placement test', perCat);
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
      $('b', null, 'Priority levels: '),
      rows.filter(r => r.pct < 0.75).map(r => `${r.lv} (${Math.round(r.pct * 100)}%)`).join(', ') ||
      'You are above 75% everywhere — try the next level up.'));
  }

  // ---- by grammar topic ----
  await getTopics();
  const catRows = [];
  for (const id in (p.cat || {})) {
    const s = p.cat[id];
    if (!s.t || !TOPICS[id]) continue;
    catRows.push({ id, name: TOPICS[id].name, pct: s.c / s.t, c: s.c, t: s.t });
  }
  if (catRows.length) {
    catRows.sort((a, b) => a.pct - b.pct);
    APP.append($('h2', null, 'Accuracy by grammar topic'));
    const weak = catRows.filter(r => r.t >= 4 && r.pct < 0.7);
    if (weak.length) {
      APP.append($('div', { class: 'callout warn' },
        $('b', null, 'Weakest topics: '),
        weak.slice(0, 4).map(r => `${r.name} ${Math.round(r.pct * 100)}%`).join(' · ')));
    }
    const ct = $('table', { class: 'stats' });
    ct.append($('tr', null, $('th', null, 'Topic'), $('th', null, ''), $('th', { class: 'num' }, 'Qs'),
      $('th', { class: 'num' }, '%'), $('th', null, '')));
    for (const r of catRows) {
      ct.append($('tr', null,
        $('td', null, r.name),
        $('td', { style: 'width:35%' }, $('div', { class: 'bar ' + pctClass(r.pct) }, $('i', { style: `width:${Math.round(r.pct * 100)}%` }))),
        $('td', { class: 'num' }, r.t),
        $('td', { class: 'num' }, Math.round(r.pct * 100) + '%'),
        $('td', null, $('a', { class: 'pill', href: '#/topic/' + r.id }, 'practise'))));
    }
    APP.append(ct);
  } else {
    APP.append($('h2', null, 'Accuracy by grammar topic'),
      $('p', { class: 'muted' }, 'Do a few quizzes and this table will show which grammar points you miss most. ',
        $('a', { href: '#/topics' }, 'Browse topics')));
  }

  APP.append($('h2', null, 'Recent attempts'));
  const ul = $('ul', { class: 'quizlist' });
  for (const at of attempts.slice(-25).reverse()) {
    const pct = at.total ? at.correct / at.total : 0;
    ul.append($('li', null,
      $('div', null, $('div', { class: 't' }, at.title || (at.quizId === '__placement__' ? 'Placement test' : at.quizId)),
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
  if (seg === 'topics') return viewTopics();
  if (seg === 'topic') return viewTopic(decodeURIComponent(arg || ''));
  if (seg === 'placement') return viewPlacement();
  if (seg === 'progress') return viewProgress();
  return viewHome();
}
window.addEventListener('hashchange', route);
initTheme();
route();
