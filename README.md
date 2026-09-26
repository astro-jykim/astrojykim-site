# astrojykim.com

Website of the UNIST Observational Astrophysics Group (Jae-Young Kim).

A small static site built with Python and published with GitHub Pages.

- `content/` — page text (Markdown)
- `data/` — highlights, members, publications, site settings (YAML)
- `assets/` — images and styles
- `templates/` — page layouts
- `build.py` — builds the site into `_site/`

Publications are updated monthly from NASA ADS by a GitHub Action.

```bash
pip install -r requirements.txt
python build.py
```
