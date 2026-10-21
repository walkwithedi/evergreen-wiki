"""Tests for tools/kb-client/quick_search.py: keywords, the ranked items of a library, the request to the model
and its streamed reply, and the page's POST /api/quick."""
import json
import os
import shutil
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools", "kb-client"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kb_manage  # noqa: E402
import quick_search as qs  # noqa: E402
import test_kb_client as tk  # noqa: E402

kb_manage.init_library()
import ingest  # noqa: E402
import kbindex  # noqa: E402

SAMPLE = os.path.join(ROOT, "examples", "sample-work-kb")


class FakeModel:
    """An OpenAI-compatible interface on 127.0.0.1: mode "stream" (server-sent events), "json" (one reply) or
    an HTTP status code to fail with. Keeps the requests it was sent."""

    def __init__(self, mode="stream", reply="The pilot runs to 2026-04-27 [1]. Budget unchanged [7]."):
        self.mode, self.reply, self.requests = mode, reply, []
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                fake.requests.append({"path": self.path, "auth": self.headers.get("Authorization"),
                                      "extra": self.headers.get("X-Team"), "body": body})
                if isinstance(fake.mode, int):
                    data = b'{"error": "no"}'
                    self.send_response(fake.mode)
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return
                if fake.mode == "json":
                    data = json.dumps({"choices": [{"message": {"content": fake.reply}}]}).encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.end_headers()
                for i in range(0, len(fake.reply), 10):
                    chunk = {"choices": [{"delta": {"content": fake.reply[i:i + 10]}}]}
                    self.wfile.write(("data: %s\n\n" % json.dumps(chunk)).encode())
                self.wfile.write(b"data: [DONE]\n\n")

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.base = "http://127.0.0.1:%d/v1" % self.server.server_address[1]

    def stop(self):
        self.server.shutdown()
        self.server.server_close()


def settings(base, key="sk-test", **extra):
    prov = {"options": {"baseURL": base, "apiKey": key, "headers": {"X-Team": "t1"}},
            "models": {"model-1": {}, "model-2": {}}}
    return dict({"model": "example/model-1", "provider": {"example": prov}}, **extra)


class KeywordsTest(unittest.TestCase):
    def test_chinese_question(self):
        self.assertEqual(qs.keywords("介绍一下示例项目的上线日期是哪天？"), ["示例项目", "上线日期"])

    def test_long_runs_give_pairs(self):
        self.assertEqual(qs.keywords("试点延期审批"), ["试点", "点延", "延期", "期审", "审批"])

    def test_words_and_function_words(self):
        self.assertEqual(qs.keywords("What is the steering group decision on the pilot?"),
                         ["steering", "group", "decision", "pilot"])
        self.assertEqual(qs.keywords("知识库里有没有关于 Project Atlas 的记录"), ["project", "atlas"])

    def test_single_characters_only_when_nothing_else(self):
        self.assertEqual(qs.keywords("的 猫 和 x 狗"), ["猫", "x", "狗"])
        self.assertEqual(qs.keywords("猫 预算"), ["预算"])
        self.assertEqual(qs.keywords("？！"), [])


class SearchTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        self.root = os.path.join(tmp, "kb")
        shutil.copytree(SAMPLE, self.root)
        self.libs = [{"id": "work", "label": "Work", "root": self.root}]

    def search(self, query):
        return qs.search(kbindex, ingest.ITEM_RE, ingest.MARK_RE, self.libs, query)

    def test_ranked_by_keywords_held(self):
        got = self.search("steering group pilot")
        self.assertEqual(got["keywords"], ["steering", "group", "pilot"])
        first = got["items"][0]
        self.assertEqual((first["n"], first["kind"], first["hits"], first["of"]), (1, "card", 3, 3))
        self.assertEqual(first["link"], "Sources/Meetings/Atlas steering minutes 2026-03-13")
        self.assertEqual(first["label"], "Work")
        self.assertTrue(all(x["hits"] >= 2 for x in got["items"]))
        self.assertEqual([x["n"] for x in got["items"]], list(range(1, len(got["items"]) + 1)))

    def test_status_card_items(self):
        card = os.path.join(self.root, "00_Status-Card.md")
        with open(card, encoding="utf-8") as f:
            text = f.read()
        with open(card, "w", encoding="utf-8") as f:
            f.write(text.replace("No entries yet.", "1. The pilot ends on 2026-04-27. [[Sources/x#^p1]] ⏳ newer source"))
        got = self.search("pilot")
        status = [x for x in got["items"] if x["kind"] == "status"]
        self.assertEqual(len(status), 1)
        self.assertTrue(status[0]["review"])
        self.assertNotIn("⏳", status[0]["text"])
        self.assertEqual(got["items"][0]["kind"], "status")

    def test_nothing_found_and_unreadable_library(self):
        self.assertEqual(self.search("zzzqqq")["items"], [])
        self.libs.append({"id": "gone", "label": "Gone", "root": os.path.join(self.root, "nope")})
        self.assertTrue(self.search("pilot")["items"])


