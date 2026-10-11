# Second Brain Kit

A learning system that stops you forgetting what you learn. Claude keeps your notes in Obsidian, quizzes you on your phone on a spaced-repetition schedule, and puts reminders in your calendar.

Built on Karpathy's "LLM wiki" idea and the CoderCo *Learn it so it sticks* method: recall first, explain it like you're teaching, review on days 1 · 3 · 7 · 14 · 31.

---

## How it works

```
learn something ──► /ingest (Mac, Claude Cowork)
                      • brain-dump what you remember
                      • Claude compares with the source → your gaps
                      • writes notes + 9 quiz questions into Obsidian
                              │
evening sync (auto) ──► loads tomorrow's questions onto your quiz page
                      • adds an 08:00 "Quiz: …" calendar event
                              │
commute (phone) ──► answer on the quiz page, Claude marks written answers
                              │
next sync (auto) ──► scores each topic, moves it up/down the ladder,
                     saves weak spots + log in Obsidian
```

**The ladder.** Pass → next step. Shaky → same step again. Fail → back to day 1.

| Step | 0 | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|---|
| Next review in | 1d | 3d | 7d | 14d | 31d | 60d | 120d |

---

## Setup (≈10 min)

**You need:** the Claude desktop app with Cowork, on a Mac (Windows untested), linked to your computer. Optional: the Google Calendar connector for reminders.

1. Open a new Cowork task linked to your computer.
2. Paste the prompt from [`SETUP_PROMPT.md`](SETUP_PROMPT.md).
3. Answer its questions. It installs Obsidian if needed, builds your vault, publishes your quiz page and schedules the sync.

---

## Using it

### After you learn something (Mac)
- In Cowork say **`/ingest`** (or "I just learned X").
- Dump everything you remember first. Messy is fine, voice is fine. Where you stall is your gap.
- Claude shows what you got right / wrong / missed, writes the notes, and asks one "teach it" question.
- Your first review is tomorrow.

### Quiz (phone)
- **Open it:** tap the link in the 08:00 calendar event, or the pinned page in the Claude app sidebar. Tip: open it in Safari (signed in to claude.ai) → Share → **Add to Home Screen** for one-tap access, like an app.
- **Multiple choice:** tap an answer.
- **Written answers:** type, or tap the keyboard mic and talk. Claude marks it and shows what you got, what's missing, the model answer and a tip.
- **First written answer:** the page asks permission to use Claude for marking. Allow it (it uses your normal Claude usage; multiple choice uses none).
- **Strictness:** Lenient / Balanced / Strict switch at the top.
- **Done screen:** shows where each topic moves on the ladder.
- Nothing to do? It says so. New questions load at the next sync.

### Notes (Mac, Obsidian)
- Open Obsidian → your vault. Each topic page shows its stage, next review date and **Weak spots**.
- Write your own thoughts under **My notes**. Claude never edits that section.
- `log.md` = history of everything that happened.

### Other things to say in Cowork
| Say | What happens |
|---|---|
| `quiz me` | Quiz in chat instead of the phone |
| `plan a build for X` / `build done` | Hands-on lab; at the end you explain your code line by line |
| `plan week` | Fits reviews and builds around your schedule |
| `anki export` | Facts (ports, flags, vocab) → file you import into Anki |
| `lint the wiki` | Monthly tidy: broken links, gaps, contradictions |

### Sync
Runs twice a day by itself. Your Mac needs to be on and awake at those times; if it's asleep, the next run catches up. Nothing is lost.

---

## Improving it with Claude

Open a Cowork task, connect your vault folder and say:
> Read CLAUDE.md in my vault. I want to change: …

`CLAUDE.md` holds every rule, so Claude has the full picture. `.sync/sync.py` is the scoring/scheduling logic, with a self-test (`python3 .sync/test_sync.py`) to run after any change.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Quiz page empty | Nothing due yet, or the sync hasn't run. Run the scheduled task manually from the Claude app. |
| Sync run says it can't find the vault | Add your vault folder in the scheduled task's settings. |
| No calendar event | Connect Google Calendar in Claude, or check the event isn't on a different calendar. |
| Marking feels harsh | Switch to Lenient on the quiz page. |

---

Credits: [Karpathy's LLM wiki idea](https://x.com/karpathy) · [obsidian-llm-brain](https://github.com/Husseinmalki/obsidian-llm-brain) · CoderCo *Learn it so it sticks*. MIT licence.
