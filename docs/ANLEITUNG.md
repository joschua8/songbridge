# SongBridge – Programm starten

*English version: [GUIDE.md](GUIDE.md)*

SongBridge ist ein einzelnes Programm, eine Python-Installation braucht es nicht.
Nach dem Start öffnet sich der Browser mit der Oberfläche (http://127.0.0.1:5005).
Das Terminal-Fenster dabei offen lassen; wenn man es schließt, wird das Programm beendet.

## macOS

1. ZIP entpacken, die Datei `SongBridge` z. B. in den Ordner „Programme“ legen.
2. Beim **ersten Start** mit **Rechtsklick → Öffnen** starten und „Öffnen“ bestätigen
   (das Programm ist nicht bei Apple signiert, deshalb fragt macOS nach).
   Falls macOS das Öffnen trotzdem verweigert: Systemeinstellungen → Datenschutz & Sicherheit →
   „Dennoch öffnen“. Oder im Terminal einmalig:
   `xattr -d com.apple.quarantine /Pfad/zu/SongBridge`
3. Danach reicht ein Doppelklick.

Fertige Programmversionen gibt es nur für Macs mit **Apple Silicon** (ab Ende 2020, M1/M2/M3/M4).
Unter Apple-Menü → „Über diesen Mac“ steht, welcher Chip verbaut ist. Für Macs mit Intel-Prozessor werden
keine neuen Versionen mehr gebaut.

## Windows

1. ZIP entpacken, `SongBridge.exe` doppelklicken.
2. Falls „Der Computer wurde durch Windows geschützt“ erscheint: „Weitere Informationen“ →
   „Trotzdem ausführen“.

## Updates

Das Programm aktualisiert sich selbst: Beim Start schaut es auf GitHub nach einer neueren Version,
lädt sie, ersetzt die Programmdatei und startet neu. Läuft es länger, erscheint oben ein Hinweis
„Neue Version verfügbar – Jetzt aktualisieren“. Abschalten und von Hand prüfen unter
**Einstellungen → Programm-Updates**. Die Programmdatei muss dafür in einem Ordner liegen, in den
du schreiben darfst (z. B. Desktop, Downloads, Programme).

## Wo liegen meine Daten?

Im Ordner **SongBridge** in deinem Benutzerordner
(macOS: `/Users/<Name>/SongBridge`, Windows: `C:\Users\<Name>\SongBridge`).
Gibt es von früher schon einen Ordner **Liedbruecke** oder **Liederverwaltung**, wird dieser weiter benutzt.

- `songs/` – die Liederdatenbank (.sng-Dateien)
- `app_settings.json`, `playlist_settings.json`, `export_settings.json` – Einstellungen
- `backup/` – Sicherungen überschriebener ProPresenter-Dateien und ersetzter Lieder

Zum Umziehen auf einen anderen Rechner einfach diesen Ordner mitkopieren.
Ein anderer Ort lässt sich über die Umgebungsvariable `SONGBRIDGE_DATA` einstellen.

Die ProPresenter-Bibliothek, den Ordner mit den Stille-Bildern und die ChurchTools-Anmeldung
stellst du in der Oberfläche unter **Einstellungen** ein.

Mit dem Häkchen **„Passwort speichern“** beim Anmelden merkt sich SongBridge das ChurchTools-Passwort im
Schlüsselbund des Computers (macOS-Schlüsselbund bzw. Windows-Anmeldeinformationsverwaltung) und meldet sich
bei jedem Start – auch nach einem Neustart des Computers – automatisch an. Unter Einstellungen lässt sich die
gespeicherte Anmeldung wieder löschen. Ist bei ChurchTools die Zwei-Faktor-Anmeldung aktiv, geht das automatische
Anmelden nur mit einem gespeicherten Login-Token.

## Lieder ohne ChurchTools hinzufügen

Unter **Lieder → Hochladen** Dateien aus CCLI SongSelect (`.usr` oder `.txt`) oder SongBeamer-Dateien
(`.sng`) hineinziehen. Gibt es ein Lied mit gleichem Titel schon, fragt SongBridge nach: ersetzen
(das alte Lied wird in `backup/ersetzt/` gesichert), als Kopie speichern oder überspringen.

Ohne Datei geht es über **Lieder → Freitext**: Titel und Liedtext eintragen. Wichtig für die richtige
Aufteilung: Leerzeile zwischen den Abschnitten, der Name des Abschnitts (`Strophe 1`, `Refrain`,
`Bridge` …) allein in der ersten Zeile, Wiederholungen nur als Name (z. B. `Refrain`) statt den Text
noch einmal zu tippen. Eine Zeile nur mit `--` beginnt innerhalb eines Abschnitts eine neue Folie.

**Zweisprachige Lieder:** In jedem Abschnitt abwechselnd eine Zeile Original und darunter ihre Übersetzung schreiben
und das Häkchen **„Zweisprachig (Zeilen abwechselnd: Original / Übersetzung)“** setzen. Erkennt SongBridge, dass
sich deutsche und englische Zeilen abwechseln, setzt es das Häkchen selbst und zeigt einen Hinweis; die
Übersetzungszeilen erscheinen in der Vorschau kursiv, damit du die Zuordnung prüfen kannst. Ein von Hand gesetztes
oder entferntes Häkchen ändert SongBridge nicht mehr. Beim Export bekommt die Übersetzung die Formatierung
„Übersetzung (2. Sprache)“, und Original und Übersetzung bleiben auf derselben Folie. Die Anleitung mit Beispiel steht direkt über dem Textfeld, rechts daneben
siehst du sofort, wie das Lied gespeichert wird.

## Lieder bearbeiten

Jedes Lied hat in der Bibliothek den Knopf **Bearbeiten** – auch Lieder aus ChurchTools. Der Text
öffnet sich im gleichen Format wie beim Freitext. Bearbeitete ChurchTools-Lieder tragen die Markierung
„bearbeitet“: Der Lieder-Import überschreibt sie nicht mehr, auch wenn sich das Lied in ChurchTools ändert.
Mit **Original wiederherstellen** holst du die ursprüngliche ChurchTools-Fassung zurück (sie wird beim
ersten Bearbeiten unter `backup/originale/` gesichert).

## Folienumbruch beim Export

Unter **ProPresenter → Export & Formatierung → Folie → Folienumbruch** legst du fest, wie der Liedtext auf
Folien verteilt wird:

- **Zeilenzahl:** Jeder Abschnitt wird auf Folien mit höchstens „Zeilen pro Folie“ Zeilen verteilt.
  Mit **„An Satzenden umbrechen“** (standardmäßig an) beginnt eine neue Folie bevorzugt nach einem Satzende
  (`.` `!` `?`), sonst nach `;`/`:`, sonst nach einem Komma – mitten im Satz nur, wenn es nicht anders geht.
  Lieder ohne Satzzeichen werden wie bisher gleichmäßig aufgeteilt.
- **Absatz:** Jeder Absatz der Lieddatei wird genau eine Folie. Passt der Text nicht in die Textbox,
  verkleinert ProPresenter die Schrift automatisch.

## Duplikate in ProPresenter finden

**ProPresenter → Duplikate** zeigt Lieder, die in der ProPresenter-Lieder-Bibliothek mehrfach vorhanden sind:
gleicher Name (auch „Lied (2)“, „Lied - Kopie“, „Lied copy“) oder gleicher Liedtext unter anderem Namen. Mit
„Alle Bibliotheken durchsuchen“ werden alle Bibliotheken einbezogen.

Je Gruppe schlägt SongBridge eine Datei zum Behalten vor (grün „behalten“). Jede andere Datei wird **nebeneinander**
damit verglichen, wie bei Git: links die Datei zum Behalten, rechts die Kopie. Verglichen wird Zeichen für Zeichen
(auch Satzzeichen), dazu Folienaufteilung, Arrangement und Formatierung (Schriften, Größen, Farben, Kontur).
Rot = nur links, grün = nur rechts, gelb = geändert (geänderte Wörter markiert). Jede Kopie ist markiert als
**identisch** (gar kein Unterschied), **nur Formatierung/Aufbau anders** oder **Text anders**.
„Gleiche Zeilen einklappen“ blendet unveränderte Zeilen aus.

„Identische auswählen“ hakt nur Kopien ohne jeden Unterschied an, „Alle Duplikate auswählen“ alle Dateien außer den
vorgeschlagenen; „… löschen“ muss zweimal geklickt werden. Gelöschte Präsentationen werden sofort aus dem Ordner der
ProPresenter-Bibliothek entfernt; eine Sicherheitskopie bleibt in `backup/geloescht/` im Datenordner. Zeigt
ProPresenter ein gelöschtes Lied noch an, ProPresenter einmal neu starten.

## Textformatierung

Unter **ProPresenter → Export & Formatierung** gibt es neben Schrift, Größe und Farbe auch **Kontur** (an/aus,
Stärke, Farbe), **Schatten** (Farbe, Unschärfe, Abstand, Deckkraft) und **Abstände** (Zeichen- und Zeilenabstand).
Die Vorschau zeigt das sofort; vorhandene Präsentationen ändern sich erst nach erneutem Export (der Abgleich vergleicht nur den Text, nicht die Formatierung).

## PowerPoint-Dateien im Ablaufplan

Präsentationen (.pptx/.ppt), die in ChurchTools am Termin hängen, werden für die Playlist in Bilder
umgewandelt. Dafür braucht es **LibreOffice** (kostenlos, libreoffice.org) oder – nur unter
Windows – ein installiertes **Microsoft PowerPoint**. Bilder, Videos und Audio gehen ohne.
Die Dateien stehen ganz oben in der Playlist.

**PDFs** am Termin erscheinen im Ablaufplan als Zeile mit leerem Häkchen. Hakst du sie an, lädt SongBridge das PDF
beim Export und macht aus jeder Seite eine Folie. Sollen alle PDFs automatisch umgewandelt werden, rechts
„PDFs am Termin automatisch umwandeln“ einschalten. Nicht angehakte PDFs und andere Dateien (z. B. .docx) werden
nicht heruntergeladen; ihre Namen stehen in einer orangen Kopfzeile am Ende der Playlist, damit nichts übersehen wird.

Standardmäßig werden aus dem Ablaufplan nur die roten Überschriften als Kopfzeilen übernommen. Normale
Ablaufpunkte (rosa) kommen mit „Auch normale Ablaufpunkte (rosa) übernehmen“ (rechts) dazu – oder einzeln per
Häkchen im Ablauf.

## Lieder in der Playlist (Windows)

Unter Windows zeigt ProPresenter die Lieder einer Playlist nur an, wenn sie in der Datei mitgeliefert
werden. Deshalb ist dort „Lieder in die Playlist-Datei packen“ (Ablaufplan, rechts) eingeschaltet.
Beim Öffnen fragt ProPresenter dann, ob vorhandene Präsentationen ersetzt werden sollen.
Unter macOS bleibt das Häkchen aus – dort reicht der Verweis auf die Bibliothek.
