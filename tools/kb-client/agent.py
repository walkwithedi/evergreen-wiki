"""OpenCode behind the knowledge base client: starts `opencode serve` on 127.0.0.1, keeps the page's
conversation windows (one OpenCode conversation each), passes their events to the page and answers
permission requests the client may answer itself.

Only this module talks to OpenCode; the page talks to kb_client.py. The interface used is the one of
OpenCode 1.19 (checked at start: GET /session and GET /permission must answer): POST /session,
GET /session/{id}/message, POST /session/{id}/prompt_async, POST /session/{id}/abort, GET /event,
POST /permission/{id}/reply, POST /question/{id}/reply and /reject. When the server does not start or
the interface is missing, a simple mode runs `opencode run <message>` once per message instead.
Python 3 standard library only.
"""
import http.client
import json
import logging
import os
import re
import shlex
import shutil
import signal
import subprocess
import threading
import time
from urllib.parse import quote

log = logging.getLogger("kb_client.agent")
LISTEN_RE = re.compile(r"opencode server listening on (https?://)?(127\.0\.0\.1|localhost):(\d+)")
GLOB_CHARS = "*?[{"
SHELL_CHARS = set(";|&`$<>(){}\n\r\\")
PYTHONS = ("python3", "python")
FEED_KEEP = 5000  # events kept for a page that reconnects; older ones come back through the history
# Every action of the OpenCode this client starts asks first; the client answers what it may itself.
ASK_ALL = {"permission": {name: "ask" for name in (
    "read", "edit", "glob", "grep", "list", "bash", "task", "external_directory", "webfetch", "websearch",
    "lsp", "skill")}}
# An option a question marks as the recommended one
RECOMMENDED = re.compile(r"recommend|推荐", re.I)
# The skills load their own instructions; reading a skill is never a question for the user.
ASK_ALL["permission"]["skill"] = "allow"
# Subagents that only look things up; what they do in turn is asked for like everything else.
REPLIES = {name: name for name in ("once", "always", "reject")}
READ_ONLY_AGENTS = ("explore",)
MAX_ALWAYS = 200  # Always allow answers kept per kind of request
# Places OpenCode's installers commonly use, for a desktop session whose PATH lacks them.
COMMON_DIRS = ("~/.opencode/bin", "~/.local/bin", "~/bin", "/usr/local/bin", "~/.npm-global/bin")
TERMINALS = (("x-terminal-emulator", ["-e"]), ("mate-terminal", ["-x"]), ("gnome-terminal", ["--"]),
             ("konsole", ["-e"]), ("xterm", ["-e"]))
SHELL_TIMEOUT = 10
# A work folder (--chat-first) is never one of these, nor the home folder or a folder holding it: the
# assistant may edit files inside it without a card.
SYSTEM_DIRS = ("/bin", "/boot", "/dev", "/etc", "/lib", "/lib32", "/lib64", "/libx32", "/proc", "/run", "/sbin",
               "/sys", "/usr", "/var")
MAX_RECENT = 5  # work folders remembered
MAX_SESSIONS = 50  # conversations listed for a work folder
MAX_WINDOWS = 8  # conversation windows the user opens; the intake's own window is not counted
EDIT_TOOLS = ("edit", "write", "patch", "multiedit", "apply_patch")
MAX_DIFF = 200000  # characters of an edit's diff passed to the page


# ---------- finding OpenCode ----------

class Program:
    """How to run OpenCode: a program file, or a shell function or alias run through `bash -ic`, so that
    what the user's ~/.bashrc does before OpenCode (refreshing settings, say) happens here as well."""

    def __init__(self, path="", shell=False, how=""):
        self.path = path
        self.shell = shell
        self.how = how  # option, path, common, shell-file, shell-function

    def __bool__(self):
        return bool(self.path or self.shell)

    def argv(self, args):
        if self.shell:
            return ["bash", "-ic", " ".join(["opencode"] + [shlex.quote(a) for a in args])]
        return [self.path] + list(args)

    def describe(self):
        return "bash -ic opencode" if self.shell else self.path


def find_opencode(explicit=""):
    """The first of: the given command or path, OpenCode on PATH, in a common install folder, or as
    the interactive shell knows it (a file, a function or an alias). An empty Program when none."""
    if explicit:
        path = shutil.which(os.path.expanduser(explicit))
        return Program(path, how="option") if path else Program()
    path = shutil.which("opencode")
    if path:
        return Program(path, how="path")
    for folder in COMMON_DIRS:
        path = os.path.join(os.path.expanduser(folder), "opencode")
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return Program(path, how="common")
    if not shutil.which("bash"):
        return Program()
    try:
        p = subprocess.run(["bash", "-ic", "type -t opencode; command -v opencode"], stdin=subprocess.DEVNULL,
                           capture_output=True, text=True, timeout=SHELL_TIMEOUT, start_new_session=True)
    except (OSError, subprocess.SubprocessError) as e:
        log.info("no answer from the interactive shell: %s", type(e).__name__)
        return Program()
    lines = [x.strip() for x in p.stdout.splitlines() if x.strip()]
    kind = lines[0] if lines else ""
    if kind == "file" and len(lines) > 1 and os.path.isabs(lines[1]):
        return Program(lines[1], how="shell-file")
    if kind in ("function", "alias"):
        return Program(shell=True, how="shell-" + kind)
    return Program()


# ---------- which requests the client answers itself ----------

def real(path):
    return os.path.realpath(os.path.normpath(path))


def inside(path, root):
    path, root = real(path), real(root)
    return path == root or path.startswith(root.rstrip(os.sep) + os.sep)


def pattern_path(pattern, cwd):
    """The folder or file a permission pattern stands for: the part before the first wildcard, taken
    from cwd when relative. "" for an empty pattern."""
    p = os.path.expanduser(str(pattern).strip())
    if not p:
        return ""
    cut = min([p.index(c) for c in GLOB_CHARS if c in p] or [len(p)])
    if cut < len(p):
        p = p[:cut]
        p = p if p.endswith(os.sep) else os.path.dirname(p)
    p = p or "."
    return real(p if os.path.isabs(p) else os.path.join(cwd, p))


def check_workdir(path):
    """The real path of a folder the assistant may work in with --chat-first. Raises ValueError with
    "missing" (not an existing absolute folder), "too_wide" (the root, the home folder or a folder holding
    it) or "system" (inside SYSTEM_DIRS)."""
    path = str(path or "").strip()
    if not path or not os.path.isabs(os.path.expanduser(path)):
        raise ValueError("missing")
    p = real(os.path.expanduser(path))
    if not os.path.isdir(p):
        raise ValueError("missing")
    if p == os.sep or inside(real(os.path.expanduser("~")), p):
        raise ValueError("too_wide")
    # the system folders as written, not resolved: on some systems they are links (/var to /private/var)
    given = os.path.normpath(os.path.abspath(os.path.expanduser(path)))
    if any(x == d or x.startswith(d + os.sep) for x in (given, p) for d in SYSTEM_DIRS):
        raise ValueError("system")
    return p


