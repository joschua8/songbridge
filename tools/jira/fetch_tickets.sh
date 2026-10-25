#!/usr/bin/env bash
#
# fetch_tickets.sh – fetch tickets (e.g. TestFLO test cases) via the Jira REST API
# and store each ticket in a folder named after its key.
#
# Modes (exactly one):
#   -k, --key KEY[,KEY...]   Single tickets by key
#   -f, --from DATE          Tickets from date (YYYY-MM-DD), optionally with --to
#   -l, --last [N]           The latest N tickets (default: 10)
#
# Configuration via environment variables or the file .jira.env next to the script:
#   JIRA_URL      e.g. https://company.atlassian.net or https://jira.company.com
#   JIRA_EMAIL    Jira Cloud only: login e-mail (together with JIRA_TOKEN = API token)
#   JIRA_TOKEN    Cloud: API token  |  Server/Data Center: Personal Access Token
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
[ -f "$SCRIPT_DIR/.jira.env" ] && . "$SCRIPT_DIR/.jira.env"

usage() {
  cat <<'EOF'
Usage:
  fetch_tickets.sh -k PROJ-123[,PROJ-124]          Tickets by key
  fetch_tickets.sh -f 2026-10-01 [-t 2026-10-14]   Tickets in a date range
  fetch_tickets.sh -l [N]                          The latest N tickets (default 10)

Options:
  -p, --project KEY      Only tickets from this project (for -f / -l)
  -q, --jql "JQL"        Additional JQL filter, e.g. 'issuetype = "Test Case"'
  -d, --date-field FIELD Date field for -f/-t and -l: created (default) or updated
  -o, --out DIR          Output folder (default: ./tickets)
  -a, --attachments      Also download attachments
  -h, --help             This help

For each ticket <out>/<TICKET-KEY>/ is created with
  issue.json    full API response (incl. comments)
  ticket.md     readable summary
  attachments/  attachments (only with -a)

Configuration (environment or tools/jira/.jira.env):
  JIRA_URL=https://company.atlassian.net
  JIRA_EMAIL=me@company.com      # Jira Cloud only
  JIRA_TOKEN=...                 # Cloud: API token, Server/DC: Personal Access Token
EOF
}

die() { echo "Error: $*" >&2; exit 1; }

# ---------- Arguments ----------
MODE="" KEYS="" FROM="" TO="" LAST=10 PROJECT="" EXTRA_JQL=""
DATE_FIELD="created" OUT_DIR="./tickets" ATTACHMENTS=0

set_mode() { [ -z "$MODE" ] || [ "$MODE" = "$1" ] || die "Do not combine -k, -f and -l."; MODE="$1"; }

while [ $# -gt 0 ]; do
  case "$1" in
    -k|--key)         set_mode key;   KEYS="${2:?ticket key missing}"; shift ;;
    -f|--from)        set_mode range; FROM="${2:?date missing}"; shift ;;
    -t|--to)          TO="${2:?date missing}"; shift ;;
    -l|--last)        set_mode last
                      if [ $# -gt 1 ] && [[ "$2" =~ ^[0-9]+$ ]]; then LAST="$2"; shift; fi ;;
    -p|--project)     PROJECT="${2:?project missing}"; shift ;;
    -q|--jql)         EXTRA_JQL="${2:?JQL missing}"; shift ;;
    -d|--date-field)  DATE_FIELD="${2:?field missing}"; shift ;;
    -o|--out)         OUT_DIR="${2:?folder missing}"; shift ;;
    -a|--attachments) ATTACHMENTS=1 ;;
    -h|--help)        usage; exit 0 ;;
    *)                usage >&2; die "Unknown option: $1" ;;
  esac
  shift
done

