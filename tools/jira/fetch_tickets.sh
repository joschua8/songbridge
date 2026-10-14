#!/usr/bin/env bash
#
# fetch_tickets.sh – Tickets (z. B. TestFLO-Testfälle) per Jira-REST-API abrufen
# und je Ticket in einem Ordner mit der Ticketnummer speichern.
#
# Modi (genau einer):
#   -k, --key KEY[,KEY...]   Einzelne Tickets anhand der Ticketnummer
#   -f, --from DATUM         Tickets ab Datum (YYYY-MM-DD), optional mit --to
#   -l, --last [N]           Die letzten N Tickets (Standard: 10)
#
# Konfiguration über Umgebungsvariablen oder die Datei .jira.env neben dem Skript:
#   JIRA_URL      z. B. https://firma.atlassian.net oder https://jira.firma.de
#   JIRA_EMAIL    nur Jira Cloud: Login-E-Mail (zusammen mit JIRA_TOKEN = API-Token)
#   JIRA_TOKEN    Cloud: API-Token  |  Server/Data Center: Personal Access Token
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
[ -f "$SCRIPT_DIR/.jira.env" ] && . "$SCRIPT_DIR/.jira.env"

usage() {
  cat <<'EOF'
Verwendung:
  fetch_tickets.sh -k PROJ-123[,PROJ-124]          Tickets per Ticketnummer
  fetch_tickets.sh -f 2026-10-01 [-t 2026-10-14]   Tickets in einem Zeitraum
  fetch_tickets.sh -l [N]                          Die letzten N Tickets (Standard 10)

Optionen:
  -p, --project KEY      Nur Tickets aus diesem Projekt (für -f / -l)
  -q, --jql "JQL"        Zusätzlicher JQL-Filter, z. B. 'issuetype = "Test Case"'
  -d, --date-field FELD  Datumsfeld für -f/-t und -l: created (Standard) oder updated
  -o, --out DIR          Zielordner (Standard: ./tickets)
  -a, --attachments      Anhänge mit herunterladen
  -h, --help             Diese Hilfe

Pro Ticket entsteht <out>/<TICKETNUMMER>/ mit
  issue.json    vollständige API-Antwort (inkl. Kommentare)
  ticket.md     lesbare Zusammenfassung
  attachments/  Anhänge (nur mit -a)

Konfiguration (Umgebung oder tools/jira/.jira.env):
  JIRA_URL=https://firma.atlassian.net
  JIRA_EMAIL=ich@firma.de        # nur Jira Cloud
  JIRA_TOKEN=...                 # Cloud: API-Token, Server/DC: Personal Access Token
EOF
}

die() { echo "Fehler: $*" >&2; exit 1; }

# ---------- Argumente ----------
MODE="" KEYS="" FROM="" TO="" LAST=10 PROJECT="" EXTRA_JQL=""
DATE_FIELD="created" OUT_DIR="./tickets" ATTACHMENTS=0

set_mode() { [ -z "$MODE" ] || [ "$MODE" = "$1" ] || die "-k, -f und -l nicht kombinieren."; MODE="$1"; }

while [ $# -gt 0 ]; do
  case "$1" in
    -k|--key)         set_mode key;   KEYS="${2:?Ticketnummer fehlt}"; shift ;;
    -f|--from)        set_mode range; FROM="${2:?Datum fehlt}"; shift ;;
    -t|--to)          TO="${2:?Datum fehlt}"; shift ;;
    -l|--last)        set_mode last
                      if [ $# -gt 1 ] && [[ "$2" =~ ^[0-9]+$ ]]; then LAST="$2"; shift; fi ;;
    -p|--project)     PROJECT="${2:?Projekt fehlt}"; shift ;;
    -q|--jql)         EXTRA_JQL="${2:?JQL fehlt}"; shift ;;
    -d|--date-field)  DATE_FIELD="${2:?Feld fehlt}"; shift ;;
    -o|--out)         OUT_DIR="${2:?Ordner fehlt}"; shift ;;
    -a|--attachments) ATTACHMENTS=1 ;;
    -h|--help)        usage; exit 0 ;;
    *)                usage >&2; die "Unbekannte Option: $1" ;;
  esac
  shift
