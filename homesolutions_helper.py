#!/usr/bin/env python3
"""homesolutions_helper.py

Scrape the Home Solutions Helper site for the latest article headlines.

The script fetches the homepage and extracts article links/headlines using a
few common HTML patterns so it keeps working even if the layout changes.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from typing import Iterable, List, Optional
import json
import csv
from urllib.parse import urlparse, parse_qs, quote

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://homesolutionshelper.com"


@dataclass
class Article:
    """Simple representation of a headline on Home Solutions Helper."""

    title: str
    url: str
    summary: Optional[str] = None
    images: List[str] = field(default_factory=list)


def fetch_html(url: str, timeout: int = 15) -> str:
    """Fetch a page and return its HTML text.

    Raises:
        requests.HTTPError: if the response returns an error status code.
    """

    headers = {
        "User-Agent": "scraping-scripts/1.0 (+https://homesolutionshelper.com/robots.txt)",
        "Accept-Language": "en-US,en;q=0.9",
    }
    response = requests.get(url, timeout=timeout, headers=headers)
    response.raise_for_status()
    return response.text


def _clean_text(text: str) -> str:
    return " ".join(text.split())


def _article_from_element(element) -> Optional[Article]:
    heading = element.find(["h1", "h2", "h3"])
    if heading is None:
        return None

    link_tag = heading.find("a") or heading
    title_text = link_tag.get_text(strip=True)
    if not title_text:
        return None

    href = link_tag.get("href") or BASE_URL
    if href.startswith("/"):
        href = BASE_URL + href

    summary_tag = element.find("p")
    summary_text = _clean_text(summary_tag.get_text()) if summary_tag else None

    # extract images from the article container if present
    images: List[str] = []
    for img in element.find_all("img", src=True):
        src = img.get("src")
        if src:
            images.append(_normalize_src(src))

    return Article(title=title_text, url=href, summary=summary_text, images=images)


def _normalize_src(src: str) -> str:
    src = src.strip()
    if src.startswith("//"):
        return "https:" + src
    if src.startswith("/"):
        return BASE_URL + src
    return src


def parse_articles(html: str) -> List[Article]:
    """Parse article headlines from the Home Solutions Helper homepage HTML."""

    soup = BeautifulSoup(html, "html.parser")

    articles: List[Article] = []
    # Use a dedupe set that prefers per-item href when available; when href == BASE_URL
    # (fallback), dedupe by title so we keep multiple distinct listings even without links.
    seen_keys: set[str] = set()

    # First try semantic <article> elements
    for container in soup.find_all("article"):
        maybe_article = _article_from_element(container)
        if maybe_article:
            key = maybe_article.url if maybe_article.url != BASE_URL else maybe_article.title
            if key not in seen_keys:
                articles.append(maybe_article)
                seen_keys.add(key)

    # Fallback: find headings with or without anchors (covers sites that don't use <article>)
    # Use a combined selector so we catch both `h2 a` and plain `h2`/`h3` elements.
    for heading in soup.select("h2 a, h3 a, h2, h3"):
        # determine title, href and an element to search for images
        search_element = None
        if heading.name == "a":
            title = heading.get_text(strip=True)
            href = heading.get("href") or BASE_URL
            search_element = heading.parent
        else:
            anchor = heading.find("a")
            if anchor and anchor.get("href"):
                title = anchor.get_text(strip=True) or heading.get_text(strip=True)
                href = anchor.get("href")
                search_element = anchor.parent
            else:
                title = heading.get_text(strip=True)
                href = BASE_URL
                search_element = heading

        if not title:
            continue

        if href.startswith("/"):
            href = BASE_URL + href

        # choose dedupe key: prefer href when it's a real per-item link, otherwise use title
        dedupe_key = href if href != BASE_URL else title
        if dedupe_key in seen_keys:
            continue

        # find images near the heading (inside element or in ancestors)
        images: List[str] = []
        if search_element is not None:
            for img in search_element.find_all("img", src=True):
                images.append(_normalize_src(img.get("src")))
            anc = search_element.parent
            steps = 0
            while not images and anc is not None and steps < 6:
                for img in anc.find_all("img", src=True):
                    images.append(_normalize_src(img.get("src")))
                anc = anc.parent
                steps += 1

        articles.append(Article(title=title, url=href, images=images))
        seen_keys.add(dedupe_key)

    return articles


def scrape(limit: Optional[int] = None) -> List[Article]:
    """Scrape the Home Solutions Helper homepage for headlines."""

    html = fetch_html(BASE_URL)
    articles = parse_articles(html)
    if limit is not None:
        articles = articles[:limit]
    return articles


def _format_articles(articles: Iterable[Article]) -> str:
    lines = []
    for idx, article in enumerate(articles, start=1):
        lines.append(f"{idx}. {article.title}")
        lines.append(f"   link: {article.url}")
        if article.summary:
            lines.append(f"   summary: {article.summary}")
        if getattr(article, "images", None):
            for i, img in enumerate(article.images, start=1):
                lines.append(f"   image_{i}: {img}")
    return "\n".join(lines)


def _article_to_dict(a: Article, dropbox_base: Optional[str] = None) -> dict:
    images = list(a.images)
    if dropbox_base and images:
        mapped = []
        for src in images:
            parsed = urlparse(src)
            qs = parse_qs(parsed.query)
            filename = None
            if "file" in qs and qs["file"]:
                filename = qs["file"][0]
            else:
                filename = parsed.path.rsplit("/", 1)[-1]
            if filename:
                mapped.append(dropbox_base.rstrip("/") + "/" + quote(filename))
        if mapped:
            images = mapped
    return {"title": a.title, "url": a.url, "summary": a.summary, "images": images}


def _write_csv(articles: List[Article], dropbox_base: Optional[str], output: Optional[str]) -> None:
    # CSV columns: title,url,summary,image_1,...,image_N
    dicts = [_article_to_dict(a, dropbox_base=dropbox_base) for a in articles]
    max_images = max((len(d.get("images") or []) for d in dicts), default=0)

    fieldnames = ["title", "url", "summary"] + [f"image_{i+1}" for i in range(max_images)]

    rows = []
    for d in dicts:
        imgs = d.get("images") or []
        row = [d.get("title") or "", d.get("url") or "", d.get("summary") or ""]
        # fill image columns, pad with empty strings
        row += imgs + [""] * (max_images - len(imgs))
        rows.append(row)

    if output:
        with open(output, "w", encoding="utf-8", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(fieldnames)
            writer.writerows(rows)
        print(f"Wrote CSV to {output}")
    else:
        writer = csv.writer(sys.stdout)
        writer.writerow(fieldnames)
        writer.writerows(rows)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Scrape https://homesolutionshelper.com for the latest headlines.")
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Maximum number of articles to display (default: 5)",
    )
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument("--csv", action="store_true", help="Output results as CSV")
    parser.add_argument("--dropbox-base", type=str, help="Base Dropbox URL to map image filenames (optional)")
    parser.add_argument("--output", type=str, help="Write JSON output to a file")
    parser.add_argument("--csv-output", type=str, help="Write CSV output to a file")
    args = parser.parse_args(argv)

    try:
        articles = scrape(limit=args.limit)
    except Exception as exc:  # pragma: no cover - used for CLI only
        print(f"Scrape failed: {exc}")
        return 1

    if not articles:
        print("No articles found on the homepage.")
        return 0

    if args.json:
        # convert articles to serializable dicts, optionally mapping images to Dropbox
        def article_to_dict(a: Article) -> dict:
            images = list(a.images)
            if args.dropbox_base and images:
                mapped = []
                for src in images:
                    parsed = urlparse(src)
                    qs = parse_qs(parsed.query)
                    filename = None
                    if "file" in qs and qs["file"]:
                        filename = qs["file"][0]
                    else:
                        filename = parsed.path.rsplit("/", 1)[-1]
                    if filename:
                        mapped.append(args.dropbox_base.rstrip("/") + "/" + quote(filename))
                if mapped:
                    images = mapped
            return {"title": a.title, "url": a.url, "summary": a.summary, "images": images}

        data = [article_to_dict(a) for a in articles]
        out = json.dumps(data, indent=2)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as fh:
                fh.write(out)
            print(f"Wrote JSON to {args.output}")
        else:
            print(out)
    elif args.csv:
        _write_csv(articles, dropbox_base=args.dropbox_base, output=args.csv_output)
    else:
        print(_format_articles(articles))
    return 0


if __name__ == "__main__":
    sys.exit(main())
