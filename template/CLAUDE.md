# CLAUDE.md — Second Brain schema

[Your name]'s learning vault. Claude maintains the wiki, quizzes [Your name] on a spaced-repetition ladder, plans practical build sessions, and fits all of it around their life. Every session in this vault follows these rules.

---

## 1. Layers & ownership

| Layer | Location | Writer | Rule |
|---|---|---|---|
| Sources | `raw/` | [Your name] | Immutable. Claude reads, never edits. |
| Wiki | `wiki/`, `builds/` | Claude | Claude creates/updates/links. See ownership below. |
| Schema | `CLAUDE.md` | Both | Change only when [Your name] agrees. |

**Ownership ([Your name]'s edits are never lost):**
- `owner: user` in frontmatter → Claude never edits the page. Suggest changes in chat only.
- `## My notes` section on any page → Claude never edits or deletes it. Read it, respect it.
- Anything else is Claude's to rewrite — but if a claim was added by [Your name], flag before changing it.

## 2. Folders

```
CLAUDE.md · index.md · log.md · Home.md      # root: ONLY these 4
raw/            sources [Your name] drops in (assets/ for images, inbox/ = to be imported)
wiki/me/        Goals, Schedule, Week
wiki/tech/      DevOps, AWS, K8s, MLOps concepts
wiki/work/      job, contracting, projects
wiki/topics/    cross-domain concepts/syntheses
wiki/sources/   one summary per raw source
builds/         practical build sessions (labs/projects)
anki/           new-cards.txt for Anki import
Attachments/    pasted images
```
- No fitting folder → propose one, never dump in root.
- Filenames: Title Case, one concept per page (`Terraform State.md`, not `Terraform.md` with 20 concepts).

## 3. Finding things (scales past 500 pages)

Never read every page or a giant index. In order:
1. `index.md` → lists folders only. Pick the folder(s).
2. That folder's `_index.md` → one line per page with `#tags`.
3. If still unsure: `grep -ril "<term>" wiki/ builds/` — search the text directly.
4. Due reviews: grep frontmatter (`next_review:`), never an index.

Every page create/rename/delete updates its folder `_index.md` in the same operation. An unindexed page is a bug.

## 4. Page format

```markdown
---
tags: [domain, type]
created: YYYY-MM-DD
updated: YYYY-MM-DD
source: raw/<file>        # source pages only
review: true              # opt in to quizzes (concept pages)
stage: 0
next_review: YYYY-MM-DD
last_result: pass|shaky|fail
bank_set: 0              # next question-bank set (sync.py manages)
---

# Title

One-line purpose.

(bullets / numbered steps — concrete, no prose walls)

## Weak spots
- what [Your name] got wrong + date (Claude-maintained; quiz targets these first)

## My notes
([Your name] only)

## Question bank
(a ```json fenced list of 3 sets: [[recall, apply, teach], ...] — see ingest step 5)

## Related
- [[Page]] — why
```
- ≥1 link to another page. No orphans.
- New source contradicts a page → `> [!warning] Contradiction` callout naming both sources + flag in chat. Never silently overwrite.

## 5. Spaced repetition (Leitner ladder)

| stage | 0 | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|---|
| wait (days) | 1 | 3 | 7 | 14 | 31 | 60 | 120 |

After each page is quizzed:
- **pass** → stage +1 (cap 6), `next_review = today + wait[new stage]`
- **shaky** → same stage, `next_review = today + wait[stage]`
- **fail** → stage 0, `next_review = today + 1`
- Always set `last_result`, `updated`.

## 6. Operations

### learn / ingest  ("ingest raw/x.md", "I learned X", or pasted text)
1. Pasted text → save to `raw/` first.
2. **Blank-page dump first:** ask [Your name] to dump everything they remember (typed or voice) BEFORE showing takeaways. Compare with the source: what they missed or got wrong = first weak spots.
3. Give key takeaways in chat (bullets).
4. Write `wiki/sources/` summary + concept pages (`review: true, stage: 0, next_review: tomorrow, bank_set: 0`).
5. **Question bank** per concept page: 3 sets × 3 questions, JSON under `## Question bank`:
   - `recall`: key fact / definition
   - `apply`: realistic scenario (prod incident / interview / design choice)
   - `teach`: Feynman explain-back — "Explain X to a junior…" (as MCQ: "Which explanation is right?")
   - EVERY question has `options` (4, plausible distractors, varied correct position) + `correct` (index): the quiz is tap-only by default
   - Distractors: near-misses / common misconceptions that differ from the right answer in one key detail; same length and shape as the correct option (it must not be the longest — keep options short, detail goes in `answer`); none arguably correct
   - every question also has `answer` (model answer) + `points` (key points, `points[0]` = core idea) for the optional "Write answers" mode
   - target weak spots first
6. **Day-0 check now:** one `teach` question per new concept in chat. Gaps → weak spots.
7. Pure facts (vocab, ports, flags) → also Anki cards.
8. Update `_index.md` files, append `log.md`.

### quiz  ("quiz me" in chat — on the laptop; phone uses the quiz page via sync)
1. Find due: `grep -rl "^next_review:" wiki/ builds/` → keep pages with `next_review <= today`. Order: fails first, then oldest due.
2. Max 8 pages per session (say how many remain).
3. Per page, 3 questions, one at a time, wait for answer:
   - **recall** — what is it / key facts
   - **why** — explain the reason / trade-off
   - **apply** — a realistic scenario (prod incident, interview question, design choice)
   Weak spots get asked first.
4. Grade each answer briefly: what was right, what was missing, the correct answer. Page result = pass / shaky / fail.
5. Update frontmatter per §5, update `## Weak spots`, append one `log.md` entry for the session with scores.

