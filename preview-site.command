#!/bin/bash
# Double-click to build the site and open it in your browser (http://localhost:8000).
cd "$(dirname "$0")" || exit 1
python3 -m pip install -q -r requirements.txt 2>/dev/null || python3 -m pip install -q --user -r requirements.txt
python3 build.py || { echo "Build failed (see above)."; read -r; exit 1; }
( sleep 1; open "http://localhost:8000" ) &
echo "Showing the site at http://localhost:8000  — close this window to stop."
python3 -m http.server -d _site 8000
