---
name: ingest
description: Ingest a topic or section the user just learned into their Second Brain vault: listen to their brain-dump (typed, dictated or voice), drill them on the gaps, then write notes and quiz questions. Use for /ingest, 'I just learned X', or 'ingest this'.
---

# Ingest into Second Brain

Flow: **listen → find gaps → drill the gaps → write notes + quizzes.** The vault's `CLAUDE.md` is the source of truth for formats.

## 0. Find the vault
- Vault: `[VAULT_PATH]`. Not connected → request folder access. Read `CLAUDE.md` §3–§6 before writing.

## Voice & dictation
- One question at a time, 1–2 spoken sentences each.
- Expect rambling and mis-transcribed terms ("cube cuttle" = kubectl, "terra form" = Terraform). Map them silently; never mark a transcription slip as wrong.
- Voice mode: plain short sentences, no tables or headers. "done" / "that's it" / a long pause ends a turn.

## 1. What was learned
Ask only what's missing: topic/section and source (pasted text, file, link, lesson, or from memory). Save pasted sources to `raw/`.

## 2. Listen: blank-page dump
- "Tell me everything you remember about X. Messy is fine."
- Don't show the source or takeaways first. Just listen. If they stop early, one nudge: "Anything on <sub-area>?"

## 3. Find the gaps
- Compare the dump with the source (or accurate knowledge).
- Short summary: what they nailed (1 line), then the gaps: wrong claims and missed key ideas. Max 5, most important first.

## 4. Drill the gaps (one at a time)
For each gap:
1. **Ask before telling:** a guiding question that points at the gap ("What happens to traffic when readiness fails?").
2. Got it → confirm in one line, next gap.
3. Stuck or wrong → teach it in 2–3 plain sentences with one concrete example (teach the concept, don't just hand over the answer).
4. **Say it back:** "Explain that back to me like I'm a junior." Mark it at the vault's strictness level.
5. Still shaky after one retry → move on; it's flagged for tomorrow.
Keep a tally: fixed vs still shaky.

## 5. Write notes + quizzes
- One page per concept, Title Case, right `wiki/` folder. Frontmatter: `review: true, stage: 0, next_review: <tomorrow>, last_result:, bank_set: 0`.
- Sections: concrete bullets, `## Weak spots` (every gap, dated; mark "(still shaky)" where it applies), `## My notes` (empty), `## Question bank`, `## Related` (≥1 link).
- Source summary in `wiki/sources/` if there was a source. Update the folder `_index.md`, append `log.md` (`## [date] ingest | <topic>`).
- Never touch `raw/`, pages with an `owner:` field, or `## My notes`.

**Question bank:** `## Question bank` + a ```json block, 3 sets of `[recall, apply, teach]`:
- every question: `{kind, prompt, options:[4], correct:<index>, answer, points}`. The quiz is tap-only by default, so all three kinds need options (vary the correct position); `answer`/`points` serve the optional written mode
- every question also has `alts`: 2 rewrites for later reviews (same `kind` and core idea, but a new scenario, wording and options; full question objects with no `alts` of their own). A review never repeats a question.
- Distractors: near-misses / common misconceptions that differ from the right answer in one key detail; same length and shape as the correct option (it must not be the longest — keep options short, detail goes in `answer`); none arguably correct
- Never ask about code the learner can't see ("in your serve.py…"). Either add a `code` field with the snippet (≤10 lines, ≤40 chars wide so it fits a phone) or make the question general. No trivia (ports, file paths, README steps)
- recall: key fact · apply: realistic prod / interview / design scenario · teach: "Explain X to a junior…" (as MCQ: which explanation is right)
- `points[0]` = core idea. **Set 1 targets the still-shaky gaps**, then the other gaps, then the rest. Then `python3 .sync/sync.py . --check` (in the vault) must print `[]`.
- Pure facts (ports, flags, vocab) → also `anki/new-cards.txt`.
- **Lesson:** also write the page's `## Lesson` for the Learn tab: 4–7 `### ` steps that teach the topic from zero (problem → idea → their real code line by line → gotchas from the weak spots → recap). Follow the vault `CLAUDE.md` **lessons** rules exactly.
- **Build it:** also write the page's `## Build it` exercises (an `order` exercise with trap lines and a Do / Don't `sort`) and include the lesson's `### Best practice` step. Follow the vault `CLAUDE.md` **build it** and **lessons** rules exactly.
- After writing, publish banks for Practice (see vault `CLAUDE.md`).

## 6. Wrap up (3 lines)
- Gaps: N fixed, N still shaky
- Pages written
- First quiz tomorrow on the phone (evening sync loads it + calendar reminder)
