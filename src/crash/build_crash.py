"""Assemble the crash-course HTML/PDF from the parts in ./parts. Usage: python src/crash/build_crash.py <lernmaterial_dir>"""
import json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1]
BUILD = os.path.join(OUT, "src", "build")
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

SLIDEMAP = {k: {int(p): n for p, n in v.items()} for k, v in
            json.load(open(os.path.join(BUILD, "slidemap.json"), encoding="utf-8")).items()}
REF_RE = re.compile(r"(?<![A-Za-z])(?:(V0[1-6]|T0[1-6])\s*)?F\.\s?(\d{1,3})((?:\s*[–\-,/]\s*\d{1,3}(?![\d.]))*)")


def fix_refs(txt, default_deck=None):
    """Same conversion as assemble.py: PDF page numbers -> printed slide numbers."""
    state = {"deck": default_deck}

    def conv(deck, n):
        return SLIDEMAP.get(deck, {}).get(n, n)

    def repl(m):
        deck = m.group(1) or state["deck"]
        if m.group(1):
            state["deck"] = m.group(1)
        if not deck or deck not in SLIDEMAP:
            return m.group(0)
        tail = re.sub(r"\d{1,3}", lambda x: str(conv(deck, int(x.group(0)))), m.group(3))
        prefix = (m.group(1) + " ") if m.group(1) else ""
        return f"{prefix}F.{conv(deck, int(m.group(2)))}{tail}"

    out = []
    for b in re.split(r"(</p>|</li>|</div>|</td>|</summary>|</h4>|</figcaption>)", txt):
        state["deck"] = default_deck
        out.append(REF_RE.sub(repl, b))
    return "".join(out)


EXTRA_CSS = r"""
.wrap { max-width: 840px; margin: 0 auto; padding: 1rem 16px 5rem; }
.main section + section { margin-top: 4rem; padding-top: 2.5rem; border-top: 2px solid var(--line); }
.hero h1 { font-size: clamp(2rem, 5vw, 2.9rem); }
.prio { display: inline-block; font: 600 .66rem var(--font-ui); letter-spacing: .06em; text-transform: uppercase; padding: .15em .55em; border-radius: 3px; vertical-align: .2em; margin-left: .4em; border: 1px solid currentColor; }
.prio.p1 { color: var(--pit); background: var(--pit-bg); }
.prio.p2 { color: var(--exam); background: var(--exam-bg); }
.prio.p3 { color: var(--muted); background: var(--surface-2); }
.flow { display: flex; flex-wrap: wrap; align-items: stretch; gap: .4em; margin: 1.1em 0; font-family: var(--font-ui); font-size: .86rem; }
.flow .st { flex: 1 1 140px; background: var(--surface); border: 1px solid var(--line); border-top: 3px solid var(--accent); border-radius: 6px; padding: .55em .7em; line-height: 1.4; }
.flow .st b { display: block; margin-bottom: .2em; }
.flow .ar { align-self: center; color: var(--accent); font-weight: 600; }
.flow.small .st { flex-basis: 95px; font-size: .8rem; }
.flow.v { flex-direction: column; }
.flow.v .st { flex-basis: auto; }
.flow.v .ar { align-self: flex-start; padding-left: 1.2em; font-size: .8rem; }
.flow .st i { display: block; color: var(--muted); font-style: normal; margin-top: .25em; font-size: .92em; }
.toc-static { font-family: var(--font-ui); }
.toc-static li { margin: .35em 0; }
.tbl.canvas td { text-align: center; vertical-align: middle; font-weight: 500; }
.tbl.canvas small { display: block; color: var(--muted); font-weight: 400; }
.tbl td:first-child, .tbl th:first-child { hyphens: manual; min-width: 7.5em; }
@media print {
  @page { size: A4; margin: 12mm 13mm 14mm; }
  body { font-size: 9.4pt; }
  .tbl td, .tbl th { overflow-wrap: break-word; }
  .tbl td:first-child, .tbl th:first-child { overflow-wrap: normal; }
  .wrap { max-width: none; padding: 0; }
  .main section + section { margin-top: 0; padding-top: 0; border-top: 0; break-before: page; }
  .flow .st, .flow { break-inside: avoid; }
  .tbl tr:first-child { break-after: avoid; }
  h4 { break-after: avoid; }
  details.quiz > summary { padding: .4em .8em; }
}
"""

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500'
         '&family=IBM+Plex+Sans+Condensed:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600'
         '&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400&display=swap">')


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


decks = {"k0": None, "k3": "V03", "k4": "V04", "k5": "V05", "k6": "V06", "kl": None}
body = "\n".join(fix_refs(read(os.path.join(HERE, "parts", f"{k}.html")), d) for k, d in decks.items())
css = read(os.path.join(BUILD, "common.css")) + EXTRA_CSS


def page(content):
    return ('<!doctype html><html lang="de"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<title>Crashkurs Wirtschaftsinformatik I</title>'
            '<meta name="description" content="Kompaktskript Kapitel 3–6 plus Klausurteil für die IS-201-Klausur am 06.11.2026.">'
            f'{FONTS}<style>{css}</style></head><body><div class="wrap"><main class="main">{content}</main></div></body></html>')


html_path = os.path.join(OUT, "04_Crashkurs.html")
with open(html_path, "w", encoding="utf-8") as f:
    f.write(page(body))

print_path = os.path.join(HERE, "crash_print.html")
with open(print_path, "w", encoding="utf-8") as f:
    f.write(page(body.replace('<details class="quiz">', '<details class="quiz" open>')))

pdf = os.path.join(OUT, "04_Crashkurs.pdf")
subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                "--run-all-compositor-stages-before-draw", "--virtual-time-budget=15000",
                f"--print-to-pdf={pdf}", "file:///" + print_path.replace("\\", "/")],
               check=True, capture_output=True, timeout=300)

import fitz
doc = fitz.open(pdf)
for i, p in enumerate(doc):
    if i == 0:
        continue
    r = p.rect
    p.insert_text((r.width / 2 - 14, r.height - 18), f"S. {i + 1}", fontsize=8, fontname="helv", color=(0.3, 0.3, 0.35))
    p.insert_text((r.width - 120, r.height - 18), "IS 201 Crashkurs K3-K6", fontsize=7, fontname="helv", color=(0.4, 0.4, 0.45))
tmp = pdf + ".tmp"
doc.save(tmp, garbage=3, deflate=True)
n = len(doc)
doc.close()
os.replace(tmp, pdf)
print("pages:", n)
