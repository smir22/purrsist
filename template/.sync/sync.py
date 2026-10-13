#!/usr/bin/env python3
"""Second Brain quiz sync: all vault logic, zero AI tokens.

Claude only moves JSON between the quiz page's db and this script:
  python3 sync.py <vault_dir> <inbox.json> [--now 2026-10-11T21:52]
inbox.json = {"questions": [rows], "answers": [rows]}   (rows exactly as ArtifactData `list` returns: {"id","data","version"})
Add --push-bank to resend every question-bank shard (after a failed run).
Prints JSON: {"batches": [[ArtifactData batch writes <=50]], "calendar": {...}|null, "summary": [...], "needs_bank": [...], "refresh_bank": [...]}
"""
import datetime as dt
import hashlib
import json
import zlib
import re
import sys
from pathlib import Path

WAIT = [1, 3, 7, 14, 31, 60, 120]          # days per ladder stage
SCORE = {"correct": 1.0, "partial": 0.5, "wrong": 0.0}
MAX_TOPICS = 8                             # topics waiting on the quiz page at once
BANK_SHARDS = 8                            # question banks published to the quiz page for Practice, split by page hash
CONFIG = {"quiz_url": "", "reminder_start": "08:00", "reminder_end": "08:15"}   # overridden by .sync/config.json
FM = re.compile(r"\A---\n(.*?)\n---\n", re.S)
BANK = re.compile(r"^## Question bank\n+```json\n(.*?)\n```", re.S | re.M)


def result(verdicts):
    avg = sum(SCORE.get(v, 0.0) for v in verdicts) / len(verdicts)
    return "pass" if avg >= 0.8 else "shaky" if avg >= 0.5 else "fail"


def next_stage(stage, r):
    return min(stage + 1, 6) if r == "pass" else stage if r == "shaky" else 0


def read_page(p):
    text = p.read_text()
    meta = {}
    m = FM.match(text)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line and not line.startswith((" ", "-")):
                k, v = line.split(":", 1)
                meta[k.strip()] = v.split(" #")[0].strip()
    return text, meta


def set_fm(text, **kv):
    m = FM.match(text)
    body = m.group(1).splitlines()
    for k, v in kv.items():
        for i, line in enumerate(body):
            if line.split(":", 1)[0].strip() == k:
                body[i] = f"{k}: {v}"
                break
        else:
            body.append(f"{k}: {v}")
    return "---\n" + "\n".join(body) + "\n---\n" + text[m.end():]


def add_weak(text, items, day):
    if not items:
        return text
    items = [i for i in items if f": {i}\n" not in text]       # don't repeat a weak spot already listed
    if not items:
        return text
    lines = "".join(f"- {day}: {i}\n" for i in items)
    m = re.search(r"^## Weak spots\n", text, re.M)
    if not m:
        return text.rstrip("\n") + f"\n\n## Weak spots\n{lines}"
    nxt = re.search(r"^## ", text[m.end():], re.M)
    pos = m.end() + nxt.start() if nxt else len(text)
    return text[:pos].rstrip("\n") + "\n" + lines + "\n" + text[pos:]


def bank(text):
    m = BANK.search(text)
    try:
        sets = json.loads(m.group(1)) if m else []
    except ValueError:
        sets = []
    return [s for s in sets if isinstance(s, list) and s]


def title(text, fallback):
    m = re.search(r"^# (.+)$", text, re.M)
    return m.group(1).strip() if m else fallback


