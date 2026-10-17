#!/usr/bin/env python3
"""OpenCode 配置辅助脚本，供 codeagent-setup.sh 调用，只用 Python 3 标准库。

读写 ~/.config/opencode/opencode.jsonc（允许注释与尾逗号），AK 在 provider.<ID>.options.apiKey。
AK 一律从标准输入读取，不出现在命令行参数里，避免被 ps 看到。

子命令：
  set-key-opencode FILE OUT        原位替换 apiKey，注释与其他设置保留
  summary-opencode FILE            打印摘要（AK 打码）
  probe-opencode FILE              用配置文件里的 AK 发一条最小请求
"""
import argparse
import json
import logging
import os
import re
import ssl
import sys
import urllib.error
import urllib.request

LOG = logging.getLogger("ca_config")
NUM_RE = re.compile(r"-?(0|[1-9]\d*)(\.\d+)?([eE][+-]?\d+)?")


class JsoncError(ValueError):
    pass


class JsoncParser:
    """最小 JSONC 解析器：解析出数据，并记下每个字符串值在原文中的位置。"""

    def __init__(self, text):
        self.text = text
        self.i = 0
        self.spans = {}  # 路径元组 -> (起, 止)，止为右引号之后

    def error(self, msg):
        line = self.text.count("\n", 0, self.i) + 1
        raise JsoncError(f"第 {line} 行：{msg}")

    def skip(self):
        t = self.text
        while self.i < len(t):
            c = t[self.i]
            if c in " \t\r\n﻿":
                self.i += 1
            elif t.startswith("//", self.i):
                end = t.find("\n", self.i)
                self.i = len(t) if end < 0 else end + 1
            elif t.startswith("/*", self.i):
                end = t.find("*/", self.i + 2)
                if end < 0:
                    self.error("注释 /* 没有闭合")
                self.i = end + 2
            else:
                break

    def parse(self):
        self.skip()
        value = self.value(())
        self.skip()
        if self.i != len(self.text):
            self.error("JSON 结束后还有多余内容")
        return value

    def value(self, path):
        t = self.text
        if self.i >= len(t):
            self.error("内容意外结束")
        c = t[self.i]
        if c == "{":
            return self.obj(path)
        if c == "[":
            return self.arr(path)
        if c == '"':
            start = self.i
            s = self.string()
            self.spans[path] = (start, self.i)
            return s
        for word, val in (("true", True), ("false", False), ("null", None)):
            if t.startswith(word, self.i):
                self.i += len(word)
                return val
        m = NUM_RE.match(t, self.i)
        if m:
            self.i = m.end()
            return json.loads(m.group())
        self.error(f"无法识别的字符 {c!r}")

    def string(self):
        t = self.text
        start = self.i
        self.i += 1
        while self.i < len(t):
            c = t[self.i]
            if c == "\\":
                self.i += 2
            elif c == '"':
                self.i += 1
                try:
                    return json.loads(t[start:self.i])
                except json.JSONDecodeError as e:
                    self.error(f"字符串格式错误：{e.msg}")
            elif c == "\n":
                self.error("字符串中间换行")
            else:
                self.i += 1
        self.error("字符串没有闭合")

    def obj(self, path):
        self.i += 1
        result = {}
        while True:
            self.skip()
            if self.text.startswith("}", self.i):
                self.i += 1
                return result
            if not self.text.startswith('"', self.i):
                self.error("对象的键必须是双引号字符串")
            key = self.string()
            self.skip()
            if not self.text.startswith(":", self.i):
                self.error(f"键 {key} 后缺少冒号")
            self.i += 1
            self.skip()
            result[key] = self.value(path + (key,))
            self.skip()
            if self.text.startswith(",", self.i):
                self.i += 1
            elif not self.text.startswith("}", self.i):
                self.error("对象成员之间缺少逗号")

    def arr(self, path):
        self.i += 1
        result = []
        while True:
            self.skip()
            if self.text.startswith("]", self.i):
                self.i += 1
                return result
            result.append(self.value(path + (len(result),)))
            self.skip()
            if self.text.startswith(",", self.i):
                self.i += 1
            elif not self.text.startswith("]", self.i):
                self.error("数组元素之间缺少逗号")


