# Update prompt

Already set up and want the latest version? Paste everything below the line into a new **Claude Cowork** task linked to your computer. Your notes, scores and history are kept.

---

Update my Second Brain to the latest https://github.com/smir22/second-brain-kit. Work step by step and confirm each step in one line.

1. **Get the latest kit:** `git pull` in my clone of the kit (or clone it fresh / download the ZIP). Read `CHANGELOG.md` and tell me in 3 bullets what's new since my version (my quiz page shows its version under Settings → About; if it has no Settings tab I'm on v1.0–1.3).
2. **Find my vault:** ask me where it is if you don't know, and request folder access. My quiz page URL is in the vault's `.sync/config.json`.
3. **Sync script:** copy `template/.sync/sync.py` and `template/.sync/test_sync.py` over the ones in my vault's `.sync/`. Don't touch `config.json`, `processed.txt` or `bank_hash.json`. Run `python3 .sync/test_sync.py` in the vault; it must print `ok`.
4. **Rules:** compare the kit's `template/CLAUDE.md` with my vault's `CLAUDE.md`. Add new or changed sections, keep my name, strictness, standing context and anything I added myself. Show me a short list of what changed before saving.
5. **Quiz page:** read the kit's `quiz/quiz.html` and publish it to my **existing** quiz page URL (pass it as `url`, so the link, my questions and my history stay), with the capabilities from `SETUP_PROMPT.md` step 4.
6. **Sync task:** update my scheduled sync task's prompt to the one in `SETUP_PROMPT.md` step 6 (keep my vault folder name, quiz URL and calendar choice). If the task has no ID saved on the quiz page yet, do the "write the task's ID" step from `SETUP_PROMPT.md`.
7. **Lessons and code questions:** run the `lessons` operation from `CLAUDE.md` for every `review: true` page that has no `## Lesson` yet (batches of 5; read my source repos so lessons quote my real code). Also fix any question that mentions code I can't see: add the snippet as `code`, or make it general. Tell me how many pages you did.
8. **Practice bank:** run the "Publish banks for Practice" step from `CLAUDE.md` once, so Learn and Practice have my lessons and questions straight away.
9. **Ingest skill:** if `skills/ingest/SKILL.md` changed, propose it as an update to my `ingest` skill.
