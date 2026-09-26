#!/bin/bash
# Double-click this file in Finder to download all images from the current Google Site.
cd "$(dirname "$0")" || exit 1
echo "Downloading images from www.astrojykim.com ..."
echo
if command -v python3 >/dev/null 2>&1; then
  python3 scripts/fetch_images.py
else
  echo "python3 was not found. Open Terminal and run:  python3 scripts/fetch_images.py"
fi
echo
echo "Done. You can close this window."
