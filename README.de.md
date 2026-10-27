# XAFS Fit Skill · EXAFS + XANES

[![test](https://github.com/catdaog/artemis-xafs-fit-skill/actions/workflows/test.yml/badge.svg)](https://github.com/catdaog/artemis-xafs-fit-skill/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[中文](README.md) · [English](README.en.md) · [Deutsch](README.de.md) · [日本語](README.ja.md) · [Français](README.fr.md)

**Ein Skill, zwei Fit-Verfahren: quantitative EXAFS-Analyse und XANES-Simulation mit geometrischer Strukturanpassung.**

`artemis-xafs-fit-skill` führt echte lokale Rechenprogramme aus und bewahrt Originaldaten, Strukturquellen, Eingaben, Ausgaben und Fit-Protokolle. Beide Verfahren lassen sich einzeln nutzen oder zur Prüfung desselben Strukturmodells kombinieren.

## Das passende Fit-Verfahren wählen

| Aspekt | EXAFS-Fit | XANES-Fit im Nahkantenbereich |
|---|---|---|
| Fragestellung | Koordinationszahlen, Bindungslängen, Debye–Waller-Faktoren und Streupfade | Übereinstimmung möglicher Koordinationsgeometrien und Nahkantenspektren mit den Daten |
| Rechenprogramme | Athena / Artemis / Demeter + FEFF | FDMNES: Green-Mehrfachstreuung oder Finite-Differenzen-Methode |
| Eingaben | Numerische Spektren oder ungewichtetes χ(k), Verarbeitungseinstellungen, Referenzstandard an derselben Absorptionskante und Struktur-/FEFF-Modell | Energie–Absorptionsdaten, Angaben zur Kalibrierung und Normierung sowie mögliche Atomstrukturen |
| Ablauf | S₀² am Standard bestimmen → Streupfade prüfen → stufenweise fitten → Parameter bewerten | Cluster aufbauen → Konvergenz prüfen → Spektren ausrichten → wenige Geometrieparameter optimieren → mehrere Startwerte vergleichen |
| Ausgaben | Erneut ladbare DPJ-Datei, k1/k2/k3- und R1/R2/R3-Tabellen, Parameter und Ablaufprotokoll | Tabellen für Messdaten, Berechnung und Residuen, Parameter, Modellvergleich, PNG/SVG, Strukturen, Eingaben und Protokolle |
| Anleitungen | [EXAFS-Anleitung (Englisch)](references/exafs-guide.en.md) | [XANES-/FDMNES-Anleitung (Englisch)](references/xanes-fdmnes.md) |

**XANES hat einen eigenen Ablauf und eigene Ergebnisdateien; die EXAFS-Kalibrierung von S₀², k/R-Fenster und eine DPJ-Datei sind keine Voraussetzung.** Die Linearkombinationsanalyse von Referenzspektren (LCF) ist ein anderes Verfahren und wird von diesem XANES-Zweig nicht umgesetzt.

## Direkter Aufruf

**EXAFS:**

```text
Verwende $artemis-xafs-fit-skill für den Fit meiner EXAFS-Daten. Bestimme S₀² anhand eines Standards an derselben Absorptionskante mit bekannter Koordination, fitte die Probe und liefere eine erneut ladbare DPJ-Datei, numerische k/R-Tabellen, Parameter und ein Ablaufprotokoll.
```

**XANES:**

```text
Verwende $artemis-xafs-fit-skill für FDMNES-Nahkantenrechnungen und die geometrische Strukturanpassung meiner Probe mit Einzelatomzentren. Erstelle mögliche Modelle anhand der Zusammensetzung und vorhandener EXAFS-Ergebnisse, prüfe die Konvergenz, vergleiche mehrere Startwerte und liefere Spektrenvergleiche, Residuen und reproduzierbare Dateien.
```

## Benötigte Unterlagen

- Für beide Verfahren: Absorberelement und Absorptionskante, Zuordnung der Dateien zu den Proben, Messbedingungen, Spaltendefinitionen, Grundlage der Energiekalibrierung und numerische Spektren. Wiederholungsmessungen aufbewahren.
- EXAFS: möglichst einen Standard an derselben Kante, Athena-`.prj`, ungewichtetes χ(k) mit Verarbeitungseinstellungen und CIF-/FEFF-Dateien. Bei einem bestehenden Fit zusätzlich `.fpj`/`.dpj` und Protokolle.
- XANES: normiertes μ(E) oder μ(E) mit geeigneten Normierungsfenstern. Rohe Detektorzählraten müssen zunächst entsprechend dem Messmodus umgerechnet werden. CIF oder explizite Atomkoordinaten verwenden; hypothetische Strukturen als Modellkandidaten kennzeichnen.

Bildschirmfotos helfen bei der Erklärung, ersetzen aber keine numerischen Fit-Daten. Fehlt eine Strukturdatei, lassen sich zunächst Modellkandidaten aus Zusammensetzung und unabhängigen Befunden erstellen.

## Installation und Ausführung

Ein [Release](https://github.com/catdaog/artemis-xafs-fit-skill/releases) herunterladen oder das Repository klonen. Den Ordner `artemis-xafs-fit-skill` im Skills-Verzeichnis ablegen, etwa unter `~/.codex/skills/`. In diesem Ordner die Abhängigkeiten in der verwendeten Python-Umgebung installieren:

```shell
python -m pip install -r requirements.txt -r requirements-xanes.txt
```

EXAFS benötigt eine separate Installation von [Demeter](https://bruceravel.github.io/demeter/) / [FEFF](https://feff.phys.washington.edu/feffproject-feff-download.html). FDMNES für XANES über die [offizielle Downloadseite](https://fdmnes.neel.cnrs.fr/download/) beziehen. Diese externen Programme sind nicht enthalten. Unter Windows:

```powershell
.\scripts\run_xanes.ps1 -Mode install -Archive C:\path\fdmnes.zip
.\scripts\run_xanes.ps1 -Mode probe
.\scripts\run_xanes.ps1 -Mode simulate -Config examples\xanes\fe-n4.json -Output C:\work\xanes_sim
.\scripts\run_xanes.ps1 -Mode fit -Config C:\work\xanes.json -Output C:\work\xanes_fit
```

Alternativ kann `FDMNES_EXE` auf eine vorhandene ausführbare Datei verweisen. Konfiguration und Befehle stehen in der XANES-Anleitung. Übersetzt werden die Anleitungen; Programmargumente und Dateinamen bleiben unverändert.

## Ergebnisse und Validierung

v1.4.0 bestand 23 lokale Tests, darunter die Rückgewinnung bekannter Parameter aus einem synthetischen Spektrum mit echtem FDMNES und eine Finite-Differenzen-Rechnung. GitHub CI führt die Tests ohne externes Rechenprogramm aus. Der synthetische Test prüft die Software und Parameterbestimmung, nicht die Struktur eines realen Katalysators.

Simulation, Spektrenausrichtung und Strukturfit werden getrennt gekennzeichnet. Auch nach numerischer Konvergenz sind Residuen, Korrelationen, Parametergrenzen und die Abhängigkeit von Startwerten zu prüfen. XANES-Übereinstimmung allein belegt weder atomare Dispersion noch eine eindeutige Struktur.

## Dokumentation und Beispiele

- [Ausführliche EXAFS-Anleitung (Englisch)](references/exafs-guide.en.md)
- [XANES-/FDMNES-Ablauf (Englisch)](references/xanes-fdmnes.md)
- [Vorlage für EXAFS-Serienauswertung](examples/pipeline.template.json)
- [XANES-Beispiel: illustratives Modell mit fünf Atomen](examples/xanes/fe-n4.json)
- [Skill-Einstieg und Vorgaben (Englisch)](SKILL.md)
- [Änderungsprotokoll (Chinesisch/Englisch)](CHANGELOG.md)

Lizenz: Der Skill-Quellcode steht unter [MIT](LICENSE); für externe Rechenprogramme gelten deren eigene Lizenzen.

[中文](README.md) · [English](README.en.md) · [Deutsch](README.de.md) · [日本語](README.ja.md) · [Français](README.fr.md)
