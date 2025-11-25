scraping_scripts
=================

A tiny starter repo for scraping scripts.

Quick start
-----------

1. Create a venv (recommended):

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the hello-world script:

```bash
python hello_world.py
```

4. Run the sample scraper (scrapes https://example.com):

```bash
python hello_world.py --scrape
```

Commit the scaffold
-------------------

```bash
cd /Users/luisgutierrez/Desktop/scraping_scripts
git init
git add .
git commit -m "chore: add hello-world scraper scaffold"
```

Notes
-----
- This repository is intended to hold multiple scraping scripts. Add new modules under this folder and keep a single `requirements.txt` updated.
- When writing scrapers, respect website `robots.txt` and terms of service, and avoid excessive request rates.
