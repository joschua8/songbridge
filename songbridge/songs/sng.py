"""Lesen und Schreiben von SongBeamer-Dateien (.sng) sowie Umwandlung von Freitext.

Aufbau einer .sng-Datei (UTF-8 mit BOM):
    #Title=...            Kopfzeilen "#Schlüssel=Wert"
    #VerseOrder=Verse 1,Chorus 1,...
    ---                   Trenner vor jedem Abschnitt („--“ = neue Folie, wird genauso gelesen)
    Verse 1               Abschnittsname (erste Zeile nach dem Trenner)
    Liedzeile ...
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

PARA_MARK = "--"  # Freitext: Folienumbruch innerhalb eines Abschnitts
_PARA_RE = re.compile(r"^-{2,3}$")

# Kennzeichnet von Hand erfasste Lieder; der ChurchTools-Import überschreibt sie nie.
MANUAL_EDITOR = "Liederverwaltung (manuell)"  # früherer Programmname – Kennung in vorhandenen Dateien, nicht ändern
# Kopfzeile in ChurchTools-Liedern, die in SongBridge bearbeitet wurden (Wert: Datum). Der Import überschreibt sie nicht.
EDITED_KEY = "SongBridgeEdited"

# Freitext-Schlüsselwort -> SongBeamer-Abschnittstyp
LABEL_TYPES = {
    "strophe": "Verse",
    "vers": "Verse",
    "verse": "Verse",
    "refrain": "Chorus",
    "chorus": "Chorus",
    "kehrvers": "Chorus",
    "pre-chorus": "Pre-Chorus",
    "prechorus": "Pre-Chorus",
    "pre chorus": "Pre-Chorus",
    "pre-refrain": "Pre-Chorus",
    "prerefrain": "Pre-Chorus",
    "bridge": "Bridge",
    "brücke": "Bridge",
    "intro": "Intro",
    "interlude": "Interlude",
    "instrumental": "Instrumental",
    "zwischenspiel": "Interlude",
    "zwischenteil": "Interlude",
    "outro": "Ending",
    "ending": "Ending",
    "ende": "Ending",
    "schluss": "Ending",
    "coda": "Coda",
    "tag": "Tag",
    "misc": "Misc",
}

_LABEL_RE = re.compile(
    r"^\s*[\[(]?\s*(" + "|".join(sorted(map(re.escape, LABEL_TYPES), key=len, reverse=True)) + r")"
    r"\s*(\d+)?\s*[\])]?\s*:?\s*$",
    re.IGNORECASE,
)
# Abschnittsname in einer .sng (erste Zeile nach „---“): bekannte Bezeichnung, optional mit Nummer („Verse 1a“).
# Alles andere ist schon Liedtext.
_SNG_LABEL_RE = re.compile(
    r"^\s*(" + "|".join(sorted(map(re.escape, [*LABEL_TYPES, "unbekannt", "unknown", "teil", "part"]),
                              key=len, reverse=True)) + r")(?:\s*\d+[a-z]?)?\s*$",
    re.IGNORECASE,
)
# Abschnitte ohne Text (leere Folie), z. B. "Instrumental" allein in einem Block
TEXTLESS_TYPES = {"Instrumental", "Interlude", "Intro", "Ending"}
# "1. Text..." oder "1) Text..." am Blockanfang (Gesangbuch-Stil)
_NUMBERED_RE = re.compile(r"^\s*(\d{1,2})[.)]\s+(\S.*)$")


@dataclass
class Section:
    label: str
    lines: list[str]  # eine Leerzeile = Absatz-/Folienumbruch innerhalb des Abschnitts


@dataclass
class Song:
    title: str = ""
    author: str = ""
    ccli: str = ""
    copyright: str = ""
    sections: list[Section] = field(default_factory=list)
    order: list[str] = field(default_factory=list)
    lang_count: int = 1
    editor: str = ""
    headers: dict[str, str] = field(default_factory=dict)

    @property
    def manual(self) -> bool:
        return self.editor == MANUAL_EDITOR

    def ordered_sections(self) -> list[Section]:
        by_label = {s.label: s for s in self.sections}
        if self.order and all(lbl in by_label for lbl in self.order):
            return [by_label[lbl] for lbl in self.order]
        return list(self.sections)


# --------------------------------------------------------------------------- lesen


def read_text(path: Path) -> str:
    raw = path.read_bytes()
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("cp1252", errors="replace")


def parse_sng(text: str) -> Song:
    song = Song()
    # SongBeamer: „---“ trennt Abschnitte, „--“ Folien. Ein Block ohne Abschnittsnamen hängt am vorigen Abschnitt.
    blocks = re.split(r"^-{2,}[ \t]*$", normalize_newlines(text), flags=re.MULTILINE)
    for line in blocks[0].splitlines():
        if line.startswith("#") and "=" in line:
            key, value = line[1:].split("=", 1)
            song.headers[key.strip()] = value.strip()

    h = song.headers
    song.title = h.get("Title", "")
    song.author = h.get("Author", "")
    song.ccli = h.get("CCLI", "")
    song.copyright = h.get("(c)", "")
    song.editor = h.get("Editor", "")
    song.order = [s.strip() for s in h.get("VerseOrder", "").split(",") if s.strip()]
    try:
        song.lang_count = max(1, int(h.get("LangCount", "1")))
    except ValueError:
        song.lang_count = 1

    parsed = []  # (Abschnittsname oder None, Zeilen)
    for block in blocks[1:]:
        lines = _undouble([ln.rstrip() for ln in block.strip("\n").split("\n")])
        while lines and not lines[-1]:
            lines.pop()
        if not lines:
            continue
        if is_sng_label(lines[0]) or lines[0].strip() in song.order:
            parsed.append((lines[0].strip(), lines[1:]))
        else:  # erste Zeile ist schon Liedtext (z. B. alte SongBeamer-Dateien ohne Abschnittsnamen)
            parsed.append((None, lines))
    if all(label for label, _ in parsed):
        song.sections = [Section(label, lines) for label, lines in parsed]
    else:
        _add_unlabeled(song, parsed)
    return song


def normalize_newlines(text: str) -> str:
    """Zeilenenden vereinheitlichen. Manche SongBeamer-/ChurchTools-Dateien enden mit „\\r\\r\\n“ –
    daraus darf keine zusätzliche Leerzeile (= Folienumbruch) werden."""
    return text.replace("\r\r\n", "\n").replace("\r\n", "\n").replace("\r", "\n")


def _undouble(lines: list[str]) -> list[str]:
    """Block „doppelzeilig“ gespeichert (nach JEDER Textzeile genau eine Leerzeile)? -> Leerzeilen entfernen.

    Sonst würde beim Folienumbruch nach Absatz jede Zeile eine eigene Folie.
    """
    text = [i for i, ln in enumerate(lines) if ln.strip()]
    if len(text) < 3:
        return lines
    last = text[-1]
    double = all(i % 2 == text[0] % 2 for i in text) and all(
        not lines[i].strip() for i in range(text[0] + 1, last, 2))
    return [ln for ln in lines if ln.strip()] if double else lines


def is_sng_label(line: str) -> bool:
    """Ist die erste Zeile eines Blocks ein Abschnittsname („Verse 1“, „Chorus“, „Unbekannt 2a“ …)?"""
    return bool(_SNG_LABEL_RE.match(line))


def _add_unlabeled(song: Song, parsed: list[tuple[str | None, list[str]]]) -> None:
    """Blöcke ohne Abschnittsnamen einordnen (wie SongBeamer):

      * nach einem benannten Abschnitt -> weitere Folie dieses Abschnitts;
      * sonst (Lied ganz ohne Namen) -> eigener Abschnitt: Text, der mehrfach vorkommt, wird „Chorus“,
        der Rest „Verse 1, 2, …“; Wiederholungen landen in der Reihenfolge.
    """
    taken = {label for label, _ in parsed if label}
    counters: dict[str, int] = {}

    def next_label(kind: str) -> str:
        n = counters.get(kind, 0) + 1
        while f"{kind} {n}" in taken:
            n += 1
        counters[kind] = n
        taken.add(f"{kind} {n}")
        return f"{kind} {n}"

    texts = [_norm_lines(lines) for label, lines in parsed if label is None]
    sequence: list[str] = []  # Abschnitte in Dateireihenfolge, mit Wiederholungen
    generated: dict[str, Section] = {}  # Text -> erzeugter Abschnitt
    named: Section | None = None  # zuletzt begonnener benannter Abschnitt
    for label, lines in parsed:
        if label:
            named = Section(label, list(lines))
            song.sections.append(named)
            sequence.append(label)
        elif named is not None:  # weitere Folie („--“/„---“ ohne Namen) -> Absatzgrenze merken
            named.lines.extend(([""] if named.lines else []) + lines)
        elif (key := _norm_lines(lines)) in generated:
            sequence.append(generated[key].label)
        else:
            sec = Section(next_label("Chorus" if texts.count(key) > 1 else "Verse"), list(lines))
            generated[key] = sec
            song.sections.append(sec)
            sequence.append(sec.label)
    # Die Kopfzeile VerseOrder kennt die erzeugten Abschnitte nicht -> Reihenfolge aus der Datei.
    if generated:
        song.order = sequence


def read_sng(path: Path) -> Song:
    return parse_sng(read_text(path))


def is_edited_file(path: Path) -> bool:
    """ChurchTools-Lied, das in SongBridge bearbeitet wurde (siehe EDITED_KEY)?"""
    try:
        head = read_text(path)[:2000]
    except OSError:
        return False
    return f"#{EDITED_KEY}=" in head


def is_manual_file(path: Path) -> bool:
    try:
        head = read_text(path)[:2000]
    except OSError:
        return False
    return f"#Editor={MANUAL_EDITOR}" in head


# ------------------------------------------------------------------------ schreiben


def build_sng(song: Song) -> str:
    """Song -> .sng-Text. Weitere Kopfzeilen aus song.headers (z. B. #BackgroundImage beim Bearbeiten) bleiben erhalten."""
    order = song.order or [s.label for s in song.sections]
    header = [
        ("LangCount", str(song.lang_count or 1)),
        ("Title", song.title),
        ("Editor", song.editor or MANUAL_EDITOR),
        ("Version", "3"),
        ("Author", song.author),
        ("CCLI", song.ccli),
        ("(c)", song.copyright),
        ("VerseOrder", ",".join(order)),
    ]
    known = {k for k, _ in header}
    header += [(k, v) for k, v in song.headers.items() if k not in known]
    out = [f"#{k}={_one_line(v)}" for k, v in header if v or k in ("Title", "LangCount")]
    for sec in song.sections:
        out.append("---")
        out.append(sec.label)
        out.extend(sec.lines)
    return "﻿" + "\n".join(out) + "\n"


def _one_line(value: str) -> str:
    return " ".join(str(value).split())


# ------------------------------------------------------------------ Freitext -> Lied


def parse_freetext(text: str) -> tuple[list[Section], list[str], list[str]]:
    """Wandelt eingefügten Liedtext in Abschnitte + Reihenfolge um.

    Regeln:
      * Leerzeilen trennen Abschnitte.
      * Erste Zeile wie "Strophe 1", "[Refrain]", "Chorus:", "Bridge" -> Abschnittsname.
      * "1. Text..." am Blockanfang -> Strophe 1.
      * Nur ein Name ohne Text (z. B. "Refrain") -> Wiederholung eines vorhandenen Abschnitts;
        bei Instrumental/Intro/Zwischenspiel/Schluss ohne Vorgänger -> leerer Abschnitt (leere Folie).
      * Ein Block ohne Namen, der wörtlich einem vorhandenen Abschnitt entspricht, gilt als Wiederholung.
      * Sonst ohne Namen -> nächste Strophe.
    Rückgabe: (Abschnitte, Reihenfolge, Hinweise)
    """
    sections: list[Section] = []
    order: list[str] = []
    warnings: list[str] = []
    counters: dict[str, int] = {}

    def by_label(label: str) -> Section | None:
        return next((s for s in sections if s.label == label), None)

    def by_lines(lines: list[str]) -> Section | None:
        key = _norm_lines(lines)
        return next((s for s in sections if _norm_lines(s.lines) == key), None)

    def next_label(kind: str) -> str:
        n = counters.get(kind, 0) + 1
        while by_label(f"{kind} {n}"):
            n += 1
        counters[kind] = n
        return f"{kind} {n}"

    def add(label: str, lines: list[str]) -> None:
        sections.append(Section(label, lines))
        order.append(label)

    normalized = normalize_newlines(text)
    blocks = [b for b in re.split(r"\n\s*\n", normalized) if b.strip()]

    for block in blocks:
        lines = [ln.strip() for ln in block.split("\n") if ln.strip()]
        # „--“ allein auf einer Zeile = Folienumbruch innerhalb des Abschnitts (intern Leerzeile)
        lines = ["" if _PARA_RE.match(ln) else ln for ln in lines]
        while lines and not lines[0]:
            lines.pop(0)
        if not lines:
            continue
        kind, number = None, None

        m = _LABEL_RE.match(lines[0])
        if m:
            kind = LABEL_TYPES[m.group(1).lower()]
            number = int(m.group(2)) if m.group(2) else None
            lines = lines[1:]
        else:
            m = _NUMBERED_RE.match(lines[0])
            if m:
                kind, number = "Verse", int(m.group(1))
                lines = [m.group(2)] + lines[1:]
        lines = _trim_marks(lines)

        if kind is None:
            same = by_lines(lines)
            if same:
                order.append(same.label)
            else:
                add(next_label("Verse"), lines)
            continue

        if not lines:  # nur Name -> Wiederholung
            if number is not None:
                target = by_label(f"{kind} {number}")
            else:
                target = next((s for s in reversed(sections) if s.label.startswith(kind + " ")), None)
            if target:
                order.append(target.label)
            elif kind in TEXTLESS_TYPES:
                add(f"{kind} {number}" if number is not None else next_label(kind), [])
            else:
                warnings.append(f"„{kind}{' ' + str(number) if number else ''}“ wird wiederholt, kommt aber vorher nicht vor – ignoriert.")
            continue

        if number is None:
            same = next(
                (s for s in sections if s.label.startswith(kind + " ") and _norm_lines(s.lines) == _norm_lines(lines)),
                None,
            )
            if same:
                order.append(same.label)
            else:
                add(next_label(kind), lines)
            continue

        label = f"{kind} {number}"
        existing = by_label(label)
        if existing is None:
            counters[kind] = max(counters.get(kind, 0), number)
            add(label, lines)
        elif _norm_lines(existing.lines) == _norm_lines(lines):
            order.append(label)
        else:
            new_label = next_label(kind)
            warnings.append(f"„{label}“ kommt zweimal mit unterschiedlichem Text vor – zweiter als „{new_label}“ gespeichert.")
            add(new_label, lines)

    return sections, order, warnings


# Liedzeile, die eigentlich eine Regieanweisung ist: „Refrain 2x“, „(Bridge)“, „[Chorus wdh.]“, „(2x)“.
_HINT_RE = re.compile(
    r"^\s*[\[(]?\s*(?:(?:" + "|".join(sorted(map(re.escape, LABEL_TYPES), key=len, reverse=True)) + r")\b.*"
    r"|\d+\s*[x×]|[x×]\s*\d+|wdh\.?|wiederholen|wiederholung|repeat)\s*[\])]?\s*:?\s*$",
    re.IGNORECASE,
)


def freetext_hints(sections: list[Section]) -> list[str]:
    """Hinweise auf Zeilen, die vermutlich nicht als Liedtext gemeint sind (Freitext-Eingabe)."""
    hints = []
    for sec in sections:
        for line in sec.lines:
            if _HINT_RE.match(line):
                hints.append(f"„{line.strip()}“ in {sec.label} wird als Liedtext gelesen. Abschnittsnamen und Wiederholungen "
                             "gehören allein in die erste Zeile eines Blocks (Leerzeile davor), z. B. nur „Refrain“.")
            elif len(line) > 50:
                hints.append(f"Lange Zeile in {sec.label} ({len(line)} Zeichen) – passt evtl. nicht auf eine Folienzeile: "
                             f"„{line[:40].strip()} …“")
    if sections and not any(s.label.startswith(("Chorus", "Refrain")) for s in sections) and len(sections) > 1:
        hints.append("Kein Refrain erkannt – falls es einen gibt, die erste Zeile des Blocks „Refrain“ nennen.")
    return hints


def song_to_freetext(song: Song) -> str:
    """Gegenstück zu parse_freetext – zum Bearbeiten eines gespeicherten Liedes."""
    by_label = {s.label: s for s in song.sections}
    order = song.order if song.order and all(l in by_label for l in song.order) else [s.label for s in song.sections]
    seen: set[str] = set()
    parts = []
    for label in order:
        if label in seen:
            parts.append(label)
        else:
            seen.add(label)
            parts.append("\n".join([label] + _text_lines(by_label[label])))
    unused = [s for s in song.sections if s.label not in seen]
    parts.extend("\n".join([s.label] + _text_lines(s)) for s in unused)
    return "\n\n".join(parts)


def _text_lines(section: Section) -> list[str]:
    # Leerzeilen innerhalb eines Abschnitts (Absatz-/Folienumbruch) würden ihn im Freitext teilen -> „--“.
    out: list[str] = []
    for ln in section.lines:
        if ln.strip():
            out.append(ln)
        elif out and out[-1] != PARA_MARK:
            out.append(PARA_MARK)
    while out and out[-1] == PARA_MARK:
        out.pop()
    return out


def _trim_marks(lines: list[str]) -> list[str]:
    """Absatzmarker (Leerzeilen) am Anfang/Ende entfernen und doppelte zusammenfassen."""
    out: list[str] = []
    for ln in lines:
        if ln.strip() or (out and out[-1].strip()):
            out.append(ln)
    while out and not out[-1].strip():
        out.pop()
    return out


def paragraphs(lines: list[str]) -> list[list[str]]:
    """Abschnittszeilen -> Absätze (an Leerzeilen getrennt, leere Absätze entfallen)."""
    out: list[list[str]] = [[]]
    for ln in lines:
        if ln.strip():
            out[-1].append(ln)
        elif out[-1]:
            out.append([])
    return [p for p in out if p]


def _norm_lines(lines: list[str]) -> str:
    return "\n".join(" ".join(ln.split()).casefold() for ln in lines)


def norm_title(title: str) -> str:
    return re.sub(r"[^\w]+", " ", title.casefold()).strip()


# ------------------------------------------------------------------ Zweisprachigkeit erkennen

_WORD_RE = re.compile(r"[a-zäöüß']+")
_DE_WORDS = set("""und der die das ist ich du er sie wir ihr nicht mit dich dir mich mir dein deine deinen deinem deiner
mein meine meinen meinem unser unsere uns euch ein eine einen einem auf für von zu im in ist bist sind sein wird wie was
wer wo auch noch nur schon so dann denn weil wenn aber oder doch hier da dort alle alles immer nie gott herr jesus
geist liebe gnade ewig ewigkeit himmel erde licht leben herz herzen heilig anbeten loben preis ehre singen will kann
wollen gib gibt kommt komm durch über unter vor nach bei ohne gegen um aus des dem den""".split())
_EN_WORDS = set("""and the is i you he she we they not with me my your yours our us a an on for of to in are be am will
how what who where also only so then because if but or here there all always never god lord jesus spirit love grace
forever heaven earth light life heart hearts holy worship praise glory sing can come through over under before after
by without against at from it its this that these those was were has have do does let oh name""".split())


def line_language(line: str) -> str:
    """„de“, „en“ oder „“ (unklar) – grob über typische Wörter und Umlaute."""
    words = _WORD_RE.findall(line.casefold())
    if not words:
        return ""
    de = sum(w in _DE_WORDS for w in words) + 2 * sum(any(c in w for c in "äöüß") for w in words)
    en = sum(w in _EN_WORDS for w in words) + sum(w.endswith("'s") or w in ("i'm", "you're", "it's") for w in words)
    if de > en and de >= 1:
        return "de"
    if en > de and en >= 1:
        return "en"
    return ""


LANG_NAMES = {"de": "Deutsch", "en": "Englisch"}


def detect_bilingual(sections: list[Section]) -> tuple[bool, str]:
    """Wechseln sich in allen Abschnitten die Sprachen zeilenweise ab (Original / Übersetzung)?

    -> (zweisprachig?, Erklärung). Bedingungen: jeder Abschnitt mit Text hat eine gerade Zeilenzahl, mindestens
    zwei Zeilenpaare lassen sich einer Sprache zuordnen, und davon wechseln mindestens 80 % die Sprache – immer in
    derselben Richtung (z. B. Deutsch oben, Englisch darunter).
    """
    pairs, odd = [], []
    for sec in sections:
        lines = [ln for ln in sec.lines if ln.strip()]
        if not lines:
            continue
        if len(lines) % 2:
            odd.append(sec.label)
            continue
        pairs.extend((line_language(lines[i]), line_language(lines[i + 1])) for i in range(0, len(lines), 2))
    if odd or len(pairs) < 2:
        return False, ""
    known = [(a, b) for a, b in pairs if a and b]
    if len(known) < 2 or len(known) < 0.5 * len(pairs):
        return False, ""
    directions = Counter(p for p in known if p[0] != p[1])
    if not directions:
        return False, ""
    (first, second), hits = directions.most_common(1)[0]
    if hits < 0.8 * len(known):
        return False, ""
    return True, (f"Die Zeilen wechseln sich ab: {LANG_NAMES[first]} (Original) / {LANG_NAMES[second]} (Übersetzung) "
                  f"– {hits} von {len(pairs)} Zeilenpaaren eindeutig.")


def bilingual_hints(sections: list[Section]) -> list[str]:
    """Hinweise für zweisprachige Lieder: Abschnitte mit ungerader Zeilenzahl passen nicht in Paare."""
    out = []
    for sec in sections:
        n = sum(1 for ln in sec.lines if ln.strip())
        if n % 2:
            out.append(f"„{sec.label}“ hat {n} Zeilen – bei zweisprachigen Liedern braucht jede Originalzeile "
                       "eine Übersetzungszeile darunter.")
    return out
