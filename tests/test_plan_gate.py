"""Tests for plan_gate.py. Standard library only: python3 -m unittest discover -s tests"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.join(ROOT, ".claude", "hooks")
SCRIPT = os.path.join(HERE, "plan_gate.py")
sys.path.insert(0, HERE)
import plan_gate as pg  # noqa: E402


class BashRules(unittest.TestCase):
    READS = [
        "ls -la", "cat a.txt | grep x 2>&1", "git status && git log --oneline -3", "git -C ../x diff",
        "python3 t.py 2>/dev/null", "sed -n 1,5p f", "git branch -a", "find . -exec grep -l y {} +",
        "gh pr view 3", "gh api repos/a/b", "curl -s https://example.com", "python3 -m unittest",
        "for f in *; do echo $f; done", 'echo "a > b"', "git stash list", "git config --get user.name",
        "echo hi >> /tmp/x", "rm /tmp/a", "mkdir -p /tmp/x/y", "echo a | tee /tmp/x", "ls &> /dev/null",
        "git fetch origin main",
    ]
    WRITES = [
        "echo hi > out.txt", "rm -rf build", "sed -i s/a/b/ f", "sed -Ei s/a/b/ f", "perl -pi -e s/a/b/ f",
        "git commit -m x", "git push -u origin x", "git branch new", "git checkout main", "git pull",
        'bash -c "rm x"', "find . -name x -delete", "find . -exec rm {} ;", "xargs -I{} rm {}",
        "echo $(rm x)", "gh pr create", "gh api -X POST x", "gh api repos/a/b -f body=x",
        "curl -d a=b https://example.com", "pip install foo", "python3 -m pip install foo", "tee out.log",
        "env FOO=1 rm x", "timeout 5 rm x", "cat <<EOF > file\nhello\nEOF", "git config user.name x",
        "ls &> out", "touch x", "cp a b", "npm install", "tar xzf a.tgz",
    ]

    def test_reads_pass(self):
        for command in self.READS:
            with self.subTest(command=command):
                self.assertIsNone(pg.bash_problem(command))

    def test_writes_blocked(self):
        for command in self.WRITES:
            with self.subTest(command=command):
                self.assertIsNotNone(pg.bash_problem(command))

    def test_marks_are_off_limits(self):
        self.assertIsNotNone(pg.bash_problem("ls ~/.claude/plan-approved"))

    def test_unparsable_is_blocked(self):
        self.assertIsNotNone(pg.bash_problem("echo 'unclosed"))


class OtherTools(unittest.TestCase):
    def test_file_tools(self):
        self.assertIsNotNone(pg.problem_for("Edit", {"file_path": "/home/user/repo/a.py"}))
        self.assertIsNotNone(pg.problem_for("Write", {"file_path": "README.md"}))
        self.assertIsNotNone(pg.problem_for("NotebookEdit", {"notebook_path": "/home/user/n.ipynb"}))
        self.assertIsNone(pg.problem_for("Write", {"file_path": os.path.join(tempfile.gettempdir(), "x")}))

    def test_github_tools(self):
        for tool in ("create_pull_request", "push_files", "merge_pull_request", "add_issue_comment",
                     "issue_write", "update_pull_request", "actions_run_trigger"):
            self.assertIsNotNone(pg.problem_for("mcp__github__" + tool, {}), tool)
        for tool in ("get_file_contents", "list_pull_requests", "search_code", "pull_request_read",
                     "issue_read", "actions_get"):
            self.assertIsNone(pg.problem_for("mcp__github__" + tool, {}), tool)

    def test_read_tools(self):
        for tool in ("Read", "Grep", "Glob", "AskUserQuestion"):
            self.assertIsNone(pg.problem_for(tool, {}))


class Flow(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp(prefix="plan_gate_home_")
        self.env = dict(os.environ, HOME=self.home, USERPROFILE=self.home, PYTHONIOENCODING="utf-8")

    def run_hook(self, data):
        p = subprocess.run([sys.executable, SCRIPT], input=json.dumps(data), capture_output=True,
                           text=True, encoding="utf-8", env=self.env)
        return p.returncode, p.stderr

    def pre(self, tool, tool_input, session="s1"):
        return self.run_hook({"hook_event_name": "PreToolUse", "session_id": session,
                              "tool_name": tool, "tool_input": tool_input})[0]

    def post(self, tool, tool_input=None, tool_response=None, session="s1"):
        return self.run_hook({"hook_event_name": "PostToolUse", "session_id": session, "tool_name": tool,
                              "tool_input": tool_input or {}, "tool_response": tool_response})[0]

    def test_blocked_until_exit_plan_mode(self):
        self.assertEqual(self.pre("Bash", {"command": "git commit -m x"}), 2)
        self.assertEqual(self.pre("Bash", {"command": "git status"}), 0)
        self.assertEqual(self.post("ExitPlanMode"), 0)
        self.assertEqual(self.pre("Bash", {"command": "git commit -m x"}), 0)
        self.assertEqual(self.pre("Edit", {"file_path": "/home/user/a.py"}), 0)
        self.assertEqual(self.pre("Edit", {"file_path": "/home/user/a.py"}, session="s2"), 2)

    def test_approval_through_question(self):
        q = "是否批准上述设计？"
        self.post("AskUserQuestion", {"answers": {q: "先不做"}})
        self.assertEqual(self.pre("Write", {"file_path": "/home/user/a"}), 2)
        self.post("AskUserQuestion", {"answers": {q: "批准方案（推荐）"}})
        self.assertEqual(self.pre("Write", {"file_path": "/home/user/a"}), 0)

    def test_approval_in_result_text(self):
        text = 'Your questions have been answered: "Approve the design?"="Approve plan (Recommended)".'
        self.post("AskUserQuestion", tool_response=text, session="s3")
        self.assertEqual(self.pre("Write", {"file_path": "/home/user/a"}, session="s3"), 0)

    def test_option_labels_are_not_answers(self):
        self.post("AskUserQuestion", {"questions": [{"options": [{"label": "批准方案"}]}],
                                      "answers": {"q": "先不做"}})
        self.assertEqual(self.pre("Write", {"file_path": "/home/user/a"}), 2)

    def test_bad_input_fails_closed(self):
        p = subprocess.run([sys.executable, SCRIPT], input="not json", capture_output=True, text=True,
                           env=self.env)
        self.assertEqual(p.returncode, 2)


if __name__ == "__main__":
    unittest.main()
