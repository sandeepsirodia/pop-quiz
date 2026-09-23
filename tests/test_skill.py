"""Offline checks for the skill file and eval set (the conversation itself is measured by evals/)."""
import json
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(ROOT, "skills", "pop-quiz", "SKILL.md")


class TestSkill(unittest.TestCase):
    def test_frontmatter(self):
        text = open(SKILL, encoding="utf-8").read()
        fm = dict(re.findall(r"^(\w+):\s*(.+)$", re.match(r"^---\n(.*?)\n---\n", text, re.S).group(1), re.M))
        self.assertEqual(fm["name"], "pop-quiz")
        self.assertTrue(20 < len(fm["description"]) <= 1024)

    def test_skill_references_bundled_scorer(self):
        self.assertIn("scripts/score.py", open(SKILL, encoding="utf-8").read())
        self.assertTrue(os.path.exists(os.path.join(ROOT, "skills", "pop-quiz", "scripts", "score.py")))

    def test_eval_cases(self):
        with open(os.path.join(ROOT, "evals", "cases.jsonl"), encoding="utf-8") as f:
            cases = [json.loads(l) for l in f if l.strip()]
        self.assertEqual({c["expect"] for c in cases}, {"E2", "E3", "E4", "E5", "E6", "E7", "E9"})
        for c in cases:
            self.assertEqual(c["messages"][-1]["role"], "user")
            self.assertTrue(c.get("judge") or c.get("regex"), c["id"])


if __name__ == "__main__":
    unittest.main()
