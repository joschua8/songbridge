#!/usr/bin/env python3
"""Abgleich Liederdatenbank (songs/*.sng) <-> ProPresenter-Lieder-Bibliothek (*.pro).

  * Zuordnung über den Exportnamen (so heißt die .pro-Datei nach dem Export), sonst über den
    normalisierten Namen (Groß/klein, Satzzeichen, Unicode egal).
  * Inhaltlicher Vergleich über den Liedtext: aus der .pro werden alle Folientexte (RTF) gelesen
    und mit den Zeilen verglichen, die der Export aus der .sng erzeugen würde. Formatierung,
    Folienaufteilung und Reihenfolge spielen keine Rolle.

Status je Lied:  same | different | db_only | pp_only | error
"""

from __future__ import annotations

import re
import shutil
import time
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from songbridge.propresenter import export as pro_export
from songbridge.propresenter import proto  # noqa: F401  (pb2-Module in den Suchpfad)
from songbridge.propresenter.playlist import nfc, norm_name
from songbridge.songs.sng import Song, read_sng

import presentation_pb2  # noqa: E402

# ------------------------------------------------------------------ RTF -> Text

_RTF_SKIP_DESTS = {"fonttbl", "colortbl", "stylesheet", "info", "pict", "expandedcolortbl", "listtable",
                   "listoverridetable", "header", "footer", "themedata", "colorschememapping"}
_RTF_TOKEN_RE = re.compile(r"\\([a-zA-Z]+)(-?\d+)? ?|\\'([0-9a-fA-F]{2})|\\(.)|([{}])|(\r?\n)|([^\\{}\r\n]+)", re.S)


def rtf_to_text(rtf: str) -> str:
    """Sehr einfacher RTF-Leser für ProPresenter-Texte (Cocoa-RTF)."""
    out: list[str] = []
    stack: list[tuple[bool, int]] = []
    skip, uc, pending_skip = False, 1, 0
    for m in _RTF_TOKEN_RE.finditer(rtf):
        word, arg, hexch, sym, brace, newline, text = m.groups()
        if brace == "{":
            stack.append((skip, uc))
            continue
        if brace == "}":
            skip, uc = stack.pop() if stack else (False, 1)
            continue
        if newline:
            continue
        if pending_skip and (text or hexch):
            if text:
                n = min(pending_skip, len(text))
                text, pending_skip = text[n:], pending_skip - n
                if not text:
                    continue
            else:
                pending_skip -= 1
                continue
        if word:
            if word in _RTF_SKIP_DESTS:
                skip = True
            elif word in ("par", "line"):
                if not skip:
                    out.append("\n")
            elif word == "tab":
                if not skip:
                    out.append("\t")
            elif word == "uc":
                uc = int(arg or 1)
            elif word == "u":
                if not skip:
                    code = int(arg or 0)
                    out.append(chr(code + 65536 if code < 0 else code))
                pending_skip = uc
            continue
        if sym is not None:
            if sym == "*":
                skip = True
            elif sym in "\\{}" and not skip:
                out.append(sym)
            elif sym in "\n\r" and not skip:  # „\<Zeilenumbruch>“ = Absatz (Cocoa)
                out.append("\n")
            elif sym == "~" and not skip:
                out.append("\u00a0")
            continue
        if hexch and not skip:
            out.append(bytes([int(hexch, 16)]).decode("cp1252", errors="replace"))
            continue
        if text and not skip:
            out.append(text)
    return "".join(out)


# ------------------------------------------------------------------ Texte vergleichen


def norm_line(line: str) -> str:
    s = unicodedata.normalize("NFC", line).replace("\u00a0", " ").casefold().replace("ß", "ss")
    return re.sub(r"[^\w]+", " ", s).strip()


def song_lines(song: Song) -> list[str]:
    """Zeilen, die der Export aus diesem Lied macht (inkl. Übersetzung), ohne Wiederholungen."""
    groups, _ = pro_export.song_groups(song, pro_export.ExportStyle(title_slide=False))
    return [t for g in groups for slide in g.slides for kind, t in slide if kind != "spacer" and t.strip()]


