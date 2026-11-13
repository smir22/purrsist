"""Self-check for sync.py: python3 test_sync.py"""
import datetime as dt
import json
import re
import tempfile
from pathlib import Path

from sync import next_stage, result, run

assert result(["correct", "correct", "partial"]) == "pass"      # .83
assert result(["correct", "partial", "wrong"]) == "shaky"       # .5
assert result(["partial", "wrong", "wrong"]) == "fail"          # .17
assert next_stage(6, "pass") == 6 and next_stage(3, "shaky") == 3 and next_stage(4, "fail") == 2 and next_stage(1, "fail") == 0   # fail: back two steps

SETS = [[{"kind": "recall", "prompt": f"q{s}{k}", "answer": "a", "points": ["p"]} for k in range(3)] for s in range(3)]
PAGE = """---
tags: [tech]
review: true
stage: 2
next_review: 2026-10-11
last_result: pass
bank_set: 1
---

# Topic A

body

## Weak spots

## My notes
mine

## Question bank
```json
%s
```
""" % json.dumps(SETS)

with tempfile.TemporaryDirectory() as d:
    v = Path(d)
    (v / "wiki/tech").mkdir(parents=True)
    (v / "builds").mkdir()
    (v / "log.md").write_text("# Log\n")
    page = v / "wiki/tech/Topic A.md"
    page.write_text(PAGE)
    rows = lambda pre, verdicts: [{"id": f"a-{i}", "version": 3, "data": {"page": "wiki/tech/Topic A.md", "topic": "Topic A",
                                    "order": i, "verdict": verdicts[i], "missing": [f"{pre}{i}"] if verdicts[i] != "correct" else []}}
                                   for i in range(3)]
    inbox = {"questions": rows("", ["x"] * 3), "answers": rows("gap", ["correct", "wrong", "wrong"])}
    evening = dt.datetime(2026, 10, 11, 21, 52)

    out = run(v, inbox, evening)
    text = page.read_text()
    assert "stage: 0" in text and "next_review: 2026-10-12" in text and "last_result: fail" in text, text
    assert "- 2026-10-11: gap1\n- 2026-10-11: gap2\n\n## My notes\nmine" in text, text      # weak spots in place, My notes untouched
    writes = [w for b in out["batches"] for w in b]
    assert sum(w["op"] == "delete" for w in writes) == 6 and all(w.get("if_version") == 3 for w in writes if w["op"] == "delete")
    sets = [w for w in writes if w["op"] == "set" and w["collection"] == "questions"]
    assert len(sets) == 3 and sets[0]["data"]["prompt"] == "q10", sets             # failed -> due tomorrow -> next bank set
    assert "bank_set: 2" in page.read_text()
    mastery = [w for w in writes if w["collection"] == "stats"][0]
    assert mastery["data"]["stages"][0] == 1 and mastery["data"]["total"] == 1 and "if_version" not in mastery
    assert out["calendar"]["date"] == "2026-10-12" and out["calendar"]["title"] == "Quiz: Topic A" and "Due: Topic A" in out["calendar"]["description"]

    # Re-running with the same inbox (db write failed last time) must not apply results twice.
    before = page.read_text().split("## Question bank")[0]
    out2 = run(v, inbox, evening)
    assert page.read_text().split("## Question bank")[0].replace("bank_set: 3", "bank_set: 2") == before
    assert sum(w["op"] == "delete" for b in out2["batches"] for w in b) == 6
    assert out2["calendar"] is None                                               # no duplicate reminder same day

    # Morning run, nothing answered, topic already queued -> no new sets, no calendar.
    queued = {"questions": [{"id": s["doc_id"], "version": 1, "data": s["data"]} for s in sets], "answers": []}
    bank1 = [w for w in writes if w["collection"] == "bank"]
    assert len(bank1) == 1 and bank1[0]["data"]["topics"][0]["t"] == "Topic A" and "if_version" not in bank1[0]   # first publish

    queued["stats"] = [{"id": "mastery", "version": 4, "data": {}}]
    queued["bank"] = [{"id": bank1[0]["doc_id"], "version": 2}]
    out3 = run(v, queued, dt.datetime(2026, 10, 12, 9, 52))
    w3 = [w for b in out3["batches"] for w in b]
    assert [w["collection"] for w in w3] == ["stats"] and w3[0]["if_version"] == 4   # bank unchanged -> not resent
    assert out3["calendar"] is None and out3["waiting_topics"] == 1
    assert "by_page" in w3[0]["data"] and w3[0]["data"]["by_page"]["wiki/tech/Topic A.md"] == 0

    # Practice answers: a miss becomes a weak spot (once), the ladder doesn't move, the answer is deleted.
    before_stage = re.search(r"^stage: (\d+)", page.read_text(), re.M).group(1)
    pr = {"id": "p-1", "version": 1, "data": {"mode": "practice", "page": "wiki/tech/Topic A.md", "verdict": "wrong", "missing": ["the right idea"]}}
    out4 = run(v, {**queued, "answers": [pr, {**pr, "id": "p-2"}]}, dt.datetime(2026, 10, 12, 12, 0))
    t4 = page.read_text()
    assert t4.count("(practice) the right idea") == 1 and re.search(r"^stage: (\d+)", t4, re.M).group(1) == before_stage
    assert sum(w["op"] == "delete" and w["collection"] == "answers" for b in out4["batches"] for w in b) == 2
    assert "Practice answers saved: 2" in out4["summary"]

    # --push-bank resends every non-empty shard
    out5 = run(v, queued, dt.datetime(2026, 10, 12, 12, 5), force_bank=True)
    assert any(w["collection"] == "bank" and w.get("if_version") == 2 for b in out5["batches"] for w in b)

    files = __import__("sync").export_bank(v, Path(d) / "bank_out")
    assert files and json.loads((Path(d) / "bank_out" / files[0]).read_text())["topics"][0]["t"] == "Topic A"
    out6 = run(v, queued, dt.datetime(2026, 10, 12, 12, 10))     # after export, an unchanged bank isn't resent
    assert not any(w["collection"] == "bank" for b in out6["batches"] for w in b)

    # Learn tab: lesson = summary + key bullets + weak spots, shipped with the bank; learn answers act like practice
    from sync import lesson
    L = lesson("---\nx: 1\n---\n\n# T\n\nOne line summary with [[Link|alias]].\n\n- `a` first\n- second\n\n## Weak spots\n- 2026-10-11: gap one\n- 2026-10-12: (practice) gap two\n\n## My notes\n")
    assert L == {"s": "One line summary with alias.", "k": ["a first", "second"], "w": ["gap one", "(practice) gap two"], "m": ""}, L
    L2 = lesson("# T\n\nsum\n\n## Lesson\n\n### Step one\nText.\n```py\nx = 1\n```\n\n### Step two\nMore.\n\n## Weak spots\n")
    assert L2["m"].startswith("### Step one") and L2["m"].endswith("More.") and "Weak" not in L2["m"], L2
    assert json.loads((Path(d) / "bank_out" / files[0]).read_text())["topics"][0]["l"]["w"][:2] == ["gap1", "gap2"]
    lr = {"id": "l-1", "version": 1, "data": {"mode": "learn", "page": "wiki/tech/Topic A.md", "verdict": "wrong", "missing": ["learned gap"]}}
    run(v, {**queued, "answers": [lr]}, dt.datetime(2026, 10, 12, 12, 20))
    assert "(learn) learned gap" in page.read_text() and re.search(r"^stage: (\d+)", page.read_text(), re.M).group(1) == before_stage

    # Flags: logged under "## Flagged questions" above My notes, page goes to refresh_bank, the flag doc is deleted
    fl = {"id": "f-1", "version": 1, "data": {"mode": "flag", "reason": "Needs code", "page": "wiki/tech/Topic A.md", "prompt": "What does X do?"}}
    out7 = run(v, {**queued, "answers": [fl, {**fl, "id": "f-2"}]}, dt.datetime(2026, 10, 12, 12, 30))
    t7 = page.read_text()
    assert t7.count("Needs code: What does X do?") == 1 and t7.index("## Flagged questions") < t7.index("## My notes"), t7
    assert "wiki/tech/Topic A.md" in out7["refresh_bank"] and any("Flagged questions: 2" in s for s in out7["summary"])
    assert sum(w["op"] == "delete" and w["collection"] == "answers" for b in out7["batches"] for w in b) == 2

