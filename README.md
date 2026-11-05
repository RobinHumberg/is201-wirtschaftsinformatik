# IS 201 Wirtschaftsinformatik I – Klausurvorbereitung

Lernmaterial für die Open-Book-Klausur IS 201 (Uni Mannheim, Prof. Heinzl), 06.11.2026.

| Datei | Inhalt |
|---|---|
| `01_Lernskript` (.html/.pdf) | Ausführliches Lernskript zu V01–V06 und T01–T06 mit Grafiken, Beispielen und Selbsttests |
| `02_Nachschlagewerk` (.html/.pdf) | Ausdruckbares Nachschlagewerk für die Klausur: Wegweiser, Antwortschemata, A–Z-Index mit Seitenzahlen |
| `03_Klausuren` (.html/.pdf) | Altklausuren mit Musterlösungen, 4 Prognose-Klausuren, Klausurmodus mit 90-Minuten-Timer |
| `04_Crashkurs` (.html/.pdf) | 48-seitiger Crashkurs zu Kapitel 3–6 plus Klausurteil (Kernschemata K1/K2, alle Altklausuren mit Lösungsskizze, Prognose, Checkliste) |

Folienverweise (z. B. „V04 F.92") nutzen die **aufgedruckte** Foliennummer, nicht die PDF-Seite.

## Neu bauen

`src/parts/` enthält die Inhaltsfragmente, `src/build/` das Assembly-Skript (Python 3, PyMuPDF; Headless Chrome für PDFs).

```bash
python src/build/assemble.py src . --pdf
```

Der Crashkurs liegt separat in `src/crash/`:

```bash
python src/crash/build_crash.py .
```