def load(path, allow_missing=False):
    """读配置文件，返回 (原文, 数据, 字符串位置)。文件不存在且允许时返回空对象。"""
    if allow_missing and not os.path.exists(path):
        return "", {}, {}
    with open(path, encoding="utf-8") as f:
        text = f.read()
    if allow_missing and not text.strip():
        return "", {}, {}
    parser = JsoncParser(text)
    try:
        data = parser.parse()
    except JsoncError as e:
        raise SystemExit(f"{path} 解析失败，{e}")
    if not isinstance(data, dict):
        raise SystemExit(f"{path} 顶层不是对象")
    return text, data, parser.spans


def write_private(path, text):
    """以 600 权限写文件：先写同目录临时文件再改名，中途失败不留半个文件。"""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = f"{path}.tmp{os.getpid()}"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)
    LOG.debug("已写入 %s", path)


def replace_span(text, span, new_value):
    start, end = span
    return text[:start] + json.dumps(new_value, ensure_ascii=False) + text[end:]


def as_dict(value):
    return value if isinstance(value, dict) else {}


def mask(value):
    if not isinstance(value, str) or not value:
        return "（未设置）"
    if value.startswith("{env:") or value.startswith("{file:"):
        return value
    if len(value) <= 10:
        return "*" * len(value)
    return f"{value[:4]}…{value[-4:]}（共 {len(value)} 位）"


def read_token():
    token = sys.stdin.read().strip()
    if not token:
        raise SystemExit("没有从标准输入读到 AK")
    if any(c.isspace() for c in token):
        raise SystemExit("AK 中含有空白字符，请检查是否复制多了内容")
    return token


# ---------- OpenCode ----------

def pick_provider(data, wanted):
    provs = as_dict(data.get("provider"))
    if wanted and wanted not in provs and len(provs) == 1:
        LOG.warning("配置中没有服务商 %s，改用唯一的服务商 %s", wanted, next(iter(provs)))
        wanted = next(iter(provs))
    if wanted:
        if wanted not in provs:
            raise SystemExit(f"配置中没有服务商 {wanted}，现有：{'、'.join(provs) or '无'}")
        return wanted
    if len(provs) == 1:
        return next(iter(provs))
    model = data.get("model")
    if isinstance(model, str) and "/" in model and model.split("/", 1)[0] in provs:
        return model.split("/", 1)[0]
    raise SystemExit(f"配置中有多个服务商（{'、'.join(provs) or '无'}），请指定服务商 ID")


def cmd_set_key_opencode(args):
    text, data, spans = load(args.file)
    pid = pick_provider(data, args.provider)
    span = spans.get(("provider", pid, "options", "apiKey"))
    if not span:
        raise SystemExit(f"服务商 {pid} 的 options 里没有 apiKey，请在配置中为该服务商补上 options.apiKey")
    old = data["provider"][pid]["options"]["apiKey"]
    if old.startswith("{env:") or old.startswith("{file:"):
        raise SystemExit(f"apiKey 引用的是 {old}，请直接修改对应的环境变量或文件")
    write_private(args.out, replace_span(text, span, read_token()))
    LOG.info("已替换 OpenCode 服务商 %s 的 AK", pid)
    return 0


def cmd_summary_opencode(args):
    _, data, _ = load(args.file)
    print(f"OpenCode 配置：{args.file}")
    print(f"  默认模型：{data.get('model', '（未设置）')}")
    provs = as_dict(data.get("provider"))
    if not provs:
        print("  服务商：（无）")
    for pid, prov in provs.items():
        prov = as_dict(prov)
        opts = as_dict(prov.get("options"))
        print(f"  服务商 {pid}：接口 {opts.get('baseURL', '（未设置）')}，AK {mask(opts.get('apiKey'))}")
        models = as_dict(prov.get("models"))
        if not models:
            print("    模型：（未列出）")
        for name, mv in models.items():
            lim = as_dict(as_dict(mv).get("limit"))
            extra = f"（上下文 {lim.get('context', '-')}，输出 {lim.get('output', '-')}）" if lim else ""
            print(f"    模型 {name}{extra}")
    return 0