class SummaryTest(unittest.TestCase):
    def setUp(self):
        for k in ("no_proxy", "NO_PROXY"):
            os.environ[k] = "127.0.0.1,localhost"
        self.fake = FakeModel()
        self.addCleanup(self.fake.stop)

    def test_target(self):
        tg = qs.target(settings(self.fake.base + "/"))
        self.assertEqual(tg, {"base": self.fake.base, "key": "sk-test", "model": "model-1", "headers": {"X-Team": "t1"}})
        self.assertEqual(qs.target(settings(self.fake.base), "example/model-2")["model"], "model-2")
        os.environ["QS_TEST_KEY"] = "sk-env"
        self.addCleanup(os.environ.pop, "QS_TEST_KEY")
        self.assertEqual(qs.target(settings(self.fake.base, "{env:QS_TEST_KEY}"))["key"], "sk-env")
        no_default = settings(self.fake.base)
        del no_default["model"]
        self.assertEqual(qs.target(no_default)["model"], "model-1")  # the only provider's first model
        for conf, reason in (({}, "no_config"), (settings(self.fake.base, model="other/x"), "no_model"),
                             (settings(""), "no_base"), (settings(self.fake.base, "{env:QS_NOT_SET}"), "no_key")):
            with self.assertRaises(qs.QuickError) as e:
                qs.target(conf)
            self.assertEqual(e.exception.reason, reason)

    def test_messages_number_the_items(self):
        items = [{"n": 1, "kind": "status", "text": "1. Pilot ends 2026-04-27.", "review": True},
                 {"n": 2, "kind": "card", "text": "The steering group approved it.", "conclusion": "Pilot extended",
                  "link": "Sources/Meetings/minutes", "date": "2026-03-13"},
                 {"n": 3, "kind": "paragraph", "text": "x" * 5000, "link": "Sources/plan", "date": ""}]
        system, user = qs.messages("When does the pilot end?", items, "en")
        self.assertIn("[1][3]", system["content"])
        self.assertIn("Question: When does the pilot end?", user["content"])
        self.assertIn("[1] Status card · marked for review\n1. Pilot ends", user["content"])
        self.assertIn("[2] Card · minutes · 2026-03-13\nConclusion: Pilot extended\nText: The steering", user["content"])
        self.assertIn("x" * qs.ITEM_CHARS, user["content"])
        self.assertNotIn("x" * (qs.ITEM_CHARS + 1), user["content"])
        self.assertIn("问题：", qs.messages("问题", items, "zh")[1]["content"])

    def test_stream_and_whole_replies(self):
        tg = qs.target(settings(self.fake.base))
        self.assertEqual("".join(qs.stream(tg, [{"role": "user", "content": "q"}])), self.fake.reply)
        sent = self.fake.requests[-1]
        self.assertEqual((sent["path"], sent["auth"], sent["extra"]), ("/v1/chat/completions", "Bearer sk-test", "t1"))
        self.assertTrue(sent["body"]["stream"])
        self.fake.mode = "json"
        self.assertEqual("".join(qs.stream(tg, [])), self.fake.reply)

    def test_failures(self):
        tg = qs.target(settings(self.fake.base))
        self.fake.mode = 401
        with self.assertRaises(qs.QuickError) as e:
            list(qs.stream(tg, []))
        self.assertEqual((e.exception.reason, e.exception.status), ("http", 401))
        self.fake.stop()
        with self.assertRaises(qs.QuickError) as e:
            list(qs.stream(tg, [], timeout=5))
        self.assertEqual(e.exception.reason, "connect")
        self.fake = FakeModel()

    def test_bad_refs(self):
        self.assertEqual(qs.bad_refs("a [1] b [2、9] c [0] d [9][3, 4]", 4), [9, 0])
        self.assertEqual(qs.bad_refs("no numbers", 0), [])


