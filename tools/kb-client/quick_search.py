"""Quick search: a question answered from the libraries' indexes at once, and summarised by one call to the
model of OpenCode's settings, without the conversation.

keywords(): the words of a question. Punctuation, spaces and common function words separate them; a run of
Chinese, Japanese or Korean text of at most SHORT_RUN characters is one keyword, a longer one gives its
overlapping pairs of characters; other words are kept whole. Single characters are dropped unless nothing else
is left.

search(): the status-card items, cards and source paragraphs of every local library holding a keyword
(kbindex search, brought up to date first), ranked by how many keywords each holds, then status-card items,
cards and paragraphs in that order, then relevance. Those holding fewer than half the keywords of the best one
are left out; at most LIMIT items, STATUS_MAX of them status-card items. Each item is numbered from 1.

messages(), target(), stream(): the request to summarise the numbered items, the model and interface it goes
to (the window's model or the settings' default, its provider's baseURL, apiKey and headers), and the reply
streamed from POST <baseURL>/chat/completions. bad_refs(): numbers in the summary that are not items.

The API key stays in this process: it is never sent to the page and never logged. Python 3 standard library only.
"""
import json
import logging
import math
import os
import re
import socket
import sqlite3
import urllib.error
import urllib.request

log = logging.getLogger("kb_client.quick")

LIMIT = 15  # items listed and sent to the model
STATUS_MAX = 5  # status-card items among them at most
MAX_KEYWORDS = 16
SHORT_RUN = 4  # a CJK run this long or shorter is one keyword
ITEM_CHARS = 1500  # characters of one item sent to the model
PROMPT_CHARS = 15000  # characters of all items sent to the model
MAX_TOKENS = 1024
TIMEOUT = 60  # seconds the interface may stay silent

CJK = "぀-ヿ㐀-䶿一-鿿豈-﫿가-힯"
# Words that only join or frame a question; they separate keywords. Longer ones first.
STOP_CJK = sorted("""有没有 是不是 为什么 什么样 怎么样 是什么 关于 什么 怎么 怎样 如何 哪些 哪个 哪里 哪儿 哪天 多少
    是否 请问 帮我 一下 这个 那个 这些 那些 我们 你们 他们 现在 目前 一些 情况 相关 有关 内容 资料 记录 介绍 讲讲 讲解
    解释 说说 了解 搜索 查找 查询 知识库 的 了 吗 呢 吧 啊 呀 么 是 和 与 及 或 在 有 请 我 你""".split(), key=len, reverse=True)
STOP_EN = set("""a an the is are was were be of to in on at for and or what who whom when where which why how does do
    did about tell me please search find look up explain any there""".split())
STOP_RE = re.compile("|".join(map(re.escape, STOP_CJK)))
RUN_RE = re.compile("([%s]+)|((?:(?![%s])[^\\W_])+)" % (CJK, CJK))
REF_RE = re.compile(r"\[(\d+(?:\s*[,，、]\s*\d+)*)\]")

PROMPT = {
    "zh": {"system": "你根据知识库检索出的编号片段回答问题。只用片段里的内容，不补充片段以外的知识，不推测。先给结论，"
                     "简洁归纳；每句末尾用 [编号] 标出依据的片段，可以标多个，如 [1][3]。片段之间不一致时分别说明，"
                     "并指出哪个更新。片段里没有答案时，直说检索到的片段里没有记录。不用标题和表格。",
           "user": "问题：{q}\n\n片段：\n{items}",
           "status": "状态卡", "review": "待复核", "card": "卡片", "paragraph": "来源", "conclusion": "结论：",
           "quote": "原文："},
    "en": {"system": "Answer the question from the numbered passages found in a knowledge base. Use only what the "
                     "passages say: add no outside knowledge and no guesses. Give the conclusions first, briefly; "
                     "end every sentence with the number of the passage it rests on in brackets, several if needed, "
                     "such as [1][3]. When passages disagree, give each and say which is newer. When the passages "
                     "hold no answer, say that they do not record it. No headings or tables.",
           "user": "Question: {q}\n\nPassages:\n{items}",
           "status": "Status card", "review": "marked for review", "card": "Card", "paragraph": "Source",
           "conclusion": "Conclusion: ", "quote": "Text: "},
}


class QuickError(Exception):
    """Why there is no summary: reason is a key the page words; detail adds what the interface said."""

    def __init__(self, reason, detail="", status=0):
        super().__init__(reason)
        self.reason, self.detail, self.status = reason, detail, status


