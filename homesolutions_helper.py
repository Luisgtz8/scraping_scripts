#!/usr/bin/env python3
"""homesolutions_helper.py

Scrape the Home Solutions Helper site for the latest article headlines.

The script fetches the homepage and extracts article links/headlines using a
few common HTML patterns so it keeps working even if the layout changes.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from typing import Iterable, List, Optional

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://homesolutionshelper.com"


@dataclass
class Article:
    """Simple representation of a headline on Home Solutions Helper."""

    title: str
    url: str
    summary: Optional[str] = None


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
    return Article(title=title_text, url=href, summary=summary_text)


def parse_articles(html: str) -> List[Article]:
    """Parse article headlines from the Home Solutions Helper homepage HTML."""

    soup = BeautifulSoup(html, "html.parser")

    articles: List[Article] = []
    for container in soup.find_all("article"):
        maybe_article = _article_from_element(container)
        if maybe_article:
            articles.append(maybe_article)

    if not articles:
        for heading in soup.select("h2 a, h3 a"):
            title = heading.get_text(strip=True)
            if not title:
                continue
            href = heading.get("href") or BASE_URL
            if href.startswith("/"):
                href = BASE_URL + href
            articles.append(Article(title=title, url=href))

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
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Scrape https://homesolutionshelper.com for the latest headlines.")
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Maximum number of articles to display (default: 5)",
    )
    args = parser.parse_args(argv)

    try:
        articles = scrape(limit=args.limit)
    except Exception as exc:  # pragma: no cover - used for CLI only
        print(f"Scrape failed: {exc}")
        return 1

    if not articles:
        print("No articles found on the homepage.")
        return 0

    print(_format_articles(articles))
    return 0


if __name__ == "__main__":
    sys.exit(main())
