#!/usr/bin/env python3
"""OpenCode 工作台首次向导：本机起一个只供本机访问的小服务，在默认浏览器中按顺序引导三步。

  python3 wk_web.py          启动服务并打开页面（双击「启动OpenCode工作台」即运行这一行）
选项：--port N（默认自动选空闲端口）、--no-browser（只显示地址）、--idle 秒数（页面关闭这么久后自动停止，
0 表示不自动停止，默认 120）、--codeagent 目录、--wiki 目录（默认取同一 tools/ 下的 opencode-setup 与
本仓库根目录）、--log-level（默认值可由环境变量 LOG_LEVEL 覆盖）。

1. 环境检查、2. 填 AK 并自检：复用 opencode-setup 的 ca_web.py，以子进程运行 codeagent-setup.sh 的
check、setup 子命令，输出逐行推送到页面。
3. 打开工作台：以独立进程启动本仓库的知识库客户端（tools/kb-client）（中文、OpenCode、
--chat-first：以对话为主，知识库收起；选简易版时另加 --simple），
读出它的页面地址交给本页跳转；本服务停止后知识库客户端照常运行，页面关闭后由它自己按时停止。
每一步是否完成由检查结果推出。另外只记两项选择（~/.config/work-kb/state.json）：第 2 步是否按
「已配置，跳过」跳过，以及工作台用简易版还是全版。只用 Python 3 标准库。
"""
import argparse
import importlib.util
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import webbrowser
from http.server import ThreadingHTTPServer

LOG = logging.getLogger("wk_web")
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s.%(funcName)s:%(lineno)d - %(message)s"
HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(HERE, "web")
STATIC = {"index.html": "text/html; charset=utf-8", "app.js": "text/javascript; charset=utf-8",
          "style.css": "text/css; charset=utf-8"}
FILES = {name: os.path.join(WEB, name) for name in STATIC}  # 只发送这几个固定文件
KB_ARGS = ["--lang", "zh", "--agent", "opencode", "--chat-first", "--no-browser"]
KB_START_TIMEOUT = 60  # 秒：等知识库客户端打印页面地址
URL_RE = re.compile(r"http://127\.0\.0\.1:\d+/\?t=\S+")
ca_web = None  # main() 从 opencode-setup 目录导入


def kb_client_path(wiki):
    return os.path.join(wiki, "tools", "kb-client", "kb_client.py")


def node_major(version):
    m = re.match(r"v?(\d+)", version or "")
    return int(m.group(1)) if m else 0


def prefs_path():
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "work-kb", "state.json")


def remember_location():
    """把本目录写进 ~/.config/work-kb/location（仅本人可读），桌面上的入口副本按它找到向导；写不了只记警告。"""
    path = os.path.join(os.path.dirname(prefs_path()), "location")
    try:
        os.makedirs(os.path.dirname(path), mode=0o700, exist_ok=True)
        fd = os.open(path + ".tmp", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(HERE + "\n")
        os.replace(path + ".tmp", path)
    except OSError as e:
        LOG.warning("没有记下向导位置 %s：%s", path, e)


def load_prefs():
    """记下的选择：ak_skipped（第 2 步按「已配置，跳过」跳过）、simple（工作台用简易版，默认是）。"""
    try:
        with open(prefs_path(), encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save_prefs(**changes):
    data = load_prefs()
    data.update(changes)
    path = prefs_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)
    return data


def wizard(st, wiki, prefs=None):
    """三步各自是否完成。第 2 步以 ~/.bashrc 中的 codeagent-setup 标记段为准：一键配置只在新 AK
    测试通过后才写入这一段。用别的办法配好 OpenCode 的，可以按「已配置，跳过」跳过，此后只要
    本机还有 OpenCode 配置就算完成（不再检查 AK）。"""
    prefs = load_prefs() if prefs is None else prefs
    s = st.get("status") or {}
    try:
        need = int(s.get("node_major") or 22)
    except ValueError:
        need = 22
    env_ok = node_major(s.get("node_version")) >= need and bool(s.get("opencode"))
    has_conf = bool((st.get("config") or {}).get("exists"))
    marked = s.get("env_block") == "1" and has_conf
    skipped = bool(prefs.get("ak_skipped")) and has_conf and not marked
    return {"env": env_ok, "ak": marked or skipped, "ak_skipped": skipped,
            "kb_ready": os.path.isfile(kb_client_path(wiki)), "node_major": need,
            "simple": prefs.get("simple", True) is not False}


LOG_KEEP_DAYS = 7


def log_folder():
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "work-kb", "logs")