def unquoted(cmd):
    """The command without the text of its quoted words, for the shell-syntax check: text in single
    quotes is literal, and so is text in double quotes without $, ` or \\. None when a quote is not closed,
    a double-quoted part holds one of those three, or the command has a line break."""
    if "\n" in cmd or "\r" in cmd:
        return None
    out, quote = [], None
    for ch in cmd:
        if quote is None:
            if ch in "'\"":
                quote = ch
            else:
                out.append(ch)
        elif ch == quote:
            quote = None
        elif quote == '"' and ch in "$`\\":
            return None
    return None if quote else "".join(out)


STDERR_RE = re.compile(r"(?<!\S)2>(?:&1|\s*/dev/null)(?!\S)")


def unquoted_mask(cmd):
    """For each character of cmd, True when it lies outside quotes (a quote character itself counts as
    quoted). A backslash in double quotes escapes the next character."""
    mask, quote, escaped = [], None, False
    for ch in cmd:
        if quote is None:
            if ch in "'\"":
                quote = ch
                mask.append(False)
            else:
                mask.append(True)
        else:
            mask.append(False)
            if escaped:
                escaped = False
            elif quote == '"' and ch == "\\":
                escaped = True
            elif ch == quote:
                quote = None
    return mask


def plain_command(cmd):
    """cmd as one line: a backslash-newline outside quotes joins lines as the shell does, and a separate
    2>&1 or 2>/dev/null outside quotes is dropped (it only says where error output goes)."""
    cmd = str(cmd)
    mask = unquoted_mask(cmd)
    out, i = [], 0
    while i < len(cmd):
        if cmd[i] == "\\" and mask[i] and cmd[i + 1:i + 2] in ("\n", "\r"):
            i += 3 if cmd[i + 1:i + 3] == "\r\n" else 2
            out.append(" ")
            continue
        out.append(cmd[i])
        i += 1
    cmd = "".join(out)
    mask = unquoted_mask(cmd)
    drops = [m.span() for m in STDERR_RE.finditer(cmd) if all(mask[m.start():m.end()])]
    for start, end in reversed(drops):
        cmd = cmd[:start] + " " + cmd[end:]
    return cmd.strip()


def skill_command(command, script_dirs, cwd):
    """True for `python3 [-I|-B|-u] <script>.py args` (optionally after one `cd <folder> &&`) whose script
    lies in one of script_dirs, with no other shell syntax outside quoted words. Lines joined with a
    backslash and a separate 2>&1 or 2>/dev/null are accepted (plain_command)."""
    cmd = plain_command(command)
    m = re.fullmatch(r"cd\s+(\"[^\"]*\"|'[^']*'|[^\s;&|]+)\s*&&\s*(.*)", cmd, re.S)
    where = cwd
    if m:
        where = os.path.join(cwd, os.path.expanduser(m.group(1).strip("'\"")))
        cmd = m.group(2)
    bare = unquoted(cmd)
    if not cmd or bare is None or SHELL_CHARS & set(bare):
        return False
    try:
        words = shlex.split(cmd)
    except ValueError:
        return False
    if not words or os.path.basename(words[0]) not in PYTHONS:
        return False
    rest = words[1:]
    while rest and rest[0] in ("-I", "-B", "-u"):
        rest = rest[1:]
    if not rest or not rest[0].endswith(".py"):
        return False
    script = os.path.join(where, os.path.expanduser(rest[0]))
    return os.path.isfile(script) and any(inside(script, d) for d in script_dirs)


FILE_COMMANDS = {"mkdir": {"-p"}, "cp": {"-p", "-r", "-R"}}

# Commands that only read and print. Their path arguments must lie in the readable places.
READ_ONLY_PROGRAMS = {"ls", "cat", "head", "tail", "wc", "stat", "file", "du", "grep", "egrep", "fgrep", "rg",
                      "find", "pwd", "echo", "test"}
FIND_ACTIONS = {"-exec", "-execdir", "-ok", "-okdir", "-delete", "-fprint", "-fprint0", "-fprintf", "-fls"}
READ_VARS = {"HOME", "USER", "KB_LIBRARIES", "PWD"}
VAR_RE = re.compile(r"\$(?:\{(\w+)\}|(\w+))")
SEPARATORS = {";", "&&", "||", "|"}


def file_command(command, places, cwd):
    """True for `mkdir [-p] <folder>...` with every folder in a writable place, and for
    `cp [-p|-r|-R] <source>... <target>` with every source in a readable place and the target in a writable
    one; no shell syntax or wildcards outside quoted words, no ~ (the shell's expansion is not followed)."""
    cmd = str(command).strip()
    bare = unquoted(cmd)
    if not cmd or bare is None or SHELL_CHARS & set(bare) or set(GLOB_CHARS) & set(bare):
        return False
    try:
        words = shlex.split(cmd)
    except ValueError:
        return False
    if not words or words[0] not in FILE_COMMANDS:
        return False
    rest = words[1:]
    while rest and rest[0] in FILE_COMMANDS[words[0]]:
        rest = rest[1:]
    if not rest or any(w.startswith(("-", "~")) or not w for w in rest):
        return False
    paths = [real(w if os.path.isabs(w) else os.path.join(cwd, w)) for w in rest]
    write = places.get("write", [])
    readable = write + places.get("read", []) + places.get("scripts", [])
    if words[0] == "mkdir":
        return all(any(inside(p, r) for r in write) for p in paths)
    if len(paths) < 2:
        return False
    return any(inside(paths[-1], r) for r in write) and \
        all(any(inside(p, r) for r in readable) for p in paths[:-1])


def expand(word):
    """~ and the variables read-only commands may use, as the shell would expand them."""
    word = VAR_RE.sub(lambda m: os.environ.get(m.group(1) or m.group(2), ""), word)
    return os.path.expanduser(word)