def resolve_key(value):
    if isinstance(value, str) and value.startswith("{env:") and value.endswith("}"):
        return os.environ.get(value[5:-1], "")
    if isinstance(value, str) and value.startswith("{file:") and value.endswith("}"):
        path = os.path.expanduser(value[6:-1])
        try:
            with open(path, encoding="utf-8") as f:
                return f.read().strip()
        except OSError as e:
            raise SystemExit(f"读取 AK 文件 {path} 失败：{e}")
    return value or ""


def cmd_probe_opencode(args):
    _, data, _ = load(args.file)
    pid = pick_provider(data, args.provider)
    prov = as_dict(data["provider"][pid])
    opts = as_dict(prov.get("options"))
    model = args.model
    if not model:
        m = data.get("model")
        model = m.split("/", 1)[1] if isinstance(m, str) and m.startswith(pid + "/") \
            else next(iter(as_dict(prov.get("models"))), "")
    return probe(opts.get("baseURL", ""), resolve_key(opts.get("apiKey")), model,
                 as_dict(opts.get("headers")), args.timeout, "OpenCode")


# ---------- 网络 ----------

def http(method, url, headers, body, timeout):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    LOG.debug("%s %s", method, url)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ssl.create_default_context()) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except urllib.error.URLError as e:
        reason = e.reason
        hint = ""
        if isinstance(reason, ssl.SSLError):
            hint = "（证书校验失败：接口可能用的是自签证书）"
        elif os.environ.get("https_proxy") or os.environ.get("http_proxy") \
                or os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY"):
            hint = "（当前设置了代理，内网地址可能需要加进 no_proxy）"
        raise SystemExit(f"连接 {url} 失败：{reason}{hint}")
    except TimeoutError:
        raise SystemExit(f"连接 {url} 超时（{timeout} 秒）")


def probe(base, token, model, extra_headers, timeout, label):
    base = (base or "").rstrip("/")
    if not base:
        raise SystemExit(f"{label}：没有接口地址")
    if not token:
        raise SystemExit(f"{label}：没有可用的 AK")
    if not model:
        raise SystemExit(f"{label}：找不到要测试的模型")
    headers = {"Authorization": f"Bearer {token}"}
    headers.update(extra_headers or {})
    body = {"model": model, "max_tokens": 16,
            "messages": [{"role": "user", "content": "只回复两个字母：OK"}]}
    print(f"{label} 连通测试：模型 {model}，地址 {base}/chat/completions")
    status, text = http("POST", base + "/chat/completions", headers, body, timeout)
    if not 200 <= status < 300:
        hint = {401: "AK 无效或已过期", 403: "AK 没有该模型的权限",
                404: "地址或模型名不对（接口地址通常以 /v1 结尾）"}.get(status, "")
        print(f"  失败：HTTP {status} {hint}\n  {text[:500]}")
        return 1
    try:
        content = json.loads(text)["choices"][0]["message"].get("content") or ""
    except (ValueError, KeyError, IndexError, TypeError, AttributeError):
        content = text[:200]
    print(f"  成功：HTTP {status}，模型回复：{content.strip()[:200]}")
    return 0


def main():
    default_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    ap = argparse.ArgumentParser(description="OpenCode 配置辅助脚本（供 codeagent-setup.sh 调用）")
    ap.add_argument("--log-level", default=default_level,
                    choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                    help="日志级别，默认 INFO，可用环境变量 LOG_LEVEL 覆盖")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("set-key-opencode")
    p.add_argument("file")
    p.add_argument("out")
    p.add_argument("--provider")
    p.set_defaults(func=cmd_set_key_opencode)

    p = sub.add_parser("summary-opencode")
    p.add_argument("file")
    p.set_defaults(func=cmd_summary_opencode)

    p = sub.add_parser("probe-opencode")
    p.add_argument("file")
    p.add_argument("--provider")
    p.add_argument("--model")
    p.add_argument("--timeout", type=int, default=60)
    p.set_defaults(func=cmd_probe_opencode)

    args = ap.parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s.%(funcName)s:%(lineno)d - %(message)s",
        stream=sys.stderr,
    )
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
