---
name: internship-daily-log
description: Turns messy, unstructured daily notes (bullet points, stream-of-consciousness, half-finished sentences) written during an internship or job into a clean, structured markdown daily log that a mentor or manager can use to assess progress, and can push it straight into a Notion database. Use this skill whenever the user pastes in their raw notes from today (or any day) and asks for them to be written up, organized, turned into a report, or summarized for their mentor/manager — even if they don't use the word "skill" or explicitly ask for "markdown." Also trigger when the user asks to "pull my notes from Notion," "sync today's notes," or process notes from their Notion scratchpad page instead of pasting them directly. Trigger on phrases like "write up today's notes," "turn this into something for my mentor," "here's what I did today," "daily log," "EOD update," "standup notes," or similar end-of-day recap requests, especially when the raw text looks like informal jotted-down bullets rather than a finished report.
---

# Internship Daily Log

## Why this matters

A mentor reading a daily log wants to quickly understand what progress was made,
without wading through raw stream-of-consciousness notes, typos, or half sentences.
The job here is to take the user's rough notes for a day and turn them into a
faithful, well-organized write-up — not to invent accomplishments, embellish scope,
or drop anything the user actually did.

## Process

1. **Get the raw notes.** Usually the user pastes them directly into the
   conversation. But if they instead ask you to pull/sync notes from Notion
   (or `NOTION_SCRATCHPAD_PAGE_ID` is set in `.env` and they don't paste anything),
   fetch the notes first instead of asking them to copy-paste:

   ```bash
   python3 <skill-directory>/scripts/read_notion_page.py "$NOTION_SCRATCHPAD_PAGE_ID"
   ```

   This prints the scratchpad page's content as markdown-ish text — treat it
   exactly like pasted notes from here on. (The user overwrites that page
   daily, so this always reflects the current day's notes; they said they'll
   clear it themselves afterward, so don't try to erase it.)

2. **Read the raw notes carefully.** They will likely be informal: dashes, run-on
   sentences, no punctuation, references to tools/people/links. Identify distinct
   pieces of work rather than trying to map notes 1:1 to output bullets — a single
   rambling sentence might contain three separate activities worth splitting out,
   while several short lines might belong under one theme.

3. **Figure out the date.** If the user specifies a date, use it. If they say
   "today" or don't mention one, use the current date. If genuinely ambiguous
   (e.g. notes could be from an unspecified past day), ask.

4. **Write the structured markdown** using the template below. Only include a
   section if the notes actually contain relevant content for it — an empty
   "Blockers" or "Meetings" section is noise, not signal. Don't force content
   into a section that doesn't fit just to fill it out.

5. **Save the file** to `daily-reports/DD-MM-YYYY.md` relative to the current
   working directory (create the `daily-reports/` folder if it doesn't exist).
   If a file for that date already exists, ask the user whether to overwrite it
   or append/merge, rather than silently clobbering it.

6. **Push it to Notion, if configured.** If a `.env` file with `NOTION_API_KEY`
   and `NOTION_DATABASE_ID` exists (in the current directory or the skill's own
   directory), the user has already set up automatic syncing — don't ask them to
   copy-paste the markdown anywhere. Run:

   ```bash
   python3 <skill-directory>/scripts/push_to_notion.py daily-reports/DD-MM-YYYY.md
   ```

   This creates a new page in their Notion database with the Date property set
   and the log's headings/bullets/links converted to native Notion blocks. Tell
   the user the page was created and share the returned URL. If the script
   errors (bad credentials, database not shared with the integration, etc.),
   surface the error message to the user rather than silently giving up — it
   usually points directly at the fix (e.g. "share the database with your
   integration").

   If no `.env` is present, just mention once that this can be automated (see
   `scripts/push_to_notion.py` for setup) — don't nag about it every time.

## Output template

Use first-person, professional language (e.g. "I explored...", "I decided...",
"I met with...") — this reads as a real work log, not a third-person report or
a raw copy of the notes. Keep it concise and skimmable: short paragraphs or
bullet points, not walls of text.

```markdown
# [Weekday] [D/M/YYYY]

## Summary
One to three sentences giving the high-level takeaway of the day — what was
the main thread of work, and where things landed by end of day.

## Tasks Worked On
What was actually done, in first person. Group related bullets together rather
than listing every raw note line separately.

## Research & Learning
Anything investigated, read, watched, or explored to inform decisions — tools
tried, articles/videos consulted, approaches compared. Include *why* something
was explored if the notes make that clear (e.g. comparing two tools' tradeoffs).

## Decisions Made
Concrete choices or conclusions reached, and briefly why. Skip this section if
the day was pure exploration with no decision yet.

## Meetings
Only include if the notes mention a meeting or conversation with someone.
Note who was involved, what was discussed, and any outcomes (decisions,
deadlines, next steps agreed upon).

## Blockers & Challenges
Only include if something got in the way or is still unresolved.

## Next Steps
What comes next, if the notes mention it (deadlines, planned next actions).
Omit if the notes don't point to anything specific.
```

## Things to avoid

- **Don't fabricate details.** If the notes don't mention an outcome, timeline,
  or decision, don't invent one to make a section feel more complete.
- **Don't just reformat the raw bullets with headers slapped on.** The value
  add is organizing scattered thoughts into a coherent narrative a reader who
  wasn't there can follow — connect the dots between related notes (e.g. "tried
  X, then Y, which led me to decide Z").
- **Don't editorialize or add opinions/praise** ("did an amazing job") that
  aren't the user's own conclusions from their notes.
- **Preserve technical specifics** (tool names, links, component names, dates,
  people's names) exactly as given — these matter for a technical reviewer.
