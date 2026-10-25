#!/bin/bash
# Double-click in Finder starts SongBridge from source and opens the browser.
cd "$(dirname "$0")"
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q -r requirements.txt
exec .venv/bin/python -m songbridge
