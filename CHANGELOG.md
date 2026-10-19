# Changelog

The quiz page shows its version under **Settings → About**. To update an existing setup, type `/update-second-brain` in Cowork (or paste [`UPDATE_PROMPT.md`](UPDATE_PROMPT.md) if you set up before v1.14).

## 1.19.0
- **Topics by step:** Progress → Mastery now lists every topic with its current gap (1d, 3d, 7d …). Tap a step to filter; tap a topic to open its lesson.
- Update needs: nothing extra.

## 1.18.0
- **Never the same question twice:** every question has 2 rewrites (same idea, new scenario and options). Each time you see a version (Quiz, Practice or Learn) the next one takes over, and the nightly sync writes a replacement (max 10 a night).
- **Skip** (Quiz: to the back of the queue, once per question; Practice: no XP change) and **Learn first** (read the lesson, then answer; that topic comes back tomorrow).
- **Flag** takes several reasons (new: "Answers unclear") and skips the question; flagged questions aren't scored.
- Default theme is now **Match phone**: GitHub Light by day, GitHub Dark at night. A theme you already picked stays.
- Update needs: say **write rewrites** in a vault session (adds 2 rewrites to every existing question; `python3 .sync/sync.py . --check` must print `[]`). The sync task prompt changed: update it from `SETUP_PROMPT.md` step 6 (new rewrites step).

## 1.17.0
- The app is now called **Purrsist**, and the repo moved to github.com/smir22/purrsist (the old second-brain-kit link redirects). All screenshots retaken.
- Update needs: nothing extra.

## 1.16.0
- **The cat:** a text-art cat under the title shows your status and reacts to each answer in Quiz, Learn and Practice (right, nearly, wrong, combo, timeout, cleared), with a big pop-up on level-up.
- Update needs: nothing extra.

## 1.15.1
- Full command list in the README and in `Home.md` (adds `/ingest`, `write lessons`, `refresh banks`, `publish banks for practice`, `sync quiz`, `/update-second-brain`).
- Update needs: replace the "Say to Claude" list in your `Home.md` with the one in `template/Home.md`.

## 1.15.0
- **Flag a question:** a small ⚑ Flag on every question (Quiz, Practice, Learn): wrong answer / unclear / needs code / too easy. The sync logs it on the topic's page under `## Flagged questions`, and **refresh banks** fixes flagged questions first.
- **Works with bad signal:** answers, XP and flags are saved on your phone when there's no signal and sent automatically when it's back ("N answers saved on this phone" shows meanwhile). Open the quiz once before you lose signal.
- Inline `code` in questions and options now renders as code.
- Update needs: nothing extra (the update copies the new sync script and merges the refresh banks rule).

## 1.14.0
- **`/update-second-brain` skill:** updating is one command. It reads your installed version (`.sync/kit_version`), shows what's new, and runs only the one-time steps you missed.
- Each version below lists its **Update needs:** (one-time steps the update runs for you).
- Update needs: nothing extra (the update installs the new skill).

## 1.13.0
- **Real lessons in Learn:** each topic gets a step-by-step `## Lesson` (problem → idea → your code line by line → gotchas → recap), 4–7 phone screens with Next/Back. New `lessons` operation in `CLAUDE.md`; `/ingest` and `import` write one for every new topic. Say **write lessons** to backfill an older vault.
- Buttons in a row are now the same size.
- Long inline code wraps instead of widening the page.
- Update needs: run `write lessons` for every `review: true` page without a `## Lesson`, then publish banks.

## 1.12.0
- Lesson renderer: steps, code blocks, lists, bold and inline code (safe, no HTML).

## 1.11.0
- **Learn tab:** weak topics get a short lesson (summary, key points, your weak spots) built from the vault at sync, then 2 right in a row to clear. **Learn this** button after any miss in Quiz or Practice. Never moves the ladder.
- sync.py ships lessons with the question bank and treats Learn answers like Practice.

## 1.10.0
- Update needs: fix questions that mention code you can't see (add the snippet as `code`, or make them general), then publish banks.
- Questions can carry a `code` snippet, shown under the question. Rule: never ask about code you can't see; add the snippet or make the question general. No trivia (ports, paths).
- Screenshots updated.

## 1.9.0
- Hard mode shows a live countdown (seconds + shrinking bar, red under 5 s).
- Ingest/question-bank rules: wrong options are near-misses, same length as the right one, so the answer can't be guessed by shape. Re-run **refresh banks** on old pages to get harder options.

## 1.8.1
- Hard mode: no recall step; 15 s per question, 10 s after 5 right in a row.

## 1.8.0
- **Hard mode made harder:** recall first (options hidden until you tap), then a 10-second timer to pick; weak topics and previously missed questions weighted much more; a miss or timeout costs full XP; combo bonus starts at 3 in a row.
- Answer options are shuffled every time in Quiz and Practice.

## 1.7.0
- **Practice reworked:** one question at a time with swap animation, a green glow and floating XP when right, a shake when wrong.
- **Hard mode:** full XP plus combo bonus when right, lose XP when wrong.
- **Your icon:** pick one in Settings; shown with your level.

## 1.6.0
- **Practice tab:** endless scroll of questions from your whole bank, weighted towards weaker topics, with a topic filter. Half XP, keeps your streak, misses become weak spots; never moves topics on the ladder.
- Sync publishes question banks to the quiz page (only changed parts) and saves practice misses into the vault.
- Settings → About shows the version. New `UPDATE_PROMPT.md` for existing users.

## 1.5.0
- **Settings tab** with 12 themes (Dracula, Dracula Light, Match phone, Light, Dark, One Dark Pro, GitHub Dark/Light, Tokyo Night, Catppuccin Mocha, Nord, Solarized Light).

## 1.4.0
- **Progress tab:** streak with weekly freeze, XP and levels, activity heatmap, mastery by ladder step, Sync now button.
- Sync runs once a night (default 20:52) instead of twice a day.

## 1.3.0
- Import, capture and refresh-banks operations; README screenshots; setup runs a test sync.

## 1.2.0
- Tap answers by default (written answers optional), Dracula theme, strictness setting.

## 1.0.0
- First release: Obsidian vault, phone quiz, spaced-repetition ladder, nightly sync script, calendar reminders, `/ingest`.
