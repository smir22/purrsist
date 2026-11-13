---
name: "write-quiz-questions"
description: "Write, rewrite or repair Second Brain / Purrsist quiz questions so they are clear, fair and repeatable. Use for question banks, rewrites, 'refresh banks', flagged or confusing questions, and inside ingest/import."
---

# Write quiz questions (Second Brain / Purrsist)

One job: produce multiple-choice questions a learner can answer on a phone in under 30 seconds, where a right answer proves they understand the idea and a wrong answer teaches them something. The vault's `CLAUDE.md` stays the source of truth for file formats (where the bank lives, sets, `alts`, publishing). This skill is the source of truth for question quality.

## When this runs
- New question bank for a page (ingest, import, capture).
- Rewrites (`alts`) when a sync reports `needs_variants`.
- "refresh banks", flagged questions, or the user says questions are unclear, weird or confusing.
- "lint questions" / "check my questions": run steps 4-5 only on the existing bank.

## 0. Scope before writing
1. Vault: `[VAULT_PATH]` (not connected → request folder access). Read the page first: intro bullets, `## Lesson`, `## Weak spots`, `## Flagged questions`.
2. Write one line per question BEFORE writing the question: the single idea it tests (this becomes `points[0]`). If two questions in a set have the same line, replace one. If you can't state the idea in one sentence, the question isn't ready.
3. Only test what the page's lesson teaches. If a good question needs a fact the lesson lacks, add it to the lesson first or drop the question.
4. Batch size: at most 5 pages per run. Say how many remain.

## 1. The shape of every question
```json
{"kind": "recall|apply|teach", "prompt": "...?", "code": "optional", "options": ["a", "b", "c", "d"], "correct": 0, "answer": "...", "points": ["core idea", "..."]}
```
- `prompt`: ONE question, ends in `?`, at most 200 characters, answerable without seeing the options (cover-the-options test: could a strong learner say the answer aloud first?).
- `options`: exactly 4, each at most 90 characters, same grammar and roughly the same length. The correct one must not be the longest. Vary the correct position across a set.
- `answer`: 1-3 sentences that say why the right option is right AND name the misconception behind the most tempting wrong one.
- `points`: 2-3 short key points; `points[0]` is the core idea from step 0.
- `code`: required whenever the prompt mentions the learner's own file, pipeline, config or repo. At most 10 lines, at most 40 characters wide. No snippet available: make the question general instead.

## 2. The three kinds
- **recall**: one fact, definition or behaviour. "What does X do when Y?" Not trivia (ports, paths, flag spellings, README steps go to Anki, not here).
- **apply**: a concrete situation with enough detail to decide: what is running, what was observed, what is being asked. Prod incident, design choice or interview question. Ask for one thing: the cause, the next step, or the best design. Never "what would you do?" with four equally sensible actions.
- **teach**: never an open "Explain X to a junior" prompt (those were the most-flagged questions). Use one of these two forms:
  - Misconception: `A junior says '<specific wrong belief>'. What's the best correction?`
  - Explanation pick: `Which explanation of <X> would be right for a junior?` with four explanations that differ in ONE claim each.

## 3. Distractors (where questions usually go wrong)
- Each wrong option is a real misconception or a near-miss that differs from the right answer in one key detail. Prefer the learner's own `## Weak spots`.
- Exactly one option is correct for a competent engineer. If a second option is defensible under a reasonable assumption, tighten the prompt or replace the option.
- No "all of the above", "none of the above", "both A and B", joke options, or options that only differ by a hedge word (always/never/usually).
- No give-aways: the right option must not be the only long one, the only one with a qualifier, or the only one repeating a keyword from the prompt.
- No negative prompts ("Which is NOT...", "...EXCEPT") and no "which of the following".

## 4. Self-review (run for every question, fix or drop)
1. **Cover test**: hide the options. Is the prompt still a complete question with one best answer?
2. **Expert test**: would two senior engineers pick the same option without arguing? If not, it's ambiguous.
3. **Skim test**: can the correct option be guessed from length, wording or grammar alone?
4. **Lesson test**: is the tested idea taught in the page's lesson?
5. **Answer test**: does `answer` agree with `options[correct]` and with the page? Re-check the index after any reordering.
6. **Phone test**: prompt plus options fit one phone screen; code is at most 40 characters wide.

## 5. Machine check (always, before finishing)
In the vault folder:
- `python3 .sync/sync.py . --lint` lists questions with detectable problems (not a question, open 'Explain' prompt, own code without a snippet, give-away or over-long options, duplicates). Fix every line that points at a question you wrote or touched; report the count for the rest.
- `python3 .sync/sync.py . --check` must print `[]`.
- Then publish banks for Practice as the vault's `CLAUDE.md` describes.

## 6. Rewrites (`alts`)
- Same `kind` and same `points[0]`, but a new scenario or angle, new wording and four freshly written options. Never the old prompt with shuffled options, and never a harder topic smuggled in.
- A rewrite must pass sections 1-5 on its own.

## 7. Repairing flagged or linted questions
- Fix in place: keep the tested idea, change the wording. Map the flag to the fix:
  - *Question unclear* -> restate as one concrete question; add the missing context to the prompt.
  - *Answers unclear* -> rewrite all four options to the same shape; make sure only one is defensible.
  - *Wrong answer* -> verify against the page and source before changing `correct`; if the page is wrong, fix the page and say so.
  - *Needs code* -> add `code`, or make the question general.
  - *Too easy* -> move from recall to apply, or make distractors closer.
- Check that question's `alts` for the same fault. Remove the handled line from `## Flagged questions`.

## 8. Report (3 lines)
- Pages and questions written or fixed.
- Lint: problems before -> after.
- Anything dropped or left for the user to decide (for example a page whose lesson is missing the fact).

## Examples
Bad (open prompt, flagged as unclear):
`Explain an MLflow run like you're teaching a junior.`

Good (teach, misconception form):
`A junior says 'an MLflow run is the trained model file'. What's the best correction?`
- `A run is one execution: its params, metrics and artifacts` (correct)
- `A run is the registered version that serving loads`
- `A run is the experiment that groups all attempts`
- `A run is the artifact store where files are kept`

Bad (own setup, no code): `Why does your CI also run on a weekly schedule?`
Good: add the `on: schedule:` lines in `code`, or ask generally: `Why would an ML test pipeline run weekly even with no commits?`