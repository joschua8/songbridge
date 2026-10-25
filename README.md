# SongBridge

**The bridge between ChurchTools and ProPresenter 7.**
SongBridge pulls your songs (SongBeamer files) from [ChurchTools](https://church.tools), converts them into
ProPresenter presentations and turns a service plan into a ready-to-use ProPresenter playlist with a single click.

> SongBridge is a private project and is not affiliated with ChurchTools (ECGroup) or
> Renewed Vision (ProPresenter).
>
> The user interface is currently in **German**, since ChurchTools is mainly used by churches in
> German-speaking countries.

---

## Features

| Area | What it does |
|---|---|
| **Service plan → playlist** | Pick an event in ChurchTools → review its service plan (agenda) → download a `.proPlaylist`. Headings and agenda items become coloured headers, songs link to the presentations that already exist in your ProPresenter library. |
| **Automatic items** | The Lord's Prayer presentation is added under "Vaterunser" (found by its CCLI number), and a random image from your "silence" folder is added under every item containing "Stille". |
| **Event files** | PowerPoint, Keynote, images, videos and audio attached to the event in ChurchTools are downloaded and inserted under the matching agenda item (e.g. "Sermon …pptx" under "Sermon"). Presentations are converted into slide images. PDFs, Word files etc. are not downloaded but listed as a note above the agenda. |
| **Song matching** | ChurchTools song name ↔ presentation: exact, ignoring punctuation/CCLI numbers, bilingual titles, similar names ("please check"). Every match can be changed in the UI. |
| **Song import** | Downloads all SongBeamer files (`.sng`) from ChurchTools into a local song database; every later import only fetches new and changed songs. |
| **Song upload** | Add songs without a `.sng` via drag & drop as a CCLI SongSelect file (`.usr`/`.txt`) or `.sng`. If a song with the same title exists, you can replace it (with backup), keep both or skip it. |
| **Free text** | Paste lyrics; sections (verse, chorus, bridge …) are detected automatically, with live preview and formatting hints. `--` on its own line starts a new slide within a section. |
| **Editing** | Edit any song (including ChurchTools songs) as free text; the import never overwrites edited songs and the original can be restored. |
| **Export to ProPresenter** | `.sng` → `.pro` with configurable formatting (font, size, colours, slide breaks by line count or by paragraph with automatic font scaling, text box positioned with the mouse), slide preview and hot keys per song part (verse 1 = A, chorus = C, bridge = B …). |
| **Library sync** | Compares the song database with your ProPresenter song library: what is missing, what has different lyrics – and updates it on request (with backup). |
| **Self-updating** | The app checks GitHub Releases on start-up and updates itself. |

## Installation

1. Download the matching ZIP from [**Releases**](../../releases/latest):
   - `SongBridge-Windows.zip`
   - `SongBridge-macOS-AppleSilicon.zip` (Macs with M1/M2/M3/M4)

   Macs with an Intel processor are no longer supported by the pre-built releases; you can still
   [run SongBridge from source](#running-from-source).
2. Unzip it and put the program file into a folder you are allowed to write to (Desktop, Applications …) –
   otherwise it cannot update itself.
3. Start it:
   - **Windows:** double-click `SongBridge.exe`. If you see "Windows protected your PC":
     "More info" → "Run anyway".
   - **macOS:** the first time use **right-click → Open** (the app is not signed by Apple).
4. Your browser opens the user interface (`http://127.0.0.1:5005`). Keep the terminal window open –
   closing it quits the app.

For PowerPoint files attached to a service plan you need [LibreOffice](https://www.libreoffice.org) (free) or –
on Windows only – an installed Microsoft PowerPoint. Images, videos and audio work without it.

A step-by-step guide for end users is included in every release: [`docs/GUIDE.md`](docs/GUIDE.md)
(German: [`docs/ANLEITUNG.md`](docs/ANLEITUNG.md)).

## Usage

### Playlist for a service ("ChurchTools → Ablaufpläne")

1. Select an event. The service plan appears together with the match for each song:
   green = found, yellow = similar name (please check), red = missing.
2. If necessary, fix matches via "ändern" (change) and tick/untick items.
3. Click **".proPlaylist herunterladen"** on the right and open the file in ProPresenter (double-click it or drag it
   into the playlist list).

> **Windows:** ProPresenter on Windows only shows the songs of a playlist if they are bundled with it.
> That is why "Lieder in die Playlist-Datei packen" (bundle songs into the playlist file) is enabled on Windows;
> ProPresenter asks whether existing presentations should be replaced when you open it. On macOS it stays off
> (otherwise duplicates would be created).

### Maintaining songs

- **ChurchTools → Lieder-Import:** downloads all `.sng` files (only new/changed ones after the first run).
- **Lieder → Hochladen:** drop SongSelect or `.sng` files.
- **Lieder → Freitext:** type or paste lyrics – the format is explained above the text box.
- **ProPresenter → Export & Formatierung:** select songs, adjust formatting, download a ZIP of `.pro` files
  and import it into ProPresenter.
- **ProPresenter → Abgleich:** shows the differences between the database and your ProPresenter library.

### Data

Songs and settings are stored in the `SongBridge` folder in your home directory (or `Liedbruecke`/`Liederverwaltung`
from earlier versions). To move to another computer, simply copy that folder. A different location can be set with
the environment variable `SONGBRIDGE_DATA`.

Nothing is sent anywhere except to your own ChurchTools instance and – for update checks – to the GitHub API.
A saved ChurchTools password is kept in the operating system's keychain (macOS Keychain / Windows Credential
Manager). Only if no keychain is available (e.g. Linux without a Secret Service) it falls back to
`credentials.json` in the data folder, readable only by your user.

## Running from source

Tested with Python 3.12 (the version used for the releases).

```sh
git clone https://github.com/joschua8/songbridge.git
cd songbridge
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m songbridge          # opens http://127.0.0.1:5005
```

On macOS you can also double-click `SongBridge.command`.

### Building the stand-alone app

```sh
pip install pyinstaller
pyinstaller --noconfirm --clean packaging/SongBridge.spec   # -> dist/SongBridge(.exe)
```

Every push to `master` is built by GitHub Actions for Windows and macOS (Apple Silicon) and published as a
GitHub Release; the app updates itself from there.

### Project layout

```
songbridge/
  app.py                 Flask web server + API for the browser UI
  churchtools.py         ChurchTools REST client, song import with change detection
  songs/                 SongBeamer (.sng) and SongSelect parsing, free-text parser
  propresenter/          .pro export, .proPlaylist builder, library sync, protobuf definitions
  web/index.html         the whole user interface (single page)
  updater.py             self-update from GitHub Releases
packaging/               PyInstaller spec and entry point
docs/                    end-user guide (English + German)
```

## Credits

- **[greyshirtguy/ProPresenter7-Proto](https://github.com/greyshirtguy/ProPresenter7-Proto)** – the
  reverse-engineered protobuf definitions of the ProPresenter 7 file format. Without them, converting SongBeamer
  files into ProPresenter presentations (and writing playlists) would not be possible.
  The generated `*_pb2.py` files in `songbridge/propresenter/proto/` are under greyshirtguy's MIT licence
  (see [`LICENSE-ProPresenter7-Proto`](songbridge/propresenter/proto/LICENSE-ProPresenter7-Proto)).
  Thank you!
- [ChurchTools](https://church.tools) for its open REST API.
