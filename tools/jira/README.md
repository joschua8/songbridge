# Fetch Jira / TestFLO tickets

`fetch_tickets.sh` downloads tickets via the Jira REST API and stores each one in its
own folder named after the ticket key. TestFLO test cases and test plans are regular
Jira issues and are fetched the same way.

Requirements: `bash`, `curl`, `jq` (macOS: `brew install jq`).

## Setup

```sh
cp tools/jira/.jira.env.example tools/jira/.jira.env   # fill in
```

## Examples

```sh
# Single tickets
tools/jira/fetch_tickets.sh -k TF-123
tools/jira/fetch_tickets.sh -k TF-123,TF-124 -a          # with attachments

# Date range (inclusive), optionally by update date
tools/jira/fetch_tickets.sh -f 2026-10-01 -t 2026-10-14 -p TF
tools/jira/fetch_tickets.sh -f 2026-10-01 -d updated

# The latest 10 (or N) tickets
tools/jira/fetch_tickets.sh -l -p TF
tools/jira/fetch_tickets.sh -l 25 -q 'issuetype = "Test Case"'
```

## Output

```
tickets/
└── TF-123/
    ├── issue.json      full API response incl. comments
    ├── ticket.md       readable summary
    └── attachments/    only with -a
```

More options: `tools/jira/fetch_tickets.sh --help`