def pro_lines(path: Path) -> tuple[str, list[str], list[str] | None]:
    """-> (Präsentationsname, Textzeilen aller Folien außer der Titelfolie, Zeilen der Titelfolie bzw. None ohne)."""
    pres = presentation_pb2.Presentation()
    pres.ParseFromString(path.read_bytes())
    title_cues = {cid.string for cg in pres.cue_groups if cg.group.name == pro_export.TITLE_NAME
                  for cid in cg.cue_identifiers}
    lines: list[str] = []
    title: list[str] = []
    for cue in pres.cues:
        target = title if cue.uuid.string in title_cues else lines
        for action in cue.actions:
            if not action.HasField("slide"):
                continue
            for el in action.slide.presentation.base_slide.elements:
                rtf = el.element.text.rtf_data
                if not rtf:
                    continue
                text = rtf_to_text(rtf.decode("latin-1", errors="replace"))
                target.extend(ln for ln in text.split("\n") if ln.strip())
    return pres.name, lines, title if title_cues else None


def compare_lines(db: list[str], pp: list[str]) -> tuple[bool, list[str], list[str]]:
    """-> (gleich?, nur in Datenbank, nur in ProPresenter). Zeilenumbrüche innerhalb des Textes egal."""
    a = [n for n in (norm_line(x) for x in db) if n]
    b = [n for n in (norm_line(x) for x in pp) if n]
    if set(a) == set(b) or Counter(" ".join(a).split()) == Counter(" ".join(b).split()):
        return True, [], []
    sa, sb = set(a), set(b)
    only_db = list(dict.fromkeys(x for x, n in zip(db, (norm_line(x) for x in db)) if n and n not in sb))
    only_pp = list(dict.fromkeys(x for x, n in zip(pp, (norm_line(x) for x in pp)) if n and n not in sa))
    return False, only_db, only_pp


# ------------------------------------------------------------------ Abgleich


@dataclass
class DbSong:
    id: str           # Pfad relativ zum Liederordner
    path: Path
    name: str         # Exportname
    stem: str         # Dateiname der .pro (eindeutig)
    manual: bool
    song: Song | None = None
    error: str = ""


def db_songs(songs_dir: Path, index: dict) -> list[DbSong]:
    """Alle Lieder mit Exportnamen – Reihenfolge und Namen wie beim ZIP-Export."""
    out, taken = [], set()
    for path in sorted(songs_dir.rglob("*.sng"), key=lambda p: p.name.casefold()) if songs_dir.exists() else []:
        rel = path.relative_to(songs_dir).as_posix()
        try:
            song = read_sng(path)
        except Exception as exc:  # defekte Datei soll den Abgleich nicht blockieren
            out.append(DbSong(rel, path, path.stem, path.stem, False, None, str(exc)))
            continue
        name = pro_export.export_name(path, songs_dir, song, index)
        stem = pro_export.unique_stem(pro_export.file_stem(name), taken)
        out.append(DbSong(rel, path, name, stem, song.manual, song))
    return out


def pp_files(pp_dir: Path | None) -> list[Path]:
    if not pp_dir or not pp_dir.is_dir():
        return []
    return sorted((f for f in pp_dir.iterdir() if f.is_file() and f.suffix.lower() == ".pro"),
                  key=lambda f: nfc(f.name).casefold())


@dataclass
class DiffRow:
    status: str
    title: str
    db: DbSong | None = None
    pp: Path | None = None
    only_db: list[str] = field(default_factory=list)
    only_pp: list[str] = field(default_factory=list)
    note: str = ""

    def to_json(self) -> dict:
        return {
            "status": self.status,
            "title": self.title,
            "id": self.db.id if self.db else None,
            "exportName": self.db.name if self.db else None,
            "proName": nfc(self.db.stem) + ".pro" if self.db else None,
            "manual": bool(self.db and self.db.manual),
            "pp": {"file": nfc(self.pp.name), "modified": self.pp.stat().st_mtime} if self.pp else None,
            "dbModified": self.db.path.stat().st_mtime if self.db else None,
            "onlyDb": self.only_db[:6],
            "onlyPp": self.only_pp[:6],
            "note": self.note,
        }


