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
      graph: "Graph",
      close: "Close",
      graph_title: "Graph: {lib}",
      kind_entity: "Entities", kind_summary: "Summary files", kind_topic: "Documents", kind_original: "Originals",
      kind_missing: "No page yet",
      only_new: "Only new or changed",
      graph_obsidian: "Open this folder in Obsidian for a fuller graph and backlinks:",
      copy_path: "Copy path", copied: "Copied",
      graph_truncated: "Too many files: only part of the library is shown.",
      graph_empty: "The library has no files to show yet.",
      graph_new: "New or changed since the client started",
      links_out: "Links to", links_in: "Linked from",
      view_graph: "View in the graph",
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
      chat_failed: "OpenCode stopped ({reason}). Choose Check again in Getting started to start it anew.",
      chat_no_program: "OpenCode was not found on this computer, so the conversation is off. Install OpenCode, or start the client with --opencode <path to opencode>, then choose Check again in Getting started.",
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
      say_resume: "continue intake in the {lib} library",
      say_work: "Work folder: {path}",
      continue_auto: "Batch {n} of {total} done; a new conversation continues the intake in {s} seconds.",
      continue_cancel: "Cancel",
      continue_left: "The intake in {lib} has batches left.",
      continue_go: "Continue intake",
      simple_no_intake: "Not available in simple mode: the assistant cannot ask questions here, so a batch plan cannot be confirmed.",
      stage_count: "Take stock", stage_convert: "Convert", stage_dedup: "Duplicates and names",
      stage_clean: "Clean up", stage_compare: "Compare conclusions", stage_write: "File", stage_final: "Wrap up",
      why_count: "Each file gets a content fingerprint first, so files already in the library or repeated in the material are not read again.",
      why_convert: "Office files and PDFs become plain text the assistant can read; your original files are only read, never changed.",
      why_dedup: "Name equals version: a new version of a document lands on the same name and the old one goes to the archive.",
      why_clean: "Only the formatting is tidied; nothing is shortened, so every sentence can still be traced to its source.",
      why_compare: "A rewrite of the status card is compared item by item by a script; a conclusion changes only with evidence.",
      why_write: "Files are added and old versions archived; nothing is ever deleted.",
      why_final: "After the last batch, the status card, change log and open items are updated once, for everything filed.",
      more_count: "Batches keep each step small enough to check. A run can stop after any batch and go on later with Continue intake.",
      more_convert: "Pictures keep a placeholder; tables stay tables. The converted text is kept in the client's work folder only while the client runs.",
      more_dedup: "Two different documents never share a name; when in doubt the assistant renames rather than overwrites. This removes most \"which version is current?\" questions.",
      more_clean: "The source text is the evidence behind every conclusion in the library, so it is kept whole.",
      more_compare: "Three questions come first: does the new material carry this kind of fact, does the card have an entry for it, and do they disagree. Only three yeses change the card.",
      more_write: "The file index records each source's content fingerprint, so the same file is recognised next time.",
      more_final: "Topics and conclusions recorded during the batches are checked against the current status card once more before it is rewritten; that rewrite waits for your confirmation.",
      progress_line: "{lib}: batch {n}/{total} · filed {written} · duplicates {duplicates} · to review {review}",
      progress_done: "{lib}: all {total} batches done · filed {written} · duplicates {duplicates} · to review {review}",
      batch_card: "Batch {n} ({group}) done: {written} filed, {duplicates} duplicates, {review} to review.",
      run_card: "Intake finished in {lib}: {written} files filed in {total} batches.",
      auto_count: "Allowed without asking: {n}",
      check_title: "Getting started",
      check_hide: "Hide", check_show: "Show",
      check_found: "OpenCode found",
      check_found_no: "Not found. Install OpenCode, or start the client with --opencode <path to opencode>, then choose Check again.",
      check_started: "OpenCode started",
      check_starting: "Starting...",
      check_started_simple: "Only simple mode: its server could not be used. Fix what the conversation panel shows, then choose Check again.",
      check_started_failed: "It stopped. Choose Check again to start it anew.",
      check_no_model: "No model found in its settings. If it does not start or answer, set up the model first.",
      check_skills: "Skills installed where OpenCode reads them",
      check_skills_no: "Choose Set up and install the skills for OpenCode.",
      check_library: "A library is set up",
      check_library_no: "Choose Set up to make one.",
      check_line: "OpenCode's instructions name the libraries",
      check_line_no: "Set up writes this line into OpenCode's AGENTS.md; answer yes when it asks.",
      check_pdf: "PDF text extraction (pdftotext, optional)",
      check_pdf_no: "Not installed: the assistant then reads each PDF whole, which is slower and uses more tokens. Install poppler-utils to add it.",
      recheck: "Check again",
      check_tries: "Ready. Pick an example: it goes into the box below to edit before you send it.",
      try_note: "note this: the team review moved to Thursday",
      try_due: "what is due this month?",
      try_find: "what does the library say about the project plan?"
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
      graph: "关系图",
      close: "关闭",
      graph_title: "关系图：{lib}",
      kind_entity: "实体", kind_summary: "汇总文件", kind_topic: "文档", kind_original: "原件",
      kind_missing: "未建页",
      only_new: "只看本次新增或更新",
      graph_obsidian: "用 Obsidian 打开这个文件夹，可以看到更完整的关系图和反向链接：",
      copy_path: "复制路径", copied: "已复制",
      graph_truncated: "文件太多，只显示了库的一部分。",
      graph_empty: "库里还没有可以显示的文件。",
      graph_new: "客户端启动后新增或更新",
      links_out: "链接到", links_in: "被链接",
      view_graph: "在关系图中查看",
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
      chat_failed: "OpenCode 已停止（{reason}）。在「首次使用清单」里点「重新检测」即可重新启动。",
      chat_no_program: "本机没有找到 OpenCode，对话不可用。请先安装 OpenCode，或启动客户端时用 --opencode <opencode 的路径> 指定，然后在「首次使用清单」里点「重新检测」。",
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
      say_resume: "继续入库（知识库「{lib}」）",
      say_work: "工作文件夹：{path}",
      continue_auto: "第 {n}/{total} 批已完成，{s} 秒后开新对话继续入库。",
      continue_cancel: "取消",
      continue_left: "知识库「{lib}」还有没入库的批次。",
      continue_go: "继续入库",
      simple_no_intake: "简易模式下不能用：助手无法在页面上提问，分批计划没法确认。",
      stage_count: "清点", stage_convert: "转换", stage_dedup: "查重与命名",
      stage_clean: "清理正文", stage_compare: "比对结论", stage_write: "写入", stage_final: "收尾",
      why_count: "先给每个文件算内容指纹，库里已有的和材料里重复的不再读取。",
      why_convert: "把 Office 和 PDF 转成助手能读的纯文本；原始文件只读不改。",
      why_dedup: "名称即版本：同一份文件的新版本落在同一个名字上，旧版移入归档。",
      why_clean: "只整理格式，不删减内容，每句话都能追溯到原文。",
      why_compare: "状态卡的改写由脚本逐条比对，有依据才改结论。",
      why_write: "只新增和归档，从不删除。",
      why_final: "最后一批完成后，一次性更新状态卡、变更日志和待决事项。",
      more_count: "分批让每一步都小到可以检查。任何一批之后都可以停下，以后用「继续入库」接着做。",
      more_convert: "图片留占位，表格仍是表格。转换出的文本只在客户端运行期间保存在它的工作文件夹里。",
      more_dedup: "两份不同的文件绝不共用一个名字；拿不准时宁可改名也不覆盖。这样就基本不会出现「哪个版本是现行的」这种问题。",
      more_clean: "原文是库里每条结论的依据，所以完整保留。",
      more_compare: "先问三个问题：新材料有没有这类事实，状态卡有没有对应条目，两者是否矛盾。三个都是「是」才改状态卡。",
      more_write: "文件索引记下每个来源的内容指纹，下次遇到同一文件能认出来。",
      more_final: "各批记下的主题和结论，改写前会再和当前状态卡核对一遍；这一步要等你确认。",
      progress_line: "{lib}：第 {n}/{total} 批 · 已入库 {written} · 重复 {duplicates} · 待复核 {review}",
      progress_done: "{lib}：{total} 批全部完成 · 已入库 {written} · 重复 {duplicates} · 待复核 {review}",
      batch_card: "第 {n} 批（{group}）完成：入库 {written} 个，重复 {duplicates} 个，待复核 {review} 个。",
      run_card: "知识库「{lib}」入库完成：共 {total} 批，入库 {written} 个文件。",
      auto_count: "已自动允许 {n} 次",
      check_title: "首次使用清单",
      check_hide: "收起", check_show: "展开",
      check_found: "找到 OpenCode",
      check_found_no: "没有找到。请安装 OpenCode，或启动客户端时用 --opencode <opencode 的路径> 指定，然后点「重新检测」。",
      check_started: "OpenCode 已启动",
      check_starting: "正在启动…",
      check_started_simple: "只能用简易模式：它的服务用不了。按对话区显示的原因处理后，点「重新检测」。",
      check_started_failed: "它已停止。点「重新检测」重新启动。",
      check_no_model: "它的配置里没有找到模型。如果启动不了或不回答，请先配好模型。",
      check_skills: "技能已装到 OpenCode 能读到的位置",
      check_skills_no: "选「安装与建库」，把技能装给 OpenCode。",
      check_library: "已建好知识库",
      check_library_no: "选「安装与建库」建一个。",
      check_line: "OpenCode 的指令文件里已写明知识库",
      check_line_no: "「安装与建库」会把这一行写进 OpenCode 的 AGENTS.md，问到时回答「是」。",
      check_pdf: "PDF 文字提取（pdftotext，可选）",
      check_pdf_no: "未安装：助手会整份读取 PDF，更慢也更费 token。安装 poppler-utils 即可补上。",
      recheck: "重新检测",
      check_tries: "已就绪。点一个例子，它会填进下面的输入框，改好再发送。",
      try_note: "记一下：团队评审改到周四",
      try_due: "这个月有什么到期的？",
      try_find: "库里关于项目计划是怎么说的？"
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
      if (lib.root && lib.exists) {
        var g = el("button", { type: "button", "class": "quiet small" }, t("graph"));
        g.addEventListener("click", function () { openGraph(lib.id); });
        li.appendChild(g);
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
    chatEnable();
  }

  // ---------- getting started ----------

  // Each item: [done (true, false, or null for not known yet), title, what to do when not done,
  // button]. Items 1-5 are needed; pdftotext only makes PDFs cheaper.
  function checklist() {
    var a = state.agent;
    var setup = [t("setup"), function () { startAction("setup"); }];
    var recheck = [t("recheck"), recheckAgent];
    var started = chat.phase === "ready" ? true : (chat.phase === "simple" || chat.phase === "failed") ? false : null;
    var startedHow = chat.phase === "simple" ? t("check_started_simple")
      : chat.phase === "failed" ? t("check_started_failed") : (a.program ? t("check_starting") : "");
    return [
      [!!a.program, t("check_found"), t("check_found_no"), recheck],
      [a.program ? started : false, t("check_started"), startedHow, started === false ? recheck : null,
       a.program && !a.model ? t("check_no_model") : ""],
      [!!state.opencode_skills, t("check_skills"), t("check_skills_no"), setup],
      [localLibs().length > 0, t("check_library"), t("check_library_no"), setup],
      [!!state.instructions, t("check_line"), t("check_line_no"), setup],
      [!!state.pdftotext, t("check_pdf"), t("check_pdf_no"), null, "", true]
    ];
  }

  function renderChecklist() {
    if (!state) return;
    var items = checklist();
    var list = $("check-list");
    list.textContent = "";
    items.forEach(function (x) {
      var mark = x[0] === true ? "done" : x[0] === null ? "wait" : (x[5] ? "optional" : "todo");
      var li = el("li", { "class": "check " + mark });
      li.appendChild(el("span", { "class": "check-mark", "aria-hidden": "true" },
        mark === "done" ? "\u2713" : mark === "wait" ? "\u2026" : mark === "optional" ? "\u2013" : "!"));
      var body = el("div", { "class": "check-body" });
      body.appendChild(el("div", { "class": "check-title" }, x[1]));
      if (x[0] !== true && x[2]) body.appendChild(el("div", { "class": "hint" }, x[2]));
      if (x[4]) body.appendChild(el("div", { "class": "warn" }, x[4]));
      li.appendChild(body);
      if (x[0] === false && x[3]) {
        var b = el("button", { type: "button", "class": "quiet small" }, x[3][0]);
        b.disabled = job !== null;
        b.addEventListener("click", x[3][1]);
        li.appendChild(b);
      }
      list.appendChild(li);
    });
    var ready = items.slice(0, 5).every(function (x) { return x[0] === true; });
    $("check-state").textContent = items.slice(0, 5).filter(function (x) { return x[0] === true; }).length + "/5";
    var tries = $("check-tries");
    tries.textContent = "";
    if (ready) {
      tries.appendChild(el("p", { "class": "hint" }, t("check_tries")));
      ["try_note", "try_due", "try_find"].forEach(function (k) {
        var b = el("button", { type: "button", "class": "quiet small" }, t(k));
        b.addEventListener("click", function () { $("input").value = t(k); $("input").focus(); });
        tries.appendChild(b);
      });
    }
    show(tries, ready);
    var folded = checkFolded();
    show($("check-body"), !folded);
    $("check-toggle").textContent = t(folded ? "check_show" : "check_hide");
    $("check-toggle").setAttribute("aria-expanded", folded ? "false" : "true");
  }

  function checkFolded() {
    try { return localStorage.getItem("kb-client-checklist") === "folded"; } catch (e) { return false; }
  }

  function foldChecklist() {
    var folded = !checkFolded();
    try { localStorage.setItem("kb-client-checklist", folded ? "folded" : "open"); } catch (e) { /* kept for this view only */ }
    show($("check-body"), !folded);
    $("check-toggle").textContent = t(folded ? "check_show" : "check_hide");
    $("check-toggle").setAttribute("aria-expanded", folded ? "false" : "true");
  }

  // Looks for OpenCode again and starts it, or starts it anew after it failed or fell back to simple mode.
  function recheckAgent() {
    api("POST", "/api/chat/recheck", {}).then(function () {
      return refresh().then(chatLoad);
    }).catch(function (e) {
      refresh();
      chatInfo(e.status === 409 ? t("chat_no_program") : String(e.message));
    });
  }

  function setBusy(on) {
    Array.prototype.forEach.call(document.querySelectorAll("[data-action], .lib button, #check-list button"), function (b) {
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

  var chat = { source: null, phase: "", ready: false, busy: false, restarting: false, simple: false, msgs: {}, parts: {}, cards: {} };

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
    var noLib = state !== null && !localLibs().length;
    Array.prototype.forEach.call(document.querySelectorAll("[data-task]"), function (b) {
      var batch = b.getAttribute("data-task") === "intake" || b.getAttribute("data-task") === "resume";
      b.disabled = !on || noLib || (chat.simple && batch);
      b.title = noLib ? t("chat_no_library") : (chat.simple && batch ? t("simple_no_intake") : "");
    });
    $("chat-new").disabled = !chat.ready || chat.busy;
    show($("chat-stop"), chat.ready && chat.busy);
    $("chat-state").textContent = !chat.ready ? "" : (chat.busy ? t("chat_busy") : t("chat_ready"));
    renderChecklist();
  }

  function chatAgent(a) {
    if (a.state !== "off") chat.phase = a.state;
    if (a.state === "starting") {
      chat.ready = false;
      if (a.restart) chat.restarting = true;
      chatInfo(t(chat.restarting ? "chat_restarting" : "chat_starting"), a.line || "");
    } else if (a.state === "ready") {
      chat.ready = true;
      chat.simple = false;
      chat.restarting = false;
      chatInfo("");
    } else if (a.state === "simple") {
      chat.simple = true;
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
    else if (ev.type === "part") {
      showPart(ev);
      if (ev.kind === "tool" && ev.script) stageFrom(ev);
      if (ev.kind === "tool" && ev.status === "error") runs.errored = true;
    }
    else if (ev.type === "delta") {
      var p = partEl({ partID: ev.partID, messageID: ev.messageID, role: ev.role, child: ev.child, kind: "text" });
      p.textContent += ev.delta;
      scrollChat();
    } else if (ev.type === "status") {
      chat.busy = ev.status !== "idle";
      chatEnable();
      if (chat.busy) cancelContinue();
      else { stagesIdle(); loadProgress().then(maybeContinue); }
    }
    else if (ev.type === "auto") {
      autoNote((ev.child ? t("child") : "") + t("auto", { what: permName(ev.permission) + " " + permWhat(ev).join(", ") }));
    }
    else if (ev.type === "error") { runs.errored = true; note(ev.text, "error"); }
    else if (ev.type === "permission") permissionCard(ev);
    else if (ev.type === "question") questionCard(ev);
    else if (ev.type === "permission_done" || ev.type === "question_done") dropCard(ev.id);
    else if (ev.type === "reset") clearChat();
  }

  // ---------- graph ----------
  // The links between the library's files, laid out by a small force simulation and drawn as SVG; nothing
  // is loaded from elsewhere. Files changed since the client started get a ring.

  var KINDS = ["entity", "summary", "topic", "original", "missing"];
  var SVGNS = "http://www.w3.org/2000/svg";
  var graph = null;

  function svgEl(name, attrs) {
    var e = document.createElementNS(SVGNS, name);
    Object.keys(attrs || {}).forEach(function (k) { e.setAttribute(k, attrs[k]); });
    return e;
  }

  function layout(nodes, links) {
    var n = nodes.length, byId = {};
    nodes.forEach(function (d, i) {
      var a = i * 2.399963, r = 12 * Math.sqrt(i + 1);  // a sunflower spiral as the start
      d.x = r * Math.cos(a); d.y = r * Math.sin(a); d.vx = 0; d.vy = 0;
      byId[d.id] = d;
    });
    var edges = links.map(function (l) { return [byId[l.source], byId[l.target]]; });
    var rounds = n > 800 ? 60 : n > 300 ? 150 : 300;
    for (var it = 0; it < rounds; it++) {
      var cool = 1 - it / rounds;
      for (var i = 0; i < n; i++) {
        var p = nodes[i];
        for (var j = i + 1; j < n; j++) {
          var q = nodes[j], dx = p.x - q.x, dy = p.y - q.y, d2 = dx * dx + dy * dy + 0.01;
          if (d2 > 90000) continue;
          var f = 900 / d2;
          p.vx += dx * f; p.vy += dy * f; q.vx -= dx * f; q.vy -= dy * f;
        }
      }
      edges.forEach(function (e) {
        var dx = e[1].x - e[0].x, dy = e[1].y - e[0].y, d = Math.sqrt(dx * dx + dy * dy) || 1;
        var f = (d - 60) * 0.02;
        e[0].vx += dx / d * f; e[0].vy += dy / d * f; e[1].vx -= dx / d * f; e[1].vy -= dy / d * f;
      });
      nodes.forEach(function (d) {
        var pull = d.links ? 0.004 : 0.02;  // files without links stay near the rest instead of drifting off
        d.vx -= d.x * pull; d.vy -= d.y * pull;
        var v = Math.sqrt(d.vx * d.vx + d.vy * d.vy), cap = 20 * cool + 1;
        if (v > cap) { d.vx *= cap / v; d.vy *= cap / v; }
        d.x += d.vx; d.y += d.vy; d.vx *= 0.5; d.vy *= 0.5;
      });
    }
    return byId;
  }

  function openGraph(libId, onlyNew) {
    api("GET", "/api/graph?lib=" + encodeURIComponent(libId)).then(function (g) {
      graph = { data: g, byId: null, shown: {}, onlyNew: !!onlyNew, view: { x: 0, y: 0, k: 1 }, selected: "" };
      KINDS.forEach(function (k) { graph.shown[k] = true; });
      $("graph-title").textContent = t("graph_title", { lib: g.label });
      $("graph-root").textContent = g.root;
      $("graph-copy").textContent = t("copy_path");
      var msg = !g.nodes.length ? t("graph_empty") : (g.truncated ? t("graph_truncated") : "");
      $("graph-note").textContent = msg;
      show($("graph-note"), !!msg);
      graph.byId = layout(g.nodes, g.links);
      graphFilters();
      show($("graph"), true);
      fitGraph();
      drawGraph();
    }).catch(function (e) { note(String(e.message || e), "error"); });
  }

  function graphFilters() {
    var box = $("graph-filters");
    box.textContent = "";
    KINDS.forEach(function (k) {
      if (!graph.data.nodes.some(function (d) { return d.kind === k; })) return;
      var c = el("input", { type: "checkbox" });
      c.checked = graph.shown[k];
      c.addEventListener("change", function () { graph.shown[k] = c.checked; drawGraph(); });
      var l = el("label", { "class": "check kind-" + k });
      l.appendChild(c); l.appendChild(el("span", { "class": "dot" })); l.appendChild(document.createTextNode(t("kind_" + k)));
      box.appendChild(l);
    });
    if (graph.data.nodes.some(function (d) { return d.new; })) {
      var c = el("input", { type: "checkbox" });
      c.checked = graph.onlyNew;
      c.addEventListener("change", function () { graph.onlyNew = c.checked; drawGraph(); });
      var l = el("label", { "class": "check" });
      l.appendChild(c); l.appendChild(document.createTextNode(t("only_new")));
      box.appendChild(l);
    }
  }

  function visible(d) {
    if (!graph.shown[d.kind]) return false;
    if (!graph.onlyNew) return true;
    if (d.new) return true;
    return graph.data.links.some(function (l) {  // the neighbours of a new file stay, for context
      return (l.source === d.id && graph.byId[l.target].new) || (l.target === d.id && graph.byId[l.source].new);
    });
  }

  function fitGraph() {
    var svg = $("graph-svg"), w = svg.clientWidth || 800, h = svg.clientHeight || 500;
    var xs = graph.data.nodes.map(function (d) { return d.x; }), ys = graph.data.nodes.map(function (d) { return d.y; });
    if (!xs.length) { graph.view = { x: w / 2, y: h / 2, k: 1 }; return; }
    var minX = Math.min.apply(null, xs), maxX = Math.max.apply(null, xs);
    var minY = Math.min.apply(null, ys), maxY = Math.max.apply(null, ys);
    var k = Math.min(2, 0.9 * Math.min(w / (maxX - minX + 240), h / (maxY - minY + 80)));
    graph.view = { k: k, x: w / 2 - k * (minX + maxX) / 2, y: h / 2 - k * (minY + maxY) / 2 };
  }

  function radius(d) { return 4 + Math.min(10, Math.sqrt(d.links) * 2); }

  function drawGraph() {
    var svg = $("graph-svg");
    svg.textContent = "";
    var v = graph.view, root = svgEl("g", { transform: "translate(" + v.x + "," + v.y + ") scale(" + v.k + ")" });
    svg.appendChild(root);
    var on = {};
    graph.data.nodes.forEach(function (d) { on[d.id] = visible(d); });
    var sel = graph.selected;
    graph.data.links.forEach(function (l) {
      if (!on[l.source] || !on[l.target]) return;
      var a = graph.byId[l.source], b = graph.byId[l.target];
      root.appendChild(svgEl("line", { x1: a.x, y1: a.y, x2: b.x, y2: b.y,
        "class": "edge" + (sel && (l.source === sel || l.target === sel) ? " hot" : "") }));
    });
    graph.data.nodes.forEach(function (d) {
      if (!on[d.id]) return;
      var g = svgEl("g", { "class": "node kind-" + d.kind + (d.new ? " new" : "") + (d.id === sel ? " sel" : ""),
                           transform: "translate(" + d.x + "," + d.y + ")" });
      if (d.new) g.appendChild(svgEl("circle", { r: radius(d) + 4, "class": "ring" }));
      g.appendChild(svgEl("circle", { r: radius(d) }));
      var title = svgEl("title");
      title.textContent = d.id + (d.new ? " (" + t("graph_new") + ")" : "");
      g.appendChild(title);
      if (d.kind !== "topic" || d.links >= 3 || d.id === sel || v.k > 1.4) {
        var label = svgEl("text", { x: radius(d) + 3, y: 4, "font-size": (12 / Math.max(v.k, 0.6)).toFixed(1) });
        label.textContent = d.id.length > 40 ? d.id.slice(0, 40) + "…" : d.id;
        g.appendChild(label);
      }
      g.addEventListener("pointerdown", function (e) { dragNode(e, d); });
      root.appendChild(g);
    });
    graphSide();
  }

  function graphSide() {
    var side = $("graph-side"), d = graph.byId && graph.byId[graph.selected];
    side.textContent = "";
    if (!d) return;
    side.appendChild(el("strong", {}, d.id));
    side.appendChild(el("div", { "class": "hint" }, t("kind_" + d.kind) + (d.path ? " · " + d.path : "")));
    if (d.new) side.appendChild(el("div", { "class": "hint" }, t("graph_new")));
    [["links_out", "source", "target"], ["links_in", "target", "source"]].forEach(function (x) {
      var ids = graph.data.links.filter(function (l) { return l[x[1]] === d.id; }).map(function (l) { return l[x[2]]; });
      if (!ids.length) return;
      side.appendChild(el("p", { "class": "side-head" }, t(x[0]) + " (" + ids.length + ")"));
      var ul = el("ul");
      ids.forEach(function (id) {
        var a = el("li", { "class": "side-link" }, id);
        a.addEventListener("click", function () { graph.selected = id; drawGraph(); });
        ul.appendChild(a);
      });
      side.appendChild(ul);
    });
  }

  // Dragging a node moves it; a click without movement selects it.
  function dragNode(e, d) {
    e.stopPropagation();
    var v = graph.view, sx = e.clientX, sy = e.clientY, ox = d.x, oy = d.y, moved = false;
    function move(m) {
      if (Math.abs(m.clientX - sx) + Math.abs(m.clientY - sy) > 3) moved = true;
      if (!moved) return;
      d.x = ox + (m.clientX - sx) / v.k; d.y = oy + (m.clientY - sy) / v.k;
      drawGraph();
    }
    function up() {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
      if (!moved) { graph.selected = graph.selected === d.id ? "" : d.id; drawGraph(); }
    }
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
  }

  function panGraph(e) {
    var v = graph.view, sx = e.clientX, sy = e.clientY, ox = v.x, oy = v.y;
    function move(m) { v.x = ox + m.clientX - sx; v.y = oy + m.clientY - sy; drawGraph(); }
    function up() { window.removeEventListener("pointermove", move); window.removeEventListener("pointerup", up); }
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
  }

  function zoomGraph(e) {
    e.preventDefault();
    var v = graph.view, r = $("graph-svg").getBoundingClientRect();
    var px = e.clientX - r.left, py = e.clientY - r.top, k = Math.max(0.1, Math.min(6, v.k * (e.deltaY < 0 ? 1.15 : 1 / 1.15)));
    v.x = px - (px - v.x) * k / v.k; v.y = py - (py - v.y) * k / v.k; v.k = k;
    drawGraph();
  }

  function closeGraph() { show($("graph"), false); graph = null; }

  // ---------- continuing a batch intake ----------
  // The skill stops after a finished batch when its conversation grows long. When the last batch script
  // step was "done" and nothing else is pending, a new conversation continues the run after a short
  // countdown; after a stop, an error, or an automatic round that filed no batch, a button does it instead.

  var runs = { lastPlan: "", errored: false, stopped: false, autoFrom: null, timer: null };

  function openRun() {
    var ids = Object.keys(stages.runs || {});
    for (var i = 0; i < ids.length; i++) {
      var p = stages.runs[ids[i]];
      if (p.done + p.skipped < p.batches) return p;
    }
    return null;
  }

  function cancelContinue() {
    clearInterval(runs.timer);
    runs.timer = null;
    var bar = $("continue-bar");
    if (bar) bar.remove();
  }

  function continueRun(p, auto) {
    cancelContinue();
    runs.autoFrom = auto ? { id: p.id, done: p.done } : null;
    runs.lastPlan = ""; runs.errored = false; runs.stopped = false;
    api("POST", "/api/chat/new", {}).then(function () {
      say(withWork(t("say_resume", { lib: p.label })));
    }).catch(function (e) { note(String(e.message), "error"); });
  }

  function continueButton(p) {
    var bar = $("continue-bar");
    if (!bar) { bar = el("div", { "class": "note batch", id: "continue-bar" }); $("messages").appendChild(bar); }
    bar.textContent = t("continue_left", { lib: p.label }) + " ";
    var go = el("button", { type: "button", "class": "quiet small" }, t("continue_go"));
    go.addEventListener("click", function () { continueRun(p, false); });
    bar.appendChild(go);
    scrollChat();
  }

  function maybeContinue() {
    var p = openRun();
    if (!p || chat.busy || chat.simple || !chat.ready || Object.keys(chat.cards).length) return;
    if (!runs.lastPlan && !runs.stopped && !runs.errored) return;  // nothing happened on this page yet
    var spun = runs.autoFrom && runs.autoFrom.id === p.id && runs.autoFrom.done === p.done;
    var auto = runs.lastPlan === "batch_plan done" && !runs.stopped && !runs.errored && !spun;
    cancelContinue();
    if (!auto) { continueButton(p); return; }
    var bar = el("div", { "class": "note batch", id: "continue-bar" });
    var text = el("span");
    var left = 3;
    var draw = function () {
      text.textContent = t("continue_auto", { n: p.done + p.skipped, total: p.batches, s: left }) + " ";
    };
    draw();
    bar.appendChild(text);
    var cancel = el("button", { type: "button", "class": "quiet small" }, t("continue_cancel"));
    cancel.addEventListener("click", function () { cancelContinue(); runs.lastPlan = ""; continueButton(p); });
    bar.appendChild(cancel);
    $("messages").appendChild(bar);
    scrollChat();
    runs.timer = setInterval(function () {
      left -= 1;
      if (left <= 0) continueRun(p, true); else draw();
    }, 1000);
  }

  // ---------- intake stages and progress ----------
  // The stage comes from the skill script a tool step runs (agent.py stage_script), never from the
  // model's wording, so it costs no tokens and cannot drift.

  var STAGES = ["count", "convert", "dedup", "clean", "compare", "write", "final"];
  var SCRIPT_STAGE = {
    "pick_materials": "count", "batch_plan plan": "count", "batch_plan next": "count",
    "convert": "convert", "index_tool check": "dedup", "meta name": "dedup", "meta date": "dedup", "meta entities": "dedup",
    "clean": "clean", "meta terms": "clean", "card_check": "compare", "meta yaml": "write",
    "assemble": "write", "index_tool add": "write", "index_tool update": "write", "index_tool write": "write", "package": "write",
    "batch_plan done": "write", "batch_plan skip": "write", "archive_plan": "write", "batch_plan finish": "final"
  };
  var stages = { current: "", shown: "", hideTimer: null, poll: null, seen: null, runs: {}, announced: {} };

  function drawStages() {
    var list = $("stage-list");
    list.textContent = "";
    var at = STAGES.indexOf(stages.current);
    STAGES.forEach(function (k, i) {
      var li = el("li", { "class": i < at ? "past" : (i === at ? "now" : "") }, t("stage_" + k));
      li.addEventListener("click", function () {
        stages.shown = stages.shown === k ? "" : k;
        drawStages();
      });
      list.appendChild(li);
    });
    var k = stages.shown || stages.current;
    $("stage-why").textContent = k ? t("why_" + k) + (stages.shown ? " " + t("more_" + k) : "") : "";
  }

  function stageFrom(ev) {
    var k = SCRIPT_STAGE[ev.script || ""];
    if (!k) return;
    if (k !== stages.current) { stages.current = k; stages.shown = ""; }
    clearTimeout(stages.hideTimer);
    show($("stages"), true);
    drawStages();
    if (ev.script.indexOf("batch_plan") === 0 && ev.status === "completed") { runs.lastPlan = ev.script; loadProgress(); }
    if (!stages.poll) stages.poll = setInterval(function () { if (chat.busy) loadProgress(); }, 5000);
  }

  // Once the assistant has been idle for two minutes, the stages fold away until the next intake.
  function stagesIdle() {
    clearTimeout(stages.hideTimer);
    if (!stages.current) return;
    stages.hideTimer = setTimeout(function () {
      show($("stages"), false);
      stages.current = ""; stages.shown = "";
      clearInterval(stages.poll); stages.poll = null;
    }, 120000);
  }

  function runCard(p) {
    if (stages.announced[p.id]) return;
    stages.announced[p.id] = true;
    note(t("run_card", { lib: p.label, total: p.batches, written: p.written }), "batch");
    var b = el("button", { type: "button", "class": "quiet small" }, t("view_graph"));
    b.addEventListener("click", function () { openGraph(p.id, true); });
    $("messages").lastChild.appendChild(b);
  }

  // Batch cards for batches finished since the page last looked, the run card when a run is wrapped up
  // (its progress file is then marked done, and moved to the archive soon after), and the progress line
  // of the run still open.
  function loadProgress() {
    return api("GET", "/api/progress").then(function (r) {
      var first = stages.seen === null;
      if (first) stages.seen = {};
      var now = {}, line = "";
      r.progress.forEach(function (p) {
        now[p.id] = p;
        var seen = stages.seen[p.id] || (stages.seen[p.id] = {});
        p.finished.forEach(function (b) {
          if (seen[b.n]) return;
          seen[b.n] = true;
          if (first) return;  // batches finished before the page looked are not announced
          var res = b.result || {};
          note(t("batch_card", { n: b.n, group: b.group + (b.part ? " " + b.part : ""), written: res.written || 0,
                                 duplicates: res.duplicates || 0, review: res.review || 0 }), "batch");
        });
        var open = p.done + p.skipped < p.batches;
        if (!open && p.final_step === "done") {
          if (!first && stages.runs[p.id] && stages.runs[p.id].final_step !== "done") runCard(p);
          return;
        }
        stages.announced[p.id] = false;
        if (!line) line = t(open ? "progress_line" : "progress_done", {
          lib: p.label, n: p.current || Math.min(p.done + p.skipped + 1, p.batches), total: p.batches,
          written: p.written, duplicates: p.duplicates, review: p.review });
      });
      Object.keys(stages.runs).forEach(function (id) {  // wrapped up and archived between two looks
        var was = stages.runs[id];
        if (!now[id] && was.done + was.skipped >= was.batches) runCard(was);
      });
      stages.runs = now;
      $("progress").textContent = line;
      show($("progress"), !!line);
    }).catch(function () {});
  }

  // Answers the client gave itself are counted on one line per stretch of conversation; the details
  // stay one click away.
  function autoNote(text) {
    var box = $("messages").lastChild;
    if (!box || !box.classList || !box.classList.contains("autos")) {
      var list = el("div", { "class": "text" });
      box = fold("", list);
      box.className = "fold note auto autos";
      box.dataset.n = "0";
      $("messages").appendChild(box);
    }
    var n = Number(box.dataset.n) + 1;
    box.dataset.n = String(n);
    box.firstChild.textContent = t("auto_count", { n: n });
    box.lastChild.appendChild(el("div", {}, text));
    scrollChat();
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

  // The client's work folder goes with the skills' tasks, so that their copies and output files land
  // where the client allows writing without a card.
  function withWork(text) {
    return state && state.work ? text + "\n" + t("say_work", { path: state.work }) : text;
  }

  function task(name) {
    if (name === "note") { noteCard(); return; }
    pickLibrary(function (lib) {
      if (name !== "intake") { say(withWork(t("say_" + name, { lib: lib.label }))); return; }
      openBrowser((state && state.home) || "", function (paths) {
        say(withWork(t("say_intake", { lib: lib.label, paths: paths.join("\n") })), paths);
      }, true);
    });
  }

  // ---------- start ----------

  translate();
  loadProgress();  // what is already finished is known, so only new batches get a card
  $("check-toggle").addEventListener("click", foldChecklist);
  $("graph-close").addEventListener("click", closeGraph);
  $("graph-svg").addEventListener("pointerdown", function (e) { if (graph) panGraph(e); });
  $("graph-svg").addEventListener("wheel", function (e) { if (graph) zoomGraph(e); }, { passive: false });
  $("graph-copy").addEventListener("click", function () {
    var text = $("graph-root").textContent;
    var done = function () { $("graph-copy").textContent = t("copied"); };
    if (navigator.clipboard) navigator.clipboard.writeText(text).then(done, function () {});
    else { var r = document.createRange(); r.selectNodeContents($("graph-root")); getSelection().removeAllRanges(); getSelection().addRange(r); }
  });
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
    else if (k.key === "Escape" && graph) closeGraph();
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
  $("chat-stop").addEventListener("click", function () {
    runs.stopped = true;
    api("POST", "/api/chat/stop", {}).catch(function () {});
  });
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