def int0(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def run(vault, inbox, now, force_bank=False):
    vault = Path(vault)
    today, day = now.date(), now.date().isoformat()
    qs = {r["id"]: r for r in inbox.get("questions", [])}
    ans = {r["id"]: r for r in inbox.get("answers", [])}
    state = vault / ".sync"
    state.mkdir(exist_ok=True)
    cfg = {**CONFIG, **(json.loads((state / "config.json").read_text()) if (state / "config.json").exists() else {})}
    done_f = state / "processed.txt"       # ponytail: grows forever, ~40 bytes per question; prune if it ever matters
    done = set(done_f.read_text().split()) if done_f.exists() else set()
    writes, summary, log = [], [], []

    # 1. Pull results: a topic counts only once every queued question for it is answered.
    by_page = {}
    for q in qs.values():
        by_page.setdefault(q["data"].get("page", ""), []).append(q)
    cleared = set()
    for page, items in by_page.items():
        ids = [q["id"] for q in items]
        if not all(i in ans for i in ids):
            continue
        cleared.add(page)
        p = vault / page
        if not set(ids) <= done and page and p.exists():   # never apply the same batch twice
            text, meta = read_page(p)
            stage = int0(meta.get("stage"))
            r = result([ans[i]["data"].get("verdict") for i in ids])
            ns = next_stage(stage, r)
            text = set_fm(text, stage=ns, next_review=(today + dt.timedelta(days=WAIT[ns])).isoformat(),
                          last_result=r, updated=day)
            missing = list(dict.fromkeys(m for i in ids for m in (ans[i]["data"].get("missing") or [])[:3]))  # max 3 weak spots per question
            p.write_text(add_weak(text, missing, day))
            topic = title(text, p.stem)
            summary.append(f"{topic}: {r} (stage {stage} -> {ns}, back in {WAIT[ns]}d)")
            log.append(f"[[{p.stem}]] {r} {stage}->{ns}")
        done.update(ids)
        for i in ids:
            writes.append({"op": "delete", "collection": "questions", "doc_id": i, "if_version": qs[i]["version"]})
            writes.append({"op": "delete", "collection": "answers", "doc_id": i, "if_version": ans[i]["version"]})
    practiced = 0
    for i, a in ans.items():                 # practice answers, and answers whose question is already gone
        if i in qs:
            continue
        d = a["data"]
        if d.get("mode") == "practice" and i not in done:
            practiced += 1
            p = vault / d.get("page", "")
            if d.get("page") and p.exists() and d.get("verdict") != "correct":   # practice never moves the ladder,
                text, _ = read_page(p)                                            # but misses become weak spots
                p.write_text(add_weak(text, [f"(practice) {m}" for m in (d.get("missing") or [])[:2]], day))
            done.add(i)
        writes.append({"op": "delete", "collection": "answers", "doc_id": i, "if_version": a["version"]})
    done_f.write_text("\n".join(sorted(done)) + "\n")

    # 2. Load newly due topics from their question banks.
    queued = {p for p in by_page if p not in cleared}
    cutoff = today + dt.timedelta(days=1 if now.hour >= 18 else 0)   # evening run preloads tomorrow
    due, stages, by_page, shards = [], [0] * len(WAIT), {}, [[] for _ in range(BANK_SHARDS)]
    for folder in ("wiki", "builds"):
        for p in sorted((vault / folder).rglob("*.md")):
            rel = p.relative_to(vault).as_posix()
            text, meta = read_page(p)
            if meta.get("review") != "true":
                continue
            stages[min(int0(meta.get("stage")), len(WAIT) - 1)] += 1
            by_page[rel] = int0(meta.get("stage"))
            sets = bank(text)
            if sets:
                shards[zlib.crc32(rel.encode()) % BANK_SHARDS].append({"t": title(text, p.stem), "p": rel, "sets": sets})
            if rel in queued:
                continue
            try:
                nr = dt.date.fromisoformat(meta.get("next_review", ""))
            except ValueError:
                continue
            if nr <= cutoff:
                due.append((meta.get("last_result") != "fail", nr, rel, p))
    due.sort(key=lambda d: d[:3])            # fails first, then oldest due
    order = max([int0(q["data"].get("order")) for q in qs.values() if q["data"].get("page") in queued] or [-1]) + 1
    loaded, needs_bank, refresh = [], [], []
    for _, _, rel, p in due[:max(0, MAX_TOPICS - len(queued))]:
        text, meta = read_page(p)
        sets = bank(text)
        if not sets:
            needs_bank.append(rel)
            continue
        n = int0(meta.get("bank_set"))
        if n >= len(sets):
            refresh.append(rel)              # bank used up: reusing sets, Claude writes fresh ones next chat
        topic, stage = title(text, p.stem), int0(meta.get("stage"))
        slug = re.sub(r"[^a-z0-9]+", "-", p.stem.lower()).strip("-")
        for k, q in enumerate(sets[n % len(sets)], 1):
            doc = {**q, "topic": topic, "page": rel, "stage": stage, "order": order}
            order += 1
            writes.append({"op": "set", "collection": "questions", "doc_id": f"{slug}-{now:%Y%m%d%H}-{k}", "data": doc})
        p.write_text(set_fm(text, bank_set=n + 1))
        loaded.append(topic)

    # Mastery snapshot for the quiz page's Progress tab (stage counts after this run's updates).
    st = {r["id"]: r for r in inbox.get("stats", [])}
    w = {"op": "set", "collection": "stats", "doc_id": "mastery",
         "data": {"stages": stages, "total": sum(stages), "by_page": by_page, "updated": now.isoformat(timespec="minutes")}}
    if "mastery" in st:
        w["if_version"] = st["mastery"]["version"]
    writes.append(w)

    # Question banks for Practice: only shards whose content changed (or that are missing on the page) are sent.
    listed = {r["id"]: r["version"] for r in inbox.get("bank", [])}
    hash_f = state / "bank_hash.json"
    hashes = json.loads(hash_f.read_text()) if hash_f.exists() and not force_bank else {}
    for k, topics in enumerate(shards):
        sid, data = f"s{k}", {"topics": topics}
        h = hashlib.sha1(json.dumps(data, sort_keys=True).encode()).hexdigest()
        if not topics and sid not in listed:
            continue
        if hashes.get(sid) != h or sid not in listed:
            bw = {"op": "set", "collection": "bank", "doc_id": sid, "data": data}
            if sid in listed:
                bw["if_version"] = listed[sid]
            writes.append(bw)
        hashes[sid] = h
    hash_f.write_text(json.dumps(hashes))

    names = sorted({q["data"].get("topic", "") for q in qs.values() if q["data"].get("page") in queued} | set(loaded))
    waiting = len(names)
    if loaded:
        summary.append("Loaded: " + ", ".join(loaded))
    if practiced:
        summary.append(f"Practice answers saved: {practiced}")
    if log or loaded:
        with open(vault / "log.md", "a") as f:
            f.write(f"\n## [{day}] quiz | sync {now:%H:%M}\n"
                    + (f"Results: {'; '.join(log)}\n" if log else "")
                    + (f"Loaded: {', '.join(loaded)}\n" if loaded else ""))
    calendar = None
    cal_f = state / "calendar.txt"           # one reminder per day, even if sync runs twice
    if now.hour >= 18 and waiting and (not cal_f.exists() or cal_f.read_text().strip() != cutoff.isoformat()):
        cal_f.write_text(cutoff.isoformat())
        calendar = {"date": cutoff.isoformat(), "start": cfg["reminder_start"], "end": cfg["reminder_end"],
                    "title": "Quiz: " + (", ".join(names) if waiting <= 2 else f"{waiting} topics due"),
                    "description": "Due: " + ", ".join(names) + f"\nOpen the quiz: {cfg['quiz_url']}"}
    return {"batches": [writes[i:i + 50] for i in range(0, len(writes), 50)], "calendar": calendar,
            "summary": summary, "waiting_topics": waiting, "needs_bank": needs_bank, "refresh_bank": refresh}


def london_now():
    try:
        from zoneinfo import ZoneInfo
        return dt.datetime.now(ZoneInfo("Europe/London"))
    except Exception:
        return dt.datetime.now()


def export_bank(vault, out_dir):
    """Write every non-empty bank shard to out_dir/s<k>.json and mark them as sent.
    For big pushes (after an import) from a chat session: push the files with ArtifactData file_path instead of
    pasting JSON. The nightly sync then only sends shards that change later."""
    vault, out = Path(vault), Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    shards = [[] for _ in range(BANK_SHARDS)]
    for folder in ("wiki", "builds"):
        for p in sorted((vault / folder).rglob("*.md")):
            text, meta = read_page(p)
            sets = bank(text)
            if meta.get("review") == "true" and sets:
                rel = p.relative_to(vault).as_posix()
                shards[zlib.crc32(rel.encode()) % BANK_SHARDS].append({"t": title(text, p.stem), "p": rel, "sets": sets})
    hashes, files = {}, []
    for k, topics in enumerate(shards):
        if not topics:
            continue
        data = {"topics": topics}
        hashes[f"s{k}"] = hashlib.sha1(json.dumps(data, sort_keys=True).encode()).hexdigest()
        (out / f"s{k}.json").write_text(json.dumps(data, ensure_ascii=False))
        files.append(f"s{k}.json")
    (vault / ".sync" / "bank_hash.json").write_text(json.dumps(hashes))
    return files


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--export-bank" in args:
        print(json.dumps(export_bank(args[0], args[args.index("--export-bank") + 1])))
        sys.exit(0)
    now = dt.datetime.fromisoformat(args[args.index("--now") + 1]) if "--now" in args else london_now()
    print(json.dumps(run(args[0], json.loads(Path(args[1]).read_text()), now, force_bank="--push-bank" in args), indent=1))
