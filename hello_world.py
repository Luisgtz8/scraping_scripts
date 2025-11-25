#!/usr/bin/env python3
"""
hello_world.py

Simple hello-world starter and tiny sample scraper for the scraping_scripts project.
"""

import argparse


def hello():
    print("Hello, world! This is the scraping_scripts starter.")


def sample_scrape():
    try:
        import requests
        from bs4 import BeautifulSoup
    except Exception:
        print("Missing dependencies. Install with: pip install -r requirements.txt")
        return

    url = "https://example.com"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        print(f"Request failed: {e}")
        return

    soup = BeautifulSoup(resp.text, "html.parser")
    title = soup.title.string.strip() if soup.title and soup.title.string else "No title found"
    print(f"Scraped {url}: title -> {title}")


def main():
    parser = argparse.ArgumentParser(description="Hello world + sample scraper")
    parser.add_argument("--scrape", action="store_true", help="Run sample scrape of example.com")
    args = parser.parse_args()

    hello()
    if args.scrape:
        sample_scrape()


if __name__ == "__main__":
    main()