def diff(songs_dir: Path, pp_dir: Path | None, index: dict, style=None) -> list[DiffRow]:
    """style: Exportformatierung – ist dort die Titelfolie an, fehlt sie aber in ProPresenter, gilt das Lied als abweichend."""
    db = db_songs(songs_dir, index)
    files = pp_files(pp_dir)
    by_stem = {nfc(f.stem).casefold(): f for f in files}
    by_norm: dict[str, list[Path]] = {}
    for f in files:
        by_norm.setdefault(norm_name(f.stem), []).append(f)
    used: set[Path] = set()

    # 1. Durchgang: exakte Dateinamen (haben Vorrang vor ähnlichen)
    pairs: dict[str, Path] = {}
    for s in db:
        f = by_stem.get(nfc(s.stem).casefold())
        if f and f not in used:
            pairs[s.id] = f
            used.add(f)
    # 2. Durchgang: normalisierte Namen
    for s in db:
        if s.id in pairs:
            continue
        f = next((f for f in by_norm.get(norm_name(s.name), []) if f not in used), None)
        if f:
            pairs[s.id] = f
            used.add(f)

    rows: list[DiffRow] = []
    for s in db:
        f = pairs.get(s.id)
        if s.song is None:
            rows.append(DiffRow("error", s.name, s, f, note=f"Lied nicht lesbar: {s.error}"))
            continue
        if f is None:
            rows.append(DiffRow("db_only", s.name, s))
            continue
        try:
            _, lines, title = pro_lines(f)
        except Exception as exc:
            rows.append(DiffRow("error", s.name, s, f, note=f".pro nicht lesbar: {exc}"))
            continue
        same, only_db, only_pp = compare_lines(song_lines(s.song), lines)
        note = "" if nfc(f.stem) == nfc(s.stem) else f"Dateiname in ProPresenter: {nfc(f.name)}"
        if same and style is not None and style.title_slide and s.song.title.strip():
            # Fehlt die Titelfolie oder steht anderes drauf (z. B. ältere Fassung ohne Autor/Copyright) -> neu schreiben.
            want = [t for k, t in pro_export.title_slide(s.song, style) if t.strip()]
            problem = ("Titelfolie fehlt" if title is None
                       else "" if [norm_line(x) for x in title] == [norm_line(x) for x in want] else "Titelfolie veraltet")
            if problem:
                same, note = False, "; ".join(filter(None, [problem, note]))
        rows.append(DiffRow("same" if same else "different", s.name, s, f, only_db, only_pp, note))
    for f in files:
        if f not in used:
            rows.append(DiffRow("pp_only", nfc(f.stem), None, f))
    rows.sort(key=lambda r: nfc(r.title).casefold())
    return rows


def write_to_library(rows: list[DbSong], pp_dir: Path, style, index: dict, songs_dir: Path,
                     targets: dict[str, Path], backup_dir: Path) -> tuple[list[str], list[str], Path | None]:
    """Schreibt .pro-Dateien in die ProPresenter-Bibliothek.

    targets: Lied-ID -> Zieldatei (vorhandene Datei bei „abweichend“, sonst neue). Überschriebene
    Dateien werden vorher nach backup_dir/<Zeitstempel>/ kopiert. -> (geschrieben, Fehler, Sicherungsordner)
    """
    written, failed = [], []
    stamp_dir: Path | None = None
    for s in rows:
        target = targets[s.id]
        try:
            name = pro_export.export_name(s.path, songs_dir, s.song, index)
            _, data = pro_export.song_to_pro(s.song, style, key=s.id, name=name)
            if target.exists():
                if stamp_dir is None:
                    stamp_dir = backup_dir / time.strftime("%Y-%m-%d_%H%M%S")
                    stamp_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, stamp_dir / target.name)
            tmp = target.with_name(target.name + ".part")
            tmp.write_bytes(data)
            tmp.replace(target)
            written.append(nfc(target.name))
        except Exception as exc:
            failed.append(f"{s.name}: {exc}")
    return written, failed, stamp_dir


# ------------------------------------------------------------------ Duplikate in ProPresenter

# Kopie-Endungen, die ProPresenter/Finder/Explorer anhängen: „Lied (2)“, „Lied - Kopie“, „Lied copy 2“.
_COPY_SUFFIX_RE = re.compile(r"\s*(?:\(\d+\)|-?\s*(?:kopie|copy)(?:\s*\(?\d+\)?)?)\s*$", re.IGNORECASE)
MIN_CONTENT_LINES = 3   # gleicher Text zählt erst ab so vielen Zeilen als Duplikat (sonst „Halleluja“ & Co.)


def base_title(stem: str) -> str:
    """Dateiname ohne Kopie-Endungen („Lied (2)“ -> „Lied“)."""
    name = nfc(stem).strip()
    while True:
        shorter = _COPY_SUFFIX_RE.sub("", name).strip()
        if shorter == name or not shorter:
            return name
        name = shorter


