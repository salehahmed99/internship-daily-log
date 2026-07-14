#!/usr/bin/env python3
"""
Fetch the text content of a Notion page (e.g. a scratchpad page the user
overwrites daily with messy notes) and print it as lightweight markdown.

Why this exists: the user's workflow is to type raw daily notes into a single
Notion page that they overwrite every day, instead of pasting them into a
chat. This script pulls that page's content out via the Notion API so it can
be fed straight into the internship-daily-log skill's normal structuring
process, exactly as if the user had pasted the text themselves.

Usage:
    python3 read_notion_page.py <page-id-or-full-notion-url>

Requires a .env file (in the current directory, or pointed to via --env-file)
containing NOTION_API_KEY (same integration secret used by push_to_notion.py).
The integration must also be shared/connected to this specific page in
Notion (Page -> ••• -> Connections -> Add connection), the same way it was
connected to the daily-logs database.
"""

import argparse
import os
import re
import sys
from pathlib import Path

import requests

NOTION_VERSION = "2022-06-28"
NOTION_API_BASE = "https://api.notion.com/v1"


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
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def get_api_key(env_file: str | None) -> str:
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
    if not api_key:
        sys.exit(
            "Missing NOTION_API_KEY. Set it as an environment variable or in a "
            f".env file (checked: {', '.join(str(c) for c in candidates)})."
        )
    return api_key


PAGE_ID_RE = re.compile(r"([0-9a-fA-F]{32})")
DASHED_ID_RE = re.compile(
    r"([0-9a-fA-F]{8})([0-9a-fA-F]{4})([0-9a-fA-F]{4})([0-9a-fA-F]{4})([0-9a-fA-F]{12})"
)


def extract_page_id(page_id_or_url: str) -> str:
    """
    Accept either a raw page ID, a dashed UUID, or a full Notion URL (the ID is
    the last 32-char hex run before any query string) and normalize to the
    dashed UUID format the API expects.
    """
    match = PAGE_ID_RE.search(page_id_or_url.replace("-", ""))
    if not match:
        sys.exit(f"Could not find a valid Notion page ID in: {page_id_or_url}")
    raw_id = match.group(1)
    dashed = DASHED_ID_RE.sub(r"\1-\2-\3-\4-\5", raw_id)
    return dashed


def rich_text_to_plain(rich_text: list[dict]) -> str:
    return "".join(part.get("plain_text", "") for part in rich_text)


def fetch_children(block_id: str, headers: dict) -> list[dict]:
    """Fetch all children of a block, following pagination cursors."""
    children = []
    cursor = None
    while True:
        params = {"page_size": 100}
        if cursor:
            params["start_cursor"] = cursor
        resp = requests.get(
            f"{NOTION_API_BASE}/blocks/{block_id}/children",
            headers=headers,
            params=params,
            timeout=30,
        )
        if resp.status_code >= 300:
            sys.exit(f"Notion API error ({resp.status_code}): {resp.text}")
        data = resp.json()
        children.extend(data.get("results", []))
        if data.get("has_more"):
            cursor = data.get("next_cursor")
        else:
            break
    return children


def blocks_to_markdown(blocks: list[dict], headers: dict, indent: int = 0) -> list[str]:
    """
    Recursively walk Notion blocks and render them as markdown-ish text lines,
    preserving nesting depth via indentation so multi-level bullet notes
    (common in a messy scratchpad) don't get flattened and lose structure.
    """
    lines = []
    prefix = "  " * indent
    for block in blocks:
        block_type = block.get("type")
        content = block.get(block_type, {})
        text = rich_text_to_plain(content.get("rich_text", [])) if isinstance(content, dict) else ""

        if block_type == "heading_1":
            lines.append(f"{prefix}# {text}")
        elif block_type == "heading_2":
            lines.append(f"{prefix}## {text}")
        elif block_type == "heading_3":
            lines.append(f"{prefix}### {text}")
        elif block_type in ("bulleted_list_item", "numbered_list_item"):
            lines.append(f"{prefix}- {text}")
        elif block_type == "to_do":
            checked = "x" if content.get("checked") else " "
            lines.append(f"{prefix}- [{checked}] {text}")
        elif block_type == "quote":
            lines.append(f"{prefix}> {text}")
        elif block_type == "code":
            lines.append(f"{prefix}```\n{text}\n{prefix}```")
        elif block_type == "paragraph":
            if text.strip():
                lines.append(f"{prefix}{text}")
        else:
            # Fall back to plain text for any block type not explicitly handled
            # (callouts, toggles, dividers, etc.) rather than silently dropping it.
            if text.strip():
                lines.append(f"{prefix}{text}")

        if block.get("has_children"):
            nested = fetch_children(block["id"], headers)
            lines.extend(blocks_to_markdown(nested, headers, indent + 1))

    return lines


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("page", help="Notion page ID or full page URL")
    parser.add_argument("--env-file", help="Path to .env file (default: ./.env)")
    args = parser.parse_args()

    api_key = get_api_key(args.env_file)
    page_id = extract_page_id(args.page)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Notion-Version": NOTION_VERSION,
    }

    blocks = fetch_children(page_id, headers)
    lines = blocks_to_markdown(blocks, headers)

    if not lines:
        sys.exit(
            "No content found on that page. Either it's empty, or the integration "
            "hasn't been connected to it yet (Page -> ••• -> Connections -> Add connection)."
        )

    print("\n".join(lines))


if __name__ == "__main__":
    main()
