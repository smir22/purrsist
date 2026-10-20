#!/usr/bin/env python3
"""Second Brain quiz sync: all vault logic, zero AI tokens.

Claude only moves JSON between the quiz page's db and this script:
  python3 sync.py <vault_dir> <inbox.json> [--now 2026-10-11T21:52]
inbox.json = {"questions": [rows], "answers": [rows]}   (rows exactly as ArtifactData `list` returns: {"id","data","version"})
Add --push-bank to resend every question-bank shard (after a failed run).
  python3 sync.py <vault_dir> --check    -> lists question-bank problems (run after writing questions or rewrites)
Prints JSON: {"batches": [[ArtifactData batch writes <=50]], "calendar": {...}|null, "summary": [...], "needs_bank": [...], "refresh_bank": [...],
             "needs_variants": [{"page", "missing"}]}
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
RESERVE = 2                                # unused rewrites ("alts") kept ready for every question
MAX_TOPICS = 5                             # topics loaded per day by default (quiz Settings → Daily quiz: stats/prefs.max_topics)
BANK_SHARDS = 8                            # question banks published to the quiz page for Practice, split by page hash
CONFIG = {"quiz_url": "", "reminder_start": "08:00", "reminder_end": "08:15"}   # overridden by .sync/config.json
FM = re.compile(r"\A---\n(.*?)\n---\n", re.S)
BANK = re.compile(r"^## Question bank\n+```json\n(.*?)\n```", re.S | re.M)
BUILD = re.compile(r"^## Build it\n+```json\n(.*?)\n```", re.S | re.M)   # {"order": {...}, "sort": {...}} for the Build it exercises


def result(verdicts):
    s = [SCORE.get(v, 0.0) for v in verdicts if v != "skip"]     # flagged questions ("skip") aren't scored
    if not s:
        return "flagged"
    avg = sum(s) / len(s)
    return "pass" if avg >= 0.8 else "shaky" if avg >= 0.5 else "fail"


def next_stage(stage, r):
    return min(stage + 1, 6) if r == "pass" else stage if r in ("shaky", "flagged") else 0


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


def add_weak(text, items, day, heading="Weak spots"):
    if not items:
        return text
    items = [i for i in items if f": {i}\n" not in text]       # don't repeat a line already listed
    if not items:
        return text
    lines = "".join(f"- {day}: {i}\n" for i in items)
    m = re.search(rf"^## {heading}\n", text, re.M)
    if not m:
        notes = re.search(r"^## My notes\n", text, re.M)       # new section goes above My notes
        if notes and heading != "Weak spots":
            return text[:notes.start()] + f"## {heading}\n{lines}\n" + text[notes.start():]
        return text.rstrip("\n") + f"\n\n## {heading}\n{lines}"
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


def set_bank(text, sets):
    m = BANK.search(text)
    return text[:m.start(1)] + json.dumps(sets, ensure_ascii=False, indent=1) + text[m.end(1):]


def rotate(q):
    """A question was used: its next unused rewrite takes its place (the used version is dropped)."""
    alts = q.get("alts") or []
    return {**alts[0], "alts": alts[1:]} if alts else q


def use_prompt(sets, prompt):
    for s in sets:
        for k, q in enumerate(s):
            if q.get("prompt") == prompt and q.get("alts"):
                s[k] = rotate(q)
                return True
    return False


def bare(q):
    return {k: v for k, v in q.items() if k != "alts"}


def title(text, fallback):
    m = re.search(r"^# (.+)$", text, re.M)
    return m.group(1).strip() if m else fallback


def clean(s):
    return re.sub(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", lambda m: m.group(2) or m.group(1), s).replace("`", "").strip()


def lesson(text):
    """Learn-tab lesson: summary line + key bullets (title to first ##) and the latest weak spots. No LLM."""
    m = re.search(r"^# [^\n]+\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    lines = [l.strip() for l in (m.group(1) if m else "").splitlines() if l.strip()]
    summary = next((clean(l) for l in lines if not l.startswith("-")), "")
    keys = [clean(l[1:]) for l in lines if l.startswith("-")][:6]
    w = re.search(r"^## Weak spots\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    weak = [clean(re.sub(r"^-\s*(\d{4}-\d\d-\d\d:\s*)?", "", l)) for l in (w.group(1) if w else "").splitlines() if l.strip().startswith("-")]
    ls = re.search(r"^## Lesson\n(.*?)(?=^## |\Z)", text, re.M | re.S)     # full lesson: ### steps, written once per page
    return {"s": summary, "k": keys, "w": list(dict.fromkeys(weak))[-5:], "m": ls.group(1).strip() if ls else ""}


def build_it(text):
    m = BUILD.search(text)
    try:
        return json.loads(m.group(1)) if m else None
    except ValueError:
        return None


def build_problems(b):
    bad, o, s = [], (b or {}).get("order"), (b or {}).get("sort")
    if o:
        lines, traps = o.get("lines") or [], o.get("traps") or []
        ids = [x.get("id") for x in lines + traps]
        if not (o.get("title") and o.get("prompt") and len(lines) >= 4 and traps):
            bad.append("order needs a title, a prompt, 4+ lines and 1+ trap")
        if len(set(ids)) != len(ids) or not all(x.get("t") and x.get("why") for x in lines + traps):
            bad.append("order: every line and trap needs a unique id, t and why")
        line_ids, done = {x.get("id") for x in lines}, set()
        for _ in lines:                               # every "after" points at a line, with no loops
            done |= {x.get("id") for x in lines if set(x.get("after") or []) <= done}
        if any(set(x.get("after") or []) - line_ids for x in lines) or done != line_ids:
            bad.append("order: 'after' must list line ids and have no loops")
    if s:
        items = s.get("items") or []
        if not (s.get("title") and s.get("prompt") and len(items) >= 6 and {True, False} <= {i.get("do") for i in items}
                and all(i.get("id") and i.get("t") and i.get("why") for i in items)):
            bad.append("sort needs a title, a prompt and 6+ items (id, t, do true/false, why) with both Do and Don't")
    return bad


def entry(text, p, rel, sets):          # Practice sees only the current version of each question
    e = {"t": title(text, p.stem), "p": rel, "sets": [[bare(q) for q in s] for s in sets], "l": lesson(text)}
    b = build_it(text)
    if b:
        e["b"] = b
    return e


def shards_of(vault):
    shards, short = [[] for _ in range(BANK_SHARDS)], []
    for folder in ("wiki", "builds"):
        for p in sorted((vault / folder).rglob("*.md")):
            text, meta = read_page(p)
            sets = bank(text)
            if meta.get("review") == "true" and sets:
                rel = p.relative_to(vault).as_posix()
                shards[zlib.crc32(rel.encode()) % BANK_SHARDS].append(entry(text, p, rel, sets))
                n = sum(max(0, RESERVE - len(q.get("alts") or [])) for s in sets for q in s)
                if n:
                    short.append({"page": rel, "missing": n})
    return shards, short


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
    st = {r["id"]: r for r in inbox.get("stats", [])}
    cap = min(12, int0((st.get("prefs") or {}).get("data", {}).get("max_topics")) or MAX_TOPICS)
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
            helped = r != "flagged" and any(ans[i]["data"].get("assisted") for i in ids)   # "Learn first" isn't recall
            ns = 0 if helped else next_stage(stage, r)
            days = 1 if r == "flagged" else WAIT[ns]                 # every question flagged: same step, back tomorrow
            kv = {"stage": ns, "next_review": (today + dt.timedelta(days=days)).isoformat(), "updated": day}
            if r != "flagged":
                kv["last_result"] = r
            text = set_fm(text, **kv)
            missing = list(dict.fromkeys(m for i in ids for m in (ans[i]["data"].get("missing") or [])[:3]))  # max 3 weak spots per question
            p.write_text(add_weak(text, missing, day))
            topic = title(text, p.stem)
            how = f"{r}, learned first" if helped else r
            summary.append(f"{topic}: {how} (stage {stage} -> {ns}, back in {days}d)")
            log.append(f"[[{p.stem}]] {how} {stage}->{ns}")
        done.update(ids)
        for i in ids:
            writes.append({"op": "delete", "collection": "questions", "doc_id": i, "if_version": qs[i]["version"]})
            writes.append({"op": "delete", "collection": "answers", "doc_id": i, "if_version": ans[i]["version"]})
    practiced, flagged = 0, []
    for i, a in ans.items():                 # practice answers, and answers whose question is already gone
        if i in qs:
            continue
        d = a["data"]
        if d.get("mode") in ("practice", "learn") and i not in done:
            practiced += 1
            p = vault / d.get("page", "")
            if d.get("page") and p.exists():
                text, _ = read_page(p)
                if d.get("verdict") != "correct":                   # practice never moves the ladder, but misses become weak spots
                    text = add_weak(text, [f"({d['mode']}) {m}" for m in (d.get("missing") or [])[:2]], day)
                sets = bank(text)
                if d.get("prompt") and use_prompt(sets, d["prompt"]):   # seen once: a rewrite takes its place
                    text = set_bank(text, sets)
                p.write_text(text)
            done.add(i)
        elif d.get("mode") == "flag" and i not in done:          # a bad question flagged on the phone
            p = vault / d.get("page", "")
            if d.get("page") and p.exists():
                text, _ = read_page(p)
                p.write_text(add_weak(text, [f"{d.get('reason', 'Flagged')}: {d.get('prompt', '')}"], day, "Flagged questions"))
                flagged.append(d["page"])
            done.add(i)
        writes.append({"op": "delete", "collection": "answers", "doc_id": i, "if_version": a["version"]})
    done_f.write_text("\n".join(sorted(done)) + "\n")

    # 2. Load newly due topics from their question banks.
    queued = {p for p in by_page if p not in cleared}
    cutoff = today + dt.timedelta(days=1 if now.hour >= 18 else 0)   # evening run preloads tomorrow
    due, stages, by_page = [], [0] * len(WAIT), {}
    for folder in ("wiki", "builds"):
        for p in sorted((vault / folder).rglob("*.md")):
            rel = p.relative_to(vault).as_posix()
            text, meta = read_page(p)
            if meta.get("review") != "true":
                continue
            stages[min(int0(meta.get("stage")), len(WAIT) - 1)] += 1
            by_page[rel] = int0(meta.get("stage"))
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
    for _, _, rel, p in due[:max(0, cap - len(queued))]:
        text, meta = read_page(p)
        sets = bank(text)
        if not sets:
            needs_bank.append(rel)
            continue
        n = int0(meta.get("bank_set"))
        cur = sets[n % len(sets)]
        if n >= len(sets) and not all(q.get("alts") for q in cur):
            refresh.append(rel)              # no rewrites left: reusing questions, Claude writes fresh ones next chat
        topic, stage = title(text, p.stem), int0(meta.get("stage"))
        slug = re.sub(r"[^a-z0-9]+", "-", p.stem.lower()).strip("-")
        for k, q in enumerate(cur, 1):
            doc = {**bare(q), "topic": topic, "page": rel, "stage": stage, "order": order, "due": meta.get("next_review", "")}
            order += 1
            writes.append({"op": "set", "collection": "questions", "doc_id": f"{slug}-{now:%Y%m%d%H}-{k}", "data": doc})
        sets[n % len(sets)] = [rotate(q) for q in cur]            # served once: next time this set shows its rewrites
        p.write_text(set_fm(set_bank(text, sets), bank_set=n + 1))
        loaded.append(topic)

    refresh += [p for p in dict.fromkeys(flagged) if p not in refresh]   # flagged questions get fixed at "refresh banks"

    # Mastery snapshot for the quiz page's Progress tab (stage counts after this run's updates).
    w = {"op": "set", "collection": "stats", "doc_id": "mastery",
         "data": {"stages": stages, "total": sum(stages), "by_page": by_page, "updated": now.isoformat(timespec="minutes")}}
    if "mastery" in st:
        w["if_version"] = st["mastery"]["version"]
    writes.append(w)

    # Question banks for Practice (built after loading, so they show the next versions): only changed shards are sent.
    shards, short = shards_of(vault)
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
    if short:
        summary.append(f"Questions short of rewrites: {sum(x['missing'] for x in short)} across {len(short)} pages")
    if flagged:
        summary.append(f"Flagged questions: {len(flagged)} (say \"refresh banks\" to fix them)")
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
            "summary": summary, "waiting_topics": waiting, "needs_bank": needs_bank, "refresh_bank": refresh,
            "needs_variants": short}


def check_banks(vault):
    """Question-bank problems that would break the quiz. [] = all good."""
    bad = []
    for folder in ("wiki", "builds"):
        for p in sorted((Path(vault) / folder).rglob("*.md")):
            text, meta = read_page(p)
            rel = p.relative_to(vault).as_posix()
            if meta.get("review") != "true" or "## Question bank" not in text:
                continue
            if "## Build it" in text:
                bad += [f"{rel} Build it: {x}" for x in (build_problems(build_it(text)) if build_it(text) else ["JSON doesn't load"])]
            m = BANK.search(text)
            try:
                sets = json.loads(m.group(1))
            except (AttributeError, ValueError):
                bad.append(f"{rel}: question bank JSON doesn't load")
                continue
            for i, st in enumerate(sets, 1):
                for j, q in enumerate(st, 1):
                    for k, v in enumerate([q, *(q.get("alts") or [])]):
                        at = f"{rel} set {i} q{j}" + (f" rewrite {k}" if k else "")
                        if not (isinstance(v.get("options"), list) and len(v["options"]) == 4
                                and isinstance(v.get("correct"), int) and 0 <= v["correct"] < 4):
                            bad.append(f"{at}: needs 4 options and correct 0-3")
                        if not (v.get("prompt") and v.get("answer") and v.get("points")):
                            bad.append(f"{at}: needs prompt, answer and points")
                        if k and ("alts" in v or v.get("kind") != q.get("kind") or v.get("prompt") == q.get("prompt")):
                            bad.append(f"{at}: a rewrite has the same kind, a new prompt and no alts of its own")
    return bad


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
    shards, _ = shards_of(vault)
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
    if "--check" in args:
        problems = check_banks(args[0])
        print(json.dumps(problems, indent=1))
        sys.exit(1 if problems else 0)
    if "--export-bank" in args:
        print(json.dumps(export_bank(args[0], args[args.index("--export-bank") + 1])))
        sys.exit(0)
    now = dt.datetime.fromisoformat(args[args.index("--now") + 1]) if "--now" in args else london_now()
    print(json.dumps(run(args[0], json.loads(Path(args[1]).read_text()), now, force_bank="--push-bank" in args), indent=1))
