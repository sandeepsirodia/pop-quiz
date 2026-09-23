"""Deterministic half of pop-quiz: the risk scorer (SPEC E1, E2, E8 + citations).
The conversational half (E3-E7, E9) is covered by evals/, which need a model."""
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "skills", "pop-quiz", "scripts"))
import score  # noqa: E402


def filediff(path, old_start, removed, added, context=("    pass",)):
    """A one-hunk unified diff for `path`."""
    body = ["+" + l for l in added] + ["-" + l for l in removed]
    body = [" " + context[0]] + body + [" " + context[0]]
    n_old = len(removed) + 2
    n_new = len(added) + 2
    return "diff --git a/{p} b/{p}\n--- a/{p}\n+++ b/{p}\n@@ -{o},{no} +{o},{nn} @@\n{b}\n".format(
        p=path, o=old_start, no=n_old, nn=n_new, b="\n".join(body))


AUTH_REMOVAL = filediff("api/users.py", 40, removed=["    if not current_user.is_admin:", "        raise Forbidden()"], added=[])
COSMETIC = [filediff("ui/button%d.py" % i, 10, removed=["    label = 'Ok'"], added=["    label = \"OK\""]) for i in range(5)]


class TestSpec(unittest.TestCase):
    def test_e1_auth_check_removal_ranks_first(self):
        top, total = score.rank("".join(COSMETIC[:3] + [AUTH_REMOVAL] + COSMETIC[3:]))
        self.assertEqual(total, 6)
        self.assertEqual(top[0]["file"], "api/users.py")
        self.assertIn("touches auth / permissions", top[0]["reasons"])
        self.assertIn("removes a check / validation", top[0]["reasons"])
        self.assertIn("removes error handling", top[0]["reasons"])
        self.assertGreater(top[0]["score"], top[1]["score"])

    def test_e2_docs_lockfiles_generated_only(self):
        diff = "".join([
            filediff("README.md", 1, ["old"], ["new"]),
            filediff("docs/guide.rst", 1, ["old"], ["new"]),
            filediff("package-lock.json", 1, ['"x": 1'], ['"x": 2']),
            filediff("poetry.lock", 1, ["a"], ["b"]),
            filediff("dist/app.min.js", 1, ["a"], ["b"]),
            filediff("src/__snapshots__/a.snap", 1, ["a"], ["b"]),
        ])
        top, total = score.rank(diff)
        self.assertEqual((top, total), ([], 0))
        out = io.StringIO()
        with mock.patch.object(score, "read_diff", return_value=diff):
            score.main(["--base", "main"], out=out)
        self.assertIn("Nothing to quiz", out.getvalue())

    def test_e8_huge_diff_caps_at_five_top_scored(self):
        hunks = [filediff("src/f%03d.py" % i, 1, ["x = %d" % i], ["x = %d" % (i + 1)]) for i in range(400)]
        hunks[123] = filediff("src/pay.py", 1, ["    balance -= amount"], ["    with lock:", "        balance -= amount"])
        hunks[321] = AUTH_REMOVAL
        diff = "".join(hunks)
        self.assertGreater(len(diff.splitlines()), 2000)
        top, total = score.rank(diff, top=50)  # caller asks for 50; still capped by main()
        self.assertEqual(total, 400)
        top5, _ = score.rank(diff, top=5)
        self.assertEqual(len(top5), 5)
        self.assertEqual({h["file"] for h in top5[:2]}, {"src/pay.py", "api/users.py"})
        out = io.StringIO()
        with mock.patch.object(score, "read_diff", return_value=diff):
            score.main(["--base", "main", "--top", "50", "--json"], out=out)
        self.assertEqual(len(json.loads(out.getvalue())["hunks"]), 5)

    def test_cites_first_changed_line(self):
        diff = ("diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -10,4 +10,5 @@\n"
                " ctx1\n ctx2\n+if password:\n+    login()\n ctx3\n")
        top, _ = score.rank(diff)
        self.assertEqual(top[0]["line"], 12)

    def test_prose_select_is_not_sql(self):
        _, reasons = score.score({"file": "a.py", "added": ["# select a file from the list"], "removed": []})
        self.assertNotIn("SQL / shell / eval", reasons)
        _, reasons = score.score({"file": "a.py", "added": ["q = 'SELECT * FROM users WHERE id=' + uid"], "removed": []})
        self.assertIn("SQL / shell / eval", reasons)

    def test_new_and_deleted_files(self):
        diff = ("diff --git a/new.py b/new.py\nnew file mode 100644\n--- /dev/null\n+++ b/new.py\n@@ -0,0 +1,2 @@\n"
                "+import subprocess\n+subprocess.run(cmd, shell=True)\n"
                "diff --git a/old.py b/old.py\ndeleted file mode 100644\n--- a/old.py\n+++ /dev/null\n@@ -1,1 +0,0 @@\n"
                "-x = 1\n")
        top, total = score.rank(diff)
        self.assertEqual(total, 2)
        self.assertEqual(top[0]["file"], "new.py")
        self.assertEqual(top[1]["file"], "old.py")
        self.assertIn("deletes code", top[1]["reasons"])


class TestGit(unittest.TestCase):
    def test_branch_vs_main_end_to_end(self):
        d = tempfile.mkdtemp()
        g = lambda *a: subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false",  # noqa: E731
                                       "-c", "core.hooksPath=/dev/null", *a], cwd=d, check=True, capture_output=True)
        g("init", "-q", "-b", "main")
        with open(os.path.join(d, "auth.py"), "w") as f:
            f.write("def delete(user):\n    if not user.is_admin:\n        raise Forbidden()\n    db.delete()\n")
        g("add", ".")
        g("commit", "-qm", "init")
        g("checkout", "-qb", "feature")
        with open(os.path.join(d, "auth.py"), "w") as f:
            f.write("def delete(user):\n    db.delete()\n")
        g("commit", "-qam", "simplify")
        r = subprocess.run([sys.executable, os.path.join(ROOT, "skills", "pop-quiz", "scripts", "score.py"), "--json"],
                           cwd=d, capture_output=True, text=True, check=True)
        hunks = json.loads(r.stdout)["hunks"]
        self.assertEqual(hunks[0]["file"], "auth.py")
        self.assertIn("touches auth / permissions", hunks[0]["reasons"])


if __name__ == "__main__":
    unittest.main()