# ---------- keywords and search ----------

def keywords(query):
    out, singles = [], []
    for part in STOP_RE.split(query or ""):
        for m in RUN_RE.finditer(part.casefold()):
            run, word = m.group(1), m.group(2)
            if run:
                words = [run] if len(run) <= SHORT_RUN else [run[i:i + 2] for i in range(len(run) - 1)]
            elif word in STOP_EN:
                continue
            else:
                words = [word]
            for w in words:
                (singles if len(w) == 1 else out).append(w)
    out = list(dict.fromkeys(out)) or list(dict.fromkeys(singles))
    return out[:MAX_KEYWORDS]


def _pattern(term):
    t = re.escape(" ".join(term.split()))
    return re.compile(r"(?<![a-z0-9])" + t if term.isascii() else t, re.I)


def _held(groups, text):
    """How many keyword groups (a keyword and the other names of its entity) the text holds."""
    return sum(1 for g in groups if any(p.search(text) for p in g))


def _status_items(path, groups, item_re, mark_re):
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.read().split("\n")
    except OSError:
        return []
    out = []
    for line in lines:
        if item_re.match(line):
            text = mark_re.sub("", line).strip()
            hits = _held(groups, text)
            if hits:
                out.append({"kind": "status", "text": text, "review": "⏳" in line, "hits": hits, "score": 0})
    return out


def search(kx, item_re, mark_re, libs, query):
    """{"keywords": [...], "items": [...]} for the query in the libraries ({id, label, root}). kx is the kbindex
    module; item_re and mark_re find status-card items and their review marks (ingest.ITEM_RE, MARK_RE)."""
    words = keywords(query)
    if not words:
        return {"keywords": [], "items": []}
    found = []
    for lib in libs:
        try:
            cfg = kx.kbconf.load_library(lib["root"])
            ix = kx.open_index(lib["root"], cfg)
            try:
                got = ix.search(keywords=words, entities=kx.library_entities(lib["root"], cfg),
                                limit=LIMIT * 10, relax=LIMIT * 10)
            finally:
                ix.close()
        except (kx.kbconf.ConfigError, OSError, sqlite3.Error) as e:
            log.warning("quick search in %s: %s", lib["id"], e)
            continue
        groups = [[_pattern(n) for n in g] for g in got["keywords"]]
        where = {"lib": lib["id"], "label": lib["label"]}
        for s in _status_items(os.path.join(lib["root"], cfg["names"]["status_card"]), groups, item_re, mark_re):
            found.append(dict(s, **where))
        for r in got["results"]:
            card = r["kind"] == "card"
            seen = " ".join([r["text"], r.get("conclusion", ""), r.get("topic", "")] + list(r.get("entities") or []))
            item = dict(where, kind=r["kind"], text=r["text"], link=r["link"], anchor=r["anchor"], date=r["date"],
                        hits=max(1, _held(groups, seen)), score=r["score"])
            if card:
                item.update(conclusion=r["conclusion"], topic=r["topic"], earlier=r["earlier"])
            found.append(item)
    order = {"status": 0, "card": 1, "paragraph": 2}
    found.sort(key=lambda x: (-x["hits"], order[x["kind"]], -x["score"]))
    best = found[0]["hits"] if found else 0
    items, status = [], 0
    for x in found:
        if x["hits"] < math.ceil(best / 2) or len(items) == LIMIT:
            break
        if x["kind"] == "status":
            if status == STATUS_MAX:
                continue
            status += 1
        items.append(x)
    for n, x in enumerate(items, 1):
        x["n"] = n
        x["of"] = len(words)
        del x["score"]
    return {"keywords": words, "items": items}


# ---------- the summary ----------

def messages(query, items, lang):
    p = PROMPT["zh" if lang == "zh" else "en"]
    parts, used = [], 0
    for x in items:
        if x["kind"] == "status":
            head = "[%d] %s%s" % (x["n"], p["status"], " · " + p["review"] if x.get("review") else "")
            body = x["text"]
        else:
            head = "[%d] %s · %s%s" % (x["n"], p[x["kind"]], x["link"].split("/")[-1],
                                       " · " + x["date"] if x.get("date") else "")
            text = " ".join(x["text"].split())
            body = p["conclusion"] + x["conclusion"] + "\n" + p["quote"] + text if x["kind"] == "card" else text
        body = body[:ITEM_CHARS]
        if used + len(head) + len(body) > PROMPT_CHARS:
            break
        parts.append(head + "\n" + body)
        used += len(head) + len(body)
    return [{"role": "system", "content": p["system"]},
            {"role": "user", "content": p["user"].format(q=query, items="\n\n".join(parts))}]


