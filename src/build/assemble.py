"""Assemble the three study artifacts from agent fragments.

Usage: python -I assemble.py <scratchpad_dir> <out_dir> [--pdf]
"""
import html
import os
import re
import subprocess
import sys
import unicodedata

SP, OUT = sys.argv[1], sys.argv[2]
DO_PDF = "--pdf" in sys.argv
PARTS = os.path.join(SP, "parts")
BUILD = os.path.join(SP, "build")
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500'
         '&family=IBM+Plex+Sans+Condensed:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600'
         '&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400&display=swap">')


def read(path, default=""):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return default


import json

SLIDEMAP = {k: {int(p): n for p, n in v.items()} for k, v in json.loads(read(os.path.join(BUILD, "slidemap.json"), "{}")).items()}
REF_RE = re.compile(r"(?<![A-Za-z])(?:(V0[1-6]|T0[1-6])\s*)?F\.\s?(\d{1,3})((?:\s*[–\-,/]\s*\d{1,3}(?![\d.]))*)")


def fix_refs(txt, default_deck=None):
    """Agents cite PDF pages; the printed slides carry their own numbers (hidden slides shift them)."""
    def conv(deck, n):
        return SLIDEMAP.get(deck, {}).get(n, n)

    state = {"deck": default_deck}

    def repl(m):
        deck = m.group(1) or state["deck"]
        if m.group(1):
            state["deck"] = m.group(1)
        if not deck or deck not in SLIDEMAP:
            return m.group(0)
        tail = re.sub(r"\d{1,3}", lambda x: str(conv(deck, int(x.group(0)))), m.group(3))
        prefix = (m.group(1) + " ") if m.group(1) else ""
        return f"{prefix}F.{conv(deck, int(m.group(2)))}{tail}"

    # deck context resets at every block boundary so a bare "F.n" inherits only from its own paragraph
    blocks = re.split(r"(</p>|</li>|</div>|</td>)", txt)
    out = []
    for b in blocks:
        state["deck"] = default_deck
        out.append(REF_RE.sub(repl, b))
    return "".join(out)


def part(name):
    txt = read(os.path.join(PARTS, name))
    if not txt:
        print("  missing:", name)
        return txt
    m = re.search(r"_k(\d)", name)
    # some agents appended the printed number in brackets ("F.86 [97]"); fix_refs converts the main number
    txt = re.sub(r"(F\.\s?\d{1,3}(?:\s*[–\-]\s*\d{1,3})?)\s\[\d{1,3}(?:\s*[–\-,]\s*\d{1,3})*\]", r"\1", txt)
    txt = fix_refs(txt, f"V0{m.group(1)}" if m else None)
    txt = re.sub(r'(<div class="box-h">Lesehilfe Folienverweise</div>)<p>.*?</p>',
                 r'\1<p>Alle Verweise nennen die <b>auf der Folie aufgedruckte Nummer</b> (unten rechts), so wie sie in deinem Folienausdruck steht: <b>V04 F.44</b> = Vorlesung 4, Folie 44; <b>T02 F.28</b> = Tutorium 2, Folie 28. In V01, V02 und V04 weicht diese Nummer wegen ausgeblendeter Folien von der PDF-Seitenzahl ab.</p>',
                 txt, flags=re.S)
    # chapter 1 explained the old PDF-page convention; references are printed numbers now
    txt = re.sub(r'<div class="box pit">\s*<div class="box-h">Hinweis zu den Folienverweisen</div>.*?</p>\s*</div>',
                 "", txt, flags=re.S)
    txt = re.sub(r'<p class="d">Folienverweise = PDF-Seite.*?</p>', "", txt, flags=re.S)
    return txt


CSS = read(os.path.join(BUILD, "common.css"))


def page(title, desc, extra_css, body, js):
    return (f'<title>{title}</title>\n<meta name="claude:viewport-fit-sides" content="cover">\n'
            f'<meta name="description" content="{html.escape(desc)}">\n{FONTS}\n'
            f'<style>\n{CSS}\n{extra_css}\n</style>\n{body}\n<script>\n{js}\n</script>\n')


