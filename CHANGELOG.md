# Changelog

The quiz page shows its version under **Settings → About**. To update an existing setup, use [`UPDATE_PROMPT.md`](UPDATE_PROMPT.md).

## 1.10.0
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
