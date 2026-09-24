<h1 align="center">pop-quiz</h1>

<p align="center">
  <em>You didn't write it. Can you explain it?</em>
</p>

<p align="center">
  <a href="https://github.com/sandeepsirodia/pop-quiz/actions/workflows/ci.yml"><img src="https://github.com/sandeepsirodia/pop-quiz/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <img src="https://img.shields.io/badge/works%20with-Claude%20Code%20·%20Cursor%20·%20Codex-111111?style=flat-square" alt="Works with Claude Code, Cursor, Codex">
  <img src="https://img.shields.io/badge/takes-2%20minutes-111111?style=flat-square" alt="Takes 2 minutes">
  <img src="https://img.shields.io/badge/license-MIT-111111?style=flat-square" alt="MIT">
</p>

---

It's 2am. Prod is down. The stack trace points at a file you merged last week.

You open it. You recognize the PR title. You do not recognize a single line, because you didn't write them. The agent did. You skimmed it, the tests were green, and you clicked merge.

That gap has a name: **comprehension debt.** In [Anthropic's own study](https://www.anthropic.com/research/AI-assistance-coding-skills), developers who coded with AI finished just as fast, then scored **17% lower** on a quiz about the code they'd just written. The biggest drop was in debugging, which is exactly the skill you need at 2am.

**pop-quiz pays that debt down before you merge.** Type `/pop-quiz`. It finds the three scariest changes in your branch and asks you about them. Two minutes, and you either understand your code or you find the bug.

## What it feels like

```
> /pop-quiz

Q1/3 · api/users.py:41
After this change, what happens when a regular (non-admin) logged-in user
calls delete_user with someone else's id?

> nothing, django checks permissions on the view anyway

❌ Miss. Django doesn't check permissions on a plain view by default.
The `if not current.is_admin` block this diff removes at api/users.py:41
was the only guard, so any logged-in user can now delete any account.

Q2/3 · billing/refund.py:12
…
```

That "miss" is the most valuable 30 seconds of your week. The quiz found a privilege escalation that the tests missed.

At the end you get a summary to paste straight into the PR:

| # | Where | Topic | Result |
|---|---|---|---|
| 1 | `api/users.py:41` | removed admin check | ❌ miss |
| 2 | `billing/refund.py:12` | refunds above the paid amount | ✅ pass |
| 3 | `wallet/transfer.py:22` | why the row lock existed | 🟡 partial |

## Install

**Easiest:** paste this into Claude Code, Cursor, or Codex:

```text
Install the pop-quiz skill from https://github.com/sandeepsirodia/pop-quiz — follow the repo's AGENTS.md
```

**Claude Code plugin:**

```
/plugin marketplace add sandeepsirodia/pop-quiz
/plugin install pop-quiz@pop-quiz
```

**Any agent** via the open [skills CLI](https://github.com/antfu/skills-cli):

```bash
npx skills add sandeepsirodia/pop-quiz
```

Then, on any branch: **`/pop-quiz`**.

## How it picks what to ask

It doesn't quiz you on renamed variables. A small, deterministic scorer ranks every hunk of your diff, and every point comes with a reason:

| What changed | Risk |
|---|:-:|
| auth / permissions (`is_admin`, `session`, `jwt`, `role`…) | 🔥🔥🔥🔥🔥 |
| money (`amount`, `refund`, `balance`, `currency`…) | 🔥🔥🔥🔥🔥 |
| locks, transactions, async | 🔥🔥🔥🔥 |
| a removed `try` / `except` / `raise` | 🔥🔥🔥🔥 |
| a removed `if` / `assert` / `validate()` | 🔥🔥🔥🔥 |
| SQL, shell, `eval` | 🔥🔥🔥🔥 |
| Dockerfiles, workflows, `*.tf`, config | 🔥🔥🔥 |

Docs, lockfiles, snapshots and build output are never quizzed. Curious? Run the scorer yourself:

```bash
python3 skills/pop-quiz/scripts/score.py --base main
```

## House rules

- **One question at a time,** each pointing at `file:line`. At most 5, even on a 2,000-line diff.
- **No hints.** It never gives away the answer in the question.
- **Honest grading.** A confident wrong answer is a ❌, not "great effort!".
- **Never a gate.** Type `skip` or `stop` whenever you like. It notes the skip and moves on, with no lecture.

## Does it behave?

8 scripted conversations: the first question, no answer leaks, grading a right answer, grading two plausible wrong ones, skipping, the summary format, and "nothing to quiz". Claude Sonnet with an LLM judge passed **8/8**, and the replies are [saved here](evals/results.json), including the privilege-escalation catch above.

## Prior art, and what's new here

- **[Gater](https://usegater.app/)** is a hosted service that quizzes teams on PRs.
- Other "merge quiz" prompts exist as skills.

pop-quiz is local and free. Its question targeting is a **deterministic, explainable risk scorer**, so you can see why each hunk was chosen, and its behavior is checked by an eval set with saved replies.

<details>
<summary><b>Development</b></summary>

```bash
python -m unittest discover -s tests -v    # scorer + skill checks, no model needed
python3 evals/run_evals.py --modes on      # conversation evals via the claude CLI
```

Tests and evals map to [SPEC.md](SPEC.md).

</details>

<p align="center"><sub>MIT © Sandeep Sirodia · If pop-quiz caught something before prod did, a ⭐ helps others find it.</sub></p>
