---
name: update-second-brain
description: Update the user's Second Brain (vault rules, sync script, quiz page, skills) to the latest Purrsist (second-brain-kit) release, keeping their notes, scores and history. Use for /update-second-brain or "update my second brain".
---

# Update Second Brain

Confirm each step in one short line. Never touch notes, `## My notes`, `raw/`, scores or history.

1. **Latest kit:** `git pull` in the user's clone of https://github.com/smir22/purrsist (ask where it is; if none, clone it to a scratch folder). The new version is `const VERSION` in `quiz/quiz.html`.
2. **Vault + installed version:** find the vault (ask if unknown; request folder access). Installed version = `.sync/kit_version`. Missing → ask the user for the version under **Settings → About** on their quiz page (no Settings tab = 1.0). Same as the new version → say "Already up to date" and stop.
3. **What's new:** read the `CHANGELOG.md` entries newer than the installed version. Tell the user in at most 3 bullets. Collect every **Update needs:** line from those entries.
4. **Sync script:** copy `template/.sync/sync.py` and `test_sync.py` over the vault's. Never touch `config.json`, `processed.txt`, `calendar.txt` or `bank_hash.json`. Run `python3 .sync/test_sync.py` in the vault; it must print `ok`.
5. **Rules:** merge the kit's `template/CLAUDE.md` into the vault's `CLAUDE.md`: add new or changed sections, keep the user's name, strictness, standing context and anything they added. Show a short list of changes, then save.
6. **Quiz page:** publish the kit's `quiz/quiz.html` to the user's **existing** quiz page URL (in `.sync/config.json`), passing it as `url` so the link, questions and history stay, with the capabilities from `SETUP_PROMPT.md` step 4.
7. **One-time steps:** run each collected **Update needs:** step, oldest version first (for example `write lessons`). Say how many pages each touched.
8. **Sync task:** only if an entry says the sync task prompt changed, update the scheduled task's prompt from `SETUP_PROMPT.md` step 6, keeping the vault folder, quiz URL and calendar choice.
9. **Skills:** if `skills/ingest/SKILL.md` or this skill changed, propose them as updates to the user's `ingest` and `update-second-brain` skills (fill in the vault path).
10. **Finish:** run "Publish banks for Practice" from `CLAUDE.md`, write the new version to `.sync/kit_version`, and report: old → new version plus what changed in 3 bullets.