# v1.18: flagged ("skip") answers aren't scored; all flagged -> same step, back tomorrow; "Learn first" -> counts as a fail (back two steps);
# every question keeps 2 unused rewrites ("alts"): using a version (quiz load, practice/learn answer) rotates in the next one.
from sync import result
assert result(["correct", "skip", "correct"]) == "pass" and result(["skip", "skip"]) == "flagged"

def qv(name, alts):
    q = {"kind": "recall", "prompt": name, "answer": "a", "points": ["p"], "options": ["a", "b", "c", "d"], "correct": 0}
    return {**q, "alts": [{**q, "prompt": f"{name}v{j}"} for j in (1, 2)]} if alts else q

def mk(v, name, stage, alts=False, due="2026-10-20"):
    sets = [[qv(f"{name}{s}{k}", alts) for k in range(3)] for s in range(3)]
    (v / f"wiki/tech/{name}.md").write_text(f"---\ntags: [tech]\nreview: true\nstage: {stage}\nnext_review: {due}\nlast_result: pass\nbank_set: 0\n---\n\n# {name}\n\nbody\n\n## Weak spots\n\n## My notes\n\n## Question bank\n```json\n{json.dumps(sets, indent=1)}\n```\n")

with tempfile.TemporaryDirectory() as d:
    v = Path(d); (v / "wiki/tech").mkdir(parents=True); (v / "log.md").write_text("# Log\n")
    for name in ("B", "C", "D"):
        mk(v, name, 3, due="2026-11-30")
    mk(v, "E", 1, alts=True)
    qrow = lambda name, k: {"id": f"{name}-{k}", "version": 1, "data": {"page": f"wiki/tech/{name}.md", "topic": name, "order": k}}
    arow = lambda name, k, verdict, **x: {"id": f"{name}-{k}", "version": 1, "data": {"verdict": verdict, "missing": [], **x}}
    inbox = {"questions": [qrow(n, k) for n in "BCD" for k in range(3)],
             "answers": [arow("B", 0, "correct"), arow("B", 1, "skip"), arow("B", 2, "correct"),
                         *[arow("C", k, "skip") for k in range(3)],
                         arow("D", 0, "correct", assisted=True), arow("D", 1, "correct"), arow("D", 2, "correct"),
                         {"id": "p-9", "version": 1, "data": {"mode": "practice", "page": "wiki/tech/E.md", "verdict": "correct", "prompt": "E10"}}]}
    out = run(v, inbox, dt.datetime(2026, 10, 20, 21, 0))
    B, C, D, E = [(v / f"wiki/tech/{n}.md").read_text() for n in "BCDE"]
    assert "stage: 4" in B and "next_review: 2026-11-20" in B, B[:200]                       # skip ignored -> pass
    assert "stage: 3" in C and "next_review: 2026-10-21" in C and "last_result: pass" in C    # all flagged -> same step, tomorrow
    assert "stage: 1" in D and "next_review: 2026-10-23" in D and any("learned first" in x for x in out["summary"])
    eb = json.loads(re.search(r"```json\n(.*?)\n```", E, re.S).group(1))
    served = [w["data"]["prompt"] for b in out["batches"] for w in b if w["collection"] == "questions" and w["op"] == "set"]
    assert served[:3] == ["E00", "E01", "E02"], served                                          # originals served first
    assert [q["prompt"] for q in eb[0]] == ["E00v1", "E01v1", "E02v1"] and len(eb[0][0]["alts"]) == 1   # then the rewrites
    assert eb[1][0]["prompt"] == "E10v1" and eb[1][1]["prompt"] == "E11"                         # practice answer rotated E10 only
    assert all("alts" not in json.dumps(w.get("data", {})) for b in out["batches"] for w in b if w["collection"] in ("questions", "bank"))
    nv = {x["page"]: x["missing"] for x in out["needs_variants"]}
    assert nv["wiki/tech/E.md"] == 4 and nv["wiki/tech/B.md"] == 18, nv                         # 3 + 1 used in E; B has none

    from sync import check_banks
    assert check_banks(v) == [], check_banks(v)[:3]
    (v / "wiki/tech/E.md").write_text(E.replace('"E11v2",', '"E11",', 1).replace('"correct": 0', '"correct": 7', 1))
    probs = check_banks(v)
    assert any("correct 0-3" in x for x in probs) and any("new prompt" in x for x in probs), probs

    # Daily cap: stats/prefs.max_topics limits how many due topics load; question docs carry their due date
    for k in range(6):
        mk(v, f"T{k}", 0, alts=True, due="2026-10-21")
    out = run(v, {"questions": [], "answers": [], "stats": [{"id": "prefs", "version": 1, "data": {"max_topics": 3}}]}, dt.datetime(2026, 10, 21, 21, 0))
    docs = [w["data"] for b in out["batches"] for w in b if w["collection"] == "questions" and w["op"] == "set"]
    assert len({d["page"] for d in docs}) == 3 and all(d["due"] for d in docs), docs[:2]

    # One batch a day: a second sync for the same day loads nothing more
    again = run(v, {"questions": [], "answers": [], "stats": [{"id": "prefs", "version": 1, "data": {"max_topics": 3}}]}, dt.datetime(2026, 10, 21, 21, 30))
    assert not [w for b in again["batches"] for w in b if w["collection"] == "questions"]
    # Brand-new topics (bank_set 0) are capped at MAX_NEW a day and come after reviews: 3 reviews + 2 new, not 8
    out = run(v, {"questions": [], "answers": [], "stats": [{"id": "prefs", "version": 1, "data": {"max_topics": 8}}]}, dt.datetime(2026, 10, 23, 9, 0))
    pages = list(dict.fromkeys(w["data"]["page"] for b in out["batches"] for w in b if w["collection"] == "questions" and w["op"] == "set"))
    fresh = [p for p in pages if "bank_set: 1\n" in (v / p).read_text()]
    assert len(pages) == 5 and len(fresh) == 2 and pages[-2:] == fresh, pages
    # No piling: while any question is still unanswered, nothing new loads
    wait = {"questions": [{"id": "T5-0", "version": 1, "data": {"page": "wiki/tech/T5.md", "topic": "T5", "order": 0}}], "answers": []}
    out = run(v, wait, dt.datetime(2026, 10, 25, 9, 0))
    assert not [w for b in out["batches"] for w in b if w["collection"] == "questions"] and out["waiting_topics"] == 1

    # Build it: a page's `## Build it` JSON ships with its bank entry and is checked by --check
    from sync import shards_of, build_problems
    good = {"order": {"title": "T", "prompt": "P", "lines": [{"id": f"l{i}", "t": f"line {i}", "why": "w", "after": [f"l{i-1}"] if i else []} for i in range(4)],
                      "traps": [{"id": "x", "t": "bad", "why": "w"}]},
            "sort": {"title": "T", "prompt": "P", "items": [{"id": f"s{i}", "t": f"item {i}", "do": i % 2 == 0, "why": "w"} for i in range(6)]}}
    assert build_problems(good) == []
    loop = json.loads(json.dumps(good)); loop["order"]["lines"][0]["after"] = ["l3"]
    assert build_problems(loop) and build_problems({"sort": {"title": "T", "prompt": "P", "items": good["sort"]["items"][:3]}})
    f = v / "wiki/tech/T0.md"; f.write_text(f.read_text().replace("## Weak spots", "## Build it\n```json\n" + json.dumps(good) + "\n```\n\n## Weak spots"))
    sh, _ = shards_of(v)
    assert [e for s in sh for e in s if e["p"] == "wiki/tech/T0.md"][0]["b"]["order"]["title"] == "T"
    assert check_banks(v) == [x for x in check_banks(v) if "E.md" in x]                           # only the earlier broken page

