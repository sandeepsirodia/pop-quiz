# pop-quiz — SPEC

> You didn't write it. Can you explain it?

A pre-merge skill that quizzes you on the riskiest parts of your branch's diff before you merge AI-written code. It targets "comprehension debt": in Anthropic's study, developers who used AI assistance scored 17% lower on comprehension.

## Who it's for
Developers who ship agent-written code and want to stay the person who understands the system. Teams that want a lightweight "can you explain this?" gate.

## Must have (v1)
1. **Skill** (`/pop-quiz`): a Claude Code plugin, also installable via `npx skills add` into Cursor, Codex and others. Bundles a deterministic risk scorer (`scripts/score.py`).
2. **Reads the diff** of the current branch vs its base (`git merge-base`).
3. **Picks the riskiest hunks** using a simple, explainable score: touches auth/permissions, money, concurrency/locking, error handling removed, deleted checks or validation, SQL/shell strings, config/infra, hunk size.
4. **Asks 3–5 questions, one at a time.** Question types: "what happens if X is null here?", "why is this lock needed?", "what breaks if this line is removed?". Each question cites `file:line`.
5. **Never reveals the answer before you respond.**
6. **Grades each answer** as pass / partial / miss against the actual code, then explains the gap with a code reference.
7. **Summary block** (score + topics missed), ready to paste into the PR description.
8. **Not a hard block:** the user can always skip; the skip is noted in the summary.

## Won't do (v1)
- CI enforcement / GitHub App (v2).
- Tracking scores over time or per person. No surveillance features.
- Quizzing on docs-only, lockfile, or generated-file changes.

## Expectations → test cases
Fixtures: `tests/fixtures/*.diff` holds canned diffs. Risk scoring is deterministic code → unit tests. Question and grading quality are LLM behavior → eval cases with an LLM judge.

| ID | Given | When | Then |
|---|---|---|---|
| E1 | Diff with 1 auth-check removal + 5 cosmetic hunks | Risk scorer | Auth hunk ranks #1 (unit test) |
| E2 | Diff of only `*.md`, lockfiles, `dist/` | Skill runs | Says "nothing to quiz" and asks no questions |
| E3 | Any quiz | Inspect each question | Cites a real `file:line` inside the diff |
| E4 | Quiz in progress | Before the user answers | The question message contains no answer (judge) |
| E5 | Correct user answer (fixture) | Grading | `pass` |
| E6 | Plausible but wrong answer (fixture) | Grading | `miss` or `partial`, with an explanation pointing at the right line |
| E7 | User says "skip" | Summary | Summary records the skip; no nagging |
| E8 | 2,000-line diff | Skill runs | Still asks ≤5 questions, all on top-scored hunks |
| E9 | Finished quiz | Summary block | Valid Markdown; contains the score and topics missed |

## Done when
- E1–E9 pass. GIF of a real 3-question quiz on an agent-written PR.
- README cites the Anthropic comprehension study as the "why".
