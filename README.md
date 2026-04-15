# XRename

XRename ist ein Tool zum automatischen Umbenennen von **Serien** und **Filmen** 
nach einem sauberen, einheitlichen Schema.

Es unterstützt:
- Drag & Drop
- Kommandozeile
- Windows-Kontextmenü (mit Untermenü für Serien & Filme)
- IMDb-Daten über OMDb API (optional für Filme)

---

## Features

### Serien
- Erkennt Muster wie s01e02, S01E02 etc.
- Wandelt Namen automatisch in lesbares Format um
- Beispiel: MEINE_SERIE.s01e02.mkv → Meine Serie s01e02.mkv
- Bestätigung bei mehr als 50 Änderungen

### Filme
- Nutzt .nfo Dateien zur Erkennung (bevorzugt)
- Unterstützte Erkennungsmethoden (in dieser Reihenfolge):
  1. IMDb ID aus NFO-Datei + OMDb API Abfrage
  2. Titel + Jahr aus NFO-Datei (intelligent geparst)
  3. Titel + Jahr aus Dateinamen
  4. Manuelle Eingabe als Fallback
- Beispiel: inception.2010.1080p.mkv → Inception (2010).mkv
- Unterstützte Dateitypen: .mkv, .mp4, .avi, .avm

---

## Installation

1. Kompiliere das Script zu einer .exe (z.B. mit PyInstaller):
   `
   pyinstaller XRename.spec
   `
   oder nutze die vorhandene Datei 
ewrenamer.spec

2. Beim ersten Start wird das Windows-Kontextmenü **automatisch installiert**

---

## Konfiguration

### OMDb API Key (nur für IMDb-Abfragen in Filmen)

Der API Key ist **optional**. Ohne ihn werden Movies über NFO-Dateien oder Dateinamen erkannt.

1. Generiere einen kostenlosen Key auf: https://www.omdbapi.com/apikey.aspx
2. Das Programm fragt beim Start danach
3. Der Key wird in pi.dat gespeichert

---

## Nutzung

### Drag & Drop
- Ziehe eine Datei oder einen Ordner auf die .exe
- Das Programm versucht automatisch zu erkennen, ob es sich um Serien oder Filme handelt
- Nicht empfohlen: Nutze stattdessen das **Kontextmenü** für Klarheit

### Kommandozeile

#### Serien umbenennen
`cmd
XRename.exe --s "C:\Pfad\zu\Serien"
XRename.exe --s
`
→ Ohne Pfad: Nutzt das aktuelle Verzeichnis

#### Filme umbenennen
`cmd
XRename.exe --m "C:\Pfad\zu\Filmen"
XRename.exe --m
`
→ Ohne Pfad: Nutzt das aktuelle Verzeichnis

### Windows Kontextmenü

XRename erstellt ein Untermenü im Rechtsklick-Menü:

`
XRename >
  ├─ Rename Serie/Folge
  └─ Rename Film
`

#### Verwendung

1. **Serien**: Rechtsklick auf Datei/Ordner → XRename → Rename Serie/Folge
2. **Filme**: Rechtsklick auf Datei/Ordner → XRename → Rename Film

---

## Anforderungen an NFO-Dateien (Filme)

Die NFO-Datei sollte einer der folgenden Formate entsprechen:

### Mit IMDb ID (empfohlen)
`xml
tt0111161
<!-- oder als URL -->
https://www.imdb.com/title/tt0111161/
`

### Mit Titel und Jahr
`
Title (2010)
The Shawshank Redemption (1994)
`

### Mit Schlüsselwörtern
`
TITLE: The Matrix
YEAR: 1999
RELEASE DATE: 1999-03-31
`

---

## Dateistruktur

- XRename.py - Hauptprogramm
- pi.dat - Gespeicherter OMDb API Key (wird automatisch erstellt)
- ersion.txt - Aktueller Versionsstring

---

## Versionshistorie

### Version 1.1.0
- Auto-Update Funktionalität hinzugefügt
- IMDb API Integration für Filmerkennung
- Verbesserte NFO-Datei Parsing
- Windows Kontextmenü Installation
- API Key Management
- Unterstützung für multiple Dateiformat-Erkennungsmethoden

---

## Hinweise

- **Backup**: Erstelle ein Backup deiner Dateien vor der Nutzung
- **Nur EXE**: Manche Features (Auto-Update, Kontextmenü) funktionieren nur in der kompilierten .exe
- **API Rate Limits**: Die OMDb API hat Rate Limits – mehrfache Abfragen können limitiert sein

---

## Fehlerbehandlung

- Wenn über 50 Änderungen erkannt werden, wirst du aufgefordert zu bestätigen (y/n)
- Existierende Dateien werden nicht überschrieben
- Fehlende NFO-Dateien → Fallback zu Dateinamen-Erkennung
- Ungültige API Keys werden erkannt und Neueingabe angefordert