# Shaky loop: two results in a row that aren't a clean pass -> the next load is marked relearn (the quiz shows the lesson first)
with tempfile.TemporaryDirectory() as d:
    v = Path(d); (v / "wiki/tech").mkdir(parents=True); (v / "log.md").write_text("# Log\n")
    mk(v, "S", 0, due="2026-10-20"); f = v / "wiki/tech/S.md"
    f.write_text(f.read_text().replace("bank_set: 0", "bank_set: 1\nmiss_run: 1"))
    out = run(v, {"questions": [qrow("S", k) for k in range(3)], "answers": [arow("S", k, "partial") for k in range(3)]}, dt.datetime(2026, 10, 20, 21, 0))
    assert "miss_run: 2" in f.read_text(), f.read_text()[:200]
    docs = [w["data"] for b in out["batches"] for w in b if w["collection"] == "questions" and w["op"] == "set"]
    assert docs and all(x.get("relearn") for x in docs), docs[:1]
    run(v, {"questions": [qrow("S", k + 5) for k in range(3)], "answers": [arow("S", k + 5, "correct") for k in range(3)]}, dt.datetime(2026, 10, 22, 21, 0))
    assert "miss_run: 0" in f.read_text()

# Packs: a page's `pack:` field travels with its bank entry (no field = no key, the app files it under My notes)
with tempfile.TemporaryDirectory() as d:
    v = Path(d); (v / "wiki/tech").mkdir(parents=True)
    mk(v, "P1", 0); mk(v, "P2", 0)
    f = v / "wiki/tech/P1.md"; f.write_text(f.read_text().replace("bank_set: 0", "bank_set: 0\npack: Docker, Kubernetes"))
    from sync import shards_of as _so
    es = {e["t"]: e for sh in _so(v)[0] for e in sh}
    assert es["P1"]["k"] == ["Docker", "Kubernetes"] and "k" not in es["P2"], es["P1"].get("k")