def open_log_file(level):
    """日志同时写入 ~/.config/work-kb/logs/wk-web-YYYYMMDD.log（只有本人可读），级别为 INFO，或更低的
    --log-level；超过 LOG_KEEP_DAYS 天的日志文件删除。返回路径，写不了时返回空串。"""
    folder = log_folder()
    try:
        os.makedirs(folder, mode=0o700, exist_ok=True)
        for f in os.listdir(folder):
            p = os.path.join(folder, f)
            if f.startswith("wk-web-") and f.endswith(".log") and time.time() - os.path.getmtime(p) > LOG_KEEP_DAYS * 86400:
                os.remove(p)
        path = os.path.join(folder, time.strftime("wk-web-%Y%m%d.log"))
        os.close(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600))
        os.chmod(path, 0o600)
        handler = logging.FileHandler(path, encoding="utf-8")
    except OSError as e:
        LOG.warning("没有日志文件：%s", e)
        return ""
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    handler.setLevel(min(logging.INFO, getattr(logging, level)))
    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(min(root.level, handler.level))
    return path


def make_app_class():
    class WorkApp(ca_web.App):
        def __init__(self, idle, wiki):
            super().__init__(idle)
            self.wiki = wiki
            self.kb_proc = None
            self.kb_url = ""
            self.kb_simple = None
            self.kb_lock = threading.Lock()

        def kb_running(self):
            """在运行的工作台是哪个版本："simple"、"full"，没有在运行时为空。"""
            if self.kb_proc is None or self.kb_proc.poll() is not None or not self.kb_url:
                return ""
            return "simple" if self.kb_simple else "full"

        def kb_call(self, method, path):
            """请求本服务启动的知识库客户端的接口，返回解析后的 JSON；不可用时返回 None。"""
            m = re.match(r"(http://127\.0\.0\.1:\d+)/\?t=(\S+)", self.kb_url or "")
            if not m:
                return None
            data = b"{}" if method == "POST" else None
            req = urllib.request.Request(f"{m.group(1)}{path}?t={m.group(2)}", data=data, method=method,
                                         headers={"Content-Type": "application/json", "X-Token": m.group(2)})
            try:
                with urllib.request.urlopen(req, timeout=5) as r:
                    return json.loads(r.read() or b"null")
            except (OSError, ValueError) as e:
                LOG.warning("请求知识库客户端 %s %s 出错：%s", method, path, e)
                return None

        def kb_step_running(self):
            """工作台此刻是否有未完成的管理步骤（安装与建库、备份等，知识库客户端 GET /api/state 的 job）。"""
            r = self.kb_call("GET", "/api/state")
            job = r.get("job") if isinstance(r, dict) else None
            return isinstance(job, dict) and not job.get("done")

        def stop_kb(self):
            """停掉本服务启动的知识库客户端：先请它自己退出（它会一并停掉它启动的 OpenCode），
            10 秒内没退出再结束进程。"""
            proc = self.kb_proc
            if proc is None or proc.poll() is not None:
                return
            self.kb_call("POST", "/api/quit")
            try:
                proc.wait(10)
            except subprocess.TimeoutExpired:
                LOG.warning("知识库客户端 10 秒内没有退出，结束进程 %s", proc.pid)
                proc.terminate()
                try:
                    proc.wait(5)
                except subprocess.TimeoutExpired:
                    proc.kill()

        def open_kb(self, opencode="", simple=True):
            """知识库客户端的页面地址，没有在运行时先启动它；在运行的版本（简易版或全版）与所选不同时
            先停掉再按所选启动。返回 (地址, 错误说明)。"""
            with self.kb_lock:
                if self.kb_proc is not None and self.kb_proc.poll() is None and self.kb_url:
                    if self.kb_simple == simple:
                        return self.kb_url, ""
                    if self.kb_step_running():
                        LOG.info("工作台有管理步骤在运行，不切换版本")
                        return "", "工作台有知识库管理步骤在运行（如安装与建库、备份）：等它完成后再换版本"
                    LOG.info("工作台改为%s，重新启动知识库客户端", "简易版" if simple else "全版")
                    self.stop_kb()
                script = kb_client_path(self.wiki)
                if not os.path.isfile(script):
                    return "", f"缺少 {script}：请把发行包里的三个文件夹放在一起"
                args = [sys.executable, script] + KB_ARGS + (["--simple"] if simple else [])
                self.kb_url = ""
                if opencode:
                    args += ["--opencode", opencode]
                # 输出写进只有本人可读的文件：本服务先停止时，知识库客户端不会因管道关闭而出错
                fd, out = tempfile.mkstemp(prefix="work-kb-client-", suffix=".log")
                LOG.info("启动知识库客户端，输出见 %s", out)
                try:
                    self.kb_proc = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=fd, stderr=fd,
                                                    start_new_session=True)
                except OSError as e:
                    return "", f"无法启动知识库客户端：{e}"
                finally:
                    os.close(fd)
                deadline = time.time() + KB_START_TIMEOUT
                while time.time() < deadline:
                    with open(out, encoding="utf-8", errors="replace") as f:
                        text = f.read()
                    m = URL_RE.search(text)
                    if m:
                        self.kb_url = m.group(0)
                        self.kb_simple = simple
                        return self.kb_url, ""
                    if self.kb_proc.poll() is not None:
                        tail = "\n".join(text.strip().splitlines()[-5:])
                        return "", f"知识库客户端已退出（退出码 {self.kb_proc.returncode}）：{tail}"
                    time.sleep(0.3)
                return "", f"知识库客户端 {KB_START_TIMEOUT} 秒内没有给出页面地址，输出见 {out}"

    return WorkApp