done

[ -n "$MODE" ] || { usage >&2; exit 1; }
[ -n "$TO" ] && [ "$MODE" != range ] && die "--to nur zusammen mit --from."
case "$DATE_FIELD" in created|updated) ;; *) die "--date-field muss created oder updated sein." ;; esac
for d in "$FROM" "$TO"; do
  [ -z "$d" ] || [[ "$d" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] || die "Datum '$d' nicht im Format YYYY-MM-DD."
done
[ "$LAST" -gt 0 ] || die "--last braucht eine Zahl > 0."

command -v curl >/dev/null || die "curl wird benötigt."
command -v jq   >/dev/null || die "jq wird benötigt (z. B. 'brew install jq')."
: "${JIRA_URL:?JIRA_URL ist nicht gesetzt (siehe --help)}"
: "${JIRA_TOKEN:?JIRA_TOKEN ist nicht gesetzt (siehe --help)}"
JIRA_URL="${JIRA_URL%/}"

# ---------- HTTP ----------
# Cloud: Basic-Auth mit E-Mail + API-Token; Server/DC: Bearer mit Personal Access Token.
if [ -n "${JIRA_EMAIL:-}" ]; then
  AUTH=(-u "$JIRA_EMAIL:$JIRA_TOKEN")
  SEARCH_PATH="/rest/api/2/search/jql"   # Cloud: neue Such-API mit nextPageToken
else
  AUTH=(-H "Authorization: Bearer $JIRA_TOKEN")
  SEARCH_PATH="/rest/api/2/search"       # Server/DC: klassische Suche mit startAt
fi

# jira_get PFAD [curl-Argumente...] – gibt den Body aus, bricht bei HTTP-Fehlern ab.
jira_get() {
  local path="$1"; shift
  local body status
  body="$(curl -sS -w $'\n%{http_code}' "${AUTH[@]}" -H "Accept: application/json" "$@" "$JIRA_URL$path")" \
    || die "Verbindung zu $JIRA_URL fehlgeschlagen."
  status="${body##*$'\n'}"
  body="${body%$'\n'*}"
  if [ "$status" -ge 400 ]; then
    local msg
    msg="$(printf '%s' "$body" | jq -r '[.errorMessages[]?, (.errors // {} | to_entries[] | "\(.key): \(.value)")] | join("; ")' 2>/dev/null || true)"
    die "HTTP $status für $path${msg:+ – $msg}"
  fi
  printf '%s' "$body"
}

# ---------- Speichern ----------
save_issue() {
  local key="$1" dir issue
  dir="$OUT_DIR/$key"
  issue="$(jira_get "/rest/api/2/issue/$key" -G --data-urlencode "expand=renderedFields,names")" || return 1
  mkdir -p "$dir"
  printf '%s\n' "$issue" | jq . > "$dir/issue.json"

  printf '%s' "$issue" | jq -r --arg url "$JIRA_URL" '
    .fields as $f |
    "# \(.key): \($f.summary // "")\n",
    "- Link: \($url)/browse/\(.key)",
    "- Typ: \($f.issuetype.name // "-")",
    "- Status: \($f.status.name // "-")",
    "- Priorität: \($f.priority.name // "-")",
    "- Bearbeiter: \($f.assignee.displayName // "-")",
    "- Autor: \($f.reporter.displayName // "-")",
    "- Erstellt: \($f.created // "-")",
    "- Aktualisiert: \($f.updated // "-")",
    "- Labels: \(($f.labels // []) | join(", "))",
    "\n## Beschreibung\n",
    ($f.description // "_(keine)_"),
    "\n## Kommentare\n",
    ( ($f.comment.comments // []) as $c
      | if ($c | length) == 0 then "_(keine)_"
        else $c[] | "### \(.author.displayName // "?") – \(.created)\n\n\(.body)\n" end )
  ' > "$dir/ticket.md"

  if [ "$ATTACHMENTS" -eq 1 ]; then
    local n=0 name url
    while IFS=$'\t' read -r name url; do
      [ -n "$url" ] || continue
      mkdir -p "$dir/attachments"
      name="${name//\//_}"
      curl -sS -fL "${AUTH[@]}" -o "$dir/attachments/$name" "$url" \
        || echo "  Warnung: Anhang '$name' konnte nicht geladen werden." >&2
      n=$((n + 1))
    done < <(printf '%s' "$issue" | jq -r '.fields.attachment[]? | [.filename, .content] | @tsv')
    echo "  $key gespeichert ($n Anhänge)"
  else
    echo "  $key gespeichert"
  fi
}

# ---------- Suche ----------
# search_keys JQL MAX – gibt Ticketnummern zeilenweise aus (MAX=0: alle).
search_keys() {
  local jql="$1" max="$2" fetched=0 page size token="" start=0 resp
  while :; do
    size=100
    [ "$max" -gt 0 ] && [ $((max - fetched)) -lt $size ] && size=$((max - fetched))
    if [ -n "${JIRA_EMAIL:-}" ]; then
      resp="$(jira_get "$SEARCH_PATH" -G --data-urlencode "jql=$jql" \
        --data-urlencode "fields=key" --data-urlencode "maxResults=$size" \
        ${token:+--data-urlencode "nextPageToken=$token"})"
    else
      resp="$(jira_get "$SEARCH_PATH" -G --data-urlencode "jql=$jql" \
        --data-urlencode "fields=key" --data-urlencode "maxResults=$size" \
        --data-urlencode "startAt=$start")"
    fi
    page="$(printf '%s' "$resp" | jq -r '.issues[].key')"
    [ -n "$page" ] || break
    printf '%s\n' "$page"
    size="$(printf '%s\n' "$page" | wc -l | tr -d ' ')"
    fetched=$((fetched + size)); start=$((start + size))
    [ "$max" -gt 0 ] && [ "$fetched" -ge "$max" ] && break
    if [ -n "${JIRA_EMAIL:-}" ]; then
      token="$(printf '%s' "$resp" | jq -r '.nextPageToken // empty')"
      [ -n "$token" ] || break
    else
      [ "$start" -lt "$(printf '%s' "$resp" | jq -r '.total // 0')" ] || break
    fi
  done
}

build_jql() {
  local parts=()
  [ -n "$PROJECT" ]   && parts+=("project = \"$PROJECT\"")
  [ -n "$EXTRA_JQL" ] && parts+=("($EXTRA_JQL)")
  if [ "$MODE" = range ]; then
    parts+=("$DATE_FIELD >= \"$FROM\"")
    # --to ist inklusive (bis Tagesende)
    [ -n "$TO" ] && parts+=("$DATE_FIELD <= \"$TO 23:59\"")
  fi
  local jql="" p
  for p in "${parts[@]+"${parts[@]}"}"; do jql="${jql:+$jql AND }$p"; done
  # Jira Cloud verlangt eine eingeschränkte Suche
  [ -n "$jql" ] || jql="$DATE_FIELD >= -3650d"
  printf '%s ORDER BY %s DESC' "$jql" "$DATE_FIELD"
}

# ---------- Ablauf ----------
mkdir -p "$OUT_DIR"

if [ "$MODE" = key ]; then
  KEY_LIST="$(printf '%s' "$KEYS" | tr ',' '\n' | tr -d ' ' | tr '[:lower:]' '[:upper:]' | grep -v '^$' || true)"
else
  JQL="$(build_jql)"
  echo "JQL: $JQL"
  max=0; [ "$MODE" = last ] && max="$LAST"
  KEY_LIST="$(search_keys "$JQL" "$max")"
fi

[ -n "$KEY_LIST" ] || { echo "Keine Tickets gefunden."; exit 0; }

count="$(printf '%s\n' "$KEY_LIST" | wc -l | tr -d ' ')"
echo "Lade $count Ticket(s) nach $OUT_DIR ..."
failed=0
while IFS= read -r key; do
  ( save_issue "$key" ) || failed=$((failed + 1))
done <<< "$KEY_LIST"

echo "Fertig: $((count - failed)) gespeichert, $failed fehlgeschlagen."
[ "$failed" -eq 0 ]
