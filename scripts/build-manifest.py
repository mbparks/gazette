#!/usr/bin/env python3
"""
Build manifest.json from backissues/broadsheet-*.html.

Walks the backissues/ directory, extracts the gazette-* meta tags from
each file, and writes a fully-enriched manifest to the repository root.

The manifest is consumed directly by index.html; there is no runtime
Worker in this architecture, the HTML files are the source of truth for
both existence and metadata.

Runs in the GitHub Action on every push touching backissues/.
License: GPL-3.0
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup

VERSION = "2.0.0"

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKISSUES_DIR = REPO_ROOT / "backissues"
MANIFEST_PATH = REPO_ROOT / "manifest.json"

FILENAME_RE = re.compile(r"^broadsheet-(\d{4}-\d{2}-\d{2})\.html$")

TITLE_STRIP_PREFIX = re.compile(r"^The Gazette\s*[:\-]+\s*", re.IGNORECASE)
TITLE_STRIP_SUFFIX = re.compile(r"\s*[:\-]+\s*M\.B\.\s*Parks$", re.IGNORECASE)


def meta_content(soup: BeautifulSoup, name: str) -> str:
    tag = soup.find("meta", attrs={"name": name})
    if tag and tag.get("content"):
        return str(tag["content"]).strip()
    return ""


def extract_metadata(html: str) -> dict:
    """Pull the four gazette-* meta tags. Fall back to <title> and description."""
    soup = BeautifulSoup(html, "html.parser")

    volume = meta_content(soup, "gazette-volume")
    number = meta_content(soup, "gazette-number")
    headline = meta_content(soup, "gazette-headline")
    subhead = meta_content(soup, "gazette-subhead") or meta_content(soup, "description")

    if not headline:
        title_tag = soup.find("title")
        if title_tag and title_tag.text:
            t = title_tag.text.strip()
            t = TITLE_STRIP_PREFIX.sub("", t)
            t = TITLE_STRIP_SUFFIX.sub("", t)
            headline = t.strip()

    if not headline:
        headline = "Untitled edition"

    return {
        "volume": volume,
        "number": number,
        "headline": headline,
        "subhead": subhead,
    }


def collect_issues() -> list[dict]:
    if not BACKISSUES_DIR.exists():
        print(f"No backissues directory at {BACKISSUES_DIR}", file=sys.stderr)
        return []

    issues = []
    for path in sorted(BACKISSUES_DIR.iterdir()):
        match = FILENAME_RE.match(path.name)
        if not match:
            continue

        date = match.group(1)
        try:
            html = path.read_text(encoding="utf-8")
        except Exception as exc:
            print(f"WARN: skipping {path.name}: {exc}", file=sys.stderr)
            continue

        meta = extract_metadata(html)
        issues.append(
            {
                "date": date,
                "volume": meta["volume"],
                "number": meta["number"],
                "headline": meta["headline"],
                "subhead": meta["subhead"],
                "url": f"/backissues/{path.name}",
            }
        )

    # Newest first
    issues.sort(key=lambda x: x["date"], reverse=True)
    return issues


def main() -> int:
    issues = collect_issues()

    manifest = {
        "version": VERSION,
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "count": len(issues),
        "issues": issues,
    }

    MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"Wrote {MANIFEST_PATH.name}: {len(issues)} issue(s).")
    for issue in issues[:5]:
        print(f"  {issue['date']}  {issue['headline']}")
    if len(issues) > 5:
        print(f"  ... and {len(issues) - 5} more")

    return 0


if __name__ == "__main__":
    sys.exit(main())
