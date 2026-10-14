# Jira-/TestFLO-Tickets abrufen

`fetch_tickets.sh` lädt Tickets über die Jira-REST-API und legt jedes in einem
eigenen Ordner mit der Ticketnummer ab. TestFLO-Testfälle und -Testpläne sind
normale Jira-Issues und werden damit genauso abgerufen.

Voraussetzungen: `bash`, `curl`, `jq` (macOS: `brew install jq`).

## Einrichtung

```sh
cp tools/jira/.jira.env.example tools/jira/.jira.env   # ausfüllen
```

## Beispiele

```sh
# Einzelne Tickets
tools/jira/fetch_tickets.sh -k TF-123
tools/jira/fetch_tickets.sh -k TF-123,TF-124 -a          # mit Anhängen

# Zeitraum (inklusive), optional nach Aktualisierungsdatum
tools/jira/fetch_tickets.sh -f 2026-10-01 -t 2026-10-14 -p TF
tools/jira/fetch_tickets.sh -f 2026-10-01 -d updated

# Die letzten 10 (oder N) Tickets
tools/jira/fetch_tickets.sh -l -p TF
tools/jira/fetch_tickets.sh -l 25 -q 'issuetype = "Test Case"'
```

## Ergebnis

```
tickets/
└── TF-123/
    ├── issue.json      vollständige API-Antwort inkl. Kommentare
    ├── ticket.md       lesbare Zusammenfassung
    └── attachments/    nur mit -a
```

Weitere Optionen: `tools/jira/fetch_tickets.sh --help`
