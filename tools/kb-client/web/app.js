/* Knowledge base client page: the state of the libraries, the management steps and their questions,
   and a folder browser. Talks only to the local server that served it; no outside resources. */
(function () {
  "use strict";

  var T = {
    en: {
      title: "Knowledge base",
      quit: "Quit",
      libraries: "Libraries",
      no_libraries: "No library yet. Choose Set up to make one.",
      manage: "Manage",
      setup: "Set up",
      backup: "Back up",
      rollback: "Roll back",
      move: "Move a library",
      uninstall: "Uninstall",
      move_this: "Move",
      welcome_title: "Welcome",
      welcome: "Set up installs the skills, makes a library and tells your agent about it; choose it again to add another library. Back up, Roll back, Move and Uninstall manage what Set up wrote. Every step shows a preview before it changes anything.",
      cancel_step: "Cancel this step",
      chat_title: "Conversation",
      chat_later: "Talking to your agent from this page comes in a later version. Until then, open your agent as usual; it finds the libraries listed here.",
      browse_title: "Choose a folder",
      up: "Up",
      go: "Open",
      show_hidden: "Show hidden folders",
      cancel: "Cancel",
      choose_this: "Choose this folder",
      new_name: "New folder inside it (made when the step writes; leave empty to use the folder itself)",
      chosen: "Answer: {path}",
      browse: "Browse...",
      ok: "OK",
      yes: "Yes",
      no: "No",
      home: "Home folder",
      media: "Drive",
      more: "{n} more entries are not listed.",
      missing: "folder not found",
      not_local: "not on this computer",
      agent_ok: "OpenCode ready",
      agent_no_model: "OpenCode: no model set",
      agent_missing: "OpenCode not found",
      skills_none: "Skills not installed",
      skills_in: "Skills: {names}",
      backups: "{n} backups",
      no_backups: "No backups yet",
      result_ok: "Finished.",
      result_cancelled: "Cancelled.",
      result_stopped: "Stopped.",
      result_error: "The step failed; the messages above say why.",
      busy: "Another step is still running.",
      lost: "The connection to the knowledge base client was lost. Start it again and reload this page.",
      quit_done: "The knowledge base client has stopped. You can close this tab.",
      quit_confirm: "A step is still running. Cancel it and quit?",
      no_token: "Open this page from the address the knowledge base client printed when it started."
    },
    zh: {
      title: "知识库",
      quit: "退出",
      libraries: "知识库",
      no_libraries: "还没有知识库。选「安装与建库」建一个。",
      manage: "管理",
      setup: "安装与建库",
      backup: "备份",
      rollback: "回滚",
      move: "移动知识库",
      uninstall: "卸载",
      move_this: "移动",
      welcome_title: "欢迎",
      welcome: "「安装与建库」会装好技能、建一个知识库并告诉助手；要再加一个库时再选一次。备份、回滚、移动和卸载用来管理安装写下的内容。每一步改动前都会先给预览。",
      cancel_step: "取消这一步",
      chat_title: "对话",
      chat_later: "在本页面直接和助手对话将在后续版本提供。在此之前请照常打开助手，它能找到这里列出的知识库。",
      browse_title: "选择文件夹",
      up: "上一级",
      go: "打开",
      show_hidden: "显示隐藏文件夹",
      cancel: "取消",
      choose_this: "选这个文件夹",
      new_name: "在它里面新建的文件夹名（这一步写入时才建；留空表示就用这个文件夹）",
      chosen: "将回答：{path}",
      browse: "浏览…",
      ok: "确定",
      yes: "是",
      no: "否",
      home: "家目录",
      media: "移动磁盘",
      more: "还有 {n} 项没有列出。",
      missing: "文件夹不存在",
      not_local: "不在本机",
      agent_ok: "OpenCode 已就绪",
      agent_no_model: "OpenCode 未配置模型",
      agent_missing: "未找到 OpenCode",
      skills_none: "技能未安装",
      skills_in: "技能：{names}",
      backups: "共 {n} 次备份",
      no_backups: "还没有备份",
      result_ok: "已完成。",
      result_cancelled: "已取消。",
      result_stopped: "已停止。",
      result_error: "这一步出错了，原因见上面的输出。",
      busy: "还有一个步骤在运行。",
      lost: "与知识库客户端的连接断开了。请重新启动它，再刷新本页面。",
      quit_done: "知识库客户端已停止，可以关闭这个标签页了。",
      quit_confirm: "还有步骤在运行。要取消它并退出吗？",
      no_token: "请从知识库客户端启动时显示的地址打开本页面。"
    }
  };

  var token = new URLSearchParams(location.search).get("t") || "";
  var lang = (navigator.language || "en").toLowerCase().indexOf("zh") === 0 ? "zh" : "en";
  var state = null;
  var job = null;   // {id, action, source, asking}
  var browse = null; // {path, done}

  function $(id) { return document.getElementById(id); }
  function t(key, vars) {
    var s = (T[lang] && T[lang][key]) || T.en[key] || key;
    Object.keys(vars || {}).forEach(function (k) { s = s.split("{" + k + "}").join(vars[k]); });
    return s;
  }
  function el(tag, attrs, text) {
    var e = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) {
      if (k === "class") e.className = attrs[k]; else e.setAttribute(k, attrs[k]);
    });
    if (text !== undefined) e.textContent = text;
    return e;
  }
  function show(e, on) { e.hidden = !on; }

  function api(method, path, body) {
    var opts = { method: method, headers: { "X-Token": token } };
    if (body !== undefined) {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(body);
    }
    return fetch(path, opts).then(function (r) {
      return r.json().then(function (data) {
        if (!r.ok) { var err = new Error(data.error || r.status); err.status = r.status; throw err; }
        return data;
      });
    });
  }

  function translate() {
    document.documentElement.lang = lang === "zh" ? "zh-CN" : "en";
    document.title = t("title");
    Array.prototype.forEach.call(document.querySelectorAll("[data-t]"), function (e) {
      e.textContent = t(e.getAttribute("data-t"));
    });
  }

  // ---------- state ----------

  function refresh() {
    return api("GET", "/api/state").then(function (s) {
      var first = state === null;
      state = s;
      if (first && s.lang !== lang) { lang = s.lang; translate(); }
      render();
      if (first && s.job && !s.job.done) follow(s.job.id, s.job.action);
    }).catch(lost);
  }

  function render() {
    var libs = $("libs");
    libs.textContent = "";
    state.libraries.forEach(function (lib) {
      var li = el("li", { "class": "lib" });
      var head = el("div", { "class": "lib-head" });
      head.appendChild(el("strong", {}, lib.label));
      if (lib.scope) head.appendChild(el("span", { "class": "scope" }, lib.scope));
      li.appendChild(head);
      li.appendChild(el("div", { "class": "where" }, lib.root || t("not_local")));
      if (lib.root && !lib.exists) li.appendChild(el("div", { "class": "warn" }, t("missing")));
      if (lib.movable) {
        var b = el("button", { type: "button", "class": "quiet small" }, t("move_this"));
        b.addEventListener("click", function () { startAction("move", lib.id); });
        li.appendChild(b);
      }
      libs.appendChild(li);
    });
    show($("libs-empty"), state.libraries.length === 0);

    var status = $("status");
    status.textContent = "";
    var a = state.agent;
    var chip = !a.program ? ["bad", t("agent_missing")] : (a.model ? ["good", t("agent_ok")] : ["warn", t("agent_no_model")]);
    status.appendChild(el("span", { "class": "chip " + chip[0], title: a.program || "" }, chip[1]));
    var names = state.skills.map(function (s) { return s.name; });
    status.appendChild(el("span", { "class": "chip " + (names.length ? "good" : "warn"),
      title: state.skills.map(function (s) { return s.folder; }).join("\n") },
      names.length ? t("skills_in", { names: names.join(", ") }) : t("skills_none")));
    $("backups").textContent = state.backups ? t("backups", { n: state.backups }) : t("no_backups");
    setBusy(job !== null);
  }

  function setBusy(on) {
    Array.prototype.forEach.call(document.querySelectorAll("[data-action], .lib button"), function (b) {
      b.disabled = on;
    });
    show($("cancel"), on);
  }

  function lost(err) {
    if (err && err.status === 403 && !token) { result("error", t("no_token")); return; }
    result("error", t("lost"));
  }

  // ---------- steps ----------

  function startAction(action, library) {
    if (job) return;
    var body = { action: action };
    if (library) body.library = library;
    api("POST", "/api/action", body).then(function (r) { follow(r.job, action); })
      .catch(function (e) { result("error", e.status === 409 ? t("busy") : String(e.message)); });
  }

  function follow(id, action) {
    job = { id: id, action: action, asking: null };
    $("step-title").textContent = t(action);
    show($("welcome"), false);
    $("log").textContent = "";
    show($("log"), true);
    show($("result"), false);
    clearAsk();
    setBusy(true);
    var src = new EventSource("/api/events?job=" + encodeURIComponent(id) + "&t=" + encodeURIComponent(token));
    job.source = src;
    src.onmessage = function (m) {
      var ev = JSON.parse(m.data);
      if (ev.type === "out") appendLog(ev.text);
      else if (ev.type === "ask") ask(ev);
      else if (ev.type === "answered") { if (job.asking === ev.of) { job.asking = null; clearAsk(); } }
      else if (ev.type === "end") { src.close(); finish(ev.result); }
    };
    src.onerror = function () {
      if (src.readyState === EventSource.CLOSED && job && job.id === id) { finish("error"); lost(); }
    };
  }

  function appendLog(text) {
    var log = $("log");
    var atEnd = log.scrollTop + log.clientHeight >= log.scrollHeight - 8;
    log.appendChild(document.createTextNode(text));
    if (atEnd) log.scrollTop = log.scrollHeight;
  }

  function finish(res) {
    clearAsk();
    job = null;
    setBusy(false);
    result(res, t("result_" + res));
    refresh();
  }

  function result(kind, text) {
    var r = $("result");
    r.className = "result " + kind;
    r.textContent = text;
    show(r, true);
  }

  function clearAsk() {
    var f = $("ask");
    f.textContent = "";
    f.onsubmit = null;
    show(f, false);
  }

  function answer(value) {
    if (!job || job.asking === null) return;
    var seq = job.asking;
    job.asking = null;
    clearAsk();
    api("POST", "/api/answer", { job: job.id, seq: seq, value: value }).catch(lost);
  }

  function cancelStep() {
    if (!job) return;
    clearAsk();
    api("POST", "/api/answer", { job: job.id, cancel: true }).catch(lost);
  }

  function ask(ev) {
    job.asking = ev.seq;
    var f = $("ask");
    f.textContent = "";
    f.appendChild(el("p", { "class": "prompt" }, ev.prompt));
    var buttons = el("div", { "class": "buttons" });
    var focus = null;
    function button(label, cls, fn) {
      var b = el("button", { type: "button", "class": cls }, label);
      b.addEventListener("click", fn);
      buttons.appendChild(b);
      return b;
    }

    if (ev.kind === "yes") {
      button(t("cancel_step"), "quiet", cancelStep);
      var no = button(t("no"), ev.default ? "" : "primary", function () { answer(false); });
      var yes = button(t("yes"), ev.default ? "primary" : "", function () { answer(true); });
      focus = ev.default ? yes : no;
      f.onsubmit = function (e) { e.preventDefault(); answer(!!ev.default); };
    } else if (ev.kind === "choose") {
      var list = el("div", { "class": "choices" });
      var name = "c" + ev.seq;
      ev.options.forEach(function (o, i) {
        var label = el("label", { "class": "choice" });
        var r = el("input", { type: "radio", name: name, value: o.value });
        if (o.value === ev.default) { r.checked = true; focus = r; }
        r.addEventListener("dblclick", function () { answer(o.value); });
        label.appendChild(r);
        label.appendChild(el("span", {}, o.text));
        list.appendChild(label);
        if (i === 0 && !focus) focus = r;
      });
      f.appendChild(list);
      button(t("cancel_step"), "quiet", cancelStep);
      var pick = function () {
        var c = f.querySelector("input[name=" + name + "]:checked");
        answer(c ? c.value : ev.default);
      };
      button(t("ok"), "primary", pick);
      f.onsubmit = function (e) { e.preventDefault(); pick(); };
    } else {
      var row = el("div", { "class": "entry" });
      var input = el("input", { type: "text", spellcheck: "false", autocomplete: "off" });
      input.value = ev.default || "";
      row.appendChild(input);
      if (ev.kind === "folder") {
        var b = el("button", { type: "button", "class": "quiet" }, t("browse"));
        b.addEventListener("click", function () {
          openBrowser(input.value || (state && state.home) || "", function (p) { input.value = p; input.focus(); });
        });
        row.appendChild(b);
      }
      f.appendChild(row);
      focus = input;
      button(t("cancel_step"), "quiet", cancelStep);
      button(t("ok"), "primary", function () { answer(input.value); });
      f.onsubmit = function (e) { e.preventDefault(); answer(input.value); };
    }
    f.appendChild(buttons);
    show(f, true);
    f.scrollIntoView({ block: "nearest" });
    if (focus) focus.focus();
  }

  // ---------- folder browser ----------

  function openBrowser(start, done) {
    browse = { path: "", done: done, start: start };
    $("newname").value = "";
    show($("browser"), true);
    api("GET", "/api/places").then(function (r) {
      var box = $("places");
      box.textContent = "";
      r.places.forEach(function (p) {
        var b = el("button", { type: "button", "class": "quiet small", title: p.path },
          (p.kind === "home" ? t("home") : t("media")) + "  " + p.path);
        b.addEventListener("click", function () { listFolder(p.path); });
        box.appendChild(b);
      });
    }).catch(lost);
    listFolder(start || (state && state.home) || "/", true);
  }

  function closeBrowser() {
    show($("browser"), false);
    browse = null;
  }

  function listFolder(path, fallback) {
    var q = "/api/fs?path=" + encodeURIComponent(path) + ($("hidden").checked ? "&hidden=1" : "") +
      (fallback ? "&nearest=1" : "");
    api("GET", q).then(function (r) {
      // A suggested folder that does not exist yet keeps its name, so choosing its parent answers it.
      if (fallback && browse.start && r.path !== browse.start && browse.start.indexOf(join(r.path, "")) === 0) {
        $("newname").value = browse.start.slice(join(r.path, "").length);
      }
      browse.path = r.path;
      $("path").value = r.path;
      updateChosen();
      $("up").disabled = !r.parent;
      show($("fs-error"), false);
      var ul = $("entries");
      ul.textContent = "";
      r.entries.forEach(function (e) {
        var li = el("li", { "class": e.dir ? "dir" : "file" }, e.name);
        if (e.dir) {
          li.tabIndex = 0;
          li.addEventListener("click", function () { listFolder(join(r.path, e.name)); });
          li.addEventListener("keydown", function (k) { if (k.key === "Enter") listFolder(join(r.path, e.name)); });
        }
        ul.appendChild(li);
      });
      $("more").textContent = t("more", { n: r.more });
      show($("more"), r.more > 0);
    }).catch(function (e) {
      if (fallback && state && path !== state.home) { listFolder(state.home, true); return; }
      $("fs-error").textContent = String(e.message);
      show($("fs-error"), true);
    });
  }

  function join(a, b) { return a.replace(/\/+$/, "") + "/" + b; }

  function chosenPath() {
    var name = $("newname").value.trim().replace(/^\/+|\/+$/g, "");
    return name ? join(browse.path, name) : browse.path;
  }

  function updateChosen() {
    if (browse && browse.path) $("chosen").textContent = t("chosen", { path: chosenPath() });
  }

  // ---------- start ----------

  translate();
  Array.prototype.forEach.call(document.querySelectorAll("[data-action]"), function (b) {
    b.addEventListener("click", function () { startAction(b.getAttribute("data-action")); });
  });
  $("cancel").addEventListener("click", cancelStep);
  $("up").addEventListener("click", function () {
    if (browse && browse.path) listFolder(browse.path.replace(/\/+[^\/]*$/, "") || "/");
  });
  $("go").addEventListener("click", function () { listFolder($("path").value.trim()); });
  $("path").addEventListener("keydown", function (k) {
    if (k.key === "Enter") { k.preventDefault(); listFolder($("path").value.trim()); }
  });
  $("hidden").addEventListener("change", function () { if (browse) listFolder(browse.path); });
  $("browse-cancel").addEventListener("click", closeBrowser);
  $("newname").addEventListener("input", updateChosen);
  $("browse-ok").addEventListener("click", function () {
    var b = browse;
    if (!b || !b.path) return;
    var p = chosenPath();
    closeBrowser();
    b.done(p);
  });
  document.addEventListener("keydown", function (k) {
    if (k.key === "Escape" && browse) closeBrowser();
  });
  $("quit").addEventListener("click", function () {
    if (job && !window.confirm(t("quit_confirm"))) return;
    api("POST", "/api/quit", {}).then(function () {
      if (job && job.source) job.source.close();
      job = null;
      setBusy(true);
      $("cancel").hidden = true;
      $("quit").disabled = true;
      result("ok", t("quit_done"));
    }).catch(lost);
  });
  if (!token) { result("error", t("no_token")); return; }
  refresh();
  setInterval(function () { if (!job) refresh(); else api("GET", "/api/state").catch(function () {}); }, 20000);
})();