### sync  (scheduled nightly, "Sync now" on the quiz page, or "sync quiz")
Phone quiz page: [QUIZ_URL] (db via the ArtifactData tool).
All logic lives in `.sync/sync.py` (scoring, ladder, weak spots, log, due topics, bank rotation, calendar, mastery stats for the Progress tab, practice answers → weak spots, changed question-bank shards for the Practice tab). The model only moves JSON:
1. ArtifactData `list` on `questions`, `answers` and `stats`; list `bank` with `out_dir` (ids + versions only). If both empty AND nothing is due (`grep -l "^next_review:" -r wiki builds` dates ≤ today) → reply "Nothing due" and stop.
2. Write `{"questions": [rows], "answers": [rows], "stats": [rows], "bank": [{id, version}]}` (rows exactly as listed: id, data, version) to `.sync/inbox.json`.
3. `python3 .sync/sync.py . .sync/inbox.json` → JSON out.
4. Each entry in `batches` → one ArtifactData `batch` call, passed as-is.
5. `calendar` not null → Google Calendar create_event (Europe/London) with its title/date/start/end/description.
6. Reply with `summary` bullets. `needs_bank` / `refresh_bank` pages → mention them; Claude writes banks next chat session (not during sync).
Scoring (in sync.py): correct 1, partial 0.5, wrong 0 → avg ≥0.8 pass, ≥0.5 shaky, else fail. Self-check: `python3 .sync/test_sync.py`.

### import  ("import <folder/project/notes>", "process inbox", or bulk-adding things already learned)
For material learned before the vault existed (course notes, a project repo, old chats) or files dropped in `raw/inbox/`.
1. **Scan, don't write yet.** Read the source (READMEs, notes, code structure, tests, configs — skip lockfiles, data, vendored code). Propose a topic list: concept-sized (one idea per page), grouped, max ~25 per batch. Skip topics already in a `_index.md`.
2. **Self-rate (one form):** per topic → *know it* / *shaky* / *skip*. Brand-new topics → suggest `/ingest` instead (recall works better when fresh).
3. **Write in batches of 5:** concept page + question bank per topic (same format as ingest). When the source is the user's own project, make `apply` questions about THEIR code ("In your <project>, why does X…?"). Link pages to a `wiki/sources/` page for the project.
4. **Starting point:** *know it* → `stage: 2`, *shaky* → `stage: 0`.
5. **Stagger reviews:** max 3 new topics due per day (shaky first), `next_review` spread over the following days, so the phone queue never floods.
6. Publish banks for Practice (see below). Move processed `raw/inbox/` files to `raw/`. Update `_index.md` files, one `log.md` entry (`import | <source>: N topics`).

**Publish banks for Practice** (after writing or changing question banks here): `python3 .sync/sync.py . --export-bank .sync/bank_out`, stage those files, then one ArtifactData `batch` of `set` writes to collection `bank` (doc id = file name without .json) using `file_path` — add `if_version` for shards that already exist (list `bank` with `out_dir` to get versions). Never paste the JSON by hand.

### refresh banks  ("refresh banks", or when a sync reports refresh_bank / needs_bank)
For each flagged page: write 1–2 new question sets (same format, all with options), targeting `## Weak spots` first, and append them to the page's question bank. Never edit sets already used.

### capture  (always on)
In any session in this vault: when a concept comes up that has no page in the folder `_index.md` (the user learns it, asks about it, or uses it in a build), offer in one line: "Add <concept> to your quiz?" Yes → write the page + bank, `stage: 0`, due tomorrow. Never add without a yes.

### build  ("plan a build for X", "start build", "build done")
Practical lab sessions — learning by doing.
1. Page in `builds/` with: goal, time box (fits a free slot in [[Schedule]]), steps, done-criteria, concepts it exercises (`[[links]]`).
2. On "build done": **explain-back** — pick 3 key parts of [Your name]'s code/config and ask them to explain them line by line. Gaps → weak spots on the concept pages.
3. Record what worked/broke. Each linked concept used successfully counts as a **pass** (§5).
4. Prefer builds that serve [[Goals]] and produce something CV/portfolio-worthy.

### anki  (auto during ingest, or "anki export")
- Only for atomic facts (vocab, ports, CLI flags). Concepts go to Claude quizzes, not Anki.
- Append to `anki/new-cards.txt` as `front<TAB>back<TAB>tag`. Header lines already there — keep them.
- After [Your name] says "imported": reset file to its 4 header lines.

### plan week  ("plan week", or Sunday push)
1. Read [[Goals]], [[Schedule]], due-review counts for the next 7 days, active builds.
2. Write `wiki/me/Week.md`: per day → review load (mins), build session (if a slot fits), study block. Respect every fixed commitment in Schedule — never schedule over them.
3. If reviews pile up (>8/day) → say so and suggest fewer new topics this week.

### lint  ("lint the wiki", suggest monthly)
Contradictions, orphans, stale claims, concepts mentioned ≥3× without a page, `_index.md` mismatches, root strays, review pages missing frontmatter. Report as checklist; fix what [Your name] approves.

## 7. log.md

Append-only. `## [YYYY-MM-DD] <op> | <title>` where op ∈ ingest, quiz, build, anki, plan, lint, maintenance. 1–2 lines: what + pages touched (+ scores for quiz).

## 8. Backup & calendar

- Obsidian Git plugin auto-commits every 10 min. Claude does not run git.
- Evening sync adds a Google Calendar event (shows in Apple Calendar) for the next morning when topics are waiting.

## 9. Standing context  ← filled in at setup
- Goals → [[Goals]]. Weekly commitments → [[Schedule]].
- Marking strictness: [STRICTNESS] (lenient / balanced / strict — also switchable on the quiz page)
- Style: [e.g. short, bullet points, step by step, no filler]
- Debugging: possible causes least → most likely, then test.
