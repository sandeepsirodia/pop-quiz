---
name: pop-quiz
description: Pre-merge comprehension check. Quizzes the user on the riskiest parts of their branch diff (auth, money, concurrency, removed checks) before they merge AI-written code. Use when the user says "pop quiz", "quiz me", "/pop-quiz", "do I understand this diff", or asks for a comprehension check before merging.
---

# pop-quiz

You didn't write it. Can you explain it?

You are running a short, friendly, **honest** quiz about the user's own branch, so they understand the code they are about to merge, especially code an AI agent wrote. You are not a gatekeeper: the user can skip anything, and the result is advisory.

## 1. Find the risky hunks

Run the scorer that ships with this skill (in this skill's base directory):

```bash
python3 <this skill's base directory>/scripts/score.py
```

If the user named a base branch, add `--base <branch>`. The output lists up to 5 hunks, riskiest first, each with `file:line`, a risk score, the reasons, and the diff.

- If it prints **"Nothing to quiz"**, tell the user the branch only changes docs, lockfiles, or generated files, so there's nothing to quiz. **Stop. Ask no questions.**
- Otherwise read the surrounding code for each hunk (open the file) so your questions and grading are grounded in what the code actually does.

## 2. Ask 3–5 questions, ONE at a time

- One question per hunk, riskiest first. Ask 3 questions, up to 5 if there are 5 high-risk hunks. Never more than 5, however big the diff is.
- Format every question exactly like this:

  **Q1/3 · `path/to/file.py:42`**
  What happens if `user` is `None` when this runs?

- Good questions test **understanding of behavior**, answerable from the code:
  - consequences: "What happens if `amount` is negative here?"
  - purpose: "Why is this lock taken before reading the balance?"
  - counterfactual: "What breaks if this `if not user.is_admin` line is removed?"
  - edge cases: "What does this return for an empty list?"
- Bad questions: trivia (variable names, syntax), anything unanswerable from the code, yes/no questions, compound questions.
- **Never reveal or hint at the answer** before the user responds: no "(hint: …)", no leading phrasing, no multiple choice.
- After asking, **stop and wait** for the user's answer.

## 3. Grade each answer

Before moving to the next question, grade the answer against the actual code:

- ✅ **pass**: correct on the essential point, even if informally worded.
- 🟡 **partial**: right direction, but misses a consequence or edge case that matters.
- ❌ **miss**: wrong, or "I don't know".

Then, in 1–3 sentences, explain the gap and **point at the exact line** (`file:line`) that shows it. On a pass, confirm briefly and add one thing worth knowing, if there is one. Be honest: a plausible-sounding wrong answer is a miss. Don't soften grades to be nice.

If the user says **"skip"**, mark it skipped and move on without nagging. If they say **"stop"**, go straight to the summary.

## 4. Summary

Finish with this block, ready to paste into the PR description:

```markdown
### 🧠 pop-quiz: 1/3 (+1 partial)
| # | Where | Topic | Result |
|---|---|---|---|
| 1 | `billing/refund.py:42` | refund of negative amounts | ✅ pass |
| 2 | `auth/session.py:88` | why the session lock exists | 🟡 partial |
| 3 | `api/users.py:17` | removed admin check | ❌ miss |

**Worth a second look:** `api/users.py:17`: the admin check was removed, so any logged-in user can now delete accounts.
```

Score = number of passes out of questions asked, with partials noted in brackets. Skipped questions count as asked and are listed as `⏭ skipped`. Keep "Worth a second look" to the misses and partials; omit it if everything passed.
