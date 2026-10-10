#!/usr/bin/env python3
"""Scan the repository for personal data that must never be published.

Looks for: e-mail addresses, phone numbers, ID-card numbers (Chinese 18-digit with check
digit), card and account numbers (16 to 19 digits, plain or grouped by four), Google Drive
file and folder IDs, private IP addresses and home-directory paths with a real user name.
Placeholders pass: example.com / noreply addresses, user names user, me, you, alice, bob,
and masked numbers (asterisks). A line can be allowed with the marker  sensitive-scan: ignore

Usage:
  python3 scripts/sensitive_scan.py                 every tracked file
  python3 scripts/sensitive_scan.py --range A..B    only lines added between two commits
Exit code 1 when anything is found.
"""
import argparse
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MARK = "sensitive-scan: ignore"
SKIP_EXT = {".png", ".jpg", ".jpeg", ".gif", ".zip", ".pdf", ".ico"}
OK_USERS = {"user", "me", "you", "alice", "bob", "runner", "name", "username", "<user>", "claude"}

RULES = [
    ("e-mail", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
     lambda m: re.search(r"@(example\.(com|org|net)|users\.noreply\.github\.com|anthropic\.com)$", m.group(0), re.I)),
    ("phone", re.compile(r"(?<![\d.])(?:\+?86[- ]?)?1[3-9]\d{9}(?!\d)"), None),
    ("phone", re.compile(r"(?<![\d.])\+?\d{1,3}[- ]\(?\d{2,4}\)?[- ]\d{3,4}[- ]\d{3,4}(?!\d)"), None),
    ("ID number", re.compile(r"(?<!\d)[1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx](?!\d)"), None),
    ("card number", re.compile(r"(?<![\d-])(?:\d{4}[ -]){3}\d{4,7}(?![\d-])|(?<!\d)\d{16,19}(?!\d)"), None),
    ("Drive ID", re.compile(r"(?<![A-Za-z0-9_-])1[A-Za-z0-9_-]{32}(?![A-Za-z0-9_-])"),
     lambda m: not (re.search(r"\d", m.group(0)[1:]) and re.search(r"[A-Za-z]", m.group(0)))),
    ("private IP", re.compile(r"(?<![\d.])(?:10|192\.168|172\.(?:1[6-9]|2\d|3[01]))(?:\.\d{1,3}){2,3}(?![\d.])"), None),
    ("home path", re.compile(r"(?:/home/|/Users/|[A-Za-z]:\\\\Users\\\\)([A-Za-z0-9._-]+)"),
     lambda m: m.group(1).lower() in OK_USERS),
]


def tracked_files():
    out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True).stdout
    return [f for f in out.decode("utf-8").split("\0") if f]


def added_lines(rng):
    out = subprocess.run(["git", "diff", "-U0", "--no-color", rng], cwd=ROOT, capture_output=True,
                         check=True).stdout.decode("utf-8", "replace")
    current, lineno = None, 0
    for line in out.split("\n"):
        if line.startswith("+++ "):
            current = line[6:] if line.startswith("+++ b/") else None
        elif line.startswith("@@"):
            m = re.search(r"\+(\d+)", line)
            lineno = int(m.group(1)) if m else 0
        elif line.startswith("+") and current:
            yield current, lineno, line[1:]
            lineno += 1


def file_lines(files):
    for f in files:
        if os.path.splitext(f)[1].lower() in SKIP_EXT or f == "scripts/sensitive_scan.py":
            continue
        try:
            with open(os.path.join(ROOT, f), encoding="utf-8") as fh:
                for i, line in enumerate(fh, 1):
                    yield f, i, line.rstrip("\n")
        except (UnicodeDecodeError, OSError):
            continue


def scan(lines):
    hits = 0
    for f, i, line in lines:
        if MARK in line or f == "scripts/sensitive_scan.py":
            continue
        for label, rx, allow in RULES:
            for m in rx.finditer(line):
                if allow and allow(m):
                    continue
                hits += 1
                print(f"{f}:{i}: {label}: {m.group(0)}")
                if os.environ.get("GITHUB_ACTIONS"):
                    print(f"::error file={f},line={i}::possible {label}")
    return hits


def main():
    ap = argparse.ArgumentParser(description="Scan for personal data")
    ap.add_argument("--range")
    a = ap.parse_args()
    lines = added_lines(a.range) if a.range else file_lines(tracked_files())
    hits = scan(lines)
    print(f"result: {hits} possible findings" if hits else "result: clean")
    sys.exit(1 if hits else 0)


if __name__ == "__main__":
    main()