def _resolve(value):
    """An apiKey value as OpenCode reads it: {env:NAME}, {file:path} or the key itself."""
    if not isinstance(value, str):
        return ""
    if value.startswith("{env:") and value.endswith("}"):
        return os.environ.get(value[5:-1], "")
    if value.startswith("{file:") and value.endswith("}"):
        try:
            with open(os.path.expanduser(value[6:-1]), encoding="utf-8") as f:
                return f.read().strip()
        except OSError:
            return ""
    return value


def target(conf, model=""):
    """{base, key, model, headers} for the model id "provider/model" (the settings' model when empty), from
    OpenCode's settings conf (a dict). Raises QuickError when the settings cannot say."""
    if not conf:
        raise QuickError("no_config")
    provs = conf.get("provider") if isinstance(conf.get("provider"), dict) else {}
    mid = model or conf.get("model") or ""
    if not isinstance(mid, str):
        mid = ""
    if "/" not in mid and len(provs) == 1:
        pid = next(iter(provs))
        models = (provs[pid] or {}).get("models") if isinstance(provs[pid], dict) else None
        mid = "%s/%s" % (pid, mid or next(iter(models or {}), ""))
    pid, _, name = mid.partition("/")
    prov = provs.get(pid)
    if not name or not isinstance(prov, dict):
        raise QuickError("no_model")
    opts = prov.get("options") if isinstance(prov.get("options"), dict) else {}
    base = opts.get("baseURL")
    if not isinstance(base, str) or not base.strip():
        raise QuickError("no_base")
    key = _resolve(opts.get("apiKey"))
    if not key:
        raise QuickError("no_key")
    headers = {str(k): str(v) for k, v in (opts.get("headers") or {}).items()} \
        if isinstance(opts.get("headers"), dict) else {}
    return {"base": base.strip().rstrip("/"), "key": key, "model": name, "headers": headers}


def stream(tg, msgs, timeout=TIMEOUT):
    """The reply's text, piece by piece, from an OpenAI-compatible chat completions interface; a reply that
    is not streamed is given whole. Raises QuickError."""
    body = json.dumps({"model": tg["model"], "messages": msgs, "stream": True, "max_tokens": MAX_TOKENS}).encode()
    headers = {"Content-Type": "application/json", "Accept": "text/event-stream",
               "Authorization": "Bearer " + tg["key"]}
    headers.update(tg["headers"])
    req = urllib.request.Request(tg["base"] + "/chat/completions", data=body, method="POST", headers=headers)
    try:
        r = urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.HTTPError as e:
        try:
            detail = e.read(300).decode("utf-8", "replace")
        except OSError:
            detail = ""
        raise QuickError("http", " ".join(detail.split()), e.code)
    except (socket.timeout, TimeoutError):
        raise QuickError("timeout")
    except urllib.error.URLError as e:
        if isinstance(e.reason, (socket.timeout, TimeoutError)):
            raise QuickError("timeout")
        raise QuickError("connect", str(e.reason))
    except OSError as e:
        raise QuickError("connect", str(e))
    try:
        with r:
            if "event-stream" not in r.headers.get("Content-Type", ""):
                try:
                    text = json.loads(r.read())["choices"][0]["message"].get("content") or ""
                except (ValueError, KeyError, IndexError, TypeError, AttributeError):
                    raise QuickError("bad_reply")
                if text:
                    yield text
                return
            for raw in r:
                line = raw.decode("utf-8", "replace").strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    return
                try:
                    piece = (json.loads(data)["choices"][0].get("delta") or {}).get("content")
                except (ValueError, KeyError, IndexError, TypeError, AttributeError):
                    continue
                if piece:
                    yield piece
    except (socket.timeout, TimeoutError):
        raise QuickError("timeout")
    except OSError as e:
        raise QuickError("connect", str(e))


def bad_refs(text, count):
    """The numbers in brackets in text that are not between 1 and count, in order, once each."""
    out = []
    for m in REF_RE.finditer(text):
        for n in re.split(r"\s*[,，、]\s*", m.group(1)):
            k = int(n)
            if not 1 <= k <= count and k not in out:
                out.append(k)
    return out
