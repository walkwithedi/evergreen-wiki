#!/usr/bin/env python3
"""OpenCode 配置的浏览器界面：本机起一个只供本机访问的小服务，在默认浏览器中打开配置页面。

  python3 ca_web.py          启动服务并打开页面（双击「启动OpenCode配置」即运行这一行）
选项：--port N（默认自动选空闲端口）、--no-browser（只显示地址）、--idle 秒数（页面关闭这么久后自动
停止，0 表示不自动停止，默认 120）、--log-level（默认值可由环境变量 LOG_LEVEL 覆盖）。

页面上的每个按钮都以子进程运行同目录的 codeagent-setup.sh 对应子命令（带 -y，不逐项确认），输出逐行
推送到页面，所以页面与终端菜单的行为一致。AK 经环境变量 CA_AK 交给子进程，不出现在命令行参数里。
服务只监听 127.0.0.1，只接受地址中带随机令牌的请求，浏览器里的其他网页无法调用；只发送 web/ 下
三个固定文件。只用 Python 3 标准库。
"""
import argparse
import json
import logging
import os
import secrets
import signal
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

import ca_config

LOG = logging.getLogger("ca_web")
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s.%(funcName)s:%(lineno)d - %(message)s"
HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "codeagent-setup.sh")
WEB = os.path.join(HERE, "web")
STATIC = {"index.html": "text/html; charset=utf-8", "app.js": "text/javascript; charset=utf-8",
          "style.css": "text/css; charset=utf-8"}
FILES = {name: os.path.join(WEB, name) for name in STATIC}  # 只发送这几个固定文件
# 页面上的动作 -> codeagent-setup.sh 的参数；need_ak 表示要从页面带 AK
ACTIONS = {
    "check": (["check"], False),
    "setup": (["setup", "-y"], True),
    "test": (["test", "-y"], False),
}
MAX_BODY = 16 * 1024
MAX_EVENTS = 5000  # 单个步骤保留的输出行数上限，超出的只计数


class Job:
    """一个正在运行（或已结束）的步骤。事件从 1 编号并一直保留，页面断线重连后可以补齐。"""

    def __init__(self, action):
        self.id = secrets.token_hex(4)
        self.action = action
        self.events = []
        self.dropped = 0
        self.cond = threading.Condition()
        self.proc = None
        self.cancelled = False
        self.done = False
        self.started = time.time()

    def emit(self, etype, **data):
        with self.cond:
            if etype == "line" and len(self.events) >= MAX_EVENTS:
                self.dropped += 1
                return
            self.events.append(dict(data, type=etype, seq=len(self.events) + 1))
            self.cond.notify_all()

    def since(self, seq, timeout):
        with self.cond:
            if len(self.events) <= seq and not self.done:
                self.cond.wait(timeout)
            return self.events[seq:]

    def cancel(self):
        """结束子进程组：先 SIGTERM，3 秒后仍在运行则 SIGKILL。"""
        self.cancelled = True
        proc = self.proc
        if proc is None or proc.poll() is not None:
            return
        for sig, wait in ((signal.SIGTERM, 3), (signal.SIGKILL, 0)):
            try:
                os.killpg(proc.pid, sig)
            except (ProcessLookupError, PermissionError):
                return
            try:
                proc.wait(wait)
                return
            except subprocess.TimeoutExpired:
                continue


def child_env(extra=None):
    """子进程环境：沿用当前环境（不继承外部的 CA_AK），另加页面传来的变量。"""
    env = dict(os.environ)
    env.pop("CA_AK", None)
    env.update(extra or {})
    return env


def run_script(args, env, timeout=None):
    """以无控制终端的方式运行 codeagent-setup.sh，返回 (退出码, 输出)。"""
    proc = subprocess.run(["bash", SCRIPT] + args, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, env=env, timeout=timeout, start_new_session=True)
    return proc.returncode, proc.stdout.decode("utf-8", "replace")


def config_summary(path):
    """OpenCode 配置的摘要（AK 打码），供状态卡片显示。"""
    out = {"exists": os.path.isfile(path), "error": "", "model": "", "providers": []}
    if not out["exists"]:
        return out
    try:
        _, data, _ = ca_config.load(path)
    except (SystemExit, OSError, ValueError) as e:
        out["error"] = str(e)
        return out
    out["model"] = data.get("model") or ""
    for pid, prov in ca_config.as_dict(data.get("provider")).items():
        opts = ca_config.as_dict(ca_config.as_dict(prov).get("options"))
        out["providers"].append({"id": pid, "base_url": opts.get("baseURL", ""),
                                 "ak": ca_config.mask(opts.get("apiKey")),
                                 "models": list(ca_config.as_dict(ca_config.as_dict(prov).get("models")))})
    return out


def state():
    """页面左侧状态卡片的全部数据。"""
    status = {}
    try:
        rc, text = run_script(["status"], child_env(), timeout=60)
        for line in text.splitlines():
            key, sep, value = line.partition("\t")
            if sep:
                status[key] = value
        if rc != 0:
            LOG.warning("codeagent-setup.sh status 退出码 %s", rc)
    except (OSError, subprocess.TimeoutExpired) as e:
        LOG.warning("读取现状失败：%s", e)
    oc_file = status.get("oc_file", "")
    return {
        "status": status,
        "config": config_summary(oc_file) if oc_file else {"exists": False},
    }


class App:
    def __init__(self, idle):
        self.idle = idle
        self.token = secrets.token_urlsafe(24)
        self.job = None
        self.lock = threading.Lock()
        self.last_seen = time.time()
        self.server = None

    def start(self, action, ak=""):
        with self.lock:
            if self.job and not self.job.done:
                return None
            job = Job(action)
            self.job = job
        args, need_ak = ACTIONS[action]
        extra = {}
        if need_ak:
            extra["CA_AK"] = ak
        threading.Thread(target=self.run, args=(job, args, child_env(extra)), daemon=True).start()
        return job

    def run(self, job, args, env):
        code = None
        try:
            job.proc = subprocess.Popen(["bash", SCRIPT] + args, stdin=subprocess.DEVNULL,
                                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env,
                                        start_new_session=True)
            if job.cancelled:  # 取消发生在进程启动之前
                job.cancel()
            for raw in job.proc.stdout:
                job.emit("line", text=raw.decode("utf-8", "replace").rstrip("\n"))
            code = job.proc.wait()
        except OSError as e:
            LOG.exception("运行 %s 失败", args)
            job.emit("line", text=f"[错误] 无法运行 {SCRIPT}：{e}")
        finally:
            result = "cancelled" if job.cancelled else ("ok" if code == 0 else "failed")
            LOG.info("步骤 %s 结束：%s（退出码 %s）", job.action, result, code)
            with job.cond:
                job.done = True
                job.events.append({"type": "end", "result": result, "code": code,
                                   "dropped": job.dropped, "seq": len(job.events) + 1})
                job.cond.notify_all()

    def idle_watch(self):
        while self.idle:
            time.sleep(min(5, self.idle))
            busy = self.job is not None and not self.job.done
            if not busy and time.time() - self.last_seen > self.idle:
                LOG.info("页面已关闭 %s 秒，自动停止", self.idle)
                threading.Thread(target=self.server.shutdown, daemon=True).start()
                return


class Handler(BaseHTTPRequestHandler):
    app = None
    server_version = "ca-web"
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        LOG.debug("%s - %s", self.address_string(), fmt % args)

    def send(self, code, body, ctype="application/json; charset=utf-8"):
        if not isinstance(body, bytes):
            body = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy",
                         "default-src 'self'; style-src 'self'; script-src 'self'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(body)

    def guard(self):
        """请求可以继续时返回 (路径, 查询参数)，否则已回复错误并返回 None。"""
        url = urlsplit(self.path)
        query = parse_qs(url.query)
        port = self.server.server_address[1]
        if self.headers.get("Host", "") not in (f"127.0.0.1:{port}", f"localhost:{port}"):
            self.send(403, {"error": "host"})
            return None
        if url.path.startswith("/api/"):
            given = self.headers.get("X-Token") or (query.get("t") or [""])[0]
            if not secrets.compare_digest(given, self.app.token):
                self.send(403, {"error": "token"})
                return None
        self.app.last_seen = time.time()
        return url.path, query

    def do_GET(self):
        g = self.guard()
        if g is None:
            return None
        path, query = g
        if path == "/api/state":
            data = state()
            job = self.app.job
            data["job"] = None if job is None else {"id": job.id, "action": job.action, "done": job.done}
            return self.send(200, data)
        if path == "/api/ping":  # 页面定时请求，表示还开着
            return self.send(200, {"ok": True})
        if path == "/api/events":
            return self.events(query)
        name = "index.html" if path == "/" else path[1:]
        if name in FILES:
            with open(FILES[name], "rb") as f:
                return self.send(200, f.read(), STATIC[name])
        return self.send(404, {"error": "not found"})

    def do_POST(self):
        g = self.guard()
        if g is None:
            return None
        path, _ = g
        if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
            return self.send(415, {"error": "json only"})
        try:
            n = int(self.headers.get("Content-Length") or 0)
            if n > MAX_BODY:
                return self.send(413, {"error": "too large"})
            body = json.loads(self.rfile.read(n) or b"{}")
            if not isinstance(body, dict):
                raise ValueError
        except ValueError:
            return self.send(400, {"error": "bad json"})
        if path == "/api/action":
            action = body.get("action")
            if action not in ACTIONS:
                return self.send(400, {"error": "未知的操作"})
            ak = body.get("ak") if isinstance(body.get("ak"), str) else ""
            ak = "".join(ak.split())
            if ACTIONS[action][1] and not ak:
                return self.send(400, {"error": "请先粘贴个人 AK"})
            job = self.app.start(action, ak)
            if job is None:
                return self.send(409, {"error": "还有一个步骤在运行"})
            return self.send(200, {"job": job.id})
        if path == "/api/cancel":
            job = self.app.job
            if job is None or job.id != body.get("job"):
                return self.send(404, {"error": "no such job"})
            threading.Thread(target=job.cancel, daemon=True).start()
            return self.send(200, {"ok": True})
        if path == "/api/quit":
            self.send(200, {"ok": True})
            job = self.app.job
            if job and not job.done:
                job.cancel()
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return None
        return self.send(404, {"error": "not found"})

    def events(self, query):
        """当前步骤的事件流（SSE），从 Last-Event-ID 或 ?after= 之后的事件开始。"""
        job = self.app.job
        if job is None or job.id != (query.get("job") or [""])[0]:
            return self.send(404, {"error": "no such job"})
        try:
            seq = int(self.headers.get("Last-Event-ID") or (query.get("after") or ["0"])[0])
        except ValueError:
            seq = 0
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()
        self.close_connection = True
        try:
            while True:
                evs = job.since(seq, 15)
                if not evs:
                    self.wfile.write(b": keep-alive\n\n")
                for ev in evs:
                    seq = ev["seq"]
                    self.wfile.write(f"id: {seq}\ndata: {json.dumps(ev, ensure_ascii=False)}\n\n".encode("utf-8"))
                self.wfile.flush()
                self.app.last_seen = time.time()
                if evs and evs[-1]["type"] == "end":
                    return None
        except (BrokenPipeError, ConnectionResetError):
            LOG.debug("页面关闭了事件流")
        return None


def serve(app, port, open_browser):
    handler = type("BoundHandler", (Handler,), {"app": app})
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    server.daemon_threads = True
    app.server = server
    url = f"http://127.0.0.1:{server.server_address[1]}/?t={app.token}"
    print(f"OpenCode 配置页面：{url}", flush=True)
    print("浏览器没有自动打开时，把上面的地址复制到浏览器中打开。配置完成后在页面上点「退出」，或关闭本窗口。",
          flush=True)
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
    print("OpenCode 配置页面已停止。", flush=True)


def main():
    ap = argparse.ArgumentParser(description="OpenCode 配置的浏览器界面")
    ap.add_argument("--port", type=int, default=0, help="端口，默认自动选空闲端口")
    ap.add_argument("--no-browser", action="store_true", help="不打开浏览器，只显示地址")
    ap.add_argument("--idle", type=int, default=120, metavar="秒数",
                    help="页面关闭这么久后自动停止，0 表示不自动停止，默认 120")
    ap.add_argument("--log-level", default=os.environ.get("LOG_LEVEL", "WARNING").upper(),
                    choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                    help="日志级别，默认 WARNING，可用环境变量 LOG_LEVEL 覆盖")
    a = ap.parse_args()
    logging.basicConfig(level=getattr(logging, a.log_level), format=LOG_FORMAT, stream=sys.stderr)
    if a.idle < 0:
        ap.error("--idle 不能小于 0")
    if not os.path.isfile(SCRIPT):
        ap.error(f"缺少 {SCRIPT}，请把整个文件夹一起拷贝")
    serve(App(a.idle), a.port, not a.no_browser)
    return 0


if __name__ == "__main__":
    sys.exit(main())