def read_only_command(command, places, cwd):
    """True for read-only commands (READ_ONLY_PROGRAMS, find without its acting options) joined by ; && ||
    or |, with at most 2>/dev/null as redirection, only the variables in READ_VARS, and every path argument
    inside the readable places. No command substitution, other redirection, background job or subshell."""
    cmd = str(command).strip()
    if not cmd or "\n" in cmd or "\r" in cmd or "`" in cmd or "$(" in cmd or "<(" in cmd:
        return False
    if any((m.group(1) or m.group(2)) not in READ_VARS for m in VAR_RE.finditer(cmd)) or \
            cmd.count("$") != len(VAR_RE.findall(cmd)):
        return False
    cmd = re.sub(r"(^|\s)2>\s*/dev/null(?=\s|$|[;|&])", " ", cmd)
    try:
        lex = shlex.shlex(cmd, posix=True, punctuation_chars=True)
        lex.whitespace_split = True
        tokens = list(lex)
    except ValueError:
        return False
    readable = places.get("write", []) + places.get("read", []) + places.get("scripts", []) + places.get("edit", [])
    commands, words = [], []
    for tok in tokens:
        if tok in SEPARATORS:
            if not words:
                return False
            commands.append(words)
            words = []
        elif tok and set(tok) <= set("();<>|&"):
            return False  # a redirection, subshell or background job
        else:
            words.append(tok)
    if words:
        commands.append(words)
    elif not tokens or tokens[-1] != ";":
        return False  # nothing, or a pipe or && with nothing after it
    for words in commands:
        prog = words[0]
        if prog not in READ_ONLY_PROGRAMS:
            return False
        args = words[1:]
        if prog == "find" and FIND_ACTIONS & set(args):
            return False
        if prog in ("echo", "pwd"):
            continue
        pattern_given = prog not in ("grep", "egrep", "fgrep", "rg") or \
            any(a in ("-e", "-f") or a.startswith(("--regexp", "--file")) for a in args)
        paths = 0
        for a in args:
            if a.startswith("-") or a in ("!", "(", ")"):
                continue
            if not pattern_given:
                pattern_given = True  # grep's first plain word is its pattern
                continue
            word = expand(a)
            if not ("/" in word or word.startswith(".") or os.path.exists(os.path.join(cwd, word))):
                continue  # a number or a name filter, not a path
            path = pattern_path(word, cwd)
            if not path or not any(inside(path, r) for r in readable):
                return False
            paths += 1
        # without a path these read the working folder (cat, head and the like read their input)
        lists_cwd = prog in ("ls", "find", "du", "rg") or (prog in ("grep", "egrep", "fgrep") and any(
            a.startswith("--recursive") or (a.startswith("-") and not a.startswith("--") and set("rR") & set(a))
            for a in args))
        if not paths and lists_cwd and not any(inside(cwd, r) for r in readable):
            return False
    return True


def wildcard(pattern, text):
    """OpenCode's wildcard match: * any run of characters, ? one; a trailing " *" may also match nothing."""
    rx = re.escape(pattern).replace(r"\*", ".*").replace(r"\?", ".")
    if pattern.endswith(" *"):
        rx = rx[:-len(re.escape(" ") + ".*")] + "(?: .*)?"
    return re.fullmatch(rx, text, re.S) is not None


def remembered(permission, patterns, always):
    """True when every pattern of the request matches one the user answered with Always allow for this kind
    of request. A command must be one plain command (no shell syntax outside quoted words), so that a
    remembered "git *" never covers "git status; rm ...". always: {permission: [patterns]}."""
    saved = always.get(permission) or []
    patterns = [str(p).strip() for p in patterns or [] if str(p).strip()]
    if not saved or not patterns:
        return False
    for p in patterns:
        if permission == "bash":
            bare = unquoted(p)
            if bare is None or SHELL_CHARS & set(bare):
                return False
        if not any(wildcard(x, p) for x in saved):
            return False
    return True


def decide(permission, patterns, places, cwd):
    """True when the client answers "once" itself. places: {"write": [...], "read": [...],
    "scripts": [...]} as real folder paths. Writing only inside a registered library; reading also in the
    chosen material, the skills and the agent's own settings; commands only the skills' own scripts,
    plain mkdir and cp within those places, and read-only commands on those places. places["edit"] (the
    work folder of --chat-first) is read and edited freely, and read-only commands may read it.
    Everything else, and anything that cannot be read clearly, goes to the user."""
    patterns = [p for p in (patterns or []) if str(p).strip()]
    if not patterns:
        return False
    if permission == "bash":
        return all(skill_command(p, places.get("scripts", []), cwd) or file_command(p, places, cwd)
                   or read_only_command(p, places, cwd) for p in patterns)
    edit = places.get("edit", [])  # the work folder of --chat-first: read and edited without a card
    if permission == "task":
        return all(str(p).strip() in READ_ONLY_AGENTS for p in patterns)
    if permission in ("edit", "write"):
        roots = places.get("write", []) + edit
    elif permission in ("read", "list", "glob", "grep", "external_directory"):
        roots = places.get("write", []) + places.get("read", []) + places.get("scripts", []) + edit
    else:
        return False
    for p in patterns:
        path = pattern_path(p, cwd)
        if not path or not any(inside(path, r) for r in roots):
            return False
    return True


# ---------- events for the page ----------

class Feed:
    """Numbered events for the page, kept for reconnects (the last FEED_KEEP)."""

    def __init__(self):
        self.cond = threading.Condition()
        self.events = []
        self.first = 1  # number of events[0]

    def emit(self, etype, **data):
        with self.cond:
            seq = self.first + len(self.events)
            self.events.append(dict(data, type=etype, seq=seq))
            if len(self.events) > FEED_KEEP:
                drop = len(self.events) - FEED_KEEP
                self.events = self.events[drop:]
                self.first += drop
            self.cond.notify_all()
            return seq

    def last(self):
        with self.cond:
            return self.first + len(self.events) - 1

    def since(self, seq, timeout):
        with self.cond:
            if self.first + len(self.events) - 1 <= seq:
                self.cond.wait(timeout)
            start = max(0, seq + 1 - self.first)
            return self.events[start:]


# The skill scripts whose runs mark a stage of an intake on the page: script name, then the subcommands
# that count (None: any). Only these fixed names reach the page, never the command line itself.
STAGE_SCRIPTS = {"batch_plan": ("plan", "next", "done", "skip", "finish", "status", "add"), "convert": None,
                 "index_tool": ("check", "add", "update", "write"), "clean": None, "card_check": None,
                 "assemble": None, "package": None, "archive_plan": None, "pick_materials": None,
                 "meta": ("name", "date", "entities", "terms", "yaml"), "prep": ("scan", "file"),
                 "consolidate": ("list", "fill", "done")}
SCRIPT_RE = re.compile(r"(?:^|[\s/'\"])(\w+)\.py['\"]?(?:\s+([a-z]+))?")


def stage_script(command):
    """"convert", "index_tool check" and the like for a command running one of STAGE_SCRIPTS, else ""."""
    for m in SCRIPT_RE.finditer(str(command)):
        name, sub = m.group(1), m.group(2) or ""
        if name not in STAGE_SCRIPTS:
            continue
        subs = STAGE_SCRIPTS[name]
        if subs is None:
            return name
        return f"{name} {sub}" if sub in subs else ""
    return ""


def part_event(part, role, child=False):
    """What the page needs of one message part: text, reasoning, or a tool step in one line. None for the
    rest. child marks a part of a subagent's conversation."""
    kind = part.get("type")
    base = {"messageID": part.get("messageID", ""), "partID": part.get("id", ""), "role": role, "child": child}
    if kind == "text" and not part.get("synthetic") and not part.get("ignored"):
        return dict(base, kind="text", text=str(part.get("text", "")))
    if kind == "reasoning":
        return dict(base, kind="reasoning", text=str(part.get("text", "")))
    if kind == "tool":
        state = part.get("state") or {}
        detail = state.get("title") or ""
        if not detail:
            inp = state.get("input") or {}
            detail = str(inp.get("command") or inp.get("filePath") or inp.get("path") or inp.get("pattern") or "")
        script = stage_script((state.get("input") or {}).get("command", "")) if part.get("tool") == "bash" else ""
        ev = dict(base, kind="tool", tool=str(part.get("tool", "")), status=str(state.get("status", "")),
                  detail=detail[:300], error=str(state.get("error", ""))[:300], script=script)
        diff = (state.get("metadata") or {}).get("diff") if part.get("tool") in EDIT_TOOLS else None
        if isinstance(diff, str) and diff.strip():
            ev["diff"] = diff[:MAX_DIFF]
        return ev
    return None