# Labs: builds/ pages with `rung:` ship to the Build tab as stats/labs; a "lab" answer from the phone marks the page done
with tempfile.TemporaryDirectory() as d:
    v = Path(d); (v / "wiki/tech").mkdir(parents=True); (v / "builds").mkdir(); (v / "log.md").write_text("# Log\n")
    lab = v / "builds/Lab 1.md"
    lab.write_text("---\ntags: [build, lab]\nstatus: planned\nrung: 1\ntime_box: 45 min\npack: Docker\n---\n\n# Lab 1\n\nThe goal.\n\nPart of [[Ladder]].\n\n## Steps\n1. Do `x`.\n2. See [[Topic A|the topic]].\n\n## Log\nprivate\n")
    (v / "builds/Ladder.md").write_text("---\ntags: [build]\n---\n\n# Ladder\n")
    out = run(v, {"questions": [], "answers": []}, dt.datetime(2026, 11, 12, 21, 0))
    lw = [w for b in out["batches"] for w in b if w["collection"] == "stats" and w["doc_id"] == "labs"][0]
    L1 = lw["data"]["labs"]
    assert len(L1) == 1 and L1[0]["t"] == "Lab 1" and L1[0]["k"] == ["Docker"] and L1[0]["goal"] == "The goal." and L1[0]["n"] == "Part of Ladder.", L1
    assert [x["h"] for x in L1[0]["s"]] == ["Steps"] and "`x`" in L1[0]["s"][0]["b"] and "the topic" in L1[0]["s"][0]["b"] and "if_version" not in lw
    same = run(v, {"questions": [], "answers": [], "stats": [{"id": "labs", "version": 3, "data": lw["data"]}]}, dt.datetime(2026, 11, 12, 21, 5))
    assert not [w for b in same["batches"] for w in b if w.get("doc_id") == "labs"]                    # unchanged -> not resent
    fin = run(v, {"questions": [], "answers": [{"id": "lab-1", "version": 1, "data": {"mode": "lab", "page": "builds/Lab 1.md"}}],
                  "stats": [{"id": "labs", "version": 3, "data": lw["data"]}]}, dt.datetime(2026, 11, 13, 21, 0))
    w2 = [w for b in fin["batches"] for w in b]
    assert "status: done" in lab.read_text() and any(w["op"] == "delete" and w["doc_id"] == "lab-1" for w in w2)
    assert [w for w in w2 if w.get("doc_id") == "labs"][0]["data"]["labs"][0]["status"] == "done" and any("Lab done" in x for x in fin["summary"])

# --lint: machine-checkable question quality (warnings only)
from sync import lint_q
ok_q = {"prompt": "A junior says 'green panels mean the model is fine'. What's the best correction?", "options": ["Green can hide wrong predictions", "Right, if 5xx stays under 1%", "Check p99 instead of p95", "Right, but watch memory too"], "correct": 0}
assert lint_q(ok_q) == [], lint_q(ok_q)
assert any("Explain" in w for w in lint_q({**ok_q, "prompt": "Explain an MLflow run like you're teaching a junior."}))
assert any("code snippet" in w for w in lint_q({**ok_q, "prompt": "Why does your CI also run on a weekly schedule?"}))
assert lint_q({**ok_q, "prompt": "Why does your CI also run weekly?", "code": "on:\n  schedule:"}) == []
assert any("longest" in w for w in lint_q({**ok_q, "options": ["Green can hide wrong predictions, so also watch drift and quality", "Right", "Check p99", "Watch memory"]}))
assert any("ending in ?" in w for w in lint_q({**ok_q, "prompt": "Data drift means\u2026"}))

print("ok")