class QuickPostTest(unittest.TestCase):
    """POST /api/quick as the page sends it: the items at once, then the summary, line by line."""
    setUp, p = tk.ChatTest.setUp, tk.ChatTest.p

    def start(self, mode="stream"):
        root = self.p("home", "kb", "work")
        shutil.copytree(SAMPLE, root)
        tk.write(self.p("home", ".config", "kb", "kb-libraries.json"), json.dumps(
            {"schema": 2, "libraries": [{"id": "work", "label": "Work", "scope": "team projects",
                                         "backend": {"type": "local", "root": root}}]}))
        self.fake = FakeModel(mode)
        self.addCleanup(self.fake.stop)
        tk.write(self.p("home", ".config", "opencode", "opencode.jsonc"),
                 "// settings\n" + json.dumps(settings(self.fake.base)) + "\n")
        self.env.update(no_proxy="127.0.0.1,localhost", NO_PROXY="127.0.0.1,localhost")
        s = tk.Server(self.env, "--idle", "0")
        self.addCleanup(s.stop)
        return s

    def quick(self, s, text, model=""):
        status, raw = s.post("/api/quick", {"text": text, "model": model})
        self.assertEqual(status, 200, raw)
        return [json.loads(line) for line in raw.splitlines() if line.strip()]

    def test_items_then_summary(self):
        s = self.start()
        lines = self.quick(s, "steering group pilot")
        self.assertEqual(lines[0]["type"], "hits")
        self.assertEqual(lines[0]["items"][0]["n"], 1)
        text = "".join(x["text"] for x in lines if x["type"] == "text")
        self.assertEqual(text, self.fake.reply)
        n = len(lines[0]["items"])
        self.assertEqual(lines[-1], {"type": "done", "bad": [7] if n < 7 else []})
        prompt = self.fake.requests[-1]["body"]["messages"][1]["content"]
        self.assertIn("[1] Card · Atlas steering minutes 2026-03-13", prompt)
        self.assertEqual(self.fake.requests[-1]["body"]["model"], "model-1")
        self.quick(s, "pilot", "example/model-2")
        self.assertEqual(self.fake.requests[-1]["body"]["model"], "model-2")
        self.assertNotIn("sk-test", raw_log(self))

    def test_nothing_found_calls_no_model(self):
        s = self.start()
        lines = self.quick(s, "zzzqqq")
        self.assertEqual(lines, [{"type": "hits", "keywords": ["zzzqqq"], "items": []},
                                 {"type": "done", "empty": True, "bad": []}])
        self.assertEqual(self.fake.requests, [])

    def test_failure_keeps_the_items(self):
        s = self.start(401)
        lines = self.quick(s, "pilot")
        self.assertTrue(lines[0]["items"])
        self.assertEqual((lines[-1]["type"], lines[-1]["reason"], lines[-1]["status"]), ("error", "http", 401))

    def test_bad_requests(self):
        s = self.start()
        self.assertEqual(s.post("/api/quick", {"text": " "})[0], 400)
        self.assertEqual(s.post("/api/quick", {"text": "x" * 2001})[0], 400)
        self.assertEqual(s.post("/api/quick", {"text": "pilot"}, token=False)[0], 403)
        os.remove(self.p("home", ".config", "kb", "kb-libraries.json"))
        status, r = s.post("/api/quick", {"text": "pilot"})
        self.assertEqual((status, r["reason"]), (409, "no_library"))


def raw_log(test):
    """Everything the client wrote to its log folder."""
    folder = test.p("home", ".config", "evergreen-wiki", "logs")
    out = []
    for name in os.listdir(folder) if os.path.isdir(folder) else []:
        with open(os.path.join(folder, name), encoding="utf-8") as f:
            out.append(f.read())
    return "\n".join(out)


if __name__ == "__main__":
    unittest.main()