def write(name, content):
    path = os.path.join(OUT, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  wrote {name} ({len(content) // 1024} KB)")
    return path


TOC_JS = r"""
(function () {
  var main = document.querySelector('.main'), toc = document.getElementById('toc');
  var secs = main.querySelectorAll(':scope > section'), links = [];
  secs.forEach(function (sec, i) {
    var h2 = sec.querySelector('h2'); if (!h2) return;
    if (!sec.id) sec.id = 's' + i;
    var li = document.createElement('li'); li.className = 't1';
    var a = document.createElement('a'); a.href = '#' + sec.id;
    var no = sec.getAttribute('data-no');
    a.innerHTML = (no ? '<span class="n">' + no + '</span>' : '') + (sec.getAttribute('data-short') || h2.textContent);
    li.appendChild(a); links.push([sec, a]);
    var subs = sec.querySelectorAll(SUBSEL);
    if (subs.length) {
      var ol = document.createElement('ol'); ol.className = 'sub';
      subs.forEach(function (h, j) {
        if (!h.id) h.id = sec.id + '-h' + j;
        var sa = document.createElement('a'); sa.href = '#' + h.id;
        sa.textContent = h.getAttribute('data-toc') || h.textContent.replace(/\s+\d+([,.]\d+)?\s*P\.?\s*$/, '');
        var sli = document.createElement('li'); sli.appendChild(sa); ol.appendChild(sli); links.push([h, sa]);
      });
      li.appendChild(ol);
    }
    toc.appendChild(li);
  });
  var cur = null;
  function spy() {
    var y = 120, best = null;
    for (var i = 0; i < links.length; i++) { if (links[i][0].getBoundingClientRect().top < y) best = links[i]; }
    if (best !== cur) { if (cur) cur[1].classList.remove('on'); cur = best; if (cur) cur[1].classList.add('on'); }
  }
  window.addEventListener('scroll', spy, { passive: true }); spy();
})();
"""

# ---------------------------------------------------------------- Lernskript
SKRIPT_CSS = r"""
.main > section .box, .main > section p, .main > section li { hyphens: auto; }
.howto { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: .8rem; margin: 1.4rem 0 0; font-family: var(--font-ui); font-size: .86rem; }
.howto div { border-left: 3px solid var(--c); background: var(--cb); padding: .6em .8em; border-radius: 0 6px 6px 0; }
.howto b { display: block; color: var(--c); font-size: .72rem; letter-spacing: .07em; text-transform: uppercase; margin-bottom: .2em; }
.legend-def { --c: var(--def); --cb: var(--def-bg); } .legend-ex { --c: var(--ex); --cb: var(--ex-bg); }
.legend-exam { --c: var(--exam); --cb: var(--exam-bg); } .legend-pit { --c: var(--pit); --cb: var(--pit-bg); }
.legend-deep { --c: var(--deep); --cb: var(--deep-bg); }
"""

SKRIPT_JS = "var SUBSEL = 'h3';\n" + TOC_JS + r"""
(function () {
  var b = document.getElementById('toggle-all'), open = false;
  b.addEventListener('click', function () {
    open = !open; b.setAttribute('aria-pressed', open);
    b.textContent = open ? 'Lösungen einklappen' : 'Alle Lösungen zeigen';
    document.querySelectorAll('details.quiz').forEach(function (d) { d.open = open; });
  });
})();
"""


def build_skript():
    chapters = "\n".join(part(f"skript_k{i}.html") for i in range(1, 7))
    for i in range(1, 7):
        chapters = chapters.replace(f'<section class="chapter" id="k{i}"', f'<section class="chapter" id="k{i}" data-no="{i}"', 1)
    nq = chapters.count('class="quiz"')
    body = f"""
<header class="topbar"><div class="topbar-in">
  <span class="brand">Wirtschaftsinformatik I <small>Lernskript · IS 201</small></span>
  <span class="spacer"></span>
  <button class="btn" id="toggle-all" type="button" aria-pressed="false">Alle Lösungen zeigen</button>
</div></header>
<div class="layout" lang="de">
  <aside class="side"><nav aria-label="Inhalt"><ol id="toc"></ol></nav></aside>
  <main class="main">
    <section class="intro" id="start" data-short="Start">
      <div class="hero">
        <p class="kicker">Klausur am 06.11.2026 · open book</p>
        <h2 style="font-size:clamp(2rem,4.5vw,2.9rem);letter-spacing:-.02em">Lernskript Wirtschaftsinformatik I</h2>
        <p>Der komplette Stoff der sechs Vorlesungen und Tutorien, so aufbereitet, dass du jeden Begriff erklären und auf einen Fall anwenden kannst. Jede Definition verweist auf die Folie (V02 F.14 = Vorlesung 2, aufgedruckte Foliennummer 14 unten rechts), damit du sie in deinem Ausdruck wiederfindest. Achtung: In V01, V02 und V04 weicht die aufgedruckte Nummer wegen ausgeblendeter Folien von der PDF-Seitenzahl ab; die Verweise nutzen immer die aufgedruckte Nummer. Am Ende jedes Kapitels steht ein Selbsttest mit {nq} Fragen insgesamt.</p>
      </div>
      <div class="howto">
        <div class="legend-def"><b>Definition</b>Wortlaut der Vorlesung. Genau diese Begriffe erwartet die Korrektur.</div>
        <div class="legend-ex"><b>Beispiel</b>Anwendung auf einen Fall, so wie in der Klausur verlangt.</div>
        <div class="legend-exam"><b>Klausurfokus</b>Wie das Thema bisher geprüft wurde und wofür es Punkte gibt.</div>
        <div class="legend-pit"><b>Typischer Fehler</b>Verwechslungen und Abgrenzungen, die Punkte kosten.</div>
        <div class="legend-deep"><b>Vertiefung</b>Hintergrund über die Folien hinaus, für das Verständnis.</div>
      </div>
    </section>
{chapters}
  </main>
</div>"""
    return write("01_Lernskript.html", page("Lernskript Wirtschaftsinformatik I",
                 "Tiefes Lernskript zu IS 201 mit Definitionen, Grafiken, Beispielen und Selbsttests.",
                 SKRIPT_CSS, body, SKRIPT_JS))


# ---------------------------------------------------------------- Klausuren
KLAUSUR_CSS = r"""
.exam-date { font-family: var(--font-mono); font-size: .8rem; font-weight: 400; color: var(--muted); margin-left: .6em; }
.exam-meta { font-family: var(--font-ui); font-size: .86rem; color: var(--muted); }
.task { margin-top: 2.6rem; }
.task > h3 { display: flex; gap: 1em; justify-content: space-between; align-items: baseline; border-bottom: 1px solid var(--line); padding-bottom: .4em; margin-top: 0; }
.pts { font-family: var(--font-mono); font-size: .78rem; font-weight: 500; color: var(--accent); white-space: nowrap; }
.case { background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: 1em 1.2em .2em; margin: 1em 0; font-size: .97em; }
.sub { margin: 1.3em 0; }
.q { font-family: var(--font-ui); font-size: .97rem; margin-bottom: .5em; }
.q .pts { margin-left: .4em; }
.timer { font-family: var(--font-mono); font-size: 1rem; font-weight: 500; color: var(--exam); }
body.exam-mode details.sol { display: none; }
.exam-intro .tbl { font-size: .8rem; }
"""

KLAUSUR_JS = "var SUBSEL = 'article.task > h3';\n" + TOC_JS + r"""
(function () {
  var b = document.getElementById('toggle-all'), open = false;
  b.addEventListener('click', function () {
    open = !open; b.setAttribute('aria-pressed', open);
    b.textContent = open ? 'Lösungen einklappen' : 'Alle Lösungen zeigen';
    document.querySelectorAll('details.sol').forEach(function (d) { d.open = open; });
  });
  var m = document.getElementById('exam-mode'), t = document.getElementById('timer'), iv = null, end = 0;
  function tick() {
    var s = Math.max(0, Math.round((end - Date.now()) / 1000));
    t.textContent = String(Math.floor(s / 60)).padStart(2, '0') + ':' + String(s % 60).padStart(2, '0');
    if (s === 0) { clearInterval(iv); t.textContent = 'Zeit vorbei'; }
  }
  m.addEventListener('click', function () {
    var on = !document.body.classList.contains('exam-mode');
    document.body.classList.toggle('exam-mode', on); m.setAttribute('aria-pressed', on);
    m.textContent = on ? 'Klausurmodus beenden' : 'Klausurmodus (90 Min)';
    t.hidden = !on; clearInterval(iv);
    if (on) { end = Date.now() + 90 * 60 * 1000; tick(); iv = setInterval(tick, 1000); }
  });
})();
"""


def build_klausuren():
    alt, neu = part("klausuren_alt.html"), part("klausuren_neu.html")
    body = f"""
<header class="topbar"><div class="topbar-in">
  <span class="brand">Wirtschaftsinformatik I <small>Klausuren &amp; Lösungen</small></span>
  <span class="spacer"></span>
  <span class="timer" id="timer" hidden>90:00</span>
  <button class="btn" id="exam-mode" type="button" aria-pressed="false">Klausurmodus (90 Min)</button>
  <button class="btn" id="toggle-all" type="button" aria-pressed="false">Alle Lösungen zeigen</button>
</div></header>
<div class="layout" lang="de">
  <aside class="side"><nav aria-label="Klausuren"><ol id="toc"></ol></nav></aside>
  <main class="main">
    <section class="intro" id="start" data-short="Start">
      <div class="hero">
        <p class="kicker">4 Altklausuren · Probeklausur 2026 · 4 Prognose-Klausuren</p>
        <h2 style="font-size:clamp(2rem,4.5vw,2.9rem);letter-spacing:-.02em">Klausurtraining Wirtschaftsinformatik I</h2>
        <p>Alle vorliegenden Klausuren mit ausgearbeiteten Musterlösungen, danach vier eigene Klausuren zu den Themen, die am 06.11. am wahrscheinlichsten drankommen. Die Lösungen sind nicht offiziell, sondern auf Basis der Folien erstellt; jede verweist auf die Folien zum Nachschlagen. Der Klausurmodus blendet alle Lösungen aus und startet einen 90-Minuten-Countdown.</p>
      </div>
    </section>
{alt}
{neu}
  </main>
</div>"""
    return write("03_Klausuren.html", page("Klausurtraining Wirtschaftsinformatik I",
                 "Alle Altklausuren und die Probeklausur 2026 mit Musterlösungen plus vier Prognose-Klausuren.",
                 KLAUSUR_CSS, body, KLAUSUR_JS))


# ---------------------------------------------------------------- Nachschlagewerk
REF_CSS = r"""
body { font-family: var(--font-cond); font-size: 15px; line-height: 1.45; }
.wrap { max-width: 1100px; margin: 0 auto; padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); padding-block: 1.5rem 5rem; }
.tabs { display: flex; flex-wrap: wrap; gap: .3em; }
.tabs a { font: 500 .8rem var(--font-ui); text-decoration: none; color: var(--fg); padding: .3em .6em; border: 1px solid var(--line); border-radius: 4px; background: var(--surface); }
.tabs a:hover { border-color: var(--accent); color: var(--accent); }
section.ref, section.finder, section.index { margin-top: 3rem; }
section.ref > h2, section.finder > h2, section.index > h2 { font-size: 1.4rem; display: flex; align-items: baseline; gap: .6em; border-bottom: 2px solid var(--fg); padding-bottom: .25em; }
section.ref > h2 .chap-no, section.finder > h2 .chap-no, section.index > h2 .chap-no { display: inline-block; background: var(--fg); color: var(--bg); padding: .1em .45em; border-radius: 3px; margin: 0; letter-spacing: .04em; }
.f { font-family: var(--font-mono); font-size: .72rem; font-weight: 400; color: var(--muted); white-space: nowrap; }
h2 .f { margin-left: auto; }
.ref-item, .schema { padding: .6em 0 .5em; border-bottom: 1px solid var(--line); }
.ref-item h3, .schema h4 { font-size: 1rem; margin: 0 0 .35em; display: flex; flex-wrap: wrap; gap: .2em .6em; align-items: baseline; }
.ref-item h3 .f, .schema h4 .f { margin-left: auto; }
.code { font-family: var(--font-mono); font-size: .74rem; font-weight: 500; color: var(--accent); background: var(--accent-soft); padding: .05em .35em; border-radius: 3px; }
.ref-item .d { font-family: var(--font-body); font-style: italic; }
.ref-item p, .schema p { margin-bottom: .4em; }
.ref-item ul, .ref-item ol, .schema ol, .schema ul { margin-bottom: .4em; }
.schema { background: var(--exam-bg); border: 1px solid var(--exam); border-radius: 5px; padding: .6em .9em .4em; margin: .8em 0; }
.schema h4 { color: var(--exam); }
.phr { font-family: var(--font-body); font-size: .95em; }
.tbl { font-family: var(--font-cond); }
.fig { padding: .6em; }
.fig svg { max-width: 560px; }
.hidden-by-search { display: none !important; }
.finder-grid { columns: 2 340px; column-gap: 2rem; }
.finder-grid h3 { font-size: .8rem; letter-spacing: .07em; text-transform: uppercase; color: var(--muted); margin: 1em 0 .3em; break-after: avoid; }
.frow, .irow { display: flex; gap: .5em; align-items: baseline; break-inside: avoid; padding: .12em 0; }
.frow a, .irow a { color: var(--fg); text-decoration: none; }
.frow a:hover, .irow a:hover { color: var(--accent); }
.dots { flex: 1; border-bottom: 1px dotted var(--muted); transform: translateY(-.25em); min-width: 1em; }
.pg { font-family: var(--font-mono); font-size: .75rem; color: var(--muted); white-space: nowrap; }
.index-grid { columns: 3 220px; column-gap: 1.6rem; font-size: .88rem; }
.index-grid .letter { font: 600 .9rem var(--font-ui); margin: .8em 0 .2em; border-bottom: 1px solid var(--line); break-after: avoid; }
.cover { padding-block: 2rem 1rem; }
.cover h1 { font-size: clamp(1.9rem, 4vw, 2.6rem); margin: .2em 0 .3em; letter-spacing: -.02em; }
.cover p { max-width: 70ch; color: var(--muted); font-family: var(--font-ui); font-size: .92rem; }

@media print {
  :root, :root[data-theme="dark"] {
    --bg: #ffffff; --surface: #ffffff; --surface-2: #eef0f4; --fg: #000000; --muted: #4a5262; --line: #c4cad4;
    --accent: #1d3aa0; --accent-soft: #e4e9fa; --hl: #fff0a0; --exam: #8a4f00; --exam-bg: #fff6e6;
    --def: #1d3aa0; --def-bg: #eef2fd; --ex: #1b7550; --ex-bg: #edf7f1; --pit: #a3221a; --pit-bg: #fdeeed;
    color-scheme: light;
  }
  @page { size: A4; margin: 10mm 10mm 13mm 10mm; }
  body { font-size: 8.4pt; line-height: 1.32; }
  body::before { display: none; }
  .topbar, .no-print { display: none !important; }
  .wrap { max-width: none; padding: 0; }
  section.ref, section.finder, section.index { break-before: page; margin-top: 0; }
  section.ref { columns: 2; column-gap: 6mm; column-fill: auto; }
  section.ref > h2 { column-span: all; font-size: 13pt; margin-bottom: 2mm; }
  .tbl-wrap, .fig, .span-all { column-span: all; }
  .ref-item h3, .schema h4 { font-size: 9.2pt; break-after: avoid; }
  .ref-item, .schema { padding: 1.2mm 0; }
  .schema { padding: 1.5mm 2.5mm; margin: 1.5mm 0; break-inside: avoid; }
  .tbl-wrap { overflow: visible; border-radius: 0; margin: 1.5mm 0; }
  .tbl td, .tbl th { overflow-wrap: anywhere; }
  .tbl { font-size: 7.6pt; line-height: 1.25; }
  .tbl th, .tbl td { padding: .8mm 1.4mm; }
  .tbl tr { break-inside: avoid; }
  .fig { break-inside: avoid; border-radius: 0; margin: 1.5mm 0; }
  .fig svg { max-width: 120mm; }
  ul, ol { padding-left: 1.2em; }
  li { margin: .3mm 0; }
  .finder-grid { columns: 2; column-gap: 8mm; font-size: 8.6pt; }
  .index-grid { columns: 3; column-gap: 5mm; font-size: 7.8pt; }
  .cover { break-after: page; }
  a { color: inherit; text-decoration: none; }
}
"""

REF_JS = r"""
(function () {
  var s = document.getElementById('q');
  var items = Array.prototype.slice.call(document.querySelectorAll('.ref-item, .schema, .irow, .frow'));
  var texts = items.map(function (el) { return el.textContent.toLowerCase(); });
  s.addEventListener('input', function () {
    var v = s.value.trim().toLowerCase();
    items.forEach(function (el, i) { el.classList.toggle('hidden-by-search', v.length > 1 && texts[i].indexOf(v) < 0); });
  });
})();
"""


def fold(s):
    s = s.lstrip("„“\"'»«(").lower().replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    return unicodedata.normalize("NFKD", s)


def number_ref(txt, ch):
    """Insert a visible code (R2.07) into every ref-item h3 and schema h4; return text and id->(code,title)."""
    codes = {}
    n = 0

    def repl(m):
        nonlocal n
        n += 1
        code = f"R{ch}.{n:02d}"
        block_id, tag = m.group(2), m.group(4)
        codes[block_id] = code
        return f'{m.group(1)}<{tag}><span class="code">{code}</span> '

    pat = re.compile(r'(<div class="(?:ref-item|schema)" id="([^"]+)"[^>]*>\s*)(<(h3|h4)>)')
    out = pat.sub(repl, txt)
    return out, codes


def strip_tags(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def build_ref(pages=None):
    pages = pages or {}
    sections, all_codes, schemas = [], {}, []
    for ch in range(1, 7):
        txt = part(f"ref_k{ch}.html")
        if not txt:
            continue
        txt, codes = number_ref(txt, ch)
        all_codes.update(codes)
        for m in re.finditer(r'<div class="schema" id="([^"]+)"[^>]*>\s*<h4>(.*?)</h4>', txt, re.S):
            title = re.sub(r'<span class="(?:code|f)">.*?</span>', "", m.group(2))
            title = strip_tags(title)
            title = re.sub(r"^Antwortschema\s*[·:\-–]\s*", "", title)
            schemas.append((ch, m.group(1), title))
        sections.append(txt)

    def pg(anchor):
        p = pages.get(anchor)
        return f"S.&#8239;{p}" if p else "S.&#8239;&#8199;&#8199;"

    chap_names = {1: "Gegenstand & Wissenschaft", 2: "Theorie, Technologie & Methoden", 3: "Gestaltung & Praxis",
                  4: "Ziele, Information & Kommunikation", 5: "Mensch & Typisierung", 6: "Infrastruktur & Digitalisierung"}
    frows = []
    for ch in range(1, 7):
        rows = [s for s in schemas if s[0] == ch]
        if not rows:
            continue
        frows.append(f'<h3>R{ch} · {chap_names[ch]}</h3>')
        for _, sid, title in rows:
            frows.append(f'<div class="frow"><span class="code">{all_codes.get(sid, "")}</span>'
                         f'<a href="#{sid}">{html.escape(title)}</a><span class="dots"></span>'
                         f'<span class="pg">{pg(sid)}</span></div>')

    entries = []
    for ch in range(1, 7):
        for line in read(os.path.join(PARTS, f"index_k{ch}.tsv")).splitlines():
            cols = [c.strip() for c in line.split("\t")]
            if len(cols) < 2 or not cols[0] or cols[0].lower() == "begriff":
                continue
            anchor = cols[1]
            if anchor not in all_codes:
                continue
            entries.append((cols[0], anchor))
    seen, uniq = set(), []
    for term, anchor in sorted(entries, key=lambda e: fold(e[0])):
        key = (fold(term), anchor)
        if key in seen:
            continue
        seen.add(key)
        uniq.append((term, anchor))
    irows, last = [], ""
    for term, anchor in uniq:
        letter = fold(term)[:1].upper()
        if not letter.isalpha():
            letter = "#"
        if letter != last:
            irows.append(f'<div class="letter">{letter}</div>')
            last = letter
        irows.append(f'<div class="irow"><a href="#{anchor}">{html.escape(term)}</a><span class="dots"></span>'
                     f'<span class="pg">{all_codes[anchor]} · {pg(anchor)}</span></div>')

    tabs = "".join(f'<a href="#r{ch}">R{ch}</a>' for ch in range(1, 7)) + '<a href="#wegweiser">Wegweiser</a><a href="#stichwort">Stichwörter</a>'
    body = f"""
<header class="topbar"><div class="topbar-in">
  <span class="brand">Nachschlagewerk <small>IS 201 · Klausur 06.11.2026</small></span>
  <nav class="tabs" aria-label="Kapitel">{tabs}</nav>
  <span class="spacer"></span>
  <label class="no-print" for="q" style="font-size:.8rem;color:var(--muted)">Suchen</label>
  <input class="search" id="q" type="search" placeholder="z. B. Moderator">
</div></header>
<div class="wrap" lang="de">
  <div class="cover">
    <p class="kicker">Open-Book-Klausur · Hardcopy</p>
    <h1>Nachschlagewerk Wirtschaftsinformatik I</h1>
    <p>So findest du in der Klausur in Sekunden, was du brauchst: Erkennst du den Aufgabentyp, gehe über den <b>Wegweiser</b> direkt zum passenden Antwortschema (orange Kästen) mit Gliederung und Formulierungsbausteinen. Suchst du einen Begriff, nimm das <b>Stichwortverzeichnis</b> am Ende. Jeder Eintrag hat einen Code (R2.07 = Kapitel 2, Eintrag 7) und einen Verweis auf die Originalfolie (V02 F.14 = aufgedruckte Foliennummer, nicht PDF-Seite) in deinem Folienausdruck.</p>
    <p>R1 Gegenstand &amp; Wissenschaft (V01) · R2 Theorie, Technologie &amp; Methoden (V02) · R3 Gestaltung &amp; Praxis (V03) · R4 Ziele, Information &amp; Kommunikation (V04) · R5 Mensch &amp; Typisierung (V05) · R6 Infrastruktur &amp; Digitalisierung (V06)</p>
  </div>
  <section class="finder" id="wegweiser">
    <h2><span class="chap-no">W</span>Wegweiser · Aufgabentyp → Antwortschema</h2>
    <div class="finder-grid">{''.join(frows)}</div>
  </section>
  {''.join(sections)}
  <section class="index" id="stichwort">
    <h2><span class="chap-no">A–Z</span>Stichwortverzeichnis</h2>
    <div class="index-grid">{''.join(irows)}</div>
  </section>
</div>"""
    return write("02_Nachschlagewerk.html", page("Nachschlagewerk Wirtschaftsinformatik I",
                 "Druckfertiges Open-Book-Nachschlagewerk mit Antwortschemata, Wegweiser und Stichwortverzeichnis.",
                 REF_CSS, body, REF_JS))


def chrome_pdf(html_path, pdf_path):
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    "--run-all-compositor-stages-before-draw", "--virtual-time-budget=15000",
                    f"--print-to-pdf={pdf_path}", "file:///" + html_path.replace("\\", "/")],
                   check=True, capture_output=True, timeout=300)


def wrap_skeleton(src, dst, open_details=False):
    """Chrome needs the doctype skeleton that the Artifact host adds at publish time."""
    body = read(src)
    if open_details:
        body = body.replace("<details ", "<details open ")
    with open(dst, "w", encoding="utf-8") as f:
        f.write('<!doctype html><html lang="de"><head><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width, initial-scale=1"></head><body>' + body + "</body></html>")


def link_pages(pdf_path):
    import fitz
    doc = fitz.open(pdf_path)
    pages = {}
    for p in doc:
        for ln in p.get_links():
            if ln.get("kind") == fitz.LINK_NAMED or ln.get("kind") == fitz.LINK_GOTO:
                target = ln.get("nameddest") or ln.get("name")
                pg = ln.get("page")
                if target and pg is not None and pg >= 0:
                    pages.setdefault(target, pg + 1)
    return pages, doc


def stamp(pdf_path, labels):
    import fitz
    doc = fitz.open(pdf_path)
    n = len(doc)
    for i, p in enumerate(doc):
        if i == 0:
            continue
        r = p.rect
        label = labels.get(i + 1, "")
        p.insert_text((r.width / 2 - 14, r.height - 18), f"S. {i + 1}", fontsize=8, fontname="helv", color=(0.3, 0.3, 0.35))
        if label:
            p.insert_text((28, r.height - 18), label, fontsize=7, fontname="helv", color=(0.4, 0.4, 0.45))
        p.insert_text((r.width - 110, r.height - 18), "IS 201 Nachschlagewerk", fontsize=7, fontname="helv", color=(0.4, 0.4, 0.45))
    tmp = pdf_path + ".tmp"
    doc.save(tmp, garbage=3, deflate=True)
    doc.close()
    os.replace(tmp, pdf_path)
    print(f"  stamped {n} pages")


def ref_pdf():
    import fitz
    src = os.path.join(OUT, "02_Nachschlagewerk.html")
    tmp_html = os.path.join(BUILD, "ref_print.html")
    pdf = os.path.join(OUT, "02_Nachschlagewerk.pdf")
    wrap_skeleton(src, tmp_html)
    chrome_pdf(tmp_html, pdf)
    # The topbar tabs are hidden in print, so the visible internal links are exactly the
    # wegweiser + index links, in document order.
    pages = {}
    doc = fitz.open(pdf)
    for p in doc:
        for ln in p.get_links():
            if ln.get("nameddest") and ln.get("page", -1) >= 0:
                pages[ln["nameddest"]] = ln["page"] + 1
    print(f"  resolved {len(pages)} anchor pages")
    doc.close()
    build_ref(pages)
    wrap_skeleton(src, tmp_html)
    chrome_pdf(tmp_html, pdf)
    # chapter labels for footers
    import fitz as _f
    d = _f.open(pdf)
    labels, cur = {}, ""
    for i, p in enumerate(d):
        t = p.get_text()
        if cur == "A–Z" or "Stichwortverzeichnis" in t[:300]:
            labels[i + 1] = cur = "A–Z"
            continue
        if "Wegweiser" in t[:300]:
            cur = "Wegweiser"
        for ch in range(1, 7):
            if re.search(rf"\bR{ch}\.\d\d\b", t) and "Wegweiser" not in t[:200]:
                m = re.findall(rf"\bR({ch})\.\d\d\b", t)
                if m:
                    cur = f"R{ch}"
        labels[i + 1] = cur
    d.close()
    stamp(pdf, labels)
    return pdf


def other_pdf(name, pdfname):
    src = os.path.join(OUT, name)
    tmp_html = os.path.join(BUILD, pdfname + ".html")
    wrap_skeleton(src, tmp_html, open_details=True)
    chrome_pdf(tmp_html, os.path.join(OUT, pdfname))
    print("  wrote", pdfname)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    build_skript()
    build_klausuren()
    build_ref()
    if DO_PDF:
        ref_pdf()
        other_pdf("01_Lernskript.html", "01_Lernskript.pdf")
        other_pdf("03_Klausuren.html", "03_Klausuren.pdf")
