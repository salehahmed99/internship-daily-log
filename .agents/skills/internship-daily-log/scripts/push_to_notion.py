#!/usr/bin/env python3
"""
Push a generated daily-log markdown file into a Notion database as a new page.

Why this exists: the skill already produces a well-structured markdown file
at daily-reports/DD-MM-YYYY.md. Copy-pasting that into Notion by hand every day
is exactly the kind of repetitive work worth automating away. This script
does the conversion + upload in one step.

Usage:
    python3 push_to_notion.py <path-to-markdown-file>

Requires a .env file (in the current directory, or pointed to via --env-file)
containing:
    NOTION_API_KEY=secret_xxx...       # Notion internal integration secret
    NOTION_DATABASE_ID=xxxxxxxx...     # target database's 32-char ID

The markdown file's first line is expected to be a level-1 heading in the
form "# Weekday D/M/YYYY" (e.g. "# Sunday 12/7/2026"), matching the skill's
template. That date is parsed and used to set the Date property; the whole
heading text is used as the page title. If parsing fails, today's date and
the raw heading text are used instead, so the upload never silently no-ops.
"""

import argparse
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import requests

NOTION_API_URL = "https://api.notion.com/v1/pages"
NOTION_VERSION = "2022-06-28"


def load_env_file(env_path: Path) -> dict:
    """Minimal .env parser: KEY=VALUE per line, '#' comments, no external deps."""
    values = {}
    if not env_path.exists():
        return values
    for raw_line in env_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        values[key] = value
    return values


def get_config(env_file: str | None) -> tuple[str, str]:
    """Resolve NOTION_API_KEY and NOTION_DATABASE_ID from real env vars or .env file."""
    candidates = []
    if env_file:
        candidates.append(Path(env_file))
    else:
        candidates.append(Path.cwd() / ".env")
        candidates.append(Path(__file__).resolve().parent.parent / ".env")

    file_values = {}
    for candidate in candidates:
        file_values = load_env_file(candidate)
        if file_values:
            break

    api_key = os.environ.get("NOTION_API_KEY") or file_values.get("NOTION_API_KEY")
    database_id = os.environ.get("NOTION_DATABASE_ID") or file_values.get("NOTION_DATABASE_ID")

    if not api_key or not database_id:
        sys.exit(
            "Missing NOTION_API_KEY or NOTION_DATABASE_ID. Set them as environment "
            "variables or in a .env file (checked: "
            f"{', '.join(str(c) for c in candidates)})."
        )
    return api_key, database_id


WEEKDAY_DATE_RE = re.compile(
    r"^#\s*([A-Za-z]+)\s+(\d{1,2})/(\d{1,2})/(\d{4})\s*$"
)


def parse_title_and_date(first_line: str, fallback_filename: str) -> tuple[str, str]:
    """
    Parse "# Sunday 12/7/2026" into (title, iso_date). Falls back to today's
    date and the raw heading (or filename) if the format doesn't match, so a
    formatting quirk never blocks the upload outright.
    """
    match = WEEKDAY_DATE_RE.match(first_line.strip())
    if match:
        weekday, day, month, year = match.groups()
        try:
            dt = datetime(int(year), int(month), int(day))
            title = f"{weekday} {int(day)}/{int(month)}/{int(year)}"
            return title, dt.strftime("%Y-%m-%d")
        except ValueError:
            pass

    # Fallback: try to pull DD-MM-YYYY from the filename (daily-reports/DD-MM-YYYY.md)
    date_in_name = re.search(r"(\d{2})-(\d{2})-(\d{4})", fallback_filename)
    if date_in_name:
        iso_date = f"{date_in_name.group(3)}-{date_in_name.group(2)}-{date_in_name.group(1)}"
    else:
        iso_date = datetime.now().strftime("%Y-%m-%d")

    title = first_line.strip().lstrip("#").strip() or Path(fallback_filename).stem
    return title, iso_date


def rich_text(text: str) -> list[dict]:
    """
    Convert a line of markdown inline syntax (bold, links) into Notion rich
    text objects. Deliberately supports only **bold** and [text](url) since
    that covers what the skill's template actually produces.
    """
    tokens = []
    # Split on bold (**...**) and links ([...](...)) while keeping the rest as plain text.
    pattern = re.compile(r"(\*\*(.+?)\*\*)|(\[(.+?)\]\((.+?)\))")
    pos = 0
    for m in pattern.finditer(text):
        if m.start() > pos:
            tokens.append({"type": "text", "text": {"content": text[pos:m.start()]}})
        if m.group(1):  # bold
            tokens.append({
                "type": "text",
                "text": {"content": m.group(2)},
                "annotations": {"bold": True},
            })
        elif m.group(3):  # link
            tokens.append({
                "type": "text",
                "text": {"content": m.group(4), "link": {"url": m.group(5)}},
            })
        pos = m.end()
    if pos < len(text):
        tokens.append({"type": "text", "text": {"content": text[pos:]}})
    if not tokens:
        tokens = [{"type": "text", "text": {"content": text}}]
    return tokens


def markdown_to_blocks(markdown_text: str) -> list[dict]:
    """
    Convert the skill's markdown output (H1 title, H2 sections, bullet lists,
    plain paragraphs) into Notion block objects. Only handles the subset of
    markdown the skill's template actually uses — this isn't a general-purpose
    converter, just enough to round-trip the daily log faithfully.
    """
    lines = markdown_text.splitlines()
    blocks = []

    # Skip the H1 title line — it becomes the page title, not a body block.
    start = 1 if lines and lines[0].strip().startswith("# ") else 0

    for line in lines[start:]:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("## "):
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {"rich_text": rich_text(stripped[3:].strip())},
            })
        elif stripped.startswith("### "):
            blocks.append({
                "object": "block",
                "type": "heading_3",
                "heading_3": {"rich_text": rich_text(stripped[4:].strip())},
            })
        elif stripped.startswith("- ") or stripped.startswith("* "):
            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": rich_text(stripped[2:].strip())},
            })
        else:
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": rich_text(stripped)},
            })

    return blocks


def create_notion_page(api_key: str, database_id: str, title: str, iso_date: str, blocks: list[dict]) -> str:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }
    payload = {
        "parent": {"database_id": database_id},
        "properties": {
            "Name": {"title": [{"text": {"content": title}}]},
            "Date": {"date": {"start": iso_date}},
        },
        # Notion caps page creation at 100 children blocks per request; the
        # skill's daily logs are short enough that this practically never
        # matters, but truncating defensively beats a hard failure.
        "children": blocks[:100],
    }
    response = requests.post(NOTION_API_URL, headers=headers, json=payload, timeout=30)
    if response.status_code >= 300:
        sys.exit(f"Notion API error ({response.status_code}): {response.text}")
    return response.json().get("url", "")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("markdown_file", help="Path to the daily log markdown file")
    parser.add_argument("--env-file", help="Path to .env file (default: ./.env)")
    args = parser.parse_args()

    md_path = Path(args.markdown_file)
    if not md_path.exists():
        sys.exit(f"File not found: {md_path}")

    api_key, database_id = get_config(args.env_file)

    markdown_text = md_path.read_text()
    lines = markdown_text.splitlines()
    first_line = lines[0] if lines else ""
    title, iso_date = parse_title_and_date(first_line, str(md_path))

    blocks = markdown_to_blocks(markdown_text)
    page_url = create_notion_page(api_key, database_id, title, iso_date, blocks)

    print(f"Created Notion page: {title} ({iso_date})")
    if page_url:
        print(page_url)


if __name__ == "__main__":
    main()