# ---------- OpenCode ----------

class Refused(Exception):
    """A request the agent turns down; reason is a fixed name the page knows (too_many, busy, simple)."""

    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


class Window:
    """One conversation window of the page: its OpenCode conversation, the subagents started from it and
    what waits in it. kind: chat, task (a write task started from a button; task is {"name", "library"})
    or intake (the client's own intake)."""

    def __init__(self, wid, session=None, kind="chat", task=None):
        self.id = wid
        self.session = session
        self.kind = kind
        self.task = task
        self.title = ""
        self.status = "idle"
        self.material = []  # paths chosen for this conversation's intake
        self.children = set()
        self.permissions = {}  # pending, id -> event
        self.questions = {}
        self.allow_all = False  # Allow everything in this window: until switched off or the client quits, never saved

    def busy(self):
        """Working, or a card waits for an answer."""
        return self.status != "idle" or bool(self.permissions or self.questions)

    def clear(self):
        self.material = []
        self.permissions.clear()
        self.questions.clear()
        self.children.clear()
        self.status = "idle"

    def saved(self):
        return {"id": self.id, "session": self.session, "kind": self.kind, "task": self.task, "title": self.title}

    def info(self):
        return dict(self.saved(), status=self.status,
                    cards=len(self.permissions) + len(self.questions), allow_all=self.allow_all)


def touches(permission, patterns, guard, places, cwd):
    """True when a request writes into guard["roots"] or runs a script in guard["scripts"]: editing a file
    there, running one of those scripts, or any other command naming one of those folders. Read-only
    commands on readable places do not count."""
    roots = [real(x) for x in guard.get("roots", [])]
    scripts = [real(x) for x in guard.get("scripts", [])]
    if permission in ("edit", "write"):
        return any(any(inside(pattern_path(p, cwd) or os.sep, r) for r in roots) for p in patterns)
    if permission != "bash":
        return False
    for p in patterns:
        if skill_command(p, scripts, cwd):
            return True
        if read_only_command(p, places, cwd):
            continue
        if any(x in str(p) for x in roots + scripts + list(guard.get("roots", [])) + list(guard.get("scripts", []))):
            return True
    return False