[ -n "$MODE" ] || { usage >&2; exit 1; }
[ -n "$TO" ] && [ "$MODE" != range ] && die "--to only together with --from."
case "$DATE_FIELD" in created|updated) ;; *) die "--date-field must be created or updated." ;; esac
for d in "$FROM" "$TO"; do
  [ -z "$d" ] || [[ "$d" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] || die "Date '$d' is not in the format YYYY-MM-DD."
done
[ "$LAST" -gt 0 ] || die "--last needs a number > 0."

command -v curl >/dev/null || die "curl is required."
command -v jq   >/dev/null || die "jq is required (e.g. 'brew install jq')."
: "${JIRA_URL:?JIRA_URL is not set (see --help)}"
: "${JIRA_TOKEN:?JIRA_TOKEN is not set (see --help)}"
JIRA_URL="${JIRA_URL%/}"

# ---------- HTTP ----------
# Cloud: basic auth with e-mail + API token; Server/DC: bearer with Personal Access Token.
if [ -n "${JIRA_EMAIL:-}" ]; then
  AUTH=(-u "$JIRA_EMAIL:$JIRA_TOKEN")
  SEARCH_PATH="/rest/api/2/search/jql"   # Cloud: new search API with nextPageToken
else
  AUTH=(-H "Authorization: Bearer $JIRA_TOKEN")
  SEARCH_PATH="/rest/api/2/search"       # Server/DC: classic search with startAt
fi

# jira_get PATH [curl args...] – prints the body, aborts on HTTP errors.
jira_get() {
  local path="$1"; shift
  local body status
  body="$(curl -sS -w $'\n%{http_code}' "${AUTH[@]}" -H "Accept: application/json" "$@" "$JIRA_URL$path")" \
    || die "Connection to $JIRA_URL failed."
  status="${body##*$'\n'}"
  body="${body%$'\n'*}"
  if [ "$status" -ge 400 ]; then
    local msg
    msg="$(printf '%s' "$body" | jq -r '[.errorMessages[]?, (.errors // {} | to_entries[] | "\(.key): \(.value)")] | join("; ")' 2>/dev/null || true)"
    die "HTTP $status for $path${msg:+ – $msg}"
  fi
  printf '%s' "$body"
}

# ---------- Saving ----------
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
    "- Type: \($f.issuetype.name // "-")",
    "- Status: \($f.status.name // "-")",
    "- Priority: \($f.priority.name // "-")",
    "- Assignee: \($f.assignee.displayName // "-")",
    "- Reporter: \($f.reporter.displayName // "-")",
    "- Created: \($f.created // "-")",
    "- Updated: \($f.updated // "-")",
    "- Labels: \(($f.labels // []) | join(", "))",
    "\n## Description\n",
    ($f.description // "_(none)_"),
    "\n## Comments\n",
    ( ($f.comment.comments // []) as $c
      | if ($c | length) == 0 then "_(none)_"
        else $c[] | "### \(.author.displayName // "?") – \(.created)\n\n\(.body)\n" end )
  ' > "$dir/ticket.md"

  if [ "$ATTACHMENTS" -eq 1 ]; then
    local n=0 name url
    while IFS=$'\t' read -r name url; do
      [ -n "$url" ] || continue
      mkdir -p "$dir/attachments"
      name="${name//\//_}"
      curl -sS -fL "${AUTH[@]}" -o "$dir/attachments/$name" "$url" \
        || echo "  Warning: attachment '$name' could not be downloaded." >&2
      n=$((n + 1))
    done < <(printf '%s' "$issue" | jq -r '.fields.attachment[]? | [.filename, .content] | @tsv')
    echo "  $key saved ($n attachments)"
  else
    echo "  $key saved"
  fi
}

# ---------- Search ----------
# search_keys JQL MAX – prints ticket keys line by line (MAX=0: all).
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
    # --to is inclusive (until end of day)
    [ -n "$TO" ] && parts+=("$DATE_FIELD <= \"$TO 23:59\"")
  fi
  local jql="" p
  for p in "${parts[@]+"${parts[@]}"}"; do jql="${jql:+$jql AND }$p"; done
  # Jira Cloud requires a bounded search
  [ -n "$jql" ] || jql="$DATE_FIELD >= -3650d"
  printf '%s ORDER BY %s DESC' "$jql" "$DATE_FIELD"
}

# ---------- Main ----------
mkdir -p "$OUT_DIR"

if [ "$MODE" = key ]; then
  KEY_LIST="$(printf '%s' "$KEYS" | tr ',' '\n' | tr -d ' ' | tr '[:lower:]' '[:upper:]' | grep -v '^$' || true)"
else
  JQL="$(build_jql)"
  echo "JQL: $JQL"
  max=0; [ "$MODE" = last ] && max="$LAST"
  KEY_LIST="$(search_keys "$JQL" "$max")"
fi

[ -n "$KEY_LIST" ] || { echo "No tickets found."; exit 0; }

count="$(printf '%s\n' "$KEY_LIST" | wc -l | tr -d ' ')"
echo "Fetching $count ticket(s) into $OUT_DIR ..."
failed=0
while IFS= read -r key; do
  ( save_issue "$key" ) || failed=$((failed + 1))
done <<< "$KEY_LIST"

echo "Done: $((count - failed)) saved, $failed failed."
[ "$failed" -eq 0 ]
