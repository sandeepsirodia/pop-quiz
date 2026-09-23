#!/usr/bin/env python3
"""pop-quiz risk scorer: rank the hunks of a branch diff by how much they deserve a question.

Deterministic and explainable: every point comes with a reason. Reads `git diff <base>...HEAD`
(or a diff on stdin with `-`) and prints the top hunks as JSON or Markdown.
"""
import argparse
import json
import re
import subprocess
import sys

SKIP = re.compile(
    r"\.(md|mdx|rst|txt|adoc|lock|map|snap|svg|png|jpe?g|gif|ico|pdf)$|\.min\.(js|css)$|"
    r"(^|/)(package-lock\.json|yarn\.lock|pnpm-lock\.yaml|poetry\.lock|Cargo\.lock|go\.sum|uv\.lock|"
    r"Gemfile\.lock|composer\.lock|CHANGELOG[^/]*|LICENSE[^/]*)$|"
    r"(^|/)(dist|build|vendor|node_modules|__snapshots__|generated|\.next)/", re.I)

# (reason, points, regex, where): where = "any" changed line, "removed" lines only, or "path"
RULES = [
    ("touches auth / permissions", 5, r"\b(auth\w*|permission\w*|authori[sz]\w*|role|roles|admin|is_?admin|"
                                      r"csrf|jwt|session|password|passwd|acl|login|logout|oauth|sudo|privilege\w*)\b", "any"),
    ("touches money", 5, r"\b(price|amount|balance|payment\w*|invoice\w*|refund\w*|charge\w*|currency|cents|"
                         r"billing|subtotal|tax|discount|payout\w*|ledger)\b", "any"),
    ("concurrency / locking", 4, r"\b(lock|unlock|mutex|rwlock|semaphore|atomic\w*|race|thread\w*|goroutine|"
                                  r"async|await|synchronized|transaction|deadlock|concurrent\w*)\b", "any"),
    ("removes error handling", 4, r"\b(try|except|catch|finally|raise|throw|rescue|recover)\b|if err != nil|\.catch\(",
     "removed"),
    ("removes a check / validation", 4, r"^\s*(if|elif|else if|unless|guard|assert|require|ensure)\b|"
                                         r"\b(validate\w*|sanitize\w*|check\w*|verify\w*)\(", "removed"),
    # case-sensitive (?-i:…) so prose like "select a file" doesn't count as SQL
    ("SQL / shell / eval", 4, r"(?-i:\b(SELECT|INSERT\s+INTO|UPDATE\s+\w+\s+SET|DELETE\s+FROM|DROP\s+TABLE)\b)|"
                              r"\b(subprocess|os\.system|exec|eval|child_process|spawn|popen|shell=True)\b", "any"),
    ("config / infra", 3, r"(^|/)(Dockerfile|docker-compose[^/]*|\.github/workflows/|terraform/|k8s/|helm/)|"
                          r"\.(tf|ya?ml|toml|ini|env)$|(^|/)config/", "path"),
    ("deletes code", 2, r"\S", "removed-only"),
]
RULES = [(r, p, re.compile(rx, re.I), w) for r, p, rx, w in RULES]


def default_base():
    for ref in ("origin/HEAD", "origin/main", "origin/master", "main", "master"):
        if subprocess.run(["git", "rev-parse", "--verify", "-q", ref], capture_output=True).returncode == 0:
            return ref
    return "HEAD~1"


def read_diff(base):
    if base == "-":
        return sys.stdin.read()
    mb = subprocess.run(["git", "merge-base", base, "HEAD"], capture_output=True, text=True)
    ref = mb.stdout.strip() if mb.returncode == 0 else base
    return subprocess.run(["git", "diff", "--no-color", "-U2", ref], capture_output=True, text=True, check=True).stdout


def parse(diff):
    """Yield hunks: {file, line, added: [..], removed: [..], text}."""
    file, hunk = None, None
    for raw in diff.splitlines():
        if raw.startswith("diff --git"):
            if hunk:
                yield hunk
            file, hunk = None, None
        elif raw.startswith("+++ "):
            path = raw[4:].strip()
            if path != "/dev/null":  # deleted file: keep the name from the `---` line
                file = re.sub(r"^b/", "", path)
        elif raw.startswith("--- "):
            if file is None:
                old = raw[4:].strip()
                file = None if old == "/dev/null" else re.sub(r"^a/", "", old)
        elif raw.startswith("@@"):
            if hunk:
                yield hunk
            m = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)", raw)
            cur = int(m.group(1)) if m else 1  # line number in the new file
            hunk = {"file": file, "line": None, "added": [], "removed": [], "text": [raw]}
        elif hunk is not None:
            hunk["text"].append(raw)
            if raw.startswith(("+", "-")) and hunk["line"] is None:
                hunk["line"] = cur  # cite the first changed line, not the context above it
            if raw.startswith("+"):
                hunk["added"].append(raw[1:])
                cur += 1
            elif raw.startswith("-"):
                hunk["removed"].append(raw[1:])
            else:
                cur += 1
    if hunk:
        yield hunk


def score(h):
    reasons, points = [], 0
    changed = h["added"] + h["removed"]
    for reason, pts, rx, where in RULES:
        if where == "path":
            hit = bool(rx.search(h["file"] or ""))
        elif where == "removed":
            hit = any(rx.search(l) for l in h["removed"])
        elif where == "removed-only":
            hit = bool(h["removed"]) and not h["added"]
        else:
            hit = any(rx.search(l) for l in changed)
        if hit:
            reasons.append(reason)
            points += pts
    size = len([l for l in changed if l.strip()])
    size_pts = min(3, size // 20)
    if size_pts:
        reasons.append("large hunk (%d lines)" % size)
        points += size_pts
    return points, reasons


def rank(diff, top=5):
    hunks = []
    for h in parse(diff):
        if not h["file"] or SKIP.search(h["file"]) or not (h["added"] or h["removed"]):
            continue
        pts, reasons = score(h)
        hunks.append({"file": h["file"], "line": h["line"], "score": pts, "reasons": reasons,
                      "diff": "\n".join(h["text"])})
    hunks.sort(key=lambda x: (-x["score"], x["file"], x["line"]))
    return hunks[:top], len(hunks)


def main(argv=None, out=None):
    out = out or sys.stdout
    ap = argparse.ArgumentParser(description="Rank diff hunks by risk for pop-quiz.")
    ap.add_argument("--base", help="base ref (default: origin/HEAD, main, or master); '-' reads a diff from stdin")
    ap.add_argument("--top", type=int, default=5, help="max hunks (default 5)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    top, total = rank(read_diff(a.base or default_base()), max(1, min(a.top, 5)))
    if a.json:
        out.write(json.dumps({"total_quizzable_hunks": total, "hunks": top}, indent=2) + "\n")
    elif not top:
        out.write("Nothing to quiz: only docs, lockfiles, or generated files changed.\n")
    else:
        for i, h in enumerate(top, 1):
            out.write("## %d. %s:%d (risk %d: %s)\n```diff\n%s\n```\n\n" % (
                i, h["file"], h["line"], h["score"], ", ".join(h["reasons"]) or "general change", h["diff"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
