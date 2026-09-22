#!/usr/bin/env python3
"""Refreshes the daily lab-blog digest and quote-of-the-day blocks in README.md."""
import json
import re
import sys
import urllib.request
from datetime import date
from email.utils import parsedate_to_datetime
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
QUOTES = Path(__file__).resolve().parent / "quotes.json"

FEEDS = [
    ("OpenAI", "https://openai.com/news/rss.xml"),
    ("Google DeepMind", "https://deepmind.google/blog/rss.xml"),
    ("Hugging Face", "https://huggingface.co/blog/feed.xml"),
    ("Google Research", "https://research.google/blog/rss/"),
    ("Berkeley BAIR", "https://bair.berkeley.edu/blog/feed.xml"),
]

ATOM_NS = "{http://www.w3.org/2005/Atom}"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; profile-readme-bot/1.0)"}


def fetch_latest_item(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = resp.read()
    root = ET.fromstring(data)

    item = root.find(".//item")
    if item is not None:
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub_raw = item.findtext("pubDate")
    else:
        item = root.find(f".//{ATOM_NS}entry")
        title = (item.findtext(f"{ATOM_NS}title") or "").strip()
        link_el = item.find(f"{ATOM_NS}link")
        link = link_el.get("href", "").strip() if link_el is not None else ""
        pub_raw = item.findtext(f"{ATOM_NS}updated")

    try:
        pub_str = parsedate_to_datetime(pub_raw).strftime("%b %d, %Y")
    except Exception:
        pub_str = ""

    return title, link, pub_str


def build_labs_block():
    lines = []
    for name, url in FEEDS:
        try:
            title, link, pub = fetch_latest_item(url)
        except Exception as exc:
            print(f"warning: failed to fetch {name} ({url}): {exc}", file=sys.stderr)
            continue
        date_part = f" ({pub})" if pub else ""
        lines.append(f"- **{name}**: [{title}]({link}){date_part}")
    if not lines:
        return "_Feeds temporarily unavailable, check back tomorrow._"
    return "\n".join(lines)


def build_quote_block():
    quotes = json.loads(QUOTES.read_text(encoding="utf-8"))
    idx = date.today().toordinal() % len(quotes)
    q = quotes[idx]
    return f'> "{q["quote"]}"\n>\n> **{q["author"]}**, {q["source"]}'


def replace_block(text, marker, new_content):
    pattern = re.compile(rf"(<!--{marker}:START-->)(.*?)(<!--{marker}:END-->)", re.DOTALL)
    return pattern.sub(lambda m: f"{m.group(1)}\n{new_content}\n{m.group(3)}", text)


def main():
    text = README.read_text(encoding="utf-8")
    text = replace_block(text, "LAB_BLOGS", build_labs_block())
    text = replace_block(text, "AI_QUOTE", build_quote_block())
    README.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
