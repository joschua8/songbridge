# SongBridge – Programm starten

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

Es gibt zwei Fassungen: **AppleSilicon** (Macs ab Ende 2020 mit M1/M2/M3/M4) und **Intel** (ältere Macs).
Unter Apple-Menü → „Über diesen Mac“ steht, welcher Chip verbaut ist.

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
- `backup/` – Sicherungen überschriebener ProPresenter-Dateien

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
noch einmal zu tippen. Die Anleitung mit Beispiel steht direkt über dem Textfeld, rechts daneben
siehst du sofort, wie das Lied gespeichert wird.

## Lieder bearbeiten

Jedes Lied hat in der Bibliothek den Knopf **Bearbeiten** – auch Lieder aus ChurchTools. Der Text
öffnet sich im gleichen Format wie beim Freitext. Bearbeitete ChurchTools-Lieder tragen die Markierung
„bearbeitet“: Der Lieder-Import überschreibt sie nicht mehr, auch wenn sich das Lied in ChurchTools ändert.
Mit **Original wiederherstellen** holst du die ursprüngliche ChurchTools-Fassung zurück (sie wird beim
ersten Bearbeiten unter `backup/originale/` gesichert).

## PowerPoint-Dateien im Ablaufplan

Präsentationen (.pptx/.ppt), die in ChurchTools am Termin hängen, werden für die Playlist in Bilder
umgewandelt. Dafür braucht es **LibreOffice** (kostenlos, libreoffice.org) oder – nur unter
Windows – ein installiertes **Microsoft PowerPoint**. Bilder, Videos und Audio gehen ohne.
Andere Dateien (z. B. .docx oder .pdf) werden gar nicht erst heruntergeladen; ihre Namen stehen in einer orangen
Kopfzeile ganz oben, damit nichts übersehen wird.

## Lieder in der Playlist (Windows)

Unter Windows zeigt ProPresenter die Lieder einer Playlist nur an, wenn sie in der Datei mitgeliefert
werden. Deshalb ist dort „Lieder in die Playlist-Datei packen“ (Ablaufplan, rechts) eingeschaltet.
Beim Öffnen fragt ProPresenter dann, ob vorhandene Präsentationen ersetzt werden sollen.
Unter macOS bleibt das Häkchen aus – dort reicht der Verweis auf die Bibliothek.
