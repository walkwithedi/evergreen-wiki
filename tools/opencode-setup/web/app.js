/* OpenCode 配置页面：左侧显示本机现状，右侧是首次设置向导与其他操作。
   每个按钮请求本机服务运行 codeagent-setup.sh 的一个子命令，输出逐行显示。只与提供本页面的本机服务通信。 */
(function () {
  "use strict";

  var TITLES = {
    check: "环境检查",
    setup: "一键配置",
    test: "连通测试与首次启动自检"
  };

  var token = new URLSearchParams(location.search).get("t") || "";
  var state = null;
  var job = null;      // {id, action, es, lines, started, timer}
  var lost = false;

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
        if (!r.ok) {
          var e = new Error(data.error || ("HTTP " + r.status));
          e.status = r.status;
          throw e;
        }
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
    $("conn").textContent = "与配置服务的连接已断开。请重新双击「启动OpenCode配置」。";
    $("conn").className = "conn bad";
    setButtons();
  }

  // ---------- 现状卡片 ----------

  function card(level, title, detail) {
    var li = document.createElement("li");
    li.className = "card " + level;
    var dot = document.createElement("span");
    dot.className = "dot";
    var box = document.createElement("div");
    var b = document.createElement("b");
    b.textContent = title;
    box.appendChild(b);
    if (detail) {
      var p = document.createElement("p");
      p.textContent = detail;
      box.appendChild(p);
    }
    li.appendChild(dot);
    li.appendChild(box);
    return li;
  }

  function nodeMajor(v) {
    var m = /^v?(\d+)/.exec(v || "");
    return m ? parseInt(m[1], 10) : 0;
  }

  function renderCards() {
    var s = state.status || {};
    var conf = state.config || {};
    var ul = $("cards");
    var need = parseInt(s.node_major || "22", 10);
    var switchHint = (s.node_hint || "用 nvm 或系统自带的软件管理切换 Node 版本") + "，选择 v" + need + " 开头的版本，然后关闭本页面和终端窗口，重新双击启动。";
    if (s.ak_hint) $("ak-hint").textContent = s.ak_hint;
    ul.textContent = "";

    if (!s.node) {
      ul.appendChild(card("bad", "Node：未找到", switchHint));
    } else if (nodeMajor(s.node_version) >= need) {
      ul.appendChild(card("ok", "Node " + s.node_version, s.node));
    } else {
      ul.appendChild(card("warn", "Node " + (s.node_version || "版本未知") + "：需要 v" + need + " 或以上", switchHint));
    }

    if (s.opencode) {
      ul.appendChild(card("ok", "opencode " + (s.opencode_version || ""), s.opencode));
    } else {
      ul.appendChild(card("warn", "opencode：未找到", "配置仍可写入，但无法做首次启动自检。在终端里能直接运行时，运行 type opencode 查看实际位置。"));
    }

    if (conf.exists && conf.error) {
      ul.appendChild(card("bad", "OpenCode 配置无法读取", conf.error));
    } else if (conf.exists && conf.providers && conf.providers.length) {
      var p = conf.providers[0];
      var detail = "默认模型 " + (conf.model || "（未设置）") + "；AK " + p.ak;
      if (s.oc_mode && s.oc_mode !== "600") {
        ul.appendChild(card("warn", "OpenCode 已配置，文件权限为 " + s.oc_mode, detail + "。其中含 AK，再做一次一键配置会改为 600。"));
      } else {
        ul.appendChild(card("ok", "OpenCode 已配置", detail));
      }
    } else {
      ul.appendChild(card("bad", "OpenCode 尚未配置", "请先把一份 OpenCode 配置放到 ~/.config/opencode/opencode.jsonc（含接口地址、模型和 AK 字段），一键配置只替换其中的 AK。"));
    }

    if (s.proxy) {
      ul.appendChild(card("warn", "设置了代理", "内网接口地址可能需要加进 no_proxy"));
    }

    setButtons();
  }

  function loadState() {
    $("refresh").disabled = true;
    return api("GET", "/api/state").then(function (s) {
      state = s;
      renderCards();
      if (!job && s.job && !s.job.done) attach(s.job.id, s.job.action);
    }).catch(function () {}).then(function () { $("refresh").disabled = false; });
  }

  // ---------- AK ----------

  function akValue() { return $("ak").value.replace(/\s+/g, ""); }

  function akInfo() {
    var raw = $("ak").value;
    var v = akValue();
    var info = "";
    if (v) {
      info = "已粘贴 " + v.length + " 位";
      if (v.length > 10) info += "（" + v.slice(0, 4) + "…" + v.slice(-4) + "）";
      if (raw.trim() !== raw || /\s/.test(raw.trim())) info += "，已自动去掉空格和换行";
    }
    $("ak-info").textContent = info;
    setButtons();
  }

  // ---------- 按钮状态 ----------

  function setButtons() {
    var busy = !!(job && !job.done) || lost;
    var hasAk = akValue().length > 0;
    var hasConf = !!(state && state.config && state.config.exists);
    Array.prototype.forEach.call(document.querySelectorAll("[data-action]"), function (b) {
      var a = b.getAttribute("data-action");
      var ok = !busy && state !== null;
      if (a === "setup") ok = ok && hasAk && hasConf;
      if (a === "test") ok = ok && hasConf;
      b.disabled = !ok;
    });
    var tip = "";
    if (state && !hasConf) tip = "本机还没有 OpenCode 配置，无法配置";
    else if (!hasAk) tip = "先在第 2 步粘贴个人 AK";
    $("setup-btn").title = tip;
  }

  // ---------- 运行一个步骤 ----------

  function run(action, extra) {
    var body = { action: action };
    if (action === "setup") body.ak = akValue();
    if (extra) Object.keys(extra).forEach(function (k) { body[k] = extra[k]; });
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
      if (job.done) return;
      if (es.readyState === EventSource.CLOSED) {
        // 服务端关闭了连接但步骤未结束：稍后从断点重连；服务已停止时显示断开
        setTimeout(function () {
          if (job.done) return;
          api("GET", "/api/ping").then(connect).catch(function () {});
        }, 2000);
      }
    };
  }

  function lineClass(t) {
    var s = t.replace(/^\s+/, "");
    if (s.indexOf("[通过]") === 0 || s.indexOf("成功：") === 0) return "ok";
    if (s.indexOf("[注意]") === 0) return "warn";
    if (s.indexOf("[错误]") === 0 || s.indexOf("失败：") === 0) return "bad";
    if (s.indexOf("== ") === 0) return "head";
    if (s.indexOf("判断：") === 0) return "warn";
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
    $("elapsed").textContent = job.done ? "用时 " + t : "已运行 " + t + (job.action === "setup" || job.action === "test" ? "（首次启动自检最长约 3 分钟）" : "");
  }

  function has(text) {
    return job.lines.some(function (l) { return l.indexOf(text) >= 0; });
  }

  function verdict(ev) {
    var a = job.action;
    if (ev.result === "cancelled") return ["warn", "已取消。已完成的部分保留。"];
    if (ev.result !== "ok") {
      if (a === "setup") return ["bad", "未完成：请看下方标红的行。连通测试不通过时不会写入任何文件。"];
      return ["bad", "未完成：请看下方标红的行。"];
    }
    if (a === "setup") {
      if (has("可以正常对话")) return ["ok", "配置完成。请关闭所有终端窗口，重新打开一个终端，输入 opencode 启动。"];
      return ["warn", "配置已写入，但首次启动自检未通过或已跳过，请看下方「首次启动自检」部分的判断。也可以重新打开终端试着启动 opencode。"];
    }
    if (a === "test") {
      if (has("成功：HTTP") && has("可以正常对话")) return ["ok", "连通测试与首次启动自检都通过了。"];
      return ["warn", "有项目未通过，请看下方标黄、标红的行。"];
    }
    if (a === "check") return ["ok", "检查完成。左侧黄色、红色的项目按提示处理。"];
    return ["ok", "已完成，详情见下方。"];
  }

  function finish(ev) {
    job.done = true;
    if (job.es) job.es.close();
    clearInterval(job.timer);
    tick();
    show($("cancel"), false);
    var v = verdict(ev);
    if (ev.dropped) addLine("（另有 " + ev.dropped + " 行输出未显示）");
    $("result").className = "result " + v[0];
    $("result").textContent = v[1];
    show($("result"), true);
    if (ev.result === "ok" && job.action === "setup") {
      $("ak").value = "";
      akInfo();
    }
    setButtons();
    loadState();
  }

  // ---------- 事件 ----------

  function init() {
    if (!token) {
      document.body.textContent = "请从启动窗口中显示的地址打开本页面（地址里带有 ?t=…）。";
      return;
    }
    Array.prototype.forEach.call(document.querySelectorAll("[data-action]"), function (b) {
      b.addEventListener("click", function () {
        run(b.getAttribute("data-action"));
      });
    });
    $("ak").addEventListener("input", akInfo);
    $("ak-show").addEventListener("click", function () {
      var hidden = $("ak").type === "password";
      $("ak").type = hidden ? "text" : "password";
      $("ak-show").textContent = hidden ? "隐藏" : "显示";
    });
    $("refresh").addEventListener("click", loadState);
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
        p.textContent = "OpenCode 配置已退出，可以关闭本页面。";
        document.body.appendChild(p);
      }).catch(function () {});
    });
    // 定时告诉服务页面还开着；页面关闭后服务会自动停止
    setInterval(function () { if (!lost) api("GET", "/api/ping").catch(function () {}); }, 20000);
    loadState();
  }

  init();
})();
