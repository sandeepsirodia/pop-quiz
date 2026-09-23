# Installing pop-quiz (instructions for coding agents)

If a user asked you to install this skill, do this:

1. Fetch both files. The skill needs its bundled scorer:
   - `https://raw.githubusercontent.com/sandeepsirodia/pop-quiz/main/skills/pop-quiz/SKILL.md`
   - `https://raw.githubusercontent.com/sandeepsirodia/pop-quiz/main/skills/pop-quiz/scripts/score.py`
2. Install them together, keeping the `scripts/` subfolder:
   - **Claude Code:** `~/.claude/skills/pop-quiz/` (all projects) or `.claude/skills/pop-quiz/` (this project only). Ask which, defaulting to all projects.
   - **Codex:** `~/.codex/skills/pop-quiz/`
   - **Cursor:** `.cursor/skills/pop-quiz/`
   - **Anything else:** put both in `.agents/pop-quiz/`, and add a line to the project's `AGENTS.md`: "When the user says /pop-quiz or asks to be quizzed on their diff, follow .agents/pop-quiz/SKILL.md."
3. Don't overwrite existing files without showing the user a diff first.
4. Tell the user it's installed. They can run `/pop-quiz` on any branch, starting from the next session.