_FS_RE = re.compile(r"\\fs(\d+)")
_FONT_RE = re.compile(r"\\f\d+\\f[a-z]+\\fcharset\d+ ([^;]+);")
_COLOR_RE = re.compile(r"\\red(\d+)\\green(\d+)\\blue(\d+);")
_STROKE_RE = re.compile(r"\\strokewidth(-?\d+)")


def pro_structure(path: Path) -> dict:
    """Aufbau einer Präsentation für den Vergleich: Gruppen mit Folien und Zeilen, Arrangement, Formatierung."""
    pres = presentation_pb2.Presentation()
    pres.ParseFromString(path.read_bytes())
    cues = {c.uuid.string: c for c in pres.cues}
    fonts, sizes, colors, strokes = set(), set(), set(), set()
    groups = []
    for cg in pres.cue_groups:
        slides = []
        for cid in cg.cue_identifiers:
            cue = cues.get(cid.string)
            lines: list[str] = []
            for action in (cue.actions if cue else []):
                if not action.HasField("slide"):
                    continue
                for el in action.slide.presentation.base_slide.elements:
                    rtf = el.element.text.rtf_data.decode("latin-1", errors="replace")
                    if not rtf:
                        continue
                    text = rtf_to_text(rtf)
                    lines.extend(nfc(ln).replace("\u00a0", " ").strip() for ln in text.split("\n") if ln.strip())
                    if lines:  # Formatierung nur von Elementen mit Text
                        fonts.update(f for f in _FONT_RE.findall(rtf) if f != "Helvetica")
                        sizes.update(int(v) / 2 for v in _FS_RE.findall(rtf) if v != "24")
                        colors.update("#%02x%02x%02x" % tuple(int(x) for x in c) for c in _COLOR_RE.findall(rtf))
                        strokes.update(int(v) for v in _STROKE_RE.findall(rtf) if v != "0")
            slides.append(lines)
        groups.append({"name": cg.group.name, "slides": slides})
    by_id = {cg.group.uuid.string: cg.group.name for cg in pres.cue_groups}
    arr = next((a for a in pres.arrangements if a.uuid.string == pres.selected_arrangement.string), None)
    arrangement = [by_id.get(g.string, "?") for g in arr.group_identifiers] if arr else []
    fmt = {"Schriften": sorted(fonts), "Größen": [f"{v:g} pt" for v in sorted(sizes)],
           "Farben": sorted(colors), "Kontur": "ja" if strokes else "nein"}
    return {"groups": groups, "arrangement": arrangement, "format": fmt,
            "slides": sum(len(g["slides"]) for g in groups)}


def _rows(structure: dict) -> list[dict]:
    """Anzeigezeilen: Gruppenname, Folientrenner, Textzeilen (für die Links/Rechts-Ansicht)."""
    rows = []
    for g in structure["groups"]:
        rows.append({"k": "group", "text": g["name"]})
        for n, slide in enumerate(g["slides"]):
            if n:
                rows.append({"k": "slide", "text": ""})
            rows.extend({"k": "line", "text": ln} for ln in slide)
    return rows


@dataclass
class DupFile:
    path: Path
    library: str
    structure: dict = field(default_factory=dict)
    error: str = ""

    @property
    def lines(self) -> list[str]:
        return [ln for g in self.structure.get("groups", []) for sl in g["slides"] for ln in sl]

    @property
    def is_copy(self) -> bool:
        return base_title(self.path.stem) != nfc(self.path.stem).strip()

    def content_key(self) -> frozenset[str] | None:
        norm = frozenset(n for n in (norm_line(x) for x in self.lines) if n)
        return norm if len(norm) >= MIN_CONTENT_LINES else None


def side_by_side(left: list[dict], right: list[dict]) -> list[dict]:
    """Zeilen beider Dateien nebeneinander (wie ein Git-Diff), exakter Vergleich.

    -> [{op: same|change|del|add, l: Zeile|None, r: Zeile|None}]; del = nur links, add = nur rechts.
    """
    import difflib
    from itertools import zip_longest
    key = lambda r: (r["k"], r["text"])
    out = []
    sm = difflib.SequenceMatcher(None, [key(r) for r in left], [key(r) for r in right], autojunk=False)
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            out.extend({"op": "same", "l": l, "r": r} for l, r in zip(left[i1:i2], right[j1:j2]))
        else:
            for l, r in zip_longest(left[i1:i2], right[j1:j2]):
                out.append({"op": "change" if l and r else ("del" if l else "add"), "l": l, "r": r})
    return out