class Agent:
    """state: off, starting, ready, simple (opencode run per message), failed. The page's conversations
    are windows (Window), all served by the one OpenCode; events carry the window they belong to."""

    def __init__(self, program, cwd, places, state_file, start_timeout=90, chat_first=False):
        self.program = program  # a Program
        self.cwd = cwd
        self.chat_first = chat_first  # a work folder can be chosen; each keeps its own windows
        self.places = places  # callable returning {"write", "read", "scripts"} without the material
        self.state_file = state_file
        self.start_timeout = start_timeout
        self.feed = Feed()
        self.lock = threading.RLock()
        self.state = "off"
        self.reason = ""
        self.output = []  # last lines OpenCode printed while starting
        self.proc = None
        self.port = None
        self.roles = {}  # messageID -> role
        self.run_proc = None  # simple mode
        self.stopping = False
        self.gen = 0  # counts restarts; an event reader of an earlier OpenCode stops
        self.events_thread = None
        self.restart_pending = False
        # set by the client: the write lock ({"holder", "win", ...} or None), and for a window the folders
        # whose writing needs a person while another window holds the lock ({"roots", "scripts"} or None)
        self.lock_fn = lambda: None
        self.guard_fn = lambda win: None
        self.always = self._load_always()  # {permission: [patterns]} answered with Always allow
        saved = self._load_state()
        self.workdir = ""
        self.recent = []
        self.windows_by_dir = {}  # work folder ("" for none) -> {"windows": [saved windows], "current"}
        self.models = []  # [{"id": "provider/model", "name"}] from OpenCode, read when it is ready
        self.windows = {}  # id -> Window, in the order of the tabs
        self.current = ""
        self.n = 0  # the highest window number given
        if chat_first:
            self.recent = [x for x in saved.get("recent") or [] if isinstance(x, str)][:MAX_RECENT]
            wbd = saved.get("windows_by_dir")
            self.windows_by_dir = {str(k): v for k, v in wbd.items() if isinstance(v, dict)} if isinstance(wbd, dict) else {}
            old = saved.get("sessions")  # one conversation per folder, as earlier clients kept them
            for d, sid in (old.items() if isinstance(old, dict) else []):
                self.windows_by_dir.setdefault(str(d), {"windows": [{"id": "w1", "session": sid}], "current": "w1"})
            try:
                self.workdir = check_workdir(saved.get("workdir") or "") if saved.get("workdir") else ""
            except ValueError:
                self.workdir = ""
            if self.workdir:
                self.cwd = self.workdir
            entry = self.windows_by_dir.get(self.workdir) or {}
        else:
            entry = {"windows": saved.get("windows"), "current": saved.get("current")}
            if not isinstance(entry["windows"], list) and isinstance(saved.get("session"), str):
                entry = {"windows": [{"id": "w1", "session": saved["session"]}], "current": "w1"}
        self._set_windows(entry)

    # ----- windows -----

    def _set_windows(self, entry):
        """The windows of a saved entry ({"windows": [...], "current"}), checked; at least one chat window."""
        self.windows = {}
        for x in (entry or {}).get("windows") or []:
            if not isinstance(x, dict) or not re.fullmatch(r"w\d{1,6}", str(x.get("id", ""))) or x["id"] in self.windows:
                continue
            sid = x.get("session")
            sid = sid if isinstance(sid, str) and re.fullmatch(r"[\w-]{1,100}", sid) else None
            kind = x.get("kind") if x.get("kind") in ("chat", "task", "intake") else "chat"
            task = x.get("task")
            task = {"name": str(task.get("name", "")), "library": str(task.get("library", ""))} \
                if kind == "task" and isinstance(task, dict) else None
            self.windows[x["id"]] = Window(x["id"], sid, kind, task)
            self.windows[x["id"]].title = str(x.get("title") or "")[:200] if sid else ""
            self.n = max(self.n, int(x["id"][1:]))
        cur = (entry or {}).get("current")
        self.current = cur if cur in self.windows else ""
        self._keep_one()

    def _keep_one(self):
        """At least one window that is not the intake's; the current one is shown."""
        if not any(w.kind != "intake" for w in list(self.windows.values())):
            self._add()
        if self.current not in self.windows or self.windows[self.current].kind == "intake":
            self.current = next(w.id for w in list(self.windows.values()) if w.kind != "intake")

    def _add(self, session=None, kind="chat", task=None):
        self.n += 1
        w = Window(f"w{self.n}", session, kind, task)
        self.windows[w.id] = w
        return w

    def window(self, wid=None):
        """The window wid, or the current one for None or "". Raises KeyError for an unknown window."""
        return self.windows[wid or self.current]

    def _window_of(self, sid):
        return next((w for w in list(self.windows.values()) if w.session == sid or sid in w.children), None) if sid else None

    @property
    def session(self):
        """The current window's conversation."""
        w = self.windows.get(self.current)
        return w.session if w else None

    @property
    def status(self):
        """busy while any window works."""
        return "busy" if any(w.status != "idle" for w in list(self.windows.values())) else "idle"

    def emit_windows(self):
        self.feed.emit("windows", windows=[w.info() for w in list(self.windows.values())], current=self.current,
                       lock=self.lock_fn())

    def open(self, session=None):
        """A new window, or for session (an earlier conversation of the work folder) the window that has it
        or a new one with it. Returns the window id; raises Refused("too_many") past MAX_WINDOWS,
        Refused("simple") in simple mode and LookupError for a session that is not one of them."""
        if self.state == "simple":
            raise Refused("simple")
        if session is not None:
            have = next((w for w in list(self.windows.values()) if w.session == session and w.kind != "intake"), None)
            if have:
                self.focus(have.id)
                return have.id
            listed = next((s for s in self.sessions() if s["id"] == session), None) if isinstance(session, str) else None
            if listed is None:
                raise LookupError(session)
        with self.lock:
            if sum(1 for w in list(self.windows.values()) if w.kind != "intake") >= MAX_WINDOWS:
                raise Refused("too_many")
            w = self._add(session)
            w.title = listed["title"] if session is not None else ""
            self.current = w.id
        self._save()
        self.emit_windows()
        return w.id

    def close(self, wid, stop=False):
        """Closes a window (its conversation stays in OpenCode). A window at work or with a card waiting
        closes only with stop, which ends its turn first: Refused("busy") otherwise."""
        w = self.window(wid)
        if w.busy() and not stop:
            raise Refused("busy")
        if w.status != "idle" and w.session and self.state == "ready":
            self.call("POST", f"/session/{w.session}/abort")
        with self.lock:
            self.windows.pop(w.id, None)
            if self.current == w.id:
                self.current = ""
            self._keep_one()
        self._save()
        self.emit_windows()

    def focus(self, wid):
        w = self.window(wid)
        if w.kind != "intake":
            self.current = w.id
            self._save()

    def task(self, name, library, text, wid=None):
        """Sends text in a task window: wid when it is one that is idle, else a new one for the task.
        Returns the window id. The client checks the write lock first."""
        with self.lock:
            w = self.windows.get(wid) if wid else None
            if w is not None and (w.kind != "task" or w.busy()):
                raise Refused("busy")
            if w is None:
                if self.state == "simple":
                    w = self.window()
                else:
                    if sum(1 for x in list(self.windows.values()) if x.kind != "intake") >= MAX_WINDOWS:
                        raise Refused("too_many")
                    w = self._add(kind="task", task={"name": name, "library": library or ""})
                    self.current = w.id
                    self._save()
        self.emit_windows()
        self.send(text, win=w.id)
        return w.id

    def intake_window(self):
        """The window of the client's intake, made when there is none; it does not count against MAX_WINDOWS."""
        with self.lock:
            w = next((x for x in list(self.windows.values()) if x.kind == "intake"), None)
            if w is None:
                w = self._add(kind="intake")
                self._save()
        self.emit_windows()
        return w

    def close_intake(self):
        """Drops the intake window kept from an earlier start (nothing of its run is left to continue)."""
        for w in [x for x in list(self.windows.values()) if x.kind == "intake"]:
            self.windows.pop(w.id, None)
        self._keep_one()

    # ----- start and stop -----

    def start(self, restart=False):
        with self.lock:
            if self.state != "off":
                return
            self.state = "starting"
        self.feed.emit("agent", state="starting", restart=restart)
        threading.Thread(target=self._start, daemon=True).start()

    def _start(self):
        env = dict(os.environ, OPENCODE_CONFIG_CONTENT=json.dumps(ASK_ALL))
        try:
            self.proc = subprocess.Popen(self.program.argv(["serve", "--hostname=127.0.0.1", "--port=0"]),
                                         cwd=self.cwd, env=env, stdin=subprocess.DEVNULL,
                                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                         text=True, encoding="utf-8", errors="replace",
                                         start_new_session=True)
        except OSError as e:
            self._simple(f"opencode serve: {e}")
            return
        found = threading.Event()
        threading.Thread(target=self._read_output, args=(found,), daemon=True).start()
        if not found.wait(self.start_timeout) or self.port is None:
            self._kill()
            self._simple("opencode serve did not start")
            return
        try:
            for path in ("/session", "/permission"):
                code, _ = self.call("GET", path)
                if code != 200:
                    raise OSError(f"GET {path} answered {code}")
        except (OSError, ValueError) as e:
            self._kill()
            self._simple(f"opencode serve: {e}")
            return
        try:
            stream = self._connect()  # before "ready", so no event of the first message is missed
        except (OSError, http.client.HTTPException) as e:
            self._kill()
            self._simple(f"opencode serve: GET /event {type(e).__name__}")
            return
        with self.lock:
            self.state = "ready"
        self.events_thread = threading.Thread(target=self._events, args=(stream, self.gen), daemon=True)
        self.events_thread.start()
        self._resume()
        self.models = self._models() if self.chat_first else []
        log.info("opencode ready on port %s in %s (%d windows)", self.port, self.cwd, len(self.windows))
        self.feed.emit("agent", state="ready", session=self.session)
        if self.restart_pending:
            self.restart(self.restart_pending)

    def _read_output(self, found):
        for line in self.proc.stdout:
            line = line.rstrip("\n")
            log.debug("opencode: %s", line)
            self.output = (self.output + [line])[-20:]
            if not found.is_set():
                self.feed.emit("agent", state="starting", line=line[:300])
                m = LISTEN_RE.search(line)
                if m:
                    self.port = int(m.group(3))
                    found.set()
        found.set()  # the program ended

    def _simple(self, reason):
        log.warning("simple mode: %s", reason)
        with self.lock:
            self.state = "simple"
            self.reason = reason
            # one window only: opencode run has no conversation to keep apart
            keep = self.window()
            self.windows = {keep.id: keep}
            self.current = keep.id
        self.feed.emit("agent", state="simple", reason=reason, output="\n".join(self.output[-10:]))

    def _kill(self):
        proc = self.proc
        if proc and proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGTERM)
                proc.wait(5)
            except (OSError, subprocess.TimeoutExpired):
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except OSError:  # the process group has ended meanwhile
                    log.debug("opencode had already stopped")

    def shutdown(self):
        self.stopping = True
        self._kill()
        rp = self.run_proc
        if rp and rp.poll() is None:
            try:
                os.killpg(rp.pid, signal.SIGTERM)
            except OSError:  # the run has ended meanwhile
                log.debug("opencode run had already stopped")

    # ----- talking to OpenCode -----

    def call(self, method, path, body=None, timeout=30):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=timeout)
        try:
            data = None if body is None else json.dumps(body).encode("utf-8")
            c.request(method, path, body=data, headers={"Content-Type": "application/json"} if data else {})
            r = c.getresponse()
            raw = r.read()
            try:
                return r.status, json.loads(raw) if raw else None
            except ValueError:
                return r.status, None
        finally:
            c.close()

    def _connect(self):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=None)
        c.request("GET", "/event", headers={"Accept": "text/event-stream"})
        r = c.getresponse()
        if r.status != 200:
            c.close()
            raise http.client.HTTPException(f"status {r.status}")
        return c, r

    def restart(self, why="setup"):
        """Starts OpenCode again, so that it reads skills and instructions installed since it started (why
        "setup") or forgets its Always allow answers (why "forget"); the conversations go on. While OpenCode
        is starting or any window is working, this waits until all are done. Simple mode needs none: each
        message starts OpenCode anew. False when there is nothing to do."""
        with self.lock:
            if self.state in ("off", "simple") or self.stopping:
                return False
            if self.state == "starting" or self.status != "idle":
                self.restart_pending = why
                return True
            self.restart_pending = False
            self.gen += 1
            self.state = "off"
        log.info("restarting opencode (%s)", why)
        self._kill()
        t = self.events_thread
        if t and t is not threading.current_thread():
            t.join(5)
        self.proc, self.port, self.output = None, None, []
        for w in list(self.windows.values()):
            w.permissions, w.questions = {}, {}
        self.start(restart=why)
        return True

    def retry(self, program):
        """Starts OpenCode anew with program after it could not be used (simple mode, or it stopped); the
        page's conversation stream goes on. False while it is starting, ready, or a simple-mode message
        is still running."""
        with self.lock:
            rp = self.run_proc
            if self.state not in ("simple", "failed") or self.stopping or (rp and rp.poll() is None):
                return False
            self.program = program
            self.gen += 1
            self.state = "off"
        log.info("starting opencode again")
        self._kill()
        self.proc, self.port, self.output = None, None, []
        for w in list(self.windows.values()):
            w.permissions, w.questions = {}, {}
        self.start()
        return True

    def _events(self, stream, gen):
        while not self.stopping and gen == self.gen:
            try:
                c, r = stream or self._connect()
                stream = None
                for raw in r.fp:
                    line = raw.decode("utf-8", "replace").rstrip("\r\n")
                    if line.startswith("data:"):
                        try:
                            ev = json.loads(line[5:].strip())
                        except ValueError:
                            continue
                        if isinstance(ev, dict):
                            self._handle(ev)
                c.close()
            except (OSError, http.client.HTTPException) as e:
                log.debug("event stream: %s", e)
            if gen != self.gen:  # restarted: the new OpenCode has its own reader
                return
            if self.proc and self.proc.poll() is not None:
                with self.lock:
                    self.state = "failed"
                    self.reason = "opencode stopped"
                log.warning("opencode stopped (exit %s); last output: %s", self.proc.returncode, " / ".join(self.output[-5:])[:500])
                self.feed.emit("agent", state="failed", reason=self.reason,
                               output="\n".join(self.output[-10:]))
                return
            time.sleep(1)

    def _handle(self, ev):
        kind = ev.get("type", "")
        p = ev.get("properties") or {}
        if log.isEnabledFor(logging.DEBUG):  # the shape only, never the content
            log.debug("event %s %s", kind, sorted(p) + sorted("part." + k for k in (p.get("part") or {})))
        if kind in ("session.created", "session.updated"):
            info = p.get("info") or {}
            if info.get("id") and info.get("parentID"):
                w = self._window_of(info["parentID"])
                if w is not None:
                    w.children.add(info["id"])
            elif info.get("id") and info.get("title"):
                w = next((x for x in list(self.windows.values()) if x.session == info["id"]), None)
                if w is not None and w.title != str(info["title"])[:200]:
                    w.title = str(info["title"])[:200]
                    self._save()
                    self.emit_windows()
            return
        sid = p.get("sessionID") or (p.get("info") or {}).get("sessionID") or (p.get("part") or {}).get("sessionID")
        w = self._window_of(sid)
        if w is None:
            return
        child = sid != w.session
        if child and kind in ("session.status", "session.idle"):
            return  # only the main conversation says whether the assistant is working
        if kind == "message.updated":
            info = p.get("info") or {}
            self.roles[info.get("id", "")] = info.get("role", "assistant")
            err = info.get("error")
            if err:
                self.feed.emit("error", win=w.id, text=str((err.get("data") or {}).get("message") or err.get("name") or err))
        elif kind == "message.part.updated":
            part = p.get("part") or {}
            pe = part_event(part, self.roles.get(part.get("messageID", ""), "assistant"), child)
            if pe:
                self.feed.emit("part", win=w.id, **pe)
        elif kind == "message.part.delta":
            if p.get("field", "text") == "text":
                self.feed.emit("delta", win=w.id, messageID=p.get("messageID", ""), partID=p.get("partID", ""),
                               role=self.roles.get(p.get("messageID", ""), "assistant"), child=child,
                               delta=str(p.get("delta", "")))
        elif kind == "session.status":
            self._set_status(w, (p.get("status") or {}).get("type", "idle"))
        elif kind == "session.idle":
            self._set_status(w, "idle")
        elif kind == "session.error":
            err = p.get("error") or {}
            self.feed.emit("error", win=w.id, text=str((err.get("data") or {}).get("message") or err.get("name") or "error"))
        elif kind == "permission.asked":
            self._permission(p, w, child)
        elif kind == "permission.replied":
            rid = p.get("requestID") or p.get("id") or ""
            if w.permissions.pop(rid, None) is not None:
                self.feed.emit("permission_done", win=w.id, id=rid)
                self.emit_windows()
        elif kind == "question.asked":
            q = {"id": p.get("id", ""), "questions": [
                {"question": str(x.get("question", "")), "header": str(x.get("header", "")),
                 "multiple": bool(x.get("multiple")), "custom": x.get("custom", True) is not False,
                 "options": [{"label": str(o.get("label", "")), "description": str(o.get("description", ""))}
                             for o in x.get("options") or []]}
                for x in p.get("questions") or []]}
            q["child"] = child
            w.questions[q["id"]] = q
            self.feed.emit("question", win=w.id, **q)
            self.emit_windows()
        elif kind in ("question.replied", "question.rejected"):
            rid = p.get("requestID") or p.get("id") or ""
            if w.questions.pop(rid, None) is not None:
                self.feed.emit("question_done", win=w.id, id=rid)
                self.emit_windows()

    def _set_status(self, w, status):
        changed = w.status != status
        w.status = status
        self.feed.emit("status", win=w.id, status=status)
        if changed:
            self.emit_windows()
        if self.status == "idle" and self.restart_pending:
            threading.Thread(target=self.restart, args=(self.restart_pending,), daemon=True).start()

    def allowed_places(self, w):
        pl = self.places()
        return {"write": [real(x) for x in pl.get("write", [])],
                "read": [real(x) for x in pl.get("read", []) + w.material],
                "scripts": [real(x) for x in pl.get("scripts", [])],
                "edit": [self.workdir] if self.workdir else []}

    def _permission(self, p, w, child=False):
        rid = p.get("id", "")
        perm = str(p.get("permission", ""))
        patterns = [str(x) for x in p.get("patterns") or []]
        places = self.allowed_places(w)
        what = " | ".join(patterns)[:200]  # the request itself, never file contents
        guard = self.guard_fn(w.id)
        if guard and touches(perm, patterns, guard, places, self.cwd):
            why = ""  # another window holds the write lock: a person decides, whatever this window allows
            log.info("permission %s kept for the page: a write task runs in another window", perm)
        else:
            why = "allow everything" if w.allow_all else "rule" if decide(perm, patterns, places, self.cwd) else \
                "always allowed" if remembered(perm, patterns, self.always) else ""
        if why:
            try:
                self.call("POST", f"/permission/{quote(rid, safe='')}/reply", {"reply": "once"})
                self.feed.emit("auto", win=w.id, permission=perm, patterns=patterns[:5], child=child)
                log.info("permission %s allowed by the client (%s): %s", perm, why, what)
                return
            except OSError as e:
                log.warning("automatic reply failed: %s", type(e).__name__)
        log.info("permission %s asked on the page: %s", perm, what)
        always = [str(x) for x in p.get("always") or []]
        ev = {"id": rid, "permission": perm, "patterns": patterns[:20], "always": always[:20], "child": child}
        w.permissions[rid] = ev
        self.feed.emit("permission", win=w.id, **ev)
        self.emit_windows()

    # ----- the conversations -----

    def _load_state(self):
        try:
            with open(self.state_file, encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def _load_always(self):
        data = self._load_state().get("always")
        if not isinstance(data, dict):
            return {}
        return {str(k): [str(x) for x in v if isinstance(x, str) and x.strip()][:MAX_ALWAYS]
                for k, v in data.items() if isinstance(v, list)}

    def remembered_count(self):
        return sum(len(v) for v in self.always.values())

    def forget(self):
        """Forgets every Always allow answer, in this client and (by starting it anew) in OpenCode."""
        with self.lock:
            self.always = {}
        self._save()
        self.restart("forget")

    def _save(self):
        try:
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            tmp = self.state_file + ".tmp"
            entry = {"windows": [w.saved() for w in list(self.windows.values())], "current": self.current}
            with open(tmp, "w", encoding="utf-8") as f:
                data = {"session": self.session, "always": self.always}
                old = self._load_state()
                if self.chat_first:
                    self.windows_by_dir[self.workdir] = entry
                    data.update(workdir=self.workdir, recent=self.recent, windows_by_dir=self.windows_by_dir)
                    data.update({k: v for k, v in old.items() if k in ("windows", "current")})
                else:  # what a --chat-first client keeps stays for its next start
                    data.update(entry)
                    data.update({k: v for k, v in old.items() if k in ("workdir", "recent", "windows_by_dir")})
                json.dump(data, f, ensure_ascii=False)
            os.replace(tmp, self.state_file)
        except OSError as e:
            log.warning("cannot save the conversations: %s", e)

    def _resume(self):
        """Keeps each window's conversation that OpenCode still has; the others start anew with their
        first message."""
        for w in list(self.windows.values()):
            if not w.session:
                continue
            try:
                code, _ = self.call("GET", f"/session/{w.session}")
                if code == 200:
                    continue
            except OSError:  # OpenCode cannot say; a new conversation starts with the first message
                log.debug("saved conversation %s not found", w.session)
            w.session = None

    def ensure_session(self, w):
        if w.session:
            return w.session
        code, data = self.call("POST", "/session", {"title": "Conversation" if self.chat_first else "Knowledge base"})
        if code != 200 or not isinstance(data, dict) or not data.get("id"):
            raise OSError(f"POST /session answered {code}")
        w.session = str(data["id"])
        w.title = ""
        self._save()
        return w.session

    def new(self, win=None):
        """A new conversation in the window win (the current one for None)."""
        w = self.window(win)
        with self.lock:
            w.clear()
            w.title = ""
            if self.state == "ready":
                w.session = None
                self.ensure_session(w)
        self.feed.emit("reset", win=w.id, session=w.session)
        self.emit_windows()

    def history(self, win=None):
        """The window's conversation as part events, for a page that opens, reconnects or shows it."""
        w = self.window(win)
        if self.state != "ready" or not w.session:
            return []
        code, data = self.call("GET", f"/session/{w.session}/message")
        out = []
        for msg in data if code == 200 and isinstance(data, list) else []:
            info = msg.get("info") or {}
            role = info.get("role", "assistant")
            self.roles[info.get("id", "")] = role
            for part in msg.get("parts") or []:
                pe = part_event(part, role)
                if pe:
                    out.append(pe)
        return out

    def send(self, text, material=(), model="", win=None):
        w = self.window(win)
        for path in material:
            if os.path.isabs(path) and path not in w.material:
                w.material.append(path)
        if self.state == "simple":
            return self._run(text, w)
        if self.state != "ready":
            raise RuntimeError("not ready")
        sid = self.ensure_session(w)
        body = {"parts": [{"type": "text", "text": text}]}
        if model:
            if not any(m["id"] == model for m in self.models):
                raise ValueError("model")
            provider, _, name = model.partition("/")
            body["model"] = {"providerID": provider, "modelID": name}
        was = w.status
        self._set_status(w, "busy")  # at once: the window holds the write lock from its first message on
        try:
            code, _ = self.call("POST", f"/session/{sid}/prompt_async", body)
        except OSError:
            self._set_status(w, was)
            raise
        if code not in (200, 204):
            self._set_status(w, was)
            raise OSError(f"prompt answered {code}")
        return None

    # ----- the work folder, earlier conversations and models (--chat-first) -----

    def set_workdir(self, path):
        """Makes path (check_workdir) the folder OpenCode works in, remembered with the recent ones, and
        starts OpenCode there; the folder's windows from last time come back. Raises ValueError (why) for
        a folder that cannot be used and RuntimeError while a window is working or the write lock is held."""
        p = check_workdir(path)
        with self.lock:
            if any(w.busy() for w in list(self.windows.values())) or self.lock_fn() or \
                    (self.run_proc and self.run_proc.poll() is None):
                raise RuntimeError("busy")
            self._save()  # the windows of the folder left
            self.workdir = p
            self.cwd = p
            self.recent = ([p] + [x for x in self.recent if x != p])[:MAX_RECENT]
            self.n = 0
            self._set_windows(self.windows_by_dir.get(p))
        self._save()
        self.feed.emit("workdir", workdir=p, recent=self.recent)
        self.emit_windows()
        if not self.restart("workdir"):  # simple mode: each message starts OpenCode in the new folder
            self.feed.emit("reset", win=self.current, session=self.session)
        return p

    def sessions(self):
        """The main conversations of the work folder, newest first: [{"id", "title", "updated"}]."""
        if self.state != "ready":
            return []
        code, data = self.call("GET", "/session")
        out = []
        where = self.workdir or real(os.path.expanduser("~"))
        for s in data if code == 200 and isinstance(data, list) else []:
            if not isinstance(s, dict) or not s.get("id") or s.get("parentID"):
                continue
            d = s.get("directory")
            if d and real(str(d)) != where:
                continue
            times = s.get("time") or {}
            out.append({"id": str(s["id"]), "title": str(s.get("title") or "")[:200],
                        "updated": times.get("updated") or times.get("created") or 0})
        out.sort(key=lambda x: x["updated"] if isinstance(x["updated"], (int, float)) else 0, reverse=True)
        return out[:MAX_SESSIONS]

    def _models(self):
        """The models OpenCode's settings offer, as "provider/model" ids; [] when it cannot say."""
        try:
            code, data = self.call("GET", "/config/providers")
        except OSError:
            return []
        out = []
        for prov in (data or {}).get("providers") or [] if code == 200 and isinstance(data, dict) else []:
            if not isinstance(prov, dict) or not prov.get("id"):
                continue
            models = prov.get("models") or {}
            for mid, m in (models.items() if isinstance(models, dict) else []):
                name = (m or {}).get("name") if isinstance(m, dict) else ""
                out.append({"id": f"{prov['id']}/{mid}", "name": str(name or mid)})
        return out[:100]

    def stop(self, win=None):
        w = self.window(win)
        log.info("stopping the assistant's turn in %s", w.id)
        if self.state == "simple":
            rp = self.run_proc
            if rp and rp.poll() is None:
                os.killpg(rp.pid, signal.SIGTERM)
            return
        if self.state == "ready" and w.session:
            self.call("POST", f"/session/{w.session}/abort")

    def _card(self, rid, kind):
        return next((w for w in list(self.windows.values()) if rid in getattr(w, kind)), None)

    def reply_permission(self, rid, reply):
        """reply: "once", "always" (OpenCode stops asking for the request's `always` patterns) or "reject"."""
        w = self._card(rid, "permissions")
        if w is None or reply not in REPLIES:
            return False
        ev = w.permissions[rid]  # taken now: OpenCode's "replied" event may remove it before the reply returns
        code, _ = self.call("POST", f"/permission/{quote(rid, safe='')}/reply", {"reply": REPLIES[reply]})
        log.info("permission %s answered %s on the page (OpenCode %s)", ev.get("permission"), reply, code)
        if code in (200, 204):
            w.permissions.pop(rid, None)
            if reply == "always" and ev.get("always"):
                with self.lock:
                    kept = self.always.setdefault(ev["permission"], [])
                    kept += [x for x in ev["always"] if x not in kept]
                    del kept[:-MAX_ALWAYS]
                self._save()
            self.feed.emit("permission_done", win=w.id, id=rid)
            self.emit_windows()
            return True
        return False

    def set_allow_all(self, on, win=None):
        """Allow everything in the window win (on) or ask again (off). Switching it on also answers the
        requests already waiting there with "once" (unless another window holds the write lock and they
        write what it guards)."""
        w = self.window(win)
        with self.lock:
            w.allow_all = bool(on)
            waiting = list(w.permissions.values()) if w.allow_all else []
        self.feed.emit("allow_all", win=w.id, on=w.allow_all)
        self.emit_windows()
        guard = self.guard_fn(w.id)
        for ev in waiting:
            if guard and touches(ev["permission"], ev["patterns"], guard, self.allowed_places(w), self.cwd):
                continue
            if self.reply_permission(ev["id"], "once"):
                self.feed.emit("auto", win=w.id, permission=ev["permission"], patterns=ev["patterns"][:5],
                               child=ev["child"])

    def answer_recommended(self, rid, fallback):
        """Answers a question card for a run the client drives with Allow everything on: each question with
        its recommended option (one whose label or description says so), else its first option, else
        fallback as a typed answer. The answers sent, or None."""
        w = self._card(rid, "questions")
        if w is None:
            return None
        answers = []
        for x in w.questions[rid]["questions"]:
            opts = x["options"]
            pick = next((o for o in opts if RECOMMENDED.search(o["label"] + " " + o["description"])),
                        opts[0] if opts else None)
            answers.append([pick["label"]] if pick else [fallback] if x["custom"] else [])
        return answers if self.reply_question(rid, answers) else None

    def reply_question(self, rid, answers):
        w = self._card(rid, "questions")
        if w is None:
            return False
        q = quote(rid, safe="")
        if answers is None:
            code, _ = self.call("POST", f"/question/{q}/reject")
        else:
            code, _ = self.call("POST", f"/question/{q}/reply", {"answers": answers})
        if code in (200, 204):
            w.questions.pop(rid, None)
            self.feed.emit("question_done", win=w.id, id=rid)
            self.emit_windows()
            return True
        return False

    # ----- simple mode -----

    def _run(self, text, w):
        with self.lock:
            if self.run_proc and self.run_proc.poll() is None:
                raise RuntimeError("busy")
            mid = "run-" + str(time.time_ns())
            self.feed.emit("part", win=w.id, messageID=mid + "-u", partID=mid + "-u", role="user", kind="text", text=text)
            self.run_proc = subprocess.Popen(self.program.argv(["run", text]), cwd=self.cwd, stdin=subprocess.DEVNULL,
                                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                             encoding="utf-8", errors="replace", start_new_session=True)
        threading.Thread(target=self._run_output, args=(self.run_proc, mid, w), daemon=True).start()

    def _run_output(self, proc, mid, w):
        self._set_status(w, "busy")
        text = ""
        for line in proc.stdout:
            text += line
            self.feed.emit("part", win=w.id, messageID=mid, partID=mid, role="assistant", kind="text", text=text)
        proc.wait()
        self._set_status(w, "idle")

    def open_terminal(self, win=None):
        """Opens the window's conversation in OpenCode's own interface, in a new terminal window. Returns
        the terminal program's name; raises RuntimeError when there is no conversation or no terminal."""
        w = self.window(win)
        if not w.session:
            raise RuntimeError("no conversation")
        cmd = self.program.argv(["--session=" + w.session])
        env = dict(os.environ)
        env.pop("OPENCODE_CONFIG_CONTENT", None)  # the terminal keeps the user's own settings
        for name, flag in TERMINALS:
            path = shutil.which(name)
            if path:
                subprocess.Popen([path] + flag + cmd, cwd=self.cwd, env=env, stdin=subprocess.DEVNULL,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
                return name
        raise RuntimeError("no terminal")

    def snapshot(self, win=None):
        """The agent as the page shows the window win (the current one for None)."""
        w = self.window(win)
        return {"state": self.state, "reason": self.reason, "session": w.session, "status": w.status,
                "output": "\n".join(self.output[-10:]) if self.state in ("simple", "failed") else "",
                "permissions": list(w.permissions.values()), "questions": list(w.questions.values()),
                "workdir": self.workdir, "recent": self.recent, "models": self.models,
                "allow_all": w.allow_all, "win": w.id, "windows": [x.info() for x in list(self.windows.values())],
                "current": self.current, "lock": self.lock_fn()}
