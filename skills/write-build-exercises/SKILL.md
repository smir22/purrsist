---
name: "write-build-exercises"
description: "Write or repair Purrsist 'Build it' drag-and-drop exercises (order the lines, do/don't sort) and plan a hands-on lab ladder for a subject such as Kubernetes. Use for 'write build exercises', a page without Build it, or 'plan labs for X'."
---

# Write Build it exercises (Second Brain / Purrsist)

Quizzes prove the learner can recognise an idea. Build it proves they can assemble the real thing. This skill covers two layers: the phone exercises on each page, and a ladder of real labs for a subject. The vault's `CLAUDE.md` (**build it** and **build** sections) is the source of truth for the JSON format and file locations; this skill is the source of truth for quality.

## 0. Scope
1. Vault: `[VAULT_PATH]` (not connected → request folder access). Read the page: lesson, weak spots, and any real code from the learner's repo linked in `wiki/sources/`.
2. Pick the ONE artifact a working engineer would actually write for this topic (a Dockerfile, a Kubernetes probe block, a GitHub Actions job, an Airflow DAG, an MLflow logging block, a Terraform backend). No natural artifact: use the real workflow steps in order.
3. At most 5 pages per run. Say how many remain.

## 1. Order exercise (`order`)
- 5-8 `lines` that together form a minimal, correct, runnable artifact. Each line is one real line (at most 60 characters, indentation kept) and would be valid if typed as shown.
- Use the learner's real setup when the page has one; otherwise a small realistic example. Never present invented code as theirs.
- `after` lists only true ordering constraints. Test: for every pair of lines, ask "would the artifact break or behave worse if these swapped?" Yes -> add the constraint. No -> leave it out, so every valid order passes.
- 2-3 `traps`: lines a real engineer plausibly writes that are bad practice here (unpinned image, secret in an env line, copying everything before installing). Never something arguably fine, and never a syntax error.
- Every line and trap has a one-sentence `why` (at most 160 characters) that states the consequence, not just the rule: "a code edit reinstalls every dependency", not "bad for caching".
- `title` says what is being built; `prompt` states the goal and how many lines to leave out; `label` names the artifact.

## 2. Sort exercise (`sort`)
- Exactly 8 practices: 4 `"do": true`, 4 false, at most 60 characters each, plain text.
- Each item is a concrete action, not a slogan ("Pin the base image tag", not "Follow best practices").
- Each don't is a tempting mistake, ideally one from the page's weak spots. No item whose answer depends on context the tile doesn't give.
- Do and don't items must not be mirror images of each other more than once per exercise.

## 3. Self-review (fix or drop)
1. **Run test**: assemble the lines in the intended order. Would it actually run or apply? Check syntax as if you were going to execute it.
2. **Order test**: write out one alternative valid order and confirm the `after` graph accepts it.
3. **Trap test**: would a senior engineer defend any trap in some normal situation? If yes, replace it.
4. **Lesson test**: every line, trap and practice is explained by the page's lesson (its `### Best practice` step especially).
5. **Phone test**: no line over 60 characters; no backticks in tiles.

## 4. Machine check
- `python3 .sync/sync.py . --check` must print `[]` (it validates ids, `after` loops, counts).
- Publish banks for Practice as the vault's `CLAUDE.md` describes.

## 5. Lab ladder ("plan labs for <subject>", e.g. Kubernetes)
Phone exercises are not enough to learn a hands-on subject; each topic also needs hands-on time. Build a ladder, not a pile:
1. List the subject's pages in dependency order (for Kubernetes: pods -> deployments -> services -> probes -> config and secrets -> autoscaling).
2. For each rung write one lab page in `builds/` per the vault's **build** rules. Give it the frontmatter `rung: <n>`, `time_box: <minutes>`, `status: planned` and `pack: <name>` so the sync shows it in the quiz page's Build tab. Each lab has:
   - **Goal**: one observable outcome ("a rolling update finishes with zero failed requests").
   - **Time box**: 30-60 minutes, sized to a free slot in the learner's schedule.
   - **Start state**: the exact repo, branch or command to begin from (prefer the learner's own lab repo).
   - **Steps**: 4-7, each ending in something checkable.
   - **Done when**: a command and its expected output, so success isn't a judgement call.
   - **Break it**: one deliberate failure to cause and then diagnose (stop a dependency, fail the readiness probe, fill the disk).
   - **Explain back**: three parts of the result the learner must explain line by line afterwards.
3. Each lab links the concept pages it exercises. Only unlock a lab once its concept pages are past day 1 on the ladder, and never plan more than two labs a week unless the user asks.
4. Prefer labs that leave something CV- or portfolio-worthy behind.

## 6. Report (3 lines)
- Pages given or repaired Build it exercises; labs planned.
- `--check` result.
- Anything dropped or needing the user's real code.