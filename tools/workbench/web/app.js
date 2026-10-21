/* OpenCode 工作台首次向导：三步依次完成，前一步没完成时后一步的按钮不可用。
   第 1、2 步请求本机服务运行 opencode-setup 里 codeagent-setup.sh 的子命令，输出逐行显示；第 3 步取得工作台页面的地址后在本页打开。
   只与提供本页面的本机服务通信。 */
(function () {
  "use strict";

  var TITLES = { check: "环境检查", setup: "配置并自检" };
  var AUTO_SECONDS = 3;

  var token = new URLSearchParams(location.search).get("t") || "";
  var state = null;
  var job = null;     // {id, action, es, lines, started, timer, seq, done}
  var lost = false;
  var opening = false;
  var autoTimer = null;
  var autoChecked = false;
  var editionTouched = false;

  function $(id) { return document.getElementById(id); }
  function show(el, on) { el.hidden = !on; }

  function api(method, path, body) {
    var opts = { method: method, headers: { "X-Token": token } };
    if (body !== undefined) {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(body);
    }
    return fetch(path, opts).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (data) {
        if (!r.ok) throw new Error(data.error || ("HTTP " + r.status));
        return data;
      });
    }, function () {
      connLost();
      throw new Error("lost");
    });
  }

  function connLost() {
    if (lost) return;
    lost = true;
    $("conn").textContent = "与向导服务的连接已断开。请重新双击「启动OpenCode工作台」。";
    $("conn").className = "conn bad";
    setButtons();
  }

  // ---------- 步骤状态 ----------

  function wiz() { return (state && state.wizard) || {}; }

  function render() {
    var w = wiz();
    var s = state.status || {};
    $("need").textContent = w.node_major || 22;
    var parts = [];
    parts.push(s.node ? "Node " + (s.node_version || "版本未知") : "Node：未找到");
    parts.push(s.opencode ? "opencode " + (s.opencode_version || "") : "opencode：未找到");
    var conf = state.config || {};
    parts.push(conf.exists ? (conf.error ? "OpenCode 配置无法读取" : "已有 OpenCode 配置") : "还没有 OpenCode 配置");
    $("env-detail").textContent = parts.join("；") + "。";
    if (!w.env) {
      $("env-detail").textContent += " 版本不够或没找到时，点「开始检查」，按标黄的行处理后重新双击启动。";
    }
    badge("env", w.env);
    badge("ak", w.ak, w.ak_skipped ? "已跳过" : "");
    show($("skip-box"), !w.ak);
    show($("skipped-note"), !!w.ak_skipped);
    if (!editionTouched) {
      var pick = document.querySelector("input[name=edition][value=" + (w.simple === false ? "full" : "simple") + "]");
      if (pick) pick.checked = true;
    }
    editionNote();
    show($("kb-missing"), !w.kb_ready);
    kbStatus();
    $("step-env").className = "step" + (w.env ? " done" : " current");
    $("step-ak").className = "step" + (w.ak ? " done" : w.env ? " current" : " locked");
    $("step-kb").className = "step" + (w.env && w.ak ? " current" : " locked");
    setButtons();
    maybeAuto();
  }

  // 知识库是否就绪（GET /api/state 的 kb）：没就绪时工作台打开后会展开知识库，指向「安装与建库」
  function kbStatus() {
    var k = state.kb;
    var el = $("kb-status");
    show(el, !!k);
    if (!k) return;
    el.textContent = "知识库技能 " + k.skills + "/" + k.skills_total + " · 已登记 " + k.libraries + " 个库" +
      (k.ok ? "。" : "。打开后先点「安装与建库」：装好技能、建一个知识库。");
    el.className = "hint" + (k.ok ? "" : " warn");
  }

  function badge(name, done, label) {
    var b = $("badge-" + name);
    b.textContent = done ? label || "已完成" : "";
    b.className = "badge" + (done ? " ok" : "");
  }

  function loadState() {
    return api("GET", "/api/state").then(function (s) {
      state = s;
      render();
      if (!job && s.job && !s.job.done) attach(s.job.id, s.job.action);
    }).catch(function () {});
  }

  // 再次打开时前两步已完成：倒数后直接打开工作台，可以留在本页
  function maybeAuto() {
    if (autoChecked) return;
    autoChecked = true;
    var w = wiz();
    if (!(w.env && w.ak && w.kb_ready) || location.hash === "#stay") return;
    var left = AUTO_SECONDS;
    show($("auto"), true);
    $("auto-left").textContent = left;
    autoTimer = setInterval(function () {
      left -= 1;
      $("auto-left").textContent = left;
      if (left <= 0) { stopAuto(); openKb(); }
    }, 1000);
  }

  function stopAuto() {
    if (autoTimer) clearInterval(autoTimer);
    autoTimer = null;
    show($("auto"), false);
  }

  // ---------- AK ----------

  function akValue() { return $("ak").value.replace(/\s+/g, ""); }

  function akInfo() {
    var v = akValue();
    $("ak-info").textContent = v ? "已粘贴 " + v.length + " 位" + (v.length > 10 ? "（" + v.slice(0, 4) + "…" + v.slice(-4) + "）" : "") : "";
    setButtons();
  }

  // ---------- 按钮 ----------

  function setButtons() {
    var w = wiz();
    var busy = !!(job && !job.done) || lost || opening || state === null;
    var hasConf = !!(state && state.config && state.config.exists);
    Array.prototype.forEach.call(document.querySelectorAll("[data-action]"), function (b) {
      var a = b.getAttribute("data-action");
      var ok = !busy;
      if (a === "setup") ok = ok && w.env && hasConf && akValue().length > 0;
      b.disabled = !ok;
    });
    $("ak").disabled = !w.env || lost;
    $("kb-btn").disabled = busy || !(w.env && w.ak && w.kb_ready);
    $("skip-btn").disabled = busy || !w.env || !hasConf;
    $("skip-btn").title = !w.env ? "先完成第 1 步" : !hasConf ? "本机还没有 OpenCode 配置，不能跳过" : "";
    var tip = "";
    if (!w.env) tip = "先完成第 1 步";
    else if (!hasConf) tip = "本机还没有 OpenCode 配置，请先放好一份配置";
    else if (!akValue()) tip = "先粘贴个人 AK";
    $("setup-btn").title = tip;
  }

  // ---------- 第 2 步：跳过 ----------

  function skipAk() {
    stopAuto();
    if (!confirm("确认本机的 OpenCode 已经配好、能正常对话，跳过第 2 步吗？")) return;
    api("POST", "/api/skip_ak", {}).then(loadState).catch(function (e) {
      if (e.message !== "lost") alert(e.message);
    });
  }

  // ---------- 第 3 步 ----------

  function edition() {
    var r = document.querySelector("input[name=edition]:checked");
    return r ? r.value : "simple";
  }

  // 工作台已经在运行而选了另一个版本时，说明打开时会先重启它
  function editionNote() {
    var running = wiz().kb_running || "";
    var other = running && running !== edition();
    $("edition-note").textContent = other ? "工作台正以" + (running === "simple" ? "简易版" : "全版") +
      "运行，打开时会先关掉它再按所选版本启动，正在进行的对话会中断（可从「历史会话」接着聊）。" : "";
    show($("edition-note"), !!other);
  }

  function openKb() {
    stopAuto();
    opening = true;
    $("kb-info").textContent = "正在启动工作台，第一次可能要等半分钟……";
    setButtons();
    api("POST", "/api/kb", { simple: edition() === "simple" }).then(function (r) {
      $("kb-info").textContent = "正在打开工作台……";
      location.href = r.url;
    }).catch(function (e) {
      opening = false;
      $("kb-info").textContent = e.message === "lost" ? "" : "没有打开：" + e.message;
      setButtons();
    });
  }

  // ---------- 运行第 1、2 步 ----------

  function run(action) {
    stopAuto();
    var body = { action: action };
    if (action === "setup") body.ak = akValue();
    api("POST", "/api/action", body).then(function (r) {
      attach(r.job, action);
    }).catch(function (e) {
      if (e.message !== "lost") alert(e.message);
    });
  }

  function attach(id, action) {
    if (job && job.es) job.es.close();
    job = { id: id, action: action, done: false, lines: [], started: Date.now(), seq: 0 };
    $("run-title").textContent = TITLES[action] || action;
    $("log").textContent = "";
    show($("result"), false);
    show($("cancel"), true);
    $("cancel").disabled = false;
    show($("run"), true);
    $("run").scrollIntoView({ behavior: "smooth", block: "start" });
    tick();
    job.timer = setInterval(tick, 1000);
    setButtons();
    connect();
  }

  function connect() {
    var es = new EventSource("/api/events?job=" + encodeURIComponent(job.id) + "&after=" + job.seq + "&t=" + encodeURIComponent(token));
    job.es = es;
    es.onmessage = function (m) {
      var ev = JSON.parse(m.data);
      job.seq = ev.seq;
      if (ev.type === "line") addLine(ev.text);
      else if (ev.type === "end") finish(ev);
    };
    es.onerror = function () {
      if (job.done || es.readyState !== EventSource.CLOSED) return;
      setTimeout(function () {
        if (!job.done) api("GET", "/api/ping").then(connect).catch(function () {});
      }, 2000);
    };
  }

  function lineClass(t) {
    var s = t.replace(/^\s+/, "");
    if (s.indexOf("[通过]") === 0 || s.indexOf("成功：") === 0) return "ok";
    if (s.indexOf("[注意]") === 0 || s.indexOf("判断：") === 0) return "warn";
    if (s.indexOf("[错误]") === 0 || s.indexOf("失败：") === 0) return "bad";
    if (s.indexOf("== ") === 0) return "head";
    return "";
  }

  function addLine(text) {
    job.lines.push(text);
    var log = $("log");
    var atBottom = log.scrollTop + log.clientHeight >= log.scrollHeight - 8;
    var span = document.createElement("span");
    var cls = lineClass(text);
    if (cls) span.className = cls;
    span.textContent = text + "\n";
    log.appendChild(span);
    if (atBottom) log.scrollTop = log.scrollHeight;
  }

  function tick() {
    if (!job) return;
    var sec = Math.round((Date.now() - job.started) / 1000);
    var t = sec >= 60 ? Math.floor(sec / 60) + " 分 " + (sec % 60) + " 秒" : sec + " 秒";
    $("elapsed").textContent = (job.done ? "用时 " : "已运行 ") + t;
  }

  function verdict(ev) {
    if (ev.result === "cancelled") return ["warn", "已取消。已完成的部分保留。"];
    if (ev.result !== "ok") return ["bad", "未完成：请看下方标红的行。AK 测试不通过时不会写入任何文件。"];
    if (job.action === "setup") {
      var ok = job.lines.some(function (l) { return l.indexOf("可以正常对话") >= 0; });
      return ok ? ["ok", "配置完成，可以打开工作台了。"]
        : ["warn", "配置已写入，但首次启动自检没有通过，请看下方「首次启动自检」的判断。"];
    }
    return ["ok", "检查完成。标黄、标红的行按提示处理。"];
  }

  function finish(ev) {
    job.done = true;
    if (job.es) job.es.close();
    clearInterval(job.timer);
    tick();
    show($("cancel"), false);
    if (ev.dropped) addLine("（另有 " + ev.dropped + " 行输出未显示）");
    var v = verdict(ev);
    $("result").className = "result " + v[0];
    $("result").textContent = v[1];
    show($("result"), true);
    if (ev.result === "ok" && job.action === "setup") { $("ak").value = ""; akInfo(); }
    setButtons();
    loadState();
  }

  // ---------- 初始化 ----------

  function init() {
    if (!token) {
      document.body.textContent = "请从启动窗口中显示的地址打开本页面（地址里带有 ?t=…）。";
      return;
    }
    Array.prototype.forEach.call(document.querySelectorAll("[data-action]"), function (b) {
      b.addEventListener("click", function () { run(b.getAttribute("data-action")); });
    });
    $("ak").addEventListener("input", akInfo);
    $("ak-show").addEventListener("click", function () {
      var hidden = $("ak").type === "password";
      $("ak").type = hidden ? "text" : "password";
      $("ak-show").textContent = hidden ? "隐藏" : "显示";
    });
    $("kb-btn").addEventListener("click", openKb);
    $("skip-btn").addEventListener("click", skipAk);
    Array.prototype.forEach.call(document.querySelectorAll("input[name=edition]"), function (r) {
      r.addEventListener("change", function () { editionTouched = true; stopAuto(); editionNote(); });
    });
    $("auto-stop").addEventListener("click", stopAuto);
    $("cancel").addEventListener("click", function () {
      if (!job || job.done) return;
      $("cancel").disabled = true;
      api("POST", "/api/cancel", { job: job.id }).catch(function () {});
    });
    $("quit").addEventListener("click", function () {
      if (job && !job.done && !confirm("还有一个步骤在运行，取消它并退出吗？")) return;
      api("POST", "/api/quit", {}).then(function () {
        lost = true;
        document.body.textContent = "";
        var p = document.createElement("p");
        p.className = "bye";
        p.textContent = "向导已退出，可以关闭本页面。";
        document.body.appendChild(p);
      }).catch(function () {});
    });
    // 定时告诉服务页面还开着；页面关闭后服务会自动停止
    setInterval(function () { if (!lost) api("GET", "/api/ping").catch(function () {}); }, 20000);
    loadState();
  }

  init();
})();
