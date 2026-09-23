# pop-quiz

**You didn't write it. Can you explain it?**

A pre-merge comprehension check for AI-written code. `/pop-quiz` reads your branch diff, finds the riskiest hunks (auth, money, concurrency, removed checks), and asks you 3–5 questions about them, one at a time. It grades your answers against the actual code.

```
> /pop-quiz

Q1/3 · api/users.py:41
After this change, what happens when a regular (non-admin) logged-in user
calls delete_user with someone else's id?

> nothing, django checks permissions on the view anyway

❌ miss. There's no other guard: the `if not current.is_admin` check at
api/users.py:41 was the only one, and this diff removes it. Any logged-in
user can now delete any account.

Q2/3 · billing/refund.py:12
…
```

At the end you get a summary to paste into the PR:

| # | Where | Topic | Result |
|---|---|---|---|
| 1 | `api/users.py:41` | removed admin check | ❌ miss |
| 2 | `billing/refund.py:12` | refunds above the paid amount | ✅ pass |
| 3 | `wallet/transfer.py:22` | why the row lock existed | 🟡 partial |

## Why

In [Anthropic's study of AI-assisted coding](https://www.anthropic.com/research/AI-assistance-coding-skills), developers who used AI finished just as fast but scored **17% lower on a comprehension quiz** afterwards, with the biggest drop in debugging. That's *comprehension debt*: code that works, merged by people who couldn't explain it during an incident.

pop-quiz is a 2-minute habit that pays it down, on the exact lines that would hurt most.

## Install

**Claude Code**

```
/plugin marketplace add sandeepsirodia/pop-quiz
/plugin install pop-quiz@pop-quiz
```

**Cursor, Codex, and 20+ other agents** via the open [skills CLI](https://github.com/antfu/skills-cli):

```bash
npx skills add sandeepsirodia/pop-quiz
```

Then, on any branch: `/pop-quiz` (or "quiz me on this diff").

## How it picks questions

A small deterministic scorer ([`scripts/score.py`](skills/pop-quiz/scripts/score.py), stdlib Python) ranks every hunk of `git diff $(git merge-base main HEAD)`, and every point has a reason:

| Signal | Points |
|---|---|
| touches auth / permissions (`is_admin`, `session`, `jwt`, `role`…) | 5 |
| touches money (`amount`, `balance`, `refund`, `currency`…) | 5 |
| concurrency / locking (`lock`, `transaction`, `atomic`, `async`…) | 4 |
| removes error handling (`try`/`except`/`catch`/`raise`…) | 4 |
| removes a check or validation (`if`, `assert`, `validate()`…) | 4 |
| SQL / shell / eval | 4 |
| config / infra (`Dockerfile`, workflows, `*.tf`, `*.yaml`) | 3 |
| pure deletion | 2 |
| hunk size | up to 3 |

Docs, lockfiles, snapshots, and build output are never quizzed. Run it yourself to see the ranking:

```bash
python3 skills/pop-quiz/scripts/score.py --base main
```

## Rules the quiz follows

- **One question at a time**, each citing `file:line`. At most 5, however big the diff.
- **Never hints at the answer** before you reply.
- **Honest grading**: a plausible-sounding wrong answer is a ❌, not a "great effort!".
- **Never blocks you.** Say `skip` to skip a question or `stop` to end the quiz. Skips are noted in the summary, and there's no nagging.

## Development

```bash
python -m unittest discover -s tests -v          # scorer + skill checks, no model needed
python3 evals/run_evals.py --modes on            # conversation evals via the claude CLI
```

Tests and evals map to the expectations in [SPEC.md](SPEC.md).

MIT © Sandeep Sirodia