def make_handler_class():
    class Handler(ca_web.Handler):
        server_version = "wk-web"

        def do_GET(self):
            path = self.path.split("?", 1)[0]
            if path == "/api/state":
                g = self.guard()
                if g is None:
                    return None
                data = ca_web.state()
                job = self.app.job
                data["job"] = None if job is None else {"id": job.id, "action": job.action, "done": job.done}
                data["wizard"] = wizard(data, self.app.wiki)
                data["wizard"]["kb_running"] = self.app.kb_running()
                return self.send(200, data)
            name = "index.html" if path == "/" else path[1:]
            if name in FILES:
                if self.guard() is None:
                    return None
                with open(FILES[name], "rb") as f:
                    return self.send(200, f.read(), STATIC[name])
            return super().do_GET()

        def read_json(self):
            try:
                n = int(self.headers.get("Content-Length") or 0)
                data = json.loads(self.rfile.read(n) or b"{}") if 0 <= n <= 4096 else None
            except (ValueError, OSError):
                data = None
            return data if isinstance(data, dict) else None

        def do_POST(self):
            path = self.path.split("?", 1)[0]
            if path not in ("/api/kb", "/api/skip_ak"):
                return super().do_POST()
            if self.guard() is None:
                return None
            if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
                return self.send(415, {"error": "json only"})
            body = self.read_json()
            if body is None:
                return self.send(400, {"error": "请求内容不对"})
            st = ca_web.state()
            if path == "/api/skip_ak":
                w = wizard(st, self.app.wiki)
                if not w["env"]:
                    return self.send(409, {"error": "请先完成第 1 步"})
                if not (st.get("config") or {}).get("exists"):
                    return self.send(409, {"error": "本机还没有 OpenCode 配置，不能跳过"})
                save_prefs(ak_skipped=True)
                LOG.info("第 2 步按「已配置，跳过」跳过")
                return self.send(200, {"ok": True})
            simple = body.get("simple", True)
            if not isinstance(simple, bool):
                return self.send(400, {"error": "simple 只能是 true 或 false"})
            w = wizard(st, self.app.wiki)
            if not (w["env"] and w["ak"]):
                return self.send(409, {"error": "请先完成第 1、2 步"})
            save_prefs(simple=simple)
            LOG.info("打开工作台（%s）", "简易版" if simple else "全版")
            url, why = self.app.open_kb((st.get("status") or {}).get("opencode", ""), simple)
            if not url:
                LOG.warning("工作台没有打开：%s", why)
                return self.send(500, {"error": why})
            return self.send(200, {"url": url})

    return Handler


