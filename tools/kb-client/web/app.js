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
      no_token: "Open this page from the address the knowledge base client printed when it started.",
      browse_multi: "Choose material",
      picked: "{n} chosen",
      choose_picked: "Use the chosen items",
      chat_new: "New conversation",
      task_intake: "File material",
      task_note: "Quick note",
      task_notes: "File quick notes",
      task_lint: "Health check",
      task_archive: "Archive old versions",
      task_resume: "Continue intake",
      chat_one_agent: "If OpenCode is also open in a terminal, quit it before filing material, so that only one of them writes to the library.",
      chat_keys: "Enter sends, Shift+Enter starts a new line.",
      chat_stop: "Stop",
      chat_send: "Send",
      chat_starting: "Starting OpenCode...",
      chat_restarting: "Restarting OpenCode so that it uses the skills and the library just set up...",
      chat_ready: "Ready",
      chat_busy: "Working...",
      chat_simple: "Simple mode: OpenCode's server could not be used ({reason}). Each message runs once with opencode run; the assistant cannot ask for permission or ask questions on this page. For full use, open OpenCode in a terminal.",
      chat_failed: "OpenCode stopped ({reason}). Quit the client and start it again.",
      chat_no_program: "OpenCode was not found on this computer, so the conversation is off. Install OpenCode, or start the client with --opencode <path to opencode>, then start it again.",
      chat_terminal: "Open in a terminal",
      terminal_confirm: "Open this conversation in OpenCode in a terminal window? While you continue there, the conversation on this page pauses; when you are back, reload the page or start a new conversation.",
      terminal_opened: "Opened in a terminal ({name}).",
      terminal_no_session: "Send a message first; then the conversation can be opened in a terminal.",
      terminal_none: "No terminal program was found on this computer.",
      queued: "Queued: {text}",
      child: "Subagent: ",
      thinking: "Thinking...",
      interim: "Working notes",
      perm_task: "Send a subagent", agent_explore: "explore (looks things up)",
      chat_no_model: "OpenCode has no model set yet, so the conversation is off. Set up the model first (your administrator's setup tool), then start the client again.",
      chat_no_library: "No library on this computer yet. Choose Set up first.",
      pick_library: "Which library?",
      note_prompt: "What should be noted?",
      ok_cancel: "Cancel",
      auto: "Allowed without asking: {what}",
      perm_title: "The assistant asks for permission",
      perm_read: "Read", perm_edit: "Change files", perm_bash: "Run a command", perm_external_directory: "Use a folder outside the home folder",
      perm_glob: "Search file names", perm_grep: "Search file contents", perm_list: "List a folder", perm_webfetch: "Open a web page",
      perm_other: "Use: {name}",
      allow_once: "Allow this once",
      allow_always: "Always allow",
      always_what: "With Always allow, OpenCode stops asking for:",
      deny: "Deny",
      q_submit: "Answer",
      q_skip: "Skip",
      q_own: "Your own answer",
      tool_running: "running", tool_completed: "done", tool_error: "failed", tool_pending: "waiting",
      say_intake: "file these into the {lib} library:\n{paths}",
      say_note: "note this: {text}",
      say_notes: "file my quick notes in the {lib} library",
      say_lint: "health check the {lib} library",
      say_archive: "archive old versions in the {lib} library",
      say_resume: "continue intake in the {lib} library"
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
      no_token: "请从知识库客户端启动时显示的地址打开本页面。",
      browse_multi: "选择材料",
      picked: "已选 {n} 项",
      choose_picked: "用选中的这些",
      chat_new: "新对话",
      task_intake: "入库",
      task_note: "随手记",
      task_notes: "整理随手记",
      task_lint: "体检",
      task_archive: "归档旧版",
      task_resume: "继续入库",
      chat_one_agent: "如果终端里也开着 OpenCode，入库前请先退出它，免得两边同时写同一个知识库。",
      chat_keys: "回车发送，Shift+回车换行。",
      chat_stop: "停止",
      chat_send: "发送",
      chat_starting: "正在启动 OpenCode…",
      chat_restarting: "正在重新启动 OpenCode，以便使用刚装好的技能和知识库…",
      chat_ready: "已就绪",
      chat_busy: "助手正在处理…",
      chat_simple: "简易模式：OpenCode 的服务用不了（{reason}）。每条消息用 opencode run 单独运行一次，助手不能在本页面请求授权或提问。需要完整功能时，请在终端里打开 OpenCode。",
      chat_failed: "OpenCode 已停止（{reason}）。请退出客户端后重新启动。",
      chat_no_program: "本机没有找到 OpenCode，对话不可用。请先安装 OpenCode，或启动客户端时用 --opencode <opencode 的路径> 指定，再重新启动客户端。",
      chat_terminal: "在终端里打开",
      terminal_confirm: "在终端窗口里用 OpenCode 打开这个对话吗？在终端里继续时，本页面上的这个对话会暂停；回来后请刷新页面或开始新对话。",
      terminal_opened: "已在终端里打开（{name}）。",
      terminal_no_session: "请先发一条消息，之后才能在终端里打开这个对话。",
      terminal_none: "本机没有找到终端程序。",
      queued: "排队中：{text}",
      child: "子助手：",
      thinking: "思考中…",
      interim: "过程说明",
      perm_task: "派一个子助手去", agent_explore: "explore（查找）",
      chat_no_model: "OpenCode 还没有配置模型，对话不可用。请先用管理员提供的配置工具配好模型，再重新启动客户端。",
      chat_no_library: "本机还没有知识库，请先选「安装与建库」。",
      pick_library: "用哪个知识库？",
      note_prompt: "要记下什么？",
      ok_cancel: "取消",
      auto: "已自动允许：{what}",
      perm_title: "助手请求授权",
      perm_read: "读取", perm_edit: "修改文件", perm_bash: "运行命令", perm_external_directory: "使用家目录以外的文件夹",
      perm_glob: "按文件名查找", perm_grep: "搜索文件内容", perm_list: "列出文件夹", perm_webfetch: "打开网页",
      perm_other: "使用：{name}",
      allow_once: "允许这一次",
      allow_always: "总是允许",
      always_what: "选「总是允许」后，以下操作不再询问：",
      deny: "拒绝",
      q_submit: "回答",
      q_skip: "跳过",
      q_own: "自己填写",
      tool_running: "进行中", tool_completed: "完成", tool_error: "失败", tool_pending: "等待中",
      say_intake: "增量整理以下材料，放入知识库「{lib}」：\n{paths}",
      say_note: "记一下：{text}",
      say_notes: "整理随手记（知识库「{lib}」）",
      say_lint: "检查知识库「{lib}」",
      say_archive: "归档旧版（知识库「{lib}」）",
      say_resume: "继续入库（知识库「{lib}」）"
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
    status.appendChild(el("span", { "class": "chip " + chip[0], title: a.program ? a.program + "  (" + a.how + ")" : "" }, chip[1]));
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

  function openBrowser(start, done, multi) {
    browse = { path: "", done: done, start: start, multi: !!multi, picked: {} };
    $("newname").value = "";
    $("browse-title").textContent = t(multi ? "browse_multi" : "browse_title");
    $("browse-ok").textContent = t(multi ? "choose_picked" : "choose_this");
    show($("newname-row"), !multi);
    show($("chosen"), !multi);
    show($("picked"), !!multi);
    updatePicked();
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
        var li = el("li", { "class": e.dir ? "dir" : "file" }, browse.multi ? undefined : e.name);
        if (browse.multi) {
          var full = join(r.path, e.name);
          var box = el("input", { type: "checkbox", "aria-label": e.name });
          box.checked = !!browse.picked[full];
          box.addEventListener("click", function (ev) {
            ev.stopPropagation();
            if (box.checked) browse.picked[full] = true; else delete browse.picked[full];
            updatePicked();
          });
          li.className += " pick";
          li.appendChild(box);
          li.appendChild(el("span", {}, e.name));
        }
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

  function updatePicked() {
    if (browse) $("picked").textContent = t("picked", { n: Object.keys(browse.picked).length });
  }

  function updateChosen() {
    if (browse && browse.path) $("chosen").textContent = t("chosen", { path: chosenPath() });
  }

  // ---------- conversation ----------

  var chat = { source: null, ready: false, busy: false, restarting: false, msgs: {}, parts: {}, cards: {} };

  function chatInfo(text, output) {
    $("chat-info").textContent = text || "";
    show($("chat-info"), !!text);
    $("chat-output").textContent = output || "";
    show($("chat-output"), !!output);
  }

  function chatEnable() {
    var on = chat.ready && !chat.busy;
    $("chat-send").disabled = !chat.ready;  // while the assistant works, a message waits its turn
    $("chat-terminal").disabled = !chat.ready;
    Array.prototype.forEach.call(document.querySelectorAll("[data-task]"), function (b) { b.disabled = !on; });
    $("chat-new").disabled = !chat.ready || chat.busy;
    show($("chat-stop"), chat.ready && chat.busy);
    $("chat-state").textContent = !chat.ready ? "" : (chat.busy ? t("chat_busy") : t("chat_ready"));
  }

  function chatAgent(a) {
    if (a.state === "starting") {
      chat.ready = false;
      if (a.restart) chat.restarting = true;
      chatInfo(t(chat.restarting ? "chat_restarting" : "chat_starting"), a.line || "");
    } else if (a.state === "ready") {
      chat.ready = true;
      chat.restarting = false;
      chatInfo("");
    } else if (a.state === "simple") {
      chat.ready = true;
      chat.restarting = false;
      chatInfo(t("chat_simple", { reason: a.reason || "" }), a.output || "");
    } else if (a.state === "failed") {
      chat.ready = false;
      chat.restarting = false;
      chatInfo(t("chat_failed", { reason: a.reason || "" }), a.output || "");
    }
    chatEnable();
  }

  function scrollChat() {
    var m = $("messages");
    m.scrollTop = m.scrollHeight;
  }

  function bubble(id, role, child) {
    var b = chat.msgs[id];
    if (!b) {
      b = el("div", { "class": "msg " + (role === "user" ? "user" : "assistant") + (child ? " child" : "") });
      if (child) b.appendChild(el("div", { "class": "who" }, t("child")));
      chat.msgs[id] = b;
      $("messages").appendChild(b);
    }
    return b;
  }

  function fold(label, body) {
    var d = el("details", { "class": "fold" });
    d.appendChild(el("summary", {}, label));
    d.appendChild(body);
    return d;
  }

  // The element whose text a part fills in. Reasoning is folded into one line from the start; text that a
  // tool step follows in the same message is folded as working notes once the step appears.
  function partEl(ev) {
    var p = chat.parts[ev.partID];
    if (!p) {
      var b = bubble(ev.messageID, ev.role, ev.child);
      if (ev.kind === "reasoning") {
        p = el("div", { "class": "text" });
        b.appendChild(fold(t("thinking"), p));
      } else {
        p = el("div", { "class": ev.kind === "tool" ? "tool" : "text" });
        if (ev.kind === "tool" && ev.role !== "user") {
          Array.prototype.slice.call(b.children).forEach(function (c) {
            if (c.className !== "text") return;
            var d = fold(t("interim"), el("span"));
            b.insertBefore(d, c);
            d.replaceChild(c, d.lastChild);  // the same element moves, so later text still lands in it
          });
        }
        b.appendChild(p);
      }
      chat.parts[ev.partID] = p;
    }
    return p;
  }

  function showPart(ev) {
    var p = partEl(ev);
    if (ev.kind === "tool") {
      var line = "▸ " + ev.tool + (ev.detail ? ": " + ev.detail : "") +
        (ev.status ? "  (" + t("tool_" + ev.status) + ")" : "");
      p.textContent = line + (ev.error ? "\n" + ev.error : "");
      p.className = "tool" + (ev.status === "error" ? " failed" : "");
    } else {
      p.textContent = ev.text;
      if (ev.role === "user") dropQueued(ev.text);
    }
    scrollChat();
  }

  function dropQueued(text) {
    var q = Array.prototype.filter.call(document.querySelectorAll("#messages .note.queued"), function (n) {
      return n.dataset.text === text;
    })[0];
    if (q) q.remove();
  }

  function note(text, cls) {
    $("messages").appendChild(el("div", { "class": "note " + (cls || "") }, text));
    scrollChat();
  }

  function permName(name) {
    var key = "perm_" + name;
    return (T[lang][key] || T.en[key]) ? t(key) : t("perm_other", { name: name });
  }

  function permWhat(ev) {
    return ev.patterns.map(function (p) {
      var key = "agent_" + p;
      return ev.permission === "task" && (T[lang][key] || T.en[key]) ? t(key) : p;
    });
  }

  function dropCard(id) {
    var c = chat.cards[id];
    if (c) { c.remove(); delete chat.cards[id]; }
  }

  function card(id, title) {
    dropCard(id);
    var c = el("div", { "class": "card" });
    c.appendChild(el("p", { "class": "prompt" }, title));
    chat.cards[id] = c;
    $("cards").appendChild(c);
    return c;
  }

  function buttonRow(c, list) {
    var row = el("div", { "class": "buttons" });
    list.forEach(function (x) {
      var b = el("button", { type: "button", "class": x[1] }, x[0]);
      b.addEventListener("click", x[2]);
      row.appendChild(b);
    });
    c.appendChild(row);
    return row;
  }

  function permissionCard(ev) {
    var c = card(ev.id, (ev.child ? t("child") : "") + t("perm_title") + ": " + permName(ev.permission));
    var pre = el("pre", { "class": "log" });
    pre.textContent = permWhat(ev).join("\n");
    c.appendChild(pre);
    var always = ev.always || [];
    if (always.length) {
      c.appendChild(el("span", { "class": "hint" }, t("always_what")));
      var pa = el("pre", { "class": "log" });
      pa.textContent = always.join("\n");
      c.appendChild(pa);
    }
    function reply(how) {
      dropCard(ev.id);
      api("POST", "/api/chat/permission", { id: ev.id, reply: how }).catch(function (e) { note(String(e.message), "error"); });
    }
    var buttons = [[t("deny"), "", function () { reply("reject"); }]];
    if (always.length) buttons.push([t("allow_always"), "", function () { reply("always"); }]);
    buttons.push([t("allow_once"), "primary", function () { reply("once"); }]);
    buttonRow(c, buttons);
    c.scrollIntoView({ block: "nearest" });
  }

  function questionCard(ev) {
    var c = card(ev.id, ev.questions.map(function (q) { return q.header; }).filter(Boolean).join(" / ") || t("q_submit"));
    var reads = ev.questions.map(function (q, qi) {
      c.appendChild(el("p", {}, q.question));
      var name = "q" + ev.id + "-" + qi;
      var inputs = q.options.map(function (o) {
        var label = el("label", { "class": "choice" });
        var r = el("input", { type: q.multiple ? "checkbox" : "radio", name: name, value: o.label });
        label.appendChild(r);
        label.appendChild(el("span", {}, o.label + (o.description ? " — " + o.description : "")));
        c.appendChild(label);
        return r;
      });
      var own = null;
      if (q.custom) {
        own = el("input", { type: "text", placeholder: t("q_own"), spellcheck: "false" });
        c.appendChild(own);
      }
      return function () {
        var got = inputs.filter(function (r) { return r.checked; }).map(function (r) { return r.value; });
        if (own && own.value.trim()) got.push(own.value.trim());
        return got;
      };
    });
    function reply(answers) {
      dropCard(ev.id);
      api("POST", "/api/chat/question", { id: ev.id, answers: answers }).catch(function (e) { note(String(e.message), "error"); });
    }
    buttonRow(c, [[t("q_skip"), "quiet", function () { reply(null); }],
                  [t("q_submit"), "primary", function () { reply(reads.map(function (r) { return r(); })); }]]);
    c.scrollIntoView({ block: "nearest" });
  }

  function chatEvent(ev) {
    if (ev.type === "agent") {
      chatAgent(ev);
      if (ev.state === "ready") chatLoad();  // a conversation picked up again brings its history
    }
    else if (ev.type === "part") showPart(ev);
    else if (ev.type === "delta") {
      var p = partEl({ partID: ev.partID, messageID: ev.messageID, role: ev.role, child: ev.child, kind: "text" });
      p.textContent += ev.delta;
      scrollChat();
    } else if (ev.type === "status") { chat.busy = ev.status !== "idle"; chatEnable(); }
    else if (ev.type === "auto") {
      note((ev.child ? t("child") : "") + t("auto", { what: permName(ev.permission) + " " + permWhat(ev).join(", ") }), "auto");
    }
    else if (ev.type === "error") note(ev.text, "error");
    else if (ev.type === "permission") permissionCard(ev);
    else if (ev.type === "question") questionCard(ev);
    else if (ev.type === "permission_done" || ev.type === "question_done") dropCard(ev.id);
    else if (ev.type === "reset") clearChat();
  }

  function clearChat() {
    $("messages").textContent = "";
    $("cards").textContent = "";
    chat.msgs = {}; chat.parts = {}; chat.cards = {};
    chat.busy = false;
    chatEnable();
  }

  function chatLoad() {
    return api("GET", "/api/chat/state").then(function (st) {
      clearChat();
      st.history.forEach(showPart);
      chatAgent(st.agent);
      chat.busy = st.agent.status && st.agent.status !== "idle";
      (st.agent.permissions || []).forEach(permissionCard);
      (st.agent.questions || []).forEach(questionCard);
      chatEnable();
      if (chat.source) chat.source.close();
      chat.source = new EventSource("/api/chat/events?after=" + st.seq + "&t=" + encodeURIComponent(token));
      chat.source.onmessage = function (m) { chatEvent(JSON.parse(m.data)); };
    });
  }

  function chatStart() {
    var a = state.agent;
    if (!a.program) { chatInfo(t("chat_no_program")); chatEnable(); return; }
    if (!a.model) { chatInfo(t("chat_no_model")); chatEnable(); return; }
    api("POST", "/api/chat/start", {}).then(chatLoad).catch(function (e) { chatInfo(String(e.message)); });
  }

  function say(text, material) {
    if (!text.trim()) return;
    var body = { text: text };
    if (material && material.length) body.material = material;
    if (chat.busy) {
      var n = el("div", { "class": "note queued" }, t("queued", { text: text.length > 80 ? text.slice(0, 80) + "\u2026" : text }));
      n.dataset.text = text;
      $("messages").appendChild(n);
      scrollChat();
    }
    chat.busy = true;
    chatEnable();
    api("POST", "/api/chat/send", body).catch(function (e) {
      chat.busy = false;
      chatEnable();
      note(String(e.message), "error");
    });
  }

  function localLibs() {
    return ((state && state.libraries) || []).filter(function (l) { return l.root && l.exists; });
  }

  function pickLibrary(then) {
    var libs = localLibs();
    if (!libs.length) { note(t("chat_no_library"), "error"); return; }
    if (libs.length === 1) { then(libs[0]); return; }
    var c = card("pick-library", t("pick_library"));
    libs.forEach(function (l, i) {
      var label = el("label", { "class": "choice" });
      var r = el("input", { type: "radio", name: "pick-library", value: String(i) });
      if (i === 0) r.checked = true;
      label.appendChild(r);
      label.appendChild(el("span", {}, l.label + "  " + l.root));
      c.appendChild(label);
    });
    buttonRow(c, [[t("ok_cancel"), "quiet", function () { dropCard("pick-library"); }],
                  [t("ok"), "primary", function () {
                    var r = c.querySelector("input[name=pick-library]:checked");
                    dropCard("pick-library");
                    then(libs[r ? Number(r.value) : 0]);
                  }]]);
  }

  function noteCard() {
    var c = card("note", t("note_prompt"));
    var box = el("textarea", { rows: "3", spellcheck: "false" });
    c.appendChild(box);
    buttonRow(c, [[t("ok_cancel"), "quiet", function () { dropCard("note"); }],
                  [t("ok"), "primary", function () {
                    var text = box.value.trim();
                    dropCard("note");
                    if (text) say(t("say_note", { text: text }));
                  }]]);
    box.focus();
  }

  function task(name) {
    if (name === "note") { noteCard(); return; }
    pickLibrary(function (lib) {
      if (name !== "intake") { say(t("say_" + name, { lib: lib.label })); return; }
      openBrowser((state && state.home) || "", function (paths) {
        say(t("say_intake", { lib: lib.label, paths: paths.join("\n") }), paths);
      }, true);
    });
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
    if (b.multi) {
      var paths = Object.keys(b.picked);
      if (!paths.length) return;
      closeBrowser();
      b.done(paths);
      return;
    }
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
      if (chat.source) chat.source.close();
      chat.ready = false;
      chatEnable();
      job = null;
      setBusy(true);
      $("cancel").hidden = true;
      $("quit").disabled = true;
      result("ok", t("quit_done"));
    }).catch(lost);
  });
  Array.prototype.forEach.call(document.querySelectorAll("[data-task]"), function (b) {
    b.addEventListener("click", function () { task(b.getAttribute("data-task")); });
  });
  $("composer").addEventListener("submit", function (e) {
    e.preventDefault();
    var text = $("input").value;
    if (!chat.ready || !text.trim()) return;
    $("input").value = "";
    say(text);
  });
  $("input").addEventListener("keydown", function (k) {
    if (k.key === "Enter" && !k.shiftKey && !k.isComposing) {
      k.preventDefault();
      $("composer").dispatchEvent(new Event("submit", { cancelable: true }));
    }
  });
  $("chat-stop").addEventListener("click", function () { api("POST", "/api/chat/stop", {}).catch(function () {}); });
  $("chat-terminal").addEventListener("click", function () {
    if (!window.confirm(t("terminal_confirm"))) return;
    api("POST", "/api/chat/terminal", {}).then(function (r) {
      note(t("terminal_opened", { name: r.terminal }), "auto");
    }).catch(function (e) {
      note(e.status === 409 ? t(String(e.message).indexOf("terminal") >= 0 ? "terminal_none" : "terminal_no_session")
        : String(e.message), "error");
    });
  });
  $("chat-new").addEventListener("click", function () {
    api("POST", "/api/chat/new", {}).catch(function (e) { note(String(e.message), "error"); });
  });
  chatEnable();
  if (!token) { result("error", t("no_token")); return; }
  refresh().then(function () { if (state) chatStart(); });
  setInterval(function () { if (!job) refresh(); else api("GET", "/api/state").catch(function () {}); }, 20000);
})();
