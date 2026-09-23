#!/usr/bin/env python3
"""Eval runner for a SKILL.md: replays scripted conversations with the skill ON and OFF,
then scores each reply with regex checks and an LLM judge. Uses the `claude` CLI.

    python3 evals/run_evals.py                      # skill on vs off, sonnet
    python3 evals/run_evals.py --model haiku --only E3

Case format (evals/cases.jsonl), one JSON object per line:
    {"id": "...", "expect": "E3", "context": "optional extra system context",
     "messages": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}, ...],
     "regex": ["must match"], "not_regex": ["must not match"], "judge": "rubric for a PASS"}
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASELINE = "You are a helpful AI coding assistant."
JUDGE = ("You are a strict evaluator. Given a RUBRIC and an assistant REPLY, decide whether the reply meets the "
         "rubric. Reply with only a JSON object: {\"pass\": true|false, \"reason\": \"one sentence\"}.")


def claude(system, prompt, model):
    cmd = ["claude", "-p", prompt, "--system-prompt", system, "--tools", "", "--no-session-persistence",
           "--output-format", "json", "--model", model]
    # --bare skips the user's hooks/CLAUDE.md for clean evals but needs an API key;
    # with a subscription login, skip user settings instead.
    cmd += ["--bare"] if os.environ.get("ANTHROPIC_API_KEY") else ["--setting-sources", ""]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    data = json.loads(r.stdout)
    if data.get("is_error"):
        raise RuntimeError(data.get("result"))
    return data["result"], data.get("total_cost_usd") or 0.0


def transcript(messages):
    lines = ["Here is a conversation so far. Write ONLY the assistant's next reply.", ""]
    for m in messages:
        lines.append("%s: %s" % ("User" if m["role"] == "user" else "Assistant", m["content"]))
        lines.append("")
    return "\n".join(lines)


def parse_verdict(text):
    # Try every "{" as a JSON start: the judge may quote code with braces around its verdict.
    dec = json.JSONDecoder()
    for i, ch in enumerate(text):
        if ch == "{":
            try:
                v, _ = dec.raw_decode(text, i)
            except ValueError:
                continue
            if isinstance(v, dict) and "pass" in v:
                return bool(v["pass"]), v.get("reason", "")
    return False, "unparseable judge output"


def check(case, reply, judge_model):
    """Return (passed, reasons, cost)."""
    reasons, cost = [], 0.0
    for rx in case.get("regex", []):
        if not re.search(rx, reply, re.I | re.M):
            reasons.append("missing /%s/" % rx)
    for rx in case.get("not_regex", []):
        if re.search(rx, reply, re.I | re.M):
            reasons.append("matched forbidden /%s/" % rx)
    if case.get("judge"):
        out, c = claude(JUDGE, "RUBRIC:\n%s\n\nREPLY:\n%s" % (case["judge"], reply), judge_model)
        cost += c
        ok, why = parse_verdict(out)
        if not ok:
            reasons.append("judge: " + why)
    return not reasons, reasons, cost


def load_cases(path, only=None):
    with open(path, encoding="utf-8") as f:
        cases = [json.loads(l) for l in f if l.strip()]
    return [c for c in cases if not only or c["expect"] in only or c["id"] in only]


def run_case(case, mode, skill, args):
    system = (skill if mode == "on" else BASELINE) + ("\n\n" + case["context"] if case.get("context") else "")
    reply, cost = claude(system, transcript(case["messages"]), args.model)
    ok, reasons, jcost = check(case, reply, args.judge_model)
    return {"id": case["id"], "expect": case["expect"], "mode": mode, "pass": ok,
            "reasons": reasons, "reply": reply, "cost": cost + jcost}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--cases", default=os.path.join(ROOT, "evals", "cases.jsonl"))
    ap.add_argument("--skill", default=(glob.glob(os.path.join(ROOT, "skills", "*", "SKILL.md")) or [None])[0])
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--judge-model", default="sonnet")
    ap.add_argument("--modes", default="off,on", help="off,on | on | off")
    ap.add_argument("--only", nargs="*", help="expectation ids (E3) or case ids")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--out", default=os.path.join(ROOT, "evals", "results.json"))
    args = ap.parse_args()

    with open(args.skill, encoding="utf-8") as f:
        skill = re.sub(r"^---.*?---\s*", "", f.read(), flags=re.S)  # drop frontmatter
    cases = load_cases(args.cases, args.only)
    jobs = [(c, m) for m in args.modes.split(",") for c in cases]
    with ThreadPoolExecutor(args.jobs) as pool:
        results = list(pool.map(lambda cm: run_case(cm[0], cm[1], skill, args), jobs))

    for r in results:
        if not r["pass"]:
            print("FAIL [%s] %-28s %s" % (r["mode"], r["id"], "; ".join(r["reasons"])))
    print("\n| Expectation | " + " | ".join("skill %s" % m for m in args.modes.split(",")) + " |")
    print("|---|" + "---|" * len(args.modes.split(",")))
    for e in sorted({c["expect"] for c in cases}) + ["ALL"]:
        cells = []
        for m in args.modes.split(","):
            rs = [r for r in results if r["mode"] == m and (e == "ALL" or r["expect"] == e)]
            cells.append("%d/%d" % (sum(r["pass"] for r in rs), len(rs)))
        print("| %s | %s |" % (e, " | ".join(cells)))
    print("\nModel: %s · judge: %s · cost: $%.2f" % (args.model, args.judge_model, sum(r["cost"] for r in results)))
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print("Replies saved to %s" % os.path.relpath(args.out))


if __name__ == "__main__":
    sys.exit(main())