def find_duplicates(dirs: list[tuple[str, Path]], preferred: str = "") -> list[dict]:
    """Doppelte Präsentationen in den Bibliotheksordnern dirs = [(Bibliothek, Ordner)].

    Zusammen gehören Dateien mit gleichem Namen (ohne Kopie-Endung, Groß/klein und Satzzeichen egal) oder gleichem
    Liedtext. Je Gruppe wird eine Datei zum Behalten vorgeschlagen (ohne Kopie-Endung, in der bevorzugten
    Bibliothek, mit dem meisten Text, zuletzt geändert); die anderen werden mit ihr verglichen.
    """
    files: list[DupFile] = []
    for library, folder in dirs:
        for f in pp_files(folder):
            d = DupFile(f, library)
            try:
                d.structure = pro_structure(f)
            except Exception as exc:  # defekte Datei trotzdem anzeigen (Name kann doppelt sein)
                d.error = f"nicht lesbar: {exc}"
            files.append(d)

    parent = list(range(len(files)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i: int, j: int) -> None:
        parent[find(i)] = find(j)

    seen: dict[tuple, int] = {}
    for i, d in enumerate(files):
        keys = [("name", norm_name(base_title(d.path.stem)))]
        if (ck := d.content_key()) is not None:
            keys.append(("text", ck))
        for key in keys:
            if key[1] and key in seen:
                union(i, seen[key])
            else:
                seen.setdefault(key, i)

    groups: dict[int, list[DupFile]] = {}
    for i, d in enumerate(files):
        groups.setdefault(find(i), []).append(d)

    out = []
    for members in groups.values():
        if len(members) < 2:
            continue
        members.sort(key=lambda d: (d.is_copy, d.library != preferred, -len(d.lines), -d.path.stat().st_mtime))
        keep = members[0]
        rows = []
        keep_rows = _rows(keep.structure) if keep.structure else []
        for d in members:
            st = d.path.stat()
            row = {
                "path": str(d.path), "file": nfc(d.path.name), "library": d.library, "size": st.st_size,
                "modified": st.st_mtime, "lines": len(d.lines), "slides": d.structure.get("slides", 0),
                "arrangement": d.structure.get("arrangement", []), "format": d.structure.get("format", {}),
                "keep": d is keep, "error": d.error,
            }
            if d is not keep:
                rows_d = _rows(d.structure) if d.structure else []
                pairs = side_by_side(keep_rows, rows_d)
                text_same = not d.error and not keep.error and all(p["op"] == "same" for p in pairs)
                layout_same = (d.structure.get("format") == keep.structure.get("format")
                               and d.structure.get("arrangement") == keep.structure.get("arrangement"))
                # identical: Text, Folienaufteilung, Arrangement und Formatierung gleich
                row["status"] = ("identical" if text_same and layout_same
                                 else "layout" if text_same else "text")
                row["pairs"] = pairs[:600]
                row["changes"] = sum(p["op"] != "same" for p in pairs)
            rows.append(row)
        title = base_title(keep.path.stem)
        status = {r.get("status") for r in rows if not r["keep"]}
        out.append({"title": title, "files": rows,
                    "status": "text" if "text" in status else "layout" if "layout" in status else "identical"})
    out.sort(key=lambda g: g["title"].casefold())
    return out


def delete_to_backup(paths: list[Path], backup_dir: Path) -> tuple[list[str], list[str], Path | None]:
    """Präsentationen in backup/geloescht/<Zeitstempel>/<Bibliothek>/ verschieben. -> (verschoben, Fehler, Ordner)."""
    if not paths:
        return [], [], None
    target_root = backup_dir / "geloescht" / time.strftime("%Y-%m-%d_%H%M%S")
    moved, failed = [], []
    for p in paths:
        try:
            dest = target_root / p.parent.name / p.name
            n = 2
            while dest.exists():
                dest = dest.with_name(f"{p.stem} ({n}){p.suffix}")
                n += 1
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(p), str(dest))
            moved.append(nfc(p.name))
        except OSError as exc:
            failed.append(f"{nfc(p.name)}: {exc}")
    return moved, failed, target_root if moved else None
