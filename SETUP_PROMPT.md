# Setup prompt

Paste everything below the line into a new **Claude Cowork** task that is linked to your computer.

---

Set up the Second Brain Kit for me from https://github.com/smir22/second-brain-kit. Work step by step, confirm each step in one short line, and keep explanations brief.

**1. Ask me first (one form):**
- My name
- Where the vault should live (default: `~/Documents/Second Brain`)
- Marking strictness: lenient / balanced / strict (default balanced)
- Time for the daily quiz reminder (default 08:00, e.g. my commute)
- Sync times (default 09:52 and 21:52)
- Calendar reminders via Google Calendar? (yes / no — if yes and the connector isn't connected, suggest it)

**2. Obsidian:** check on my computer whether Obsidian is installed (macOS: `/Applications/Obsidian.app`). If not, offer to install it (`brew install --cask obsidian` if Homebrew exists, otherwise send me to https://obsidian.md/download) and wait for me.

**3. Vault:** get the kit (git clone, or download the repo ZIP), then copy the `template/` folder, including hidden `.sync/` and `.obsidian/`, to my vault location. Request access to that folder if you need it. In the copied files replace `[Your name]` with my name and `[STRICTNESS]` with my choice. Never overwrite an existing folder: if it exists, ask me.

**4. Quiz page:** read `quiz/quiz.html` from the kit and publish it with the Artifact tool as a new artifact: capabilities `{"db": {}, "sample": {}}`, icon `quiz`. Then:
- put its URL in place of `[QUIZ_URL]` in `CLAUDE.md`, `Home.md` and `.sync/config.json`
- set `reminder_start` / `reminder_end` (15 min) in `.sync/config.json` to my reminder time
- pin the artifact to my sidebar

**5. Check:** run `python3 .sync/test_sync.py` in the vault. It must print `ok`.

**6. Sync task:** create a scheduled task named "Second Brain quiz sync" that needs my computer, runs at my sync times in my time zone, and attaches my vault folder. Use this prompt, with my vault folder name and quiz URL filled in:

> Quiz sync for my Obsidian vault. In device_bash, cd into the vault first: `cd "$HOME/mnt/<VAULT FOLDER NAME>"` (run `ls $HOME/mnt` if that fails). Follow these steps exactly and do nothing else:
> 1. Load ArtifactData via ToolSearch. List collections `questions` and `answers` on <QUIZ URL>.
> 2. Write {"questions": [rows], "answers": [rows]} to .sync/inbox.json, rows exactly as listed (id, data, version).
> 3. Run: python3 .sync/sync.py . .sync/inbox.json
> 4. For each array in the output's "batches": one ArtifactData batch call with those writes, unchanged.
> 5. If "calendar" is not null: create a Google Calendar event (my time zone) using its title, date, start, end and description.
> 6. If "summary" is empty, nothing was loaded and "waiting_topics" is 0: reply "Nothing due" and stop. Otherwise reply with the summary as short bullets, plus any needs_bank / refresh_bank pages.
> Never run git. Never edit vault files yourself — sync.py does all vault changes. If a step fails, report the error in one line and stop.

Tell me I can switch the task's model to Haiku in its settings once one run has worked (it only moves JSON around).

**7. Ingest skill:** propose `skills/ingest/SKILL.md` from the kit as a new skill named `ingest` (replace the vault path in it with mine) so I can type `/ingest`.

**8. Optional extras — offer each in one line, set up the ones I pick:**
- Obsidian Git plugin for automatic backups (keep the repo private)
- Anki export for pure facts
- Weekly plan around my schedule (`plan week`)
- Apple Reminders / calendar blocks for study sessions

**9. First run:** ask me for one thing I learned recently and run `/ingest` on it, so my first quiz is ready tomorrow. Then show me the "Using it" section of the kit's README in 5 bullets.
