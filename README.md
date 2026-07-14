# daily-log

Claude Code skill that turns rough daily notes into structured markdown logs and syncs them to Notion.

## What it does

You paste in (or pull from Notion) your messy, unstructured daily notes — bullet points, half-finished sentences, stream-of-consciousness — and it produces a clean, structured markdown report organized into sections like Summary, Tasks Worked On, Research & Learning, Decisions Made, and Next Steps. The output is saved locally as a markdown file and optionally pushed to a Notion database.

## How to use it

1. **Paste your notes** into Claude Code and ask for a write-up:
   - "here's what I did today"
   - "write up today's notes"
   - "daily log"
   - "EOD update"

2. **Or pull from Notion** if you keep a scratchpad page:
   - "sync today's notes"
   - "pull my notes from Notion"

The skill saves the structured log to `daily-reports/DD-MM-YYYY.md`.

## Notion integration (optional)

To enable automatic syncing to a Notion database:

1. Create a [Notion internal integration](https://www.notion.so/my-integrations) and copy the secret.
2. Create a database in Notion with at least a **Name** (title) and **Date** (date) property.
3. Share the database with your integration (database page → `•••` → Connections → Add connection).
4. Copy `.env.example` to `.env` and fill in your values:

```env
NOTION_API_KEY=secret_xxx...
NOTION_DATABASE_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Scratchpad page (optional)

If you'd rather type your raw notes into a Notion page instead of pasting them into Claude Code:

1. Create a page in Notion for your daily scratchpad.
2. Share it with the same integration.
3. Add the page ID to `.env`:

```env
NOTION_SCRATCHPAD_PAGE_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Then just say "sync today's notes" and the skill will pull your notes from Notion, structure them, save the markdown, and push the result back to your database.

## Setup

1. Clone this repo into your project (or anywhere Claude Code can reach it).
2. Install the Python dependency:
   ```bash
   pip install requests
   ```
3. (Optional) Set up the `.env` file for Notion integration as described above.

## Project structure

```
.agents/skills/internship-daily-log/
├── SKILL.md              # Skill definition (instructions for Claude Code)
├── .env.example          # Template for Notion credentials
└── scripts/
    ├── push_to_notion.py     # Pushes a markdown log to a Notion database
    └── read_notion_page.py   # Pulls raw notes from a Notion scratchpad page
daily-reports/                # Generated markdown logs (DD-MM-YYYY.md)
```