def serve(app, handler_class, port, open_browser):
    handler = type("BoundHandler", (handler_class,), {"app": app})
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    server.daemon_threads = True
    app.server = server
    url = f"http://127.0.0.1:{server.server_address[1]}/?t={app.token}"
    print(f"OpenCode 工作台向导：{url}", flush=True)
    print("浏览器没有自动打开时，把上面的地址复制到浏览器中打开。", flush=True)
    if open_browser:
        threading.Thread(target=webbrowser.open, args=(url,), daemon=True).start()
    if app.idle:
        threading.Thread(target=app.idle_watch, daemon=True).start()
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        LOG.info("在终端中按了 Ctrl+C")
    finally:
        if app.job and not app.job.done:
            app.job.cancel()
        server.server_close()
    print("OpenCode 工作台向导已停止。已打开的工作台页面不受影响。", flush=True)


def main():
    global ca_web
    ap = argparse.ArgumentParser(description="OpenCode 工作台首次向导")
    ap.add_argument("--port", type=int, default=0, help="端口，默认自动选空闲端口")
    ap.add_argument("--no-browser", action="store_true", help="不打开浏览器，只显示地址")
    ap.add_argument("--idle", type=int, default=120, metavar="秒数",
                    help="页面关闭这么久后自动停止，0 表示不自动停止，默认 120")
    ap.add_argument("--codeagent", default=os.path.join(HERE, "..", "opencode-setup"), metavar="目录",
                    help="opencode-setup 所在目录，默认取同一 tools/ 下的")
    ap.add_argument("--wiki", default=os.path.join(HERE, "..", ".."), metavar="目录",
                    help="evergreen-wiki 仓库（或发行包解压后的 evergreen-wiki/）根目录，默认取本目录上两级")
    ap.add_argument("--log-level", default=os.environ.get("LOG_LEVEL", "WARNING").upper(),
                    choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                    help="日志级别，默认 WARNING，可用环境变量 LOG_LEVEL 覆盖")
    a = ap.parse_args()
    logging.basicConfig(level=getattr(logging, a.log_level), format=LOG_FORMAT, stream=sys.stderr)
    logging.getLogger().handlers[0].setLevel(getattr(logging, a.log_level))
    path = open_log_file(a.log_level)
    LOG.info("向导启动（Python %s），日志 %s", sys.version.split()[0], path or "无")
    if a.idle < 0:
        ap.error("--idle 不能小于 0")
    remember_location()
    codeagent = os.path.realpath(a.codeagent)
    if not os.path.isfile(os.path.join(codeagent, "ca_web.py")):
        ap.error(f"在 {codeagent} 找不到 opencode-setup：请保持发行包解压后的目录结构")
    # 按文件路径加载 opencode-setup/ca_web.py；它自己导入同目录的 ca_config
    sys.path.insert(0, codeagent)
    spec = importlib.util.spec_from_file_location("ca_web", os.path.join(codeagent, "ca_web.py"))
    ca_web = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ca_web)
    serve(make_app_class()(a.idle, os.path.realpath(a.wiki)), make_handler_class(), a.port, not a.no_browser)
    return 0


if __name__ == "__main__":
    sys.exit(main())
