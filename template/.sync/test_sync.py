"""Self-check for sync.py: python3 test_sync.py"""
import datetime as dt
import json
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
    queued["stats"] = [{"id": "mastery", "version": 4, "data": {}}]
    out3 = run(v, queued, dt.datetime(2026, 10, 12, 9, 52))
    w3 = [w for b in out3["batches"] for w in b]
    assert [w["collection"] for w in w3] == ["stats"] and w3[0]["if_version"] == 4   # only the mastery refresh
    assert out3["calendar"] is None and out3["waiting_topics"] == 1

print("ok")
