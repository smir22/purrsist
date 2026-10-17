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
assert next_stage(6, "pass") == 6 and next_stage(3, "shaky") == 3 and next_stage(4, "fail") == 0

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

print("ok")
