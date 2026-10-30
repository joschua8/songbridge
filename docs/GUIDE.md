# SongBridge – Getting started

SongBridge is a single program file; you do not need to install Python.
After starting it, your browser opens the user interface (http://127.0.0.1:5005).
Keep the terminal window open while you work – closing it quits the program.

The user interface is in German. The most important menu entries are translated in brackets below.

## macOS

1. Unzip the ZIP file and put `SongBridge` somewhere, e.g. into "Applications".
2. On the **first start** use **right-click → Open** and confirm with "Open"
   (the program is not signed by Apple, so macOS asks).
   If macOS still refuses: System Settings → Privacy & Security → "Open Anyway".
   Or once in Terminal:
   `xattr -d com.apple.quarantine /path/to/SongBridge`
3. From then on a double-click is enough.

Pre-built versions are only available for Macs with Apple Silicon (M1/M2/M3/M4, from late 2020).
Apple menu → "About This Mac" shows which chip your Mac has.

## Windows

1. Unzip the ZIP file and double-click `SongBridge.exe`.
2. If "Windows protected your PC" appears: "More info" → "Run anyway".

## Updates

The program updates itself: on start-up it checks GitHub for a newer version, downloads it, replaces the
program file and restarts. If it keeps running for a long time, a banner "Neue Version … verfügbar" (new version
available) with the button "Jetzt aktualisieren" (update now) appears at the top. You can switch this off and check
manually under **Einstellungen → Programm-Updates** (Settings → Program updates). For this to work, the program
file must be in a folder you are allowed to write to (e.g. Desktop, Downloads, Applications).

## Where is my data?

In the **SongBridge** folder in your home directory
(macOS: `/Users/<name>/SongBridge`, Windows: `C:\Users\<name>\SongBridge`).
If a folder **Liedbruecke** or **Liederverwaltung** from an earlier version exists, that one is used instead.

- `songs/` – the song database (.sng files)
- `app_settings.json`, `playlist_settings.json`, `export_settings.json` – settings
- `backup/` – backups of overwritten ProPresenter files and replaced songs

To move to another computer, simply copy this folder.
A different location can be set with the environment variable `SONGBRIDGE_DATA`.

The ProPresenter library, the folder with the "silence" images and the ChurchTools login are configured in the
user interface under **Einstellungen** (Settings).

With the checkbox **"Passwort speichern"** (save password) at login, SongBridge stores the ChurchTools password in
the computer's keychain (macOS Keychain or Windows Credential Manager) and logs in automatically on every start –
even after rebooting the computer. The saved login can be deleted again under Settings. If two-factor
authentication is enabled in ChurchTools, automatic login only works with a saved login token.

## Adding songs without ChurchTools

Under **Lieder → Hochladen** (Songs → Upload) drop files from CCLI SongSelect (`.usr` or `.txt`) or SongBeamer
files (`.sng`). If a song with the same title already exists, SongBridge asks: replace it (the old song is backed
up in `backup/ersetzt/`), save as a copy, or skip.

Without a file, use **Lieder → Freitext** (Songs → Free text): enter the title and lyrics. For the sections to be
recognised correctly: leave an empty line between sections, put the section name (`Strophe 1`/`Verse 1`,
`Refrain`/`Chorus`, `Bridge` …) alone on the first line, and write repetitions only as the name (e.g. `Chorus`)
instead of typing the lyrics again. A line containing only `--` starts a new slide within the same section.
The instructions with an example are shown right above the text box; on the right you immediately see how the
song will be saved.

## Editing songs

Every song in the library has an **Bearbeiten** (Edit) button – including songs from ChurchTools. The lyrics open
in the same format as free text. Edited ChurchTools songs are marked "bearbeitet" (edited): the song import no
longer overwrites them, even if the song changes in ChurchTools. **Original wiederherstellen** (restore original)
brings back the original ChurchTools version (it is backed up in `backup/originale/` the first time you edit).

## Slide breaks when exporting

Under **ProPresenter → Export & Formatierung → Folie → Folienumbruch** (slide break) you choose how lyrics are
split into slides:

- **Zeilenzahl** (line count): every section is split into slides with at most "Zeilen pro Folie" (lines per slide).
  With **"An Satzenden umbrechen"** (break at sentence ends, on by default) SongBridge prefers to start a new slide
  after a full stop, `!`, `?`, then after `;`/`:`, then after a comma – and avoids breaking mid-sentence where
  possible. Songs without punctuation are split evenly, as before.
- **Absatz** (paragraph): every paragraph of the song file becomes exactly one slide. If the text does not fit
  into the text box, ProPresenter automatically scales the font down.

## Finding duplicates in ProPresenter

**ProPresenter → Duplikate** (duplicates) lists songs that exist more than once in your ProPresenter song library:
same name (also "Song (2)", "Song - Kopie", "Song copy") or the same lyrics under a different name. Tick
"Alle Bibliotheken durchsuchen" to search all libraries.

For every group SongBridge suggests one file to keep (green "behalten"). Every other file is compared with it line
by line: red = only in the kept file, green = only in this file; "gleicher Text" means the lyrics are identical.
"Alle Duplikate auswählen" (select all duplicates) ticks every file except the suggested ones, and
"… löschen" (delete) has to be clicked twice. Deleted files are not removed permanently but moved to
`backup/geloescht/` in the data folder.

## Text formatting

Under **ProPresenter → Export & Formatierung** you can set, besides font, size and colour:
**Kontur** (outline: on/off, width, colour), **Schatten** (shadow: colour, blur, distance, opacity) and
**Abstände** (letter spacing, line spacing). The preview shows the result immediately; existing presentations change
only after exporting them again ("Abgleich" compares lyrics only, not formatting).

## PowerPoint files in a service plan

Presentations (.pptx/.ppt) attached to an event in ChurchTools are converted into images for the playlist.
This requires **LibreOffice** (free, libreoffice.org) or – on Windows only – an installed **Microsoft PowerPoint**.
Images, videos and audio work without it. They are placed at the very top of the playlist. Other files (e.g. .docx or .pdf) are not downloaded at
all; their names are shown in an orange header at the end of the playlist so nothing gets overlooked.

By default only the red headings of the service plan become playlist headers. Normal agenda items (pink) can be
added with "Auch normale Ablaufpunkte (rosa) übernehmen" (also include normal agenda items) on the right, or
individually by ticking them in the service plan.

## Songs in the playlist (Windows)

On Windows, ProPresenter only shows the songs of a playlist if they are bundled with the file. That is why
"Lieder in die Playlist-Datei packen" (bundle songs into the playlist file, service plan view, right-hand side)
is enabled there. When opening it, ProPresenter asks whether existing presentations should be replaced.
On macOS the checkbox stays off – a reference to the library is enough there.
