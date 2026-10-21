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
      pending_title: "Waiting for confirmation",
      pending_intro: "Decisions an ingest run needs before it writes. Answering here or in the conversation both work.",
      pending_run: "{lib} \u00b7 run {run} \u00b7 {created}",
      pending_topics: "New topics", pending_topic_add: "add as a new topic", pending_topic_under: "under {topic}",
      pending_entities: "New entities", pending_entity_add: "add as new", pending_entity_alias: "alias of {name}",
      type_project: "project", type_team: "department or team", type_organisation: "organisation",
      type_system: "system or product", type_other: "other",
      pending_versions: "Possible new versions", pending_version: "{new} is a new version of {old}",
      pending_groups: "Documents with the same name", pending_group: "{name}: which one is current?",
      pending_group_separate: "another document", pending_group_hint: "The others are filed as its older versions; tick \u201canother document\u201d to keep one apart under its folder's name.",
      pending_duplicates: "Already in the library, not filed again: {n}",
      pending_all_add: "Add all", pending_all_under: "Put all under\u2026", pending_all_yes: "Tick all", pending_all_no: "Untick all",
      pending_all_accept: "Accept all", pending_all_restore: "Restore all", pending_filter: "Filter",
      pending_version_score: "name {name}, shared paragraphs {overlap}",
      pending_conflicts: "Conclusions the new versions change or drop",
      conflict_changed: "changed", conflict_removed: "removed", conflict_not_carried: "not carried over",
      pending_accept: "accept the change", pending_restore: "restore the old card",
      pending_save: "Save decisions", pending_saved: "Saved; the conversation goes on with the run.",
      pending_saved_quiet: "Saved. Tell the assistant: \"{text}\"",
      pending_review: "Status-card items to review", pending_ask: "Ask",
      say_review: "Check this status-card item against the sources and propose an update: {item}",
      uninstall: "Uninstall",
      move_this: "Move",
      graph: "Graph",
      ingest_btn: "Ingest", ingest_title: "Ingest into {lib}",
      ingest_material: "Material folder:", ingest_choose: "Choose\u2026", ingest_none: "none chosen",
      ingest_rules: "Cards first for", ingest_rules_hint: "Every document is filed and can be searched at once; the ones the rules pick get cards now, the others later (Write cards while idle).",
      ingest_all_folders: "every folder", ingest_top: "(top of the material folder)", ingest_since: "changed on or after",
      ingest_list: "List the documents", ingest_listed: "{total} documents: {important} get cards now, {rest} are filed first and get cards later.",
      ingest_other: "{n} other files (not documents) are left out.", ingest_parallel: "Card runs at once:",
      ingest_start: "Start the ingest", ingest_stop: "Stop", ingest_continue: "Continue", ingest_discard: "Discard",
      ingest_discard_ask: "Give up this ingest run? Its work folder is removed; what was already filed stays in the library.",
      ingest_progress: "{label}: {done}/{total}", ingest_waiting: "Waiting for your decisions under Waiting for confirmation.",
      ingest_show_pending: "Show", ingest_log: "Log:", ingest_missing: "Gave no source ({n}):",
      ingest_step_convert: "Converting the documents", ingest_step_versions: "Looking for duplicates and versions",
      ingest_step_file: "Filing the documents without cards", ingest_step_cards: "Writing cards",
      ingest_step_decide: "Checking topics and conflicts", ingest_step_write: "Writing the cards and topic pages",
      ingest_state_running: "running", ingest_state_stopping: "stopping\u2026", ingest_state_waiting: "waiting for you",
      ingest_state_done: "done", ingest_state_stopped: "stopped", ingest_state_failed: "failed",
      ist_waiting: "waiting", ist_working: "cards\u2026", ist_carded: "cards", ist_filed: "filed", ist_duplicate: "in library",
      ist_older: "older", ist_failed: "no cards", ist_empty: "no text",
      ingest_summary: "Filed without cards for now: {filed}; with cards: {carded}; topic pages rebuilt: {topics}.",
      backfill_title: "Write cards while idle", backfill_hint: "Writes the cards of documents filed without them while no conversation needs the assistant, the rules' documents first, newest first; a message in any window makes it give way.",
      backfill_on: "Switch on", backfill_off: "Switch off", backfill_pause: "Pause", backfill_resume: "Go on",
      backfill_state: "{state}: {left} to do, {written} written, {held} waiting for decisions",
      bfs_off: "Off", bfs_idle: "Waiting for the assistant to be free", bfs_working: "Writing cards", bfs_paused: "Paused", bfs_done: "Done", bfs_waiting: "Waiting",
      backfill_use_rules: "Use the rules above first",
      auto_title: "Automatic ingest", auto_on: "Ingest what is put in the drop folder", auto_drop: "Drop folder:",
      auto_hint: "Documents left there for two minutes are ingested with cards when the assistant is free; decisions still wait for you. Done ones move to {filed}, ones without text to {not_filed}. While it is on, closing the page does not stop the client.",
      auto_waiting: "{n} documents in the drop folder.", auto_last: "Last run {at}: {state}, {files} documents.",
      lock_ingest: "The client's ingest is running",
      health: "Health check", health_title: "Health check: {lib}", health_running: "Checking\u2026",
      health_intro: "Read only: nothing in the library is changed.",
      health_summary: "{sources} sources, {uncarded} of them without cards yet; {problems} problems.",
      health_none: "Nothing to fix.", health_more: "and {n} more",
      health_fix_pages: "Ask in the conversation to rebuild the topic pages of this library.",
      hk_quotes: "Cards whose quote is not in its paragraph", hk_links: "Links to files that do not exist",
      hk_missing: "Topic pages missing", hk_stale: "Topic pages that differ from the cards",
      hk_extra: "Year pages no longer built", hk_unpaired: "Cards files without their source",
      hk_review: "Status-card items marked for review", hk_not_current: "Status-card items citing a source that is not current",
      hk_pending: "Runs waiting for decisions for more than 7 days",
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
      welcome_title: "Welcome",
      ideas_label: "Ideas behind the knowledge base",
      idea_prev: "Previous", idea_next: "Next", idea_more: "More", idea_less: "Less", idea_pause: "Pause", idea_play: "Play",
      skills_title: "Skills",
      skills_intro: "What the assistant can do. Every other skill can be changed (backed up first) and restored; knowledge-base skills are only upgraded, when this client has a newer version.",
      skill_new: "New skill", skill_import: "Import", skills_none_found: "No skills found where OpenCode reads them.",
      skill_kb_group: "Knowledge base", skill_other_group: "Other skills",
      skill_try: "Try it", skill_upgrade: "Upgrade", skill_modify: "Change", skill_restore_btn: "Restore",
      skill_shadowed: "Not used: a skill with this name in {folder} comes first.",
      skill_triggers: "Say: ", skill_version: "version {v}",
      skill_backup: "Back up a skill", skill_restore: "Restore a skill",
      skill_upgrade_hint: "Upgrading replaces the skill's folder with the new release; a change made here stays only in its backup.",
      skill_latest: "Up to date: this client comes with {v}.",
      skill_wait: "{what}; upgrade when it is done.",
      try_req: "{phrase}",
      modify_title: "Change {name}",
      modify_how: "What should change?",
      modify_triggers: "When it is used: the phrases and situations that start it",
      modify_steps: "What it does: add, remove or reorder steps",
      modify_examples: "Examples: add an example of a request and of the answer",
      modify_output: "The answer: its format, length or tone",
      modify_other: "Something else",
      modify_detail: "Describe the change in a sentence or two (what, and why):",
      modify_tips: "A good request names one change, says what should happen instead, and gives a short example. Keep the front matter (name, description) valid. A backup is made first; Restore puts it back.",
      modify_go: "Back up and prepare the request",
      modify_req: "Change the skill {name} (its folder: {folder}). Change: {how}. Details: {detail}\nEdit only the files in that folder, keep the SKILL.md front matter (name, description) valid, and tell me what you changed. A backup was made before this request.",
      new_req: "Fill in the new skill {name} (its folder: {folder}): complete the steps and the output section of its SKILL.md so that it does what its description says, keep the description to one clear sentence with two or three example phrases, and tell me how to use it.",
      welcome_simple: "Set up installs the skills, makes a library and tells your agent about it; choose it again to add another library. Back up keeps a copy of what Set up wrote. Every step shows a preview before it changes anything. To ingest many documents and search them at once, use Ingest under a library; for a few files, say \"ingest: <file or folder path>\" in the conversation.",
      welcome: "Set up installs the skills, makes a library and tells your agent about it; choose it again to add another library. Back up, Roll back, Move and Uninstall manage what Set up wrote. Every step shows a preview before it changes anything. To ingest many documents and search them at once, use Ingest under a library; for a few files, say \"ingest: <file or folder path>\" in the conversation.",
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
      kb_skills_ok: "Knowledge-base skills: {n}/{total} installed", kb_skills_missing: "Knowledge-base skills: {names} missing",
      kb_skills_title: "Knowledge-base skills where OpenCode reads them",
      kb_skills_found: "{name} (version {version}): {folder}", kb_skills_not_found: "{name}: not found",
      kb_skills_checked: "Folders checked, in the order OpenCode reads them:", kb_skills_install: "Install them",
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
      side_fold: "Fold the left column", side_unfold: "Unfold the left column",
      side_label_kb: "Knowledge base", side_label_skills: "Skills",
      win_add: "New window", win_n: "Conversation {n}",
      win_close: "Close this window (the conversation stays in OpenCode)",
      win_close_confirm: "The assistant is still working in this window. Stop it and close the window?",
      win_busy: "working", win_cards: "waiting for you", win_unread: "new reply",
      win_full: "Eight windows are open; close one first.",
      lock_step: "A management step is running",
      lock_note: "{what}: the tasks that write the libraries wait until it is done.", lock_view: "Show",
      ingest_long: "An ingest run takes a long time (hours for many documents). You can leave this page as it is; the result shows in this window. Meanwhile talk or use other skills in another window; writing a library from there asks first.",
      ingest_cli: "How to open OpenCode from a terminal", ingest_cli_hint: "In a terminal, run:", copy: "Copy",
      session_open: "(open)",
      task_note: "Quick note",
      task_note_hint: "Keep one sentence in the library at once",
      log_dir: "Logs:",
      log_hint: "Logs hold file names and paths, not the files' text. When something goes wrong, send the log to whoever maintains the client.",
      chat_one_agent: "If OpenCode is also open in a terminal, quit it before filing material, so that only one of them writes to the library.",
      chat_keys: "Enter sends, Shift+Enter starts a new line.",
      chat_stop: "Stop",
      chat_send: "Send",
      chat_starting: "Starting OpenCode...",
      chat_restarting: "Restarting OpenCode so that it uses the skills and the library just set up...",
      chat_ready: "Ready",
      chat_busy: "Working...",
      chat_simple: "One-shot mode: OpenCode's server could not be used ({reason}). Each message runs once with opencode run; the assistant cannot ask for permission or ask questions on this page. For full use, open OpenCode in a terminal.",
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
      note_prompt: "What should be noted?",
      ok_cancel: "Cancel",
      auto: "Allowed without asking: {what}",
      perm_title: "The assistant asks for permission",
      perm_read: "Read", perm_edit: "Change files", perm_bash: "Run a command", perm_external_directory: "Use a folder outside the home folder",
      perm_glob: "Search file names", perm_grep: "Search file contents", perm_list: "List a folder", perm_webfetch: "Open a web page",
      perm_other: "Use: {name}",
      allow_once: "Allow this once",
      allow_always: "Always allow",
      allow_all: "Allow everything",
      allow_all_on: "Everything allowed · switch off",
      allow_all_card: "Allow everything on this page",
      allow_all_confirm: "Allow everything the assistant asks for from now on? Reading, changing and deleting files and running any command will no longer be asked about, until you switch it off or quit the client. Changes to the knowledge-base skills stay refused.",
      allow_all_note_on: "Everything is allowed without asking until you switch it off or quit the client.",
      allow_all_note_off: "The assistant asks for permission again.",
      always_what: "With Always allow, OpenCode stops asking for:",
      deny: "Deny",
      q_submit: "Answer",
      q_skip: "Skip",
      q_own: "Your own answer",
      tool_running: "running", tool_completed: "done", tool_error: "failed", tool_pending: "waiting",
      say_note: "note this: {text}",
      stage_convert: "Convert", stage_check: "Check quotes", stage_file: "File", stage_pages: "Topic pages",
      why_convert: "Office files and PDFs become batch files of plain text with an anchor on every paragraph; your original files are only read, never changed.",
      why_check: "Every card carries the exact sentence it rests on; a script looks that sentence up in the source before anything is written.",
      why_file: "Sources and cards are written; an older version of a source moves to the archive with its cards, nothing is deleted.",
      why_pages: "The pages of the topics touched are rebuilt from the cards, newest first, each line linked to its source sentence.",
      more_convert: "Pictures keep a placeholder; tables stay tables. The library's settings give the size of a batch.",
      more_check: "A card whose quote is not found is written once more from the source; one that fails twice is dropped and listed in the report.",
      more_file: "A source's name is its version: a new version of a document lands on the same name.",
      more_pages: "A script builds the pages from the cards; the model does not write them.",
      auto_count: "Allowed without asking: {n}",
      check_title: "Getting started",
      check_hide: "Hide", check_show: "Show",
      check_found: "OpenCode found",
      check_found_no: "Not found. Install OpenCode, or start the client with --opencode <path to opencode>, then choose Check again.",
      check_started: "OpenCode started",
      check_starting: "Starting...",
      check_started_simple: "Only one-shot mode: its server could not be used. Fix what the conversation panel shows, then choose Check again.",
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
      try_find: "what does the library say about the project plan?",
      step_hide: "Hide", step_show: "Show output",
      steps: "{n} steps", steps_failed: "{n} failed",
      remembered: "{n} Always allow answers remembered",
      forget: "Clear",
      forget_confirm: "Forget every Always allow answer? The assistant will ask again for those actions, and OpenCode is restarted so that it forgets them too.",
      chat_restarting_forget: "Restarting OpenCode so that it forgets the Always allow answers...",
      title_chat: "OpenCode",
      kb_open: "Knowledge base", kb_close: "Fold the knowledge base",
      skills_panel_intro: "What the assistant can do. Say one of the phrases, or ask in your own words.",
      skills_filter: "Filter skills", skills_no_match: "No skill matches.",
      copy_code: "Copy", copy_answer: "Copy answer", copy_cite: "({name})",
      ingest_details: "Details", ingest_close: "Hide",
      source_around: "{name} \u00a7{n}, with the paragraphs around it", source_missing: "That paragraph is not in a library's index.",
      workdir_label: "Work folder:", workdir_none: "none chosen (your home folder; edits ask first)",
      workdir_change: "Change\u2026", workdir_recent: "Recent folders", workdir_title: "Choose the work folder",
      workdir_hint: "The assistant reads and edits files in this folder without asking; commands and anything outside it still ask.",
      model_default: "Model: as in the settings",
      sessions_btn: "Earlier conversations", sessions_title: "Earlier conversations in this folder",
      sessions_none: "No earlier conversation in this folder.", session_untitled: "(untitled)",
      diff_show: "Show the change", diff_more: "\u2026 {n} more lines; open the file to see them all.",
      chat_restarting_workdir: "Starting OpenCode in the chosen folder...",
      input_hint: "Start with search, look up, tell me about \u2026 to search the knowledge base at once.",
      quick_switch: "Search the knowledge base", quick_switch_hint: "Every message of this window searches the knowledge base first",
      quick_head: "Knowledge base \u00b7 keywords: {k}", quick_searching: "Searching the knowledge base\u2026",
      quick_summarising: "Summarising\u2026",
      quick_note: "A quick summary of the passages below. For an answer whose every quote is checked, use Deep search.",
      quick_passages: "Passages ({n})", quick_none: "Nothing in the knowledge base matches these keywords.",
      quick_deep: "Deep search", quick_assistant: "Give to the assistant",
      quick_deep_text: "Use kb-query to look this up in the knowledge base: {q}",
      quick_status: "Status card", quick_card: "Card", quick_paragraph: "Source", quick_review: "marked for review",
      quick_some: "{h} of {k} keywords", quick_open: "Open",
      quick_bad: "Not among the passages: {n}", quick_failed: "No summary: {why}",
      quick_no_config: "OpenCode's settings were not found",
      quick_no_model: "the settings name no model",
      quick_no_base: "the model's provider has no interface address (baseURL) in the settings",
      quick_no_key: "the model's provider has no API key in the settings",
      quick_http: "the interface answered HTTP {status}", quick_http_401: "the API key is not valid or has expired (HTTP 401)",
      quick_http_403: "the API key may not use this model (HTTP 403)", quick_http_404: "the address or the model name is wrong (HTTP 404)",
      quick_connect: "the interface cannot be reached ({detail})", quick_timeout: "the interface did not answer in time",
      quick_bad_reply: "the interface's reply could not be read", quick_not_ready: "The conversation is not ready yet.",
      quick_lost: "the search stopped ({detail})"
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
      pending_title: "等待确认",
      pending_intro: "入库写入前需要你决定的事项。在这里或在对话里回答都可以。",
      pending_run: "{lib} \u00b7 第 {run} 轮 \u00b7 {created}",
      pending_topics: "新主题", pending_topic_add: "作为新主题加入", pending_topic_under: "并入「{topic}」",
      pending_entities: "新实体", pending_entity_add: "作为新实体加入", pending_entity_alias: "作为「{name}」的别名",
      type_project: "项目", type_team: "部门或团队", type_organisation: "单位",
      type_system: "系统或产品", type_other: "其他",
      pending_versions: "可能的新版本", pending_version: "{new} 是 {old} 的新版本",
      pending_groups: "同名文件", pending_group: "{name}：以哪一份为现行版？",
      pending_group_separate: "不是同一份", pending_group_hint: "其余的作为它的旧版本归档；勾选「不是同一份」的会在名字前加上文件夹名，作为另一份文件保存。",
      pending_duplicates: "库里已有、不再入库：{n} 份",
      pending_all_add: "全部新增", pending_all_under: "全部并入\u2026", pending_all_yes: "全选", pending_all_no: "全不选",
      pending_all_accept: "全部接受", pending_all_restore: "全部恢复", pending_filter: "筛选",
      pending_version_score: "名称相似度 {name}，段落重合 {overlap}",
      pending_conflicts: "新版本改变或去掉的结论",
      conflict_changed: "已改变", conflict_removed: "已删除", conflict_not_carried: "未带过来",
      pending_accept: "接受改动", pending_restore: "恢复旧卡片",
      pending_save: "保存决定", pending_saved: "已保存，对话会接着完成这一轮。",
      pending_saved_quiet: "已保存。请告诉助手：「{text}」",
      pending_review: "待复核的状态卡条目", pending_ask: "问一下",
      say_review: "请对照来源核实这条状态卡条目并提议更新：{item}",
      uninstall: "卸载",
      move_this: "移动",
      graph: "关系图",
      ingest_btn: "入库", ingest_title: "入库到「{lib}」",
      ingest_material: "资料文件夹：", ingest_choose: "选择\u2026", ingest_none: "未选择",
      ingest_rules: "先抽卡的范围", ingest_rules_hint: "所有文档都会先入库，马上能检索；按规则选中的现在抽卡，其余的以后抽（见「空闲时补抽卡片」）。",
      ingest_all_folders: "全部文件夹", ingest_top: "（资料文件夹最上层）", ingest_since: "修改日期不早于",
      ingest_list: "列出清单", ingest_listed: "共 {total} 份文档：{important} 份现在抽卡，{rest} 份先入原文、以后抽卡。",
      ingest_other: "另有 {n} 个非文档文件，不入库。", ingest_parallel: "同时抽卡路数：",
      ingest_start: "开始入库", ingest_stop: "停止", ingest_continue: "继续", ingest_discard: "放弃",
      ingest_discard_ask: "放弃这次入库？它的工作文件夹会被删除，已经入库的内容留在库里。",
      ingest_progress: "{label}：{done}/{total}", ingest_waiting: "有事项等你决定，见「等待确认」。",
      ingest_show_pending: "查看", ingest_log: "日志：", ingest_missing: "没有生成来源（{n} 份）：",
      ingest_step_convert: "正在转换文档", ingest_step_versions: "正在查重和比对版本",
      ingest_step_file: "正在先入原文（暂不抽卡）", ingest_step_cards: "正在抽卡",
      ingest_step_decide: "正在核对主题和冲突", ingest_step_write: "正在写入卡片和主题页",
      ingest_state_running: "进行中", ingest_state_stopping: "正在停止\u2026", ingest_state_waiting: "等你决定",
      ingest_state_done: "完成", ingest_state_stopped: "已停止", ingest_state_failed: "出错",
      ist_waiting: "等待", ist_working: "抽卡中", ist_carded: "已抽卡", ist_filed: "已入原文", ist_duplicate: "库里已有",
      ist_older: "旧版", ist_failed: "无卡片", ist_empty: "无文字",
      ingest_summary: "先入原文（暂未抽卡）{filed} 份，抽卡 {carded} 份，重建主题页 {topics} 个。",
      backfill_title: "空闲时补抽卡片", backfill_hint: "在没有对话需要助手时，为先入原文、还没抽卡的文档补抽卡片：规则选中的优先，新的在前；任何窗口一发消息就先让出。",
      backfill_on: "打开", backfill_off: "关闭", backfill_pause: "暂停", backfill_resume: "继续",
      backfill_state: "{state}：还剩 {left} 份，已写 {written} 份，{held} 份等你决定",
      bfs_off: "未打开", bfs_idle: "等助手空闲", bfs_working: "正在抽卡", bfs_paused: "已暂停", bfs_done: "已全部完成", bfs_waiting: "等待",
      backfill_use_rules: "按上面的规则优先",
      auto_title: "自动入库", auto_on: "放进投放文件夹的文档自动入库", auto_drop: "投放文件夹：",
      auto_hint: "文档放进去两分钟不再变化、助手空闲时，自动入库并抽卡；需要你决定的事项照样等你。处理完的移到 {filed}，读不出文字的移到 {not_filed}。打开期间，关掉页面客户端也不会停止。",
      auto_waiting: "投放文件夹里有 {n} 份文档。", auto_last: "上次 {at}：{state}，{files} 份。",
      lock_ingest: "客户端正在入库",
      health: "体检", health_title: "体检：{lib}", health_running: "正在检查\u2026",
      health_intro: "只读：不改动知识库里的任何文件。",
      health_summary: "共 {sources} 份来源，其中 {uncarded} 份尚未抽卡；发现 {problems} 个问题。",
      health_none: "没有需要处理的问题。", health_more: "另有 {n} 条",
      health_fix_pages: "可以在对话里请助手重建这个知识库的主题页。",
      hk_quotes: "引文不在所链接段落里的卡片", hk_links: "指向不存在文件的链接",
      hk_missing: "缺少的主题页", hk_stale: "与卡片不一致的主题页",
      hk_extra: "已不再生成的年份页", hk_unpaired: "没有对应来源的卡片文件",
      hk_review: "状态卡中待复核的条目", hk_not_current: "状态卡中引用了非现行来源的条目",
      hk_pending: "等待决定超过 7 天的入库",
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
      welcome_title: "欢迎",
      ideas_label: "知识库背后的思路",
      idea_prev: "上一张", idea_next: "下一张", idea_more: "详情", idea_less: "收起", idea_pause: "暂停", idea_play: "播放",
      skills_title: "技能",
      skills_intro: "助手能做的事。其他技能都可以修改（先自动备份）和回滚；知识库技能只在这个客户端带有新版本时升级。",
      skill_new: "新建技能", skill_import: "导入", skills_none_found: "OpenCode 能读到的位置没有找到技能。",
      skill_kb_group: "知识库", skill_other_group: "其他技能",
      skill_try: "试一试", skill_upgrade: "升级", skill_modify: "修改", skill_restore_btn: "回滚",
      skill_shadowed: "未生效：{folder} 里的同名技能优先。",
      skill_triggers: "口令：", skill_version: "版本 {v}",
      skill_backup: "备份技能", skill_restore: "回滚技能",
      skill_upgrade_hint: "升级会用新版本替换整个技能文件夹；在这里做的修改只保留在备份里。",
      skill_latest: "已是最新：这个客户端带的是 {v}。",
      skill_wait: "{what}，等它结束再升级。",
      try_req: "{phrase}",
      modify_title: "修改 {name}",
      modify_how: "要改哪方面？",
      modify_triggers: "什么时候用：触发它的说法和场合",
      modify_steps: "做什么：增加、删除或调整步骤",
      modify_examples: "例子：加一个请求和回答的例子",
      modify_output: "回答：格式、篇幅或语气",
      modify_other: "其他",
      modify_detail: "用一两句话说明要怎么改、为什么：",
      modify_tips: "好的修改请求一次只改一件事，写清改成什么样，并给一个简短的例子；SKILL.md 开头的 name 和 description 要保持完整。修改前会先备份，「回滚」可以恢复。",
      modify_go: "备份并准备请求",
      modify_req: "修改技能 {name}（文件夹：{folder}）。要改的方面：{how}。具体说明：{detail}\n只改这个文件夹里的文件，保持 SKILL.md 开头的 name 和 description 完整有效，改完告诉我改了什么。提出这个请求前已经做了备份。",
      new_req: "补全新技能 {name}（文件夹：{folder}）：把 SKILL.md 的步骤和输出两节写完整，让它做到描述里说的事；描述保持一句清楚的话，带两三个示例口令；最后告诉我怎么用。",
      welcome_simple: "「安装与建库」会装好技能、建一个知识库并告诉助手；要再加一个库时再选一次。「备份」保存一份安装写下的内容。每一步改动前都会先给预览。入库：文档多、想马上能查时，用库下面的「入库」；少量文件可以在对话里说「入库：<文件或文件夹路径>」。",
      welcome: "「安装与建库」会装好技能、建一个知识库并告诉助手；要再加一个库时再选一次。备份、回滚、移动和卸载用来管理安装写下的内容。每一步改动前都会先给预览。入库：文档多、想马上能查时，用库下面的「入库」；少量文件可以在对话里说「入库：<文件或文件夹路径>」。",
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
      kb_skills_ok: "知识库技能：已安装 {n}/{total}", kb_skills_missing: "知识库技能：缺 {names}",
      kb_skills_title: "知识库技能（OpenCode 读得到的位置）",
      kb_skills_found: "{name}（版本 {version}）：{folder}", kb_skills_not_found: "{name}：没有找到",
      kb_skills_checked: "检查过的文件夹（按 OpenCode 的读取顺序）：", kb_skills_install: "去安装",
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
      side_fold: "收拢左栏", side_unfold: "展开左栏",
      side_label_kb: "知识库", side_label_skills: "技能",
      win_add: "新窗口", win_n: "对话 {n}",
      win_close: "关闭这个窗口（对话仍保存在 OpenCode 里）",
      win_close_confirm: "助手还在这个窗口里处理。停止并关闭这个窗口吗？",
      win_busy: "处理中", win_cards: "等你处理", win_unread: "有新回复",
      win_full: "已经开了 8 个窗口，先关掉一个。",
      lock_step: "管理步骤正在运行",
      lock_note: "{what}：写知识库的任务要等它结束。", lock_view: "查看",
      ingest_long: "入库会运行较长时间（文档多时可能要几个小时），可以把页面留在这里不用管，做完会在这个窗口里显示结果。期间可以在其他窗口对话或使用别的技能；那边要写知识库时会先询问。",
      ingest_cli: "如何在终端里打开 OpenCode", ingest_cli_hint: "在终端里运行：", copy: "复制",
      session_open: "（已打开）",
      task_note: "随手记",
      task_note_hint: "记一句话，马上存进知识库",
      log_dir: "日志文件夹：",
      log_hint: "日志里有文件名和路径，没有文件正文。出问题时把日志发给维护者。",
      chat_one_agent: "如果终端里也开着 OpenCode，入库前请先退出它，免得两边同时写同一个知识库。",
      chat_keys: "回车发送，Shift+回车换行。",
      chat_stop: "停止",
      chat_send: "发送",
      chat_starting: "正在启动 OpenCode…",
      chat_restarting: "正在重新启动 OpenCode，以便使用刚装好的技能和知识库…",
      chat_ready: "已就绪",
      chat_busy: "助手正在处理…",
      chat_simple: "单次运行模式：OpenCode 的服务用不了（{reason}）。每条消息用 opencode run 单独运行一次，助手不能在本页面请求授权或提问。需要完整功能时，请在终端里打开 OpenCode。",
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
      note_prompt: "要记下什么？",
      ok_cancel: "取消",
      auto: "已自动允许：{what}",
      perm_title: "助手请求授权",
      perm_read: "读取", perm_edit: "修改文件", perm_bash: "运行命令", perm_external_directory: "使用家目录以外的文件夹",
      perm_glob: "按文件名查找", perm_grep: "搜索文件内容", perm_list: "列出文件夹", perm_webfetch: "打开网页",
      perm_other: "使用：{name}",
      allow_once: "允许这一次",
      allow_always: "总是允许",
      allow_all: "全部允许",
      allow_all_on: "已全部允许 · 关闭",
      allow_all_card: "本页都允许",
      allow_all_confirm: "之后助手的所有请求都自动允许吗？读取、修改、删除文件和运行任何命令都不再询问，直到你关闭或退出客户端。修改知识库技能仍会被拒绝。",
      allow_all_note_on: "已全部允许：之后不再询问，直到你关闭或退出客户端。",
      allow_all_note_off: "已恢复询问授权。",
      always_what: "选「总是允许」后，以下操作不再询问：",
      deny: "拒绝",
      q_submit: "回答",
      q_skip: "跳过",
      q_own: "自己填写",
      tool_running: "进行中", tool_completed: "完成", tool_error: "失败", tool_pending: "等待中",
      say_note: "记一下：{text}",
      stage_convert: "转换", stage_check: "核对引文", stage_file: "写入", stage_pages: "主题页",
      why_convert: "把 Office 和 PDF 转成分批文件，每段带锚点；原始文件只读不改。",
      why_check: "每张卡片都带着它依据的原句；写入前由脚本到原文里逐句核对。",
      why_file: "写入来源和卡片；同一来源的旧版本连同卡片移入归档，从不删除。",
      why_pages: "涉及的主题页由卡片重建，新的在前，每句都链接到原句。",
      more_convert: "图片留占位，表格仍是表格。每批的大小由知识库的设置决定。",
      more_check: "引文找不到的卡片照原文重写一次；两次都不通过的丢弃，并在报告里列出。",
      more_file: "名称即版本：同一份文件的新版本落在同一个名字上。",
      more_pages: "主题页由脚本根据卡片生成，模型不撰写。",
      auto_count: "已自动允许 {n} 次",
      check_title: "首次使用清单",
      check_hide: "收起", check_show: "展开",
      check_found: "找到 OpenCode",
      check_found_no: "没有找到。请安装 OpenCode，或启动客户端时用 --opencode <opencode 的路径> 指定，然后点「重新检测」。",
      check_started: "OpenCode 已启动",
      check_starting: "正在启动…",
      check_started_simple: "只能用单次运行模式：它的服务用不了。按对话区显示的原因处理后，点「重新检测」。",
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
      try_find: "库里关于项目计划是怎么说的？",
      step_hide: "收起", step_show: "展开输出",
      steps: "{n} 个步骤", steps_failed: "其中 {n} 个失败",
      remembered: "已记住 {n} 项「总是允许」",
      forget: "清除",
      forget_confirm: "清除所有「总是允许」吗？之后这些操作助手会再次询问；OpenCode 会重新启动，让它也忘掉这些授权。",
      chat_restarting_forget: "正在重新启动 OpenCode，让它忘掉「总是允许」的授权…",
      title_chat: "OpenCode 工作台",
      kb_open: "知识库", kb_close: "收起知识库",
      skills_panel_intro: "助手能做的事。说出其中的话，或者用自己的话提出要求。",
      skills_filter: "筛选技能", skills_no_match: "没有匹配的技能。",
      copy_code: "复制", copy_answer: "复制回答", copy_cite: "（{name}）",
      ingest_details: "详情", ingest_close: "收起",
      source_around: "{name} \u00a7{n} 及前后段落", source_missing: "知识库索引里没有这一段。",
      workdir_label: "工作文件夹：", workdir_none: "未选择（家目录；改文件前会先问）",
      workdir_change: "更换\u2026", workdir_recent: "最近的文件夹", workdir_title: "选择工作文件夹",
      workdir_hint: "助手在这个文件夹里读、改文件不再询问；运行命令和文件夹以外的操作仍会询问。",
      model_default: "模型：按配置",
      sessions_btn: "历史会话", sessions_title: "这个文件夹里的历史会话",
      sessions_none: "这个文件夹里还没有历史会话。", session_untitled: "（无标题）",
      diff_show: "查看改动", diff_more: "\u2026 另有 {n} 行，打开文件查看全部。",
      chat_restarting_workdir: "正在在所选文件夹里启动 OpenCode…",
      input_hint: "以「搜索」「查找」「介绍」等开头，先在知识库里快速查找并归纳。",
      quick_switch: "知识库搜索", quick_switch_hint: "打开后，这个窗口的每条消息都先在知识库里搜索",
      quick_head: "知识库 · 关键字：{k}", quick_searching: "正在搜索知识库…", quick_summarising: "正在归纳…",
      quick_note: "根据下面的片段快速归纳。需要逐句核对引文时，用「深度搜索」。",
      quick_passages: "依据片段（{n} 条）", quick_none: "知识库里没有与这些关键字匹配的内容。",
      quick_deep: "深度搜索", quick_assistant: "交给助手",
      quick_deep_text: "用 kb-query 在知识库里查：{q}",
      quick_status: "状态卡", quick_card: "卡片", quick_paragraph: "来源", quick_review: "待复核",
      quick_some: "含 {h}/{k} 个关键字", quick_open: "原文",
      quick_bad: "不在片段里的编号：{n}", quick_failed: "没能归纳：{why}",
      quick_no_config: "没有找到 OpenCode 配置",
      quick_no_model: "配置里没有指定模型",
      quick_no_base: "配置里这个模型的服务商没有接口地址（baseURL）",
      quick_no_key: "配置里这个模型的服务商没有 AK",
      quick_http: "接口返回 HTTP {status}", quick_http_401: "AK 无效或已过期（HTTP 401）",
      quick_http_403: "AK 没有该模型的权限（HTTP 403）", quick_http_404: "接口地址或模型名不对（HTTP 404）",
      quick_connect: "连不上接口（{detail}）", quick_timeout: "接口没有及时回复",
      quick_bad_reply: "读不懂接口的回复", quick_not_ready: "对话还没有准备好。",
      quick_lost: "搜索中断了（{detail}）"
    }
  };

  // The ideas the knowledge base is built on, shown in turn in the welcome area and, shorter, while an
  // ingest run goes on: [title, one line, a few more sentences].
  var IDEAS = {
    en: [
      ["LLM wiki", "Reconcile when material arrives, not when a question is asked.",
       "Searching raw documents at question time returns whatever matches best, even an outdated plan. A wiki that an assistant maintains does the reconciling once, at intake, and keeps the result, so answers come from pages that are kept current."],
      ["Evergreen notes", "Pages that are kept up to date instead of piling up.",
       "One page per subject, revised as understanding changes. The archive keeps every earlier state, so the page itself can stay short and current."],
      ["Name equals version", "A new version lands on the old name.",
       "File names carry no date. The next version of a document replaces the previous one under the same name and the old copy moves to the archive, so “which one is current?” stops being a question."],
      ["One status card", "The current answer to every recurring question, in one place.",
       "Each line links to the file it comes from. It changes only when new material actually contradicts it, and the change log keeps how it changed."],
      ["Evidence or no change", "Every judgement quotes its source.",
       "Duplicate, new version, changed fact: each needs a quotation. Without one, the conservative choice wins and the question is listed for you."],
      ["Checked rewrites", "A script compares the old summary with the new one.",
       "Every item that disappears must be explained in the change list, and a summary that shrinks a lot needs your consent. Nothing is lost silently."],
      ["Archive, never delete", "Old versions move aside; nothing is thrown away.",
       "History stays readable, every change can be traced back, and a mistake can always be undone by hand."],
      ["A spec that grows", "Each library keeps its own rules and extends them with care.",
       "Partitions, topics, terms and thresholds live in the library's spec. Material that fits no topic adds one, and every addition is reported for review."],
      ["Library first", "Answers come from the library and name their file.",
       "The assistant searches the library before it answers, cites the basis file for each fact, and says plainly when the library holds no record."]
    ],
    zh: [
      ["LLM Wiki", "在材料进来时理清，而不是在提问时检索。",
       "提问时直接检索原始文档，返回的是最匹配的那份，可能是过时的方案。由助手维护的 wiki 在入库时一次理清并保存结果，回答来自持续更新的页面。"],
      ["常青笔记", "页面持续更新，而不是越堆越多。",
       "一个主题一页，随认识变化而修订；历次旧状态都在归档里，页面本身保持简短、最新。"],
      ["名称即版本", "新版本落在旧名字上。",
       "文件名不带日期。同一份文件的新版本用同一个名字替换旧版，旧版移入归档，「哪份是最新的」就不再是问题。"],
      ["一张状态卡", "所有常问问题的当前答案，集中在一处。",
       "每一条都链接到出处。只有新材料确实与它矛盾时才改，变更日志记下怎么改的。"],
      ["有证据才改", "每个判断都要引原文。",
       "重复、新版本、事实变化，都要有引文；没有引文就取保守结论，并列出来请你确认。"],
      ["改写有核对", "脚本逐条比对新旧汇总文件。",
       "消失的每一条都要在变更清单里说明，篇幅大幅缩水要你同意，不会悄悄丢内容。"],
      ["只归档不删除", "旧版本移到一边，什么都不扔。",
       "历史随时可查，每次变化都能追溯，出了错也总能手工恢复。"],
      ["规范随材料生长", "每个库有自己的规则，谨慎地扩充。",
       "分区、主题、术语和阈值写在库自己的规范里。材料放不进现有主题时新增一个，每次新增都报告给你审阅。"],
      ["先查库再回答", "回答来自知识库，并注明依据文件。",
       "助手回答前先检索知识库，每条事实注明依据文件，查不到就直说知识库里没有记录。"]
    ]
  };

  // A carousel of the ideas in box. mini: title and one line only, for the stage area. It turns every 8
  // seconds, waits while the pointer or the keyboard focus is on it, and never turns by itself when the
  // system asks for reduced motion.
  function carousel(box, mini) {
    var list = IDEAS[lang] || IDEAS.en;
    var still = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    var c = { i: Math.floor(Math.random() * list.length), held: false, paused: still, timer: null, open: false };
    box.textContent = "";
    box.setAttribute("aria-label", t("ideas_label"));
    var slide = el("div", { "class": "idea", "aria-live": "polite" });
    var title = el("p", { "class": "idea-title" });
    var line = el("p", { "class": "idea-line" });
    var more = el("p", { "class": "idea-more" });
    slide.appendChild(title);
    slide.appendChild(line);
    if (!mini) slide.appendChild(more);
    box.appendChild(slide);
    var nav = el("div", { "class": "idea-nav" });
    var prev = el("button", { type: "button", "class": "quiet small", "aria-label": t("idea_prev") }, "‹");
    var next = el("button", { type: "button", "class": "quiet small", "aria-label": t("idea_next") }, "›");
    var dots = el("div", { "class": "idea-dots" });
    var toggle = el("button", { type: "button", "class": "quiet small idea-toggle" });
    var play = el("button", { type: "button", "class": "quiet small" });
    if (!mini) {
      nav.appendChild(prev);
      list.forEach(function (_, k) {
        var d = el("button", { type: "button", "class": "idea-dot", "aria-label": (k + 1) + " / " + list.length });
        d.addEventListener("click", function () { go(k); });
        dots.appendChild(d);
      });
      nav.appendChild(dots);
      nav.appendChild(next);
      nav.appendChild(toggle);
      nav.appendChild(play);
      box.appendChild(nav);
    }
    function draw() {
      var x = list[c.i];
      title.textContent = x[0];
      line.textContent = x[1];
      more.textContent = x[2];
      show(more, c.open);
      toggle.textContent = c.open ? t("idea_less") : t("idea_more");
      play.textContent = c.paused ? t("idea_play") : t("idea_pause");
      Array.prototype.forEach.call(dots.children, function (d, k) { d.classList.toggle("on", k === c.i); });
    }
    function go(k) { c.i = (k + list.length) % list.length; draw(); arm(); }
    function arm() {
      clearTimeout(c.timer);
      if (c.paused || c.held || c.open) return;
      c.timer = setTimeout(function () { if (!box.hidden && box.offsetParent !== null) c.i = (c.i + 1) % list.length; draw(); arm(); }, 8000);
    }
    prev.addEventListener("click", function () { go(c.i - 1); });
    next.addEventListener("click", function () { go(c.i + 1); });
    toggle.addEventListener("click", function () { c.open = !c.open; draw(); arm(); });
    play.addEventListener("click", function () { c.paused = !c.paused; draw(); arm(); });
    box.addEventListener("mouseenter", function () { c.held = true; arm(); });
    box.addEventListener("mouseleave", function () { c.held = false; arm(); });
    box.addEventListener("focusin", function () { c.held = true; arm(); });
    box.addEventListener("focusout", function () { c.held = false; arm(); });
    if (mini) slide.addEventListener("click", function () { go(c.i + 1); });
    draw();
    arm();
  }

  var token = new URLSearchParams(location.search).get("t") || "";
  var lang = (navigator.language || "en").toLowerCase().indexOf("zh") === 0 ? "zh" : "en";
  var state = null;
  var job = null;   // {id, action, source, asking}
  var refused = false;  // a step was refused: the knowledge base stays unfolded to show why
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
        if (!r.ok) { var err = new Error(data.error || r.status); err.status = r.status; err.data = data; throw err; }
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
    $("input").placeholder = t("input_hint");
    $("quick-switch-box").title = t("quick_switch_hint");
  }

  // ---------- state ----------

  function refresh() {
    return api("GET", "/api/state").then(function (s) {
      var first = state === null;
      state = s;
      if (first && s.lang !== lang) { lang = s.lang; translate(); }
      if (first) { carousel($("ideas"), false); carousel($("ideas-mini"), true); }
      render();
      loadPending();
      if (first && s.job && !s.job.done) follow(s.job.id, s.job.action);
    }).catch(lost);
  }

  function render() {
    // A client started with --simple refuses moving, uninstalling, rolling back, changing skills and
    // forgetting permission answers; style.css hides their buttons under body.simple.
    document.body.classList.toggle("simple", !!state.simple);
    applyKb();
    $("welcome").textContent = t(state.simple ? "welcome_simple" : "welcome");
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
      if (lib.movable && !state.simple) {
        var b = el("button", { type: "button", "class": "quiet small" }, t("move_this"));
        b.addEventListener("click", function () { startAction("move", lib.id); });
        li.appendChild(b);
      }
      if (lib.root && lib.exists) {
        var g = el("button", { type: "button", "class": "quiet small" }, t("graph"));
        g.addEventListener("click", function () { openGraph(lib.id); });
        li.appendChild(g);
        var ib = el("button", { type: "button", "class": "quiet small" }, t("ingest_btn"));
        ib.addEventListener("click", function () { openIngest(lib); });
        li.appendChild(ib);
        var h = el("button", { type: "button", "class": "quiet small" }, t("health"));
        h.addEventListener("click", function () { openHealth(lib); });
        li.appendChild(h);
      }
      libs.appendChild(li);
    });
    show($("libs-empty"), state.libraries.length === 0);

    var status = $("status");
    status.textContent = "";
    var a = state.agent;
    var chip = !a.program ? ["bad", t("agent_missing")] : (a.model ? ["good", t("agent_ok")] : ["warn", t("agent_no_model")]);
    status.appendChild(el("span", { "class": "chip " + chip[0], title: a.program ? a.program + "  (" + a.how + ")" : "" }, chip[1]));
    var ks = state.kb_skills || { ok: false, found: [], missing: [], checked: [] };
    var sc = el("button", { type: "button", "class": "chip chip-button " + (ks.ok ? "good" : "bad"), id: "kb-skills-chip",
      "aria-expanded": $("skill-pop").hidden ? "false" : "true", "aria-controls": "skill-pop" },
      ks.ok ? t("kb_skills_ok", { n: ks.found.length, total: ks.found.length })
        : t("kb_skills_missing", { names: ks.missing.join(", ") }));
    sc.addEventListener("click", function () { show($("skill-pop"), $("skill-pop").hidden); drawSkillPop(); });
    status.appendChild(sc);
    drawSkillPop();
    $("backups").textContent = state.backups ? t("backups", { n: state.backups }) : t("no_backups");
    $("remembered-text").textContent = t("remembered", { n: state.remembered || 0 });
    logWhere($("log-dir"), t("log_dir"), state.log_dir);
    show($("remembered"), !!state.remembered);
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
    // With the knowledge base folded: only whether OpenCode can be used
    var kbShown = document.body.classList.contains("kb-open");
    var items = kbShown ? checklist() : checklist().slice(0, 2);
    var need = kbShown ? 5 : 2;
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
    var ready = items.slice(0, need).every(function (x) { return x[0] === true; });
    $("check-state").textContent = items.slice(0, need).filter(function (x) { return x[0] === true; }).length + "/" + need;
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
    show(tries, ready && kbShown);
    // Folded once by itself when Set up (or a recheck) completes what was missing; what the user chooses
    // afterwards stays. OpenCode still starting when the page opens does not count as missing.
    var missing = [0, 2, 3, 4].some(function (i) { return i < items.length && items[i][0] !== true; });
    if (ready && checkMissing) saveFold("folded");
    checkMissing = missing;
    checkReady = ready;
    showFold(checkFolded());
  }

  var checkReady = null;  // whether the needed items were done at the last look
  var checkMissing = false;  // whether something other than OpenCode starting was missing then

  function checkFolded() {
    var v = null;
    try { v = localStorage.getItem("kb-client-checklist"); } catch (e) { v = null; }
    return v === "folded" || (v !== "open" && checkReady === true);
  }

  function saveFold(v) {
    try { localStorage.setItem("kb-client-checklist", v); } catch (e) { /* kept for this view only */ }
  }

  function showFold(folded) {
    show($("check-body"), !folded);
    $("check-toggle").textContent = t(folded ? "check_show" : "check_hide");
    $("check-toggle").setAttribute("aria-expanded", folded ? "false" : "true");
  }

  function foldChecklist() {
    var folded = !checkFolded();
    saveFold(folded ? "folded" : "open");
    showFold(folded);
  }

  // The step panel folds to its title and result line after a step that finished well.
  function foldStep(folded) {
    show($("log"), !folded && $("log").textContent !== "");
    show($("step-toggle"), $("log").textContent !== "");
    $("step-toggle").textContent = t(folded ? "step_show" : "step_hide");
    $("step-toggle").setAttribute("aria-expanded", folded ? "false" : "true");
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
    Array.prototype.forEach.call(document.querySelectorAll("[data-action], .lib button, #check-list button, " +
        ".skills-box button"), function (b) {
      b.disabled = on || b.classList.contains("latest");
    });
    show($("cancel"), on);
    lockUpgrade();
  }

  // Upgrade waits while a management step holds the write lock (the server refuses it then).
  function lockUpgrade() {
    var lock = chat.lock;
    Array.prototype.forEach.call(document.querySelectorAll(".skills-box button.upgrade"), function (b) {
      if (b.classList.contains("latest")) return;  // its title says it is up to date
      if (lock) b.disabled = true;
      else if (!job) b.disabled = false;
      b.title = lock ? t("skill_wait", { what: lockWhat(lock) }) : "";
    });
  }

  function lost(err) {
    if (err && err.status === 403 && !token) { result("error", t("no_token")); return; }
    result("error", t("lost"));
  }

  // ---------- steps ----------

  // arg: the library of a move, or the skill of a skill step. after(log text) runs when the step went
  // through.
  var afterJob = null;

  function startAction(action, arg, after) {
    if (job) return;
    var body = { action: action };
    if (arg) body[action.indexOf("skill_") === 0 ? "skill" : "library"] = arg;
    api("POST", "/api/action", body).then(function (r) { afterJob = after || null; follow(r.job, action); })
      .catch(function (e) {
        result("error", e.status === 409 ? (e.message || t("busy")) : String(e.message));
        refused = true;  // the message is in the step panel, folded away with --chat-first
        applyKb();
        $("result").scrollIntoView({ block: "nearest" });
      });
  }

  function follow(id, action) {
    job = { id: id, action: action, asking: null };
    refused = false;
    $("step-title").textContent = t(action);
    show($("welcome"), false);
    show($("ideas"), false);
    $("log").textContent = "";
    show($("log"), true);
    show($("step-toggle"), false);
    show($("result"), false);
    clearAsk();
    setBusy(true);
    applyKb();
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
    var action = job && job.action;
    job = null;
    setBusy(false);
    result(res, t("result_" + res));
    var after = afterJob;
    afterJob = null;
    if (res === "ok" && after) after($("log").textContent);
    if (action) loadSkills();  // Set up, Uninstall and Roll back change the skills too
    foldStep(res === "ok");
    refresh();
  }

  function fillInput(text) {
    var box = $("input");
    box.value = text;
    box.focus();
    $("chat").scrollIntoView({ block: "nearest" });
  }

  // ---------- waiting for confirmation ----------
  // Ingest runs of local libraries that wait for the owner's decisions (kb-ingest writes
  // _pending/<run>.json; ingest.py pending), shown as forms, and status-card items marked for review.

  var pendingShown = "";

  function loadPending() {
    return api("GET", "/api/pending").then(function (p) {
      var key = JSON.stringify(p);
      if (key === pendingShown) return;  // a form being filled in is not redrawn
      pendingShown = key;
      drawPending(p);
    }).catch(function () {});
  }

  function choiceSelect(options, value) {
    var s = el("select");
    options.forEach(function (o) {
      var opt = el("option", { value: o[0] }, o[1]);
      if (o[0] === value) opt.selected = true;
      s.appendChild(opt);
    });
    return s;
  }

  // A group of decisions; with many rows it gets a filter (by the row's text) and the bulk buttons given:
  // [[label, function (rowControls) {...}]] applied to the rows the filter shows.
  var PENDING_BULK_ROWS = 8;

  function pendingGroup(form, title, n, bulk) {
    var g = el("fieldset", { "class": "pending-group" });
    g.appendChild(el("legend", {}, title + (n > 1 ? " (" + n + ")" : "")));
    form.appendChild(g);
    if (bulk && n > 1) {
      var bar = el("div", { "class": "pending-bulk" });
      var filter = null;
      if (n > PENDING_BULK_ROWS) {
        filter = el("input", { type: "search", placeholder: t("pending_filter"), spellcheck: "false" });
        filter.addEventListener("input", function () {
          var q = filter.value.trim().toLowerCase();
          Array.prototype.forEach.call(g.querySelectorAll(".pending-row, .pending-check"), function (row) {
            show(row, !q || row.textContent.toLowerCase().indexOf(q) >= 0);
          });
        });
        bar.appendChild(filter);
      }
      bulk.forEach(function (b) {
        var c = b[2] || el("button", { type: "button", "class": "quiet small" }, b[0]);
        c.addEventListener(b[2] ? "change" : "click", function () {
          Array.prototype.forEach.call(g.querySelectorAll(".pending-row, .pending-check"), function (row) {
            if (!row.hidden) b[1](row, c);
          });
          if (b[2]) c.value = "";
        });
        bar.appendChild(c);
      });
      g.appendChild(bar);
    }
    return g;
  }

  function setSelect(row, value) {
    var s = row.querySelector("select");
    if (s) { s.value = value; s.dispatchEvent(new Event("change")); }
  }

  function pendingRow(group, label, controls) {
    var row = el("div", { "class": "pending-row" });
    row.appendChild(el("span", { "class": "pending-what" }, label));
    controls.forEach(function (c) { row.appendChild(c); });
    group.appendChild(row);
  }

  function drawPending(p) {
    var box = $("pending-runs");
    box.textContent = "";
    p.runs.forEach(function (r) { box.appendChild(pendingForm(r)); });
    var rev = $("pending-review");
    rev.textContent = "";
    if (p.review.length) {
      rev.appendChild(el("h3", {}, t("pending_review")));
      var ul = el("ul", { "class": "pending-items" });
      p.review.forEach(function (it) {
        var li = el("li", {}, it.label + ": " + it.item + " ");
        var ask = el("button", { type: "button", "class": "quiet small" }, t("pending_ask"));
        ask.addEventListener("click", function () { fillInput(t("say_review", { item: it.item })); });
        li.appendChild(ask);
        ul.appendChild(li);
      });
      rev.appendChild(ul);
    }
    show($("pending"), p.runs.length > 0 || p.review.length > 0);
  }

  function pendingForm(r) {
    var pd = r.pending, reads = [];
    var form = el("form", { "class": "pending-run" });
    form.appendChild(el("h3", {}, t("pending_run", { lib: r.label, run: r.run, created: pd.created || "" })));
    if ((pd.groups || []).length) {
      var gg = pendingGroup(form, t("pending_groups"), pd.groups.length);
      gg.appendChild(el("p", { "class": "hint" }, t("pending_group_hint")));
      pd.groups.forEach(function (grp, k) {
        var box = el("div", { "class": "pending-row pending-grp" });
        box.appendChild(el("span", { "class": "pending-what" }, t("pending_group", { name: grp.name })));
        var picks = [];
        grp.members.forEach(function (m) {
          var line = el("label", { "class": "pending-check" });
          var radio = el("input", { type: "radio", name: "grp-" + r.run + "-" + k, value: m.path });
          radio.checked = m.path === grp.current;
          var sep = el("input", { type: "checkbox" });
          line.appendChild(radio);
          line.appendChild(document.createTextNode(" " + m.path + (m.modified ? " \u00b7 " + m.modified : "") + "  "));
          var sl = el("label", { "class": "quiet" });
          sl.appendChild(sep);
          sl.appendChild(document.createTextNode(" " + t("pending_group_separate")));
          line.appendChild(sl);
          box.appendChild(line);
          picks.push([radio, sep, m.path]);
        });
        gg.appendChild(box);
        reads.push(function (d) {
          var cur = picks.filter(function (x) { return x[0].checked; })[0];
          d.groups[grp.name] = { current: cur ? cur[2] : grp.current,
            separate: picks.filter(function (x) { return x[1].checked && x[0] !== (cur && cur[0]); }).map(function (x) { return x[2]; }) };
        });
      });
    }
    if ((pd.duplicates || []).length) {
      var dups = el("details", { "class": "pending-group" });
      dups.appendChild(el("summary", {}, t("pending_duplicates", { n: pd.duplicates.length })));
      var dl = el("ul", { "class": "pending-items" });
      pd.duplicates.slice(0, 200).forEach(function (x) { dl.appendChild(el("li", {}, x.source + " = " + x.existing)); });
      dups.appendChild(dl);
      form.appendChild(dups);
    }
    if ((pd.new_topics || []).length) {
      var under = choiceSelect([["", t("pending_all_under")]].concat(pd.topics.map(function (x) { return [x, x]; })), "");
      var g = pendingGroup(form, t("pending_topics"), pd.new_topics.length, [
        [t("pending_all_add"), function (row) { setSelect(row, ""); }],
        ["", function (row, c) { if (c.value) setSelect(row, c.value); }, under]]);
      pd.new_topics.forEach(function (name) {
        var s = choiceSelect([["", t("pending_topic_add")]].concat(pd.topics.map(function (x) {
          return [x, t("pending_topic_under", { topic: x })]; })), "");
        pendingRow(g, name, [s]);
        reads.push(function (d) { d.topics[name] = s.value ? { under: s.value } : { add: true }; });
      });
    }
    if ((pd.entities || []).length) {
      var ge = pendingGroup(form, t("pending_entities"), pd.entities.length, [
        [t("pending_all_add"), function (row) { setSelect(row, ""); }]]);
      pd.entities.forEach(function (e) {
        var to = choiceSelect([["", t("pending_entity_add")]].concat(pd.entity_names.map(function (x) {
          return [x, t("pending_entity_alias", { name: x })]; })), "");
        var kind = choiceSelect(["project", "team", "organisation", "system", "other"].map(function (k) {
          return [k, t("type_" + k)]; }), e.type || "other");
        to.addEventListener("change", function () { kind.disabled = !!to.value; });
        pendingRow(ge, e.name, [to, kind]);
        reads.push(function (d) { d.entities[e.name] = to.value ? { alias: to.value } : { add: true, type: kind.value }; });
      });
    }
    if ((pd.versions || []).length) {
      var gv = pendingGroup(form, t("pending_versions"), pd.versions.length, [
        [t("pending_all_yes"), function (row) { var c = row.querySelector("input"); if (c) c.checked = true; }],
        [t("pending_all_no"), function (row) { var c = row.querySelector("input"); if (c) c.checked = false; }]]);
      pd.versions.forEach(function (v) {
        var cb = el("input", { type: "checkbox" });
        var label = el("label", { "class": "pending-check" });
        label.appendChild(cb);
        label.appendChild(document.createTextNode(" " + t("pending_version", { "new": v["new"], old: v.old }) + " (" +
          t("pending_version_score", { name: v.name_score, overlap: v.overlap === null ? "?" : v.overlap }) + ")"));
        gv.appendChild(label);
        reads.push(function (d) { if (cb.checked) d.versions.push(v["new"] + "=" + v.old); });
      });
    }
    if ((pd.conflicts || []).length) {
      var gc = pendingGroup(form, t("pending_conflicts"), pd.conflicts.length, [
        [t("pending_all_accept"), function (row) { setSelect(row, "accept"); }],
        [t("pending_all_restore"), function (row) { setSelect(row, "restore"); }]]);
      pd.conflicts.forEach(function (c) {
        var s = choiceSelect([["accept", t("pending_accept")], ["restore", t("pending_restore")]], "accept");
        var what = c.id + " \u00b7 " + t("conflict_" + c.kind) + " \u00b7 " + c.old.conclusion +
          (c["new"] ? " \u2192 " + c["new"].conclusion : "");
        pendingRow(gc, what, [s]);
        reads.push(function (d) { d.conflicts[c.id] = s.value; });
      });
    }
    var msg = el("p", { "class": "hint" });
    var save = el("button", { type: "submit", "class": "primary small" }, t("pending_save"));
    form.appendChild(save);
    form.appendChild(msg);
    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      var d = { topics: {}, entities: {}, versions: [], conflicts: {}, groups: {} };
      reads.forEach(function (f) { f(d); });
      save.disabled = true;
      api("POST", "/api/pending", { library: r.library, run: r.run, decisions: d }).then(function (res) {
        msg.textContent = res.said ? t("pending_saved") : t("pending_saved_quiet", { text: res.text });
        pendingShown = "";
        setTimeout(loadPending, 3000);
      }).catch(function (e) {
        save.disabled = false;
        msg.textContent = (e.data && e.data.problems ? e.data.problems.join("; ") : String(e.message));
      });
    });
    return form;
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

  var chat = { quick: {}, source: null, phase: "", ready: false, busy: false, restarting: false, simple: false, allowAll: false, msgs: {}, parts: {}, cards: {},
               model: "", workdir: "", recent: [], models: [],
               win: "", windows: [], lock: null, unread: {} };  // the window shown, all windows, the write lock

  var MAX_WINDOWS = 8;  // as agent.MAX_WINDOWS

  function shown() {
    return chat.windows.filter(function (w) { return w.id === chat.win; })[0] || { id: chat.win, status: "idle", cards: 0 };
  }

  function winLabel(w, i) {
    return w.title || t("win_n", { n: i + 1 });
  }

  // What holds the write lock (a management step), as a short phrase; "" when nothing does.
  function lockWhat(lock) {
    return !lock ? "" : t(lock.holder === "ingest" ? "lock_ingest" : "lock_step");
  }

  function drawTabs() {
    var box = $("win-tabs");
    box.textContent = "";
    var n = 0;
    chat.windows.forEach(function (w) {
      var i = n++;
      var tab = el("div", { "class": "win-tab", role: "tab" });
      tab.classList.toggle("active", w.id === chat.win);
      tab.setAttribute("aria-selected", w.id === chat.win ? "true" : "false");
      var busy = w.status && w.status !== "idle";
      tab.classList.toggle("busy", !!busy);
      tab.classList.toggle("cards", w.cards > 0);
      tab.classList.toggle("unread", !!chat.unread[w.id] && w.id !== chat.win);
      var name = el("button", { type: "button", "class": "win-name" }, winLabel(w, i));
      var marks = [busy ? t("win_busy") : "", w.cards > 0 ? t("win_cards") : "", chat.unread[w.id] ? t("win_unread") : ""].filter(Boolean);
      name.title = marks.join(" \u00b7 ");
      name.addEventListener("click", function () { showWindow(w.id); });
      tab.appendChild(name);
      var x = el("button", { type: "button", "class": "win-close", "aria-label": t("win_close"), title: t("win_close") }, "\u00d7");
      x.addEventListener("click", function () { closeWindow(w); });
      tab.appendChild(x);
      box.appendChild(tab);
    });
    var add = el("button", { type: "button", "class": "quiet small", id: "win-add", title: t("win_add") }, "+");
    add.disabled = !chat.ready || chat.simple || chat.windows.length >= MAX_WINDOWS;
    if (add.disabled && chat.ready && !chat.simple) add.title = t("win_full");
    add.addEventListener("click", function () {
      api("POST", "/api/chat/open", {}).then(function (r) { chatLoad(r.win); })
        .catch(function (e) { note(String(e.message), "error"); });
    });
    box.appendChild(add);
    show(box, chat.ready && !chat.simple);
  }

  function showWindow(win) {
    if (win === chat.win) return;
    api("POST", "/api/chat/focus", { win: win }).catch(function () {});
    chatLoad(win);
  }

  function closeWindow(w) {
    var busy = (w.status && w.status !== "idle") || w.cards > 0;
    if (busy && !window.confirm(t("win_close_confirm"))) return;
    api("POST", "/api/chat/close", { win: w.id, stop: busy }).then(function (r) {
      delete chat.unread[w.id];
      if (w.id === chat.win) chatLoad(r.current);
    }).catch(function (e) { note(String(e.message), "error"); });
  }

  function chatInfo(text, output) {
    $("chat-info").textContent = text || "";
    show($("chat-info"), !!text);
    $("chat-output").textContent = output || "";
    show($("chat-output"), !!output);
  }

  function chatEnable() {
    var lock = chat.lock;
    $("chat-terminal").disabled = !chat.ready;
    $("chat-allow-all").disabled = !chat.ready || chat.simple;
    $("chat-allow-all").setAttribute("data-t", chat.allowAll ? "allow_all_on" : "allow_all");
    $("chat-allow-all").textContent = t(chat.allowAll ? "allow_all_on" : "allow_all");
    $("chat-allow-all").classList.toggle("on", chat.allowAll);
    var noLib = state !== null && !localLibs().length;
    var anyBusy = chat.windows.some(function (x) { return (x.status && x.status !== "idle") || x.cards > 0; });
    // while the assistant works, a message waits its turn
    $("chat-send").disabled = !chat.ready;
    Array.prototype.forEach.call(document.querySelectorAll("[data-task]"), function (b) {
      b.disabled = !chat.ready || noLib || chat.busy;
      b.title = noLib ? t("chat_no_library") : "";
    });
    show($("lock-note"), !!lock && chat.ready);
    show($("lock-view"), !!lock);
    $("lock-text").textContent = lock ? t("lock_note", { what: lockWhat(lock) }) : "";
    $("chat-new").disabled = !chat.ready || chat.busy;
    ["workdir-change", "workdir-recent"].forEach(function (id) { $(id).disabled = !chat.ready || anyBusy || !!lock; });
    $("sessions").disabled = !chat.ready || chat.simple;
    drawTabs();
    show($("chat-stop"), chat.ready && chat.busy);
    $("chat-state").textContent = !chat.ready ? "" : (chat.busy ? t("chat_busy") : t("chat_ready"));
    renderChecklist();
  }

  function chatAgent(a) {
    if (a.state !== "off") chat.phase = a.state;
    if (a.state === "starting") {
      chat.ready = false;
      if (a.restart) chat.restarting = a.restart === "forget" || a.restart === "workdir" ? a.restart : true;
      chatInfo(t(chat.restarting === "forget" || chat.restarting === "workdir" ? "chat_restarting_" + chat.restarting
        : chat.restarting ? "chat_restarting"
        : "chat_starting"), a.line || "");
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
      if (role !== "user") {
        // The answer's own text (not the folded notes or the tool steps) is copied as plain text.
        var foot = el("div", { "class": "msg-foot" });
        foot.hidden = true;
        var copy = el("button", { type: "button", "class": "quiet small" }, t("copy_answer"));
        copy.addEventListener("click", function () {
          var raw = Array.prototype.slice.call(b.children).filter(function (c) { return c.className === "text"; })
            .map(function (c) { return c.dataset.raw || ""; }).join("\n\n");
          if (raw.trim()) copyText(plainText(raw), copy);
        });
        foot.appendChild(copy);
        b.appendChild(foot);
        b.foot = foot;
      }
      chat.msgs[id] = b;
      $("messages").appendChild(b);
    }
    return b;
  }

  // Parts go before the copy row, which stays last; the row shows once the answer has text of its own.
  function putPart(b, node) {
    b.insertBefore(node, b.foot || null);
  }

  function footNow(b) {
    if (b.foot) b.foot.hidden = !Array.prototype.some.call(b.children, function (c) { return c.className === "text"; });
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
        putPart(b, fold(t("thinking"), p));
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
        putPart(b, p);
      }
      footNow(b);
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
      p.dataset.tool = ev.tool || "";
      if (ev.diff) p.appendChild(diffFold(ev.diff));
    } else {
      setText(p, ev.text, ev.role);
      if (ev.role === "user") dropQueued(ev.text);
    }
    scrollChat();
  }

  // ---------- Markdown in the assistant's answers ----------
  // A small subset, built as DOM nodes (never as HTML, so that nothing in an answer runs): headings,
  // lists, quotes, tables, rules, fenced code with colours, inline code, bold, italic and web links.
  // The user's own messages stay plain text.

  function setText(p, text, role) {
    p.dataset.raw = text || "";
    if (role === "user") { p.textContent = text; return; }
    p.dataset.md = "1";
    p.textContent = "";
    p.appendChild(markdown(text || ""));
  }

  // While an answer streams in, it is drawn again at most once per frame.
  function addText(p, delta, role) {
    p.dataset.raw = (p.dataset.raw || "") + delta;
    if (role === "user") { p.textContent = p.dataset.raw; return; }
    if (p.dataset.drawing) return;
    p.dataset.drawing = "1";
    requestAnimationFrame(function () {
      delete p.dataset.drawing;
      setText(p, p.dataset.raw, role);
      scrollChat();
    });
  }

  var MD_FENCE = /^ {0,3}(`{3,}|~{3,})\s*([\w+#.-]*)/;
  var MD_HEAD = /^ {0,3}(#{1,6})\s+(.*?)(?:\s+#+)?\s*$/;
  var MD_RULE = /^ {0,3}([-*_])(?:\s*\1){2,}\s*$/;
  var MD_QUOTE = /^ {0,3}>\s?/;
  var MD_ITEM = /^(\s*)([-*+]|\d{1,9}[.)])\s+(.*)$/;
  var MD_TABLE_SEP = /^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$/;

  function indentOf(line) { return /^\s*/.exec(line)[0].replace(/\t/g, "    ").length; }

  function markdown(text) {
    var frag = document.createDocumentFragment();
    mdBlocks(text.replace(/\r\n?/g, "\n").split("\n"), frag);
    return frag;
  }

  function mdBlocks(lines, into) {
    var i = 0, para = [];
    function flush() {
      if (!para.length) return;
      var p = el("p", { "class": "md-p" });
      para.forEach(function (l, k) {
        if (k) p.appendChild(el("br"));
        mdInline(l.trim(), p);
      });
      into.appendChild(p);
      para = [];
    }
    while (i < lines.length) {
      var line = lines[i], m;
      if (!line.trim()) { flush(); i++; continue; }
      if ((m = MD_FENCE.exec(line))) {
        flush();
        var mark = m[1], body = [];
        i++;
        while (i < lines.length && !(lines[i].trim().indexOf(mark) === 0 &&
               lines[i].trim().split(mark.charAt(0)).join("") === "")) body.push(lines[i++]);
        i++;  // the closing fence; an answer still streaming may not have it yet
        into.appendChild(codeBlock(body.join("\n"), m[2]));
        continue;
      }
      if ((m = MD_HEAD.exec(line))) {
        flush();
        var h = el("p", { "class": "md-h md-h" + m[1].length });
        mdInline(m[2], h);
        into.appendChild(h);
        i++;
        continue;
      }
      if (MD_RULE.test(line)) { flush(); into.appendChild(el("hr", { "class": "md-rule" })); i++; continue; }
      if (MD_QUOTE.test(line)) {
        flush();
        var q = [];
        while (i < lines.length && MD_QUOTE.test(lines[i])) q.push(lines[i++].replace(MD_QUOTE, ""));
        var bq = el("blockquote", { "class": "md-quote" });
        mdBlocks(q, bq);
        into.appendChild(bq);
        continue;
      }
      if (line.indexOf("|") >= 0 && i + 1 < lines.length && MD_TABLE_SEP.test(lines[i + 1]) &&
          lines[i + 1].indexOf("|") >= 0) {
        flush();
        var rows = [line];
        i += 2;
        while (i < lines.length && lines[i].indexOf("|") >= 0 && lines[i].trim()) rows.push(lines[i++]);
        into.appendChild(table(rows));
        continue;
      }
      if ((m = MD_ITEM.exec(line))) {
        flush();
        i = list(lines, i, into);
        continue;
      }
      para.push(line);
      i++;
    }
    flush();
  }

  // A list from line i: its items at the first item's indent, each with the more indented lines under it
  // (nested lists, continued text). Returns the line after the list.
  function list(lines, i, into) {
    var first = MD_ITEM.exec(lines[i]);
    var base = indentOf(first[1]);
    var ordered = /\d/.test(first[2]);
    var ol = el(ordered ? "ol" : "ul", { "class": "md-list" });
    if (ordered && parseInt(first[2], 10) !== 1) ol.setAttribute("start", String(parseInt(first[2], 10)));
    var item = null;
    while (i < lines.length) {
      var line = lines[i], m = MD_ITEM.exec(line);
      if (m && indentOf(m[1]) <= base + 1) {
        if (/\d/.test(m[2]) !== ordered) break;
        if (item) ol.appendChild(listItem(item));
        item = [m[3]];
        i++;
      } else if (line.trim() && indentOf(line) > base) {
        item.push(line.slice(Math.min(indentOf(line), base + 2)));
        i++;
      } else if (!line.trim() && i + 1 < lines.length && lines[i + 1].trim() &&
                 (indentOf(lines[i + 1]) > base || MD_ITEM.test(lines[i + 1]) &&
                  indentOf(MD_ITEM.exec(lines[i + 1])[1]) <= base + 1)) {
        i++;  // a blank line inside the list
      } else break;
    }
    if (item) ol.appendChild(listItem(item));
    into.appendChild(ol);
    return i;
  }

  function listItem(lines) {
    var li = el("li");
    if (lines.length === 1) mdInline(lines[0], li);
    else mdBlocks(lines, li);
    return li;
  }

  function cells(row) {
    var s = row.trim().replace(/^\|/, "").replace(/\|$/, "");
    var out = [""];
    for (var k = 0; k < s.length; k++) {
      if (s.charAt(k) === "\\" && s.charAt(k + 1) === "|") { out[out.length - 1] += "|"; k++; }
      else if (s.charAt(k) === "|") out.push("");
      else out[out.length - 1] += s.charAt(k);
    }
    return out.map(function (c) { return c.trim(); });
  }

  function table(rows) {
    var wrap = el("div", { "class": "md-table" });
    var tb = el("table");
    rows.forEach(function (r, k) {
      var tr = el("tr");
      cells(r).forEach(function (c) {
        var td = el(k ? "td" : "th");
        mdInline(c, td);
        tr.appendChild(td);
      });
      tb.appendChild(tr);
    });
    wrap.appendChild(tb);
    return wrap;
  }

  var MD_INLINE = /(`+)([\s\S]*?[^`])\1(?!`)|\*\*(?=\S)([\s\S]*?\S)\*\*|__(?=\S)([\s\S]*?\S)__|\*(?=[^\s*])([^*]*?[^\s*])\*|\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)|(https?:\/\/[^\s<>()　-〿＀-￯]+[^\s<>().,;:!?'"　-〿＀-￯])|\[\[([^\]|#]+)#\^(p\d+)(?:\|[^\]]*)?\]\]/g;

  function mdInline(text, into) {
    var re = new RegExp(MD_INLINE.source, "g"), last = 0, m;  // its own: bold and italic call this again
    while ((m = re.exec(text))) {
      if (m.index > last) into.appendChild(document.createTextNode(text.slice(last, m.index)));
      if (m[1]) into.appendChild(el("code", { "class": "md-code" }, m[2].replace(/^ (.*) $/, "$1")));
      else if (m[3] !== undefined || m[4] !== undefined) {
        var b = el("strong");
        mdInline(m[3] !== undefined ? m[3] : m[4], b);
        into.appendChild(b);
      } else if (m[5] !== undefined) {
        var e = el("em");
        mdInline(m[5], e);
        into.appendChild(e);
      } else if (m[9] !== undefined) {
        // a source link: opens the paragraph and its neighbours above the conversation
        var link = m[9].trim(), anchor = m[10];
        var cite = el("button", { type: "button", "class": "cite", title: link + "#^" + anchor },
                      sourceName(link) + " \u00a7" + anchor.slice(1));
        cite.addEventListener("click", function () { openContext(link, anchor); });
        into.appendChild(cite);
      } else {
        var href = m[7] || m[8];
        var a = el("a", { href: href, target: "_blank", rel: "noopener noreferrer" }, m[6] || href);
        into.appendChild(a);
      }
      last = re.lastIndex;
    }
    if (last < text.length) into.appendChild(document.createTextNode(text.slice(last)));
  }

  function copyText(text, button) {
    var label = button.textContent;
    var done = function () {
      button.textContent = t("copied");
      setTimeout(function () { button.textContent = label; }, 1500);
    };
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(text).then(done, function () {});
      return;
    }
    var box = el("textarea");
    box.value = text;
    box.style.position = "fixed";
    box.style.opacity = "0";
    document.body.appendChild(box);
    box.select();
    try { if (document.execCommand("copy")) done(); } catch (e) { /* the text stays selectable */ }
    box.remove();
  }

  // An answer as plain text for pasting elsewhere: [[Sources/…/Name#^p12]] becomes (Name §12), Markdown
  // marks are dropped, table rows become tab-separated lines; the text inside code fences stays as it is.
  function plainText(md) {
    var out = [], code = false;
    md.replace(/\r\n?/g, "\n").split("\n").forEach(function (line) {
      if (MD_FENCE.test(line)) { code = !code; return; }
      if (code) { out.push(line); return; }
      if (MD_RULE.test(line) || MD_TABLE_SEP.test(line) && line.indexOf("-") >= 0 && line.indexOf("|") >= 0) return;
      var m;
      while (MD_QUOTE.test(line)) line = line.replace(MD_QUOTE, "");
      if ((m = MD_HEAD.exec(line))) line = m[2];
      else if ((m = MD_ITEM.exec(line))) line = m[1] + (/\d/.test(m[2]) ? m[2] : "•") + " " + m[3];
      else if (line.indexOf("|") >= 0 && /^\s*\|/.test(line)) line = cells(line).join("\t");
      out.push(plainInline(line));
    });
    return out.join("\n").replace(/\n{3,}/g, "\n\n").trim();
  }

  function plainInline(s) {
    return s
      .replace(/\[\[([^\]|#]+)(?:#\^?([^\]|]*))?(?:\|([^\]]+))?\]\]/g, function (_, path, anchor, alias) {
        var name = alias || path.split("/").pop().replace(/\.md$/i, "");
        var p = /^p(\d+)$/.exec(anchor || "");
        return t("copy_cite", { name: name + (p ? " §" + p[1] : anchor ? " " + anchor : "") });
      })
      .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, "$1 ($2)")
      .replace(/(`+)([\s\S]*?[^`])\1(?!`)/g, "$2")
      .replace(/\*\*(?=\S)([\s\S]*?\S)\*\*|__(?=\S)([\s\S]*?\S)__/g, function (_, a, b) { return a !== undefined ? a : b; })
      .replace(/\*(?=[^\s*])([^*]*?[^\s*])\*/g, "$1");
  }

  function codeBlock(code, lang) {
    var wrap = el("div", { "class": "md-pre" });
    var head = el("div", { "class": "md-pre-head" });
    head.appendChild(el("span", { "class": "md-lang" }, lang || ""));
    var copy = el("button", { type: "button", "class": "quiet small" }, t("copy_code"));
    copy.addEventListener("click", function () { copyText(code, copy); });
    head.appendChild(copy);
    wrap.appendChild(head);
    var pre = el("pre");
    var c = el("code");
    highlight(code, lang, c);
    pre.appendChild(c);
    wrap.appendChild(pre);
    return wrap;
  }

  // ---------- code colours ----------
  // A token pass per language: comments, strings, variables or keys, numbers and keywords get a class
  // (tok-com, tok-str, tok-var, tok-num, tok-kw); everything else stays plain text. Not a parser: unusual
  // code may be coloured wrongly, its text is always shown as it is.

  function words(s) {
    var o = {};
    s.split(" ").forEach(function (w) { o[w] = true; });
    return o;
  }

  var STR_DQ = '"(?:[^"\\\\\\n]|\\\\.)*"', STR_SQ = "'(?:[^'\\\\\\n]|\\\\.)*'";
  var NUM = "\\b(?:0[xX][\\da-fA-F]+|\\d+(?:\\.\\d+)?(?:[eE][+-]?\\d+)?)\\b";
  var WORD = "[A-Za-z_$][\\w$]*";
  var JS_KW = words("var let const function return if else for while do switch case break continue new try catch " +
    "finally throw typeof instanceof in of class extends import export from default async await yield null " +
    "undefined true false this super delete void static get set");
  var LANGS = {
    python: { tokens: [["com", "#.*"], ["str", "[rRbBuUfF]{0,2}(?:\"\"\"[\\s\\S]*?\"\"\"|'''[\\s\\S]*?'''|" + STR_DQ + "|" + STR_SQ + ")"],
                       ["var", "@[\\w.]+"]],
              kw: words("and as assert async await break class continue def del elif else except False finally for " +
                        "from global if import in is lambda None nonlocal not or pass raise return True try while " +
                        "with yield self print len range") },
    shell: { tokens: [["com", "(?:^|\\s)#.*"], ["str", STR_DQ + "|'[^']*'"],
                      ["var", "\\$(?:\\{[^}\\n]*\\}|[\\w@#?*!$-]+)"]],
             kw: words("if then else elif fi for while until do done case esac in function return local export " +
                       "readonly declare set unset echo printf cd exit source sudo shift break continue true false") },
    js: { tokens: [["com", "\\/\\/.*|\\/\\*[\\s\\S]*?\\*\\/"], ["str", STR_DQ + "|" + STR_SQ + "|`(?:[^`\\\\]|\\\\.)*`"]],
          kw: JS_KW },
    json: { tokens: [["var", STR_DQ + "(?=\\s*:)"], ["str", STR_DQ]], kw: words("true false null") },
    yaml: { tokens: [["com", "(?:^|\\s)#.*"], ["var", "^[ \\t]*(?:- +)?[^\\s:#'\"][^:#\\n]*(?=:(?:\\s|$))"],
                     ["str", STR_DQ + "|" + STR_SQ]],
            kw: words("true false null yes no on off True False Null ~") },
    sql: { tokens: [["com", "--.*|\\/\\*[\\s\\S]*?\\*\\/"], ["str", STR_SQ + "|" + STR_DQ]],
           kw: words("select from where and or not insert into values update set delete create table view index " +
                     "drop alter add join left right inner outer full on group by order having limit offset as " +
                     "distinct null is in like between union all case when then else end exists primary key " +
                     "references default count sum avg min max asc desc with"), lower: true }
  };
  var LANG_NAMES = { py: "python", python: "python", python3: "python", sh: "shell", bash: "shell", shell: "shell",
    zsh: "shell", console: "shell", js: "js", javascript: "js", ts: "js", typescript: "js", mjs: "js",
    jsx: "js", json: "json", jsonc: "js", yaml: "yaml", yml: "yaml", sql: "sql" };
  var LANG_RE = {};

  function langRe(name) {
    if (!LANG_RE[name]) {
      var spec = LANGS[name];
      var parts = spec.tokens.map(function (x) { return "(" + x[1] + ")"; });
      parts.push("(" + NUM + ")", "(" + WORD + ")");
      LANG_RE[name] = new RegExp(parts.join("|"), "gm");
    }
    return LANG_RE[name];
  }

  function highlight(code, lang, into) {
    lang = (lang || "").toLowerCase();
    if (lang === "diff" || lang === "patch") { diffLines(code, into); return; }
    var name = LANG_NAMES[lang];
    if (!name) { into.textContent = code; return; }
    var spec = LANGS[name], re = langRe(name), last = 0, m;
    var classes = spec.tokens.map(function (x) { return x[0]; }).concat(["num", "word"]);
    re.lastIndex = 0;
    while ((m = re.exec(code))) {
      if (m[0] === "") { re.lastIndex++; continue; }
      var k = 1;
      while (m[k] === undefined) k++;
      var cls = classes[k - 1];
      if (cls === "word") {
        cls = spec.kw[spec.lower ? m[0].toLowerCase() : m[0]] ? "kw" : "";
        if (!cls) continue;  // left in the plain text before the next token
      }
      if (m.index > last) into.appendChild(document.createTextNode(code.slice(last, m.index)));
      into.appendChild(el("span", { "class": "tok-" + cls }, m[0]));
      last = re.lastIndex;
    }
    if (last < code.length) into.appendChild(document.createTextNode(code.slice(last)));
  }

  function diffLines(code, into) {
    var lines = code.split("\n");
    lines.forEach(function (l, k) {
      var cls = /^(\+\+\+|---)/.test(l) ? "head" : l.charAt(0) === "+" ? "add" : l.charAt(0) === "-" ? "del"
        : l.indexOf("@@") === 0 ? "hunk" : "";
      into.appendChild(cls ? el("span", { "class": "tok-" + cls }, l) : document.createTextNode(l));
      if (k < lines.length - 1) into.appendChild(document.createTextNode("\n"));
    });
  }

  // A finished turn keeps its answer in view and folds its steps into one line, so that the conversation
  // does not grow by a line for every file read or script run. The part elements move as they are, so a
  // late update still lands in them.
  var STEP_KIND = { read: "perm_read", bash: "perm_bash", edit: "perm_edit", write: "perm_edit", glob: "perm_glob",
                    grep: "perm_grep", list: "perm_list", task: "perm_task", webfetch: "perm_webfetch" };

  function stepsLine(tools) {
    var counts = {}, failed = 0;
    tools.forEach(function (p) {
      var k = t(STEP_KIND[p.dataset.tool] || "perm_other", { name: p.dataset.tool || "?" });
      counts[k] = (counts[k] || 0) + 1;
      if (p.className.indexOf("failed") >= 0) failed++;
    });
    var parts = Object.keys(counts).map(function (k) { return k + " " + counts[k]; });
    return t("steps", { n: tools.length }) + " (" + parts.join(" \u00b7 ") + ")" +
      (failed ? " \u2014 " + t("steps_failed", { n: failed }) : "");
  }

  function compactBubble(b) {
    if (b.dataset.compact) return;
    var child = b.className.indexOf("child") >= 0;
    var items = Array.prototype.filter.call(b.children, function (c) {
      return child ? c.className !== "who" : c.className.split(" ")[0] === "tool";
    });
    var tools = items.filter(function (c) { return c.className.split(" ")[0] === "tool"; });
    if (tools.length < 2 && !(child && tools.length && items.length > 1)) return;
    var body = el("div", { "class": "steps-body" });
    var d = fold(stepsLine(tools), body);
    d.className = "fold steps" + (tools.some(function (p) { return p.className.indexOf("failed") >= 0; }) ? " failed" : "");
    b.insertBefore(d, items[0]);
    items.forEach(function (c) { body.appendChild(c); });
    b.dataset.compact = "1";
  }

  function compactTurns() {
    var bubbles = Array.prototype.slice.call(document.querySelectorAll("#messages > .msg"));
    var last = -1;  // while the assistant works, its current turn (after the last user message) stays open
    if (chat.busy) bubbles.forEach(function (b, i) { if (b.className.indexOf("user") >= 0) last = i; });
    bubbles.forEach(function (b, i) {
      if (b.className.indexOf("assistant") >= 0 && (!chat.busy || i < last)) compactBubble(b);
    });
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
    buttons.push([t("allow_all_card"), "", function () { setAllowAll(true); }]);
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
    if (ev.type === "ingest" || ev.type === "backfill") { ingestSoon(); return; }
    if (ev.type === "windows") {
      chat.windows = ev.windows || [];
      chat.lock = ev.lock || null;
      lockUpgrade();
      if (!chat.windows.some(function (w) { return w.id === chat.win; }) && chat.windows.length) chatLoad(ev.current);
      chatEnable();
      return;
    }
    if (ev.win && ev.win !== chat.win) {  // another window: its tab says what happens there
      if ((ev.type === "part" || ev.type === "delta") && ev.role === "assistant" && !chat.unread[ev.win]) {
        chat.unread[ev.win] = true;
        drawTabs();
      }
      return;
    }
    if (ev.type === "agent") {
      chatAgent(ev);
      if (ev.state === "ready") chatLoad(chat.win);  // a conversation picked up again brings its history
    }
    else if (ev.type === "part") {
      showPart(ev);
      if (ev.kind === "tool" && ev.script) stageFrom(ev);
    }
    else if (ev.type === "delta") {
      var p = partEl({ partID: ev.partID, messageID: ev.messageID, role: ev.role, child: ev.child, kind: "text" });
      addText(p, ev.delta, ev.role);
      scrollChat();
    } else if (ev.type === "status") {
      chat.busy = ev.status !== "idle";
      chatEnable();
      if (!chat.busy) { compactTurns(); stagesIdle(); loadPending(); }
    }
    else if (ev.type === "auto") {
      autoNote((ev.child ? t("child") : "") + t("auto", { what: permName(ev.permission) + " " + permWhat(ev).join(", ") }));
    }
    else if (ev.type === "error") note(ev.text, "error");
    else if (ev.type === "permission") permissionCard(ev);
    else if (ev.type === "question") questionCard(ev);
    else if (ev.type === "permission_done" || ev.type === "question_done") dropCard(ev.id);
    else if (ev.type === "reset") { chat.model = ""; $("model").value = ""; clearChat(); }
    else if (ev.type === "workdir") chatBar(ev);
    else if (ev.type === "allow_all") {
      if (chat.allowAll !== ev.on) note(t(ev.on ? "allow_all_note_on" : "allow_all_note_off"), ev.on ? "error" : "auto");
      chat.allowAll = ev.on;
      chatEnable();
    }
  }

  // ---------- --chat-first: the knowledge base folded, a work folder, models, earlier conversations ----------

  // Whether the knowledge base is unfolded: remembered by the browser, apart for --chat-first. It starts
  // folded with --chat-first and unfolded otherwise.
  function kbKey() { return state && state.chat_first ? "kb-client-kb-open" : "kb-client-kb-open-full"; }

  // Until the knowledge-base skills are installed and a library is there, Set up is what to do first: the
  // knowledge base is unfolded whatever the browser remembers (unless folded on this page) and Set up stands out.
  var kbFoldedHere = false;

  function kbNotReady() {
    return !!state && (!(state.kb_skills && state.kb_skills.ok) || !localLibs().length);
  }

  function kbOpen() {
    if (kbNotReady() && !kbFoldedHere) return true;
    var v = null;
    try { v = localStorage.getItem(kbKey()); } catch (e) { v = null; }
    return v === null ? !(state && state.chat_first) : v === "open";
  }

  // Without body.kb-open the page shows the skills and the conversation only (style.css); a running step
  // unfolds it.
  function applyKb() {
    var cf = !!(state && state.chat_first);
    document.body.classList.toggle("chat-first", cf);
    document.body.classList.toggle("kb-open", kbOpen() || !!job || refused);
    var setup = document.querySelector(".actions [data-action=setup]");
    if (setup) setup.classList.toggle("primary", kbNotReady());
    show($("kb-toggle"), !!state);
    show($("chat-bar"), cf);
    $("kb-toggle-text").textContent = t(kbOpen() ? "kb_close" : "kb_open");
    $("kb-toggle").setAttribute("aria-expanded", kbOpen() ? "true" : "false");
    var title = t(cf ? "title_chat" : "title");
    $("title").textContent = title;
    document.title = title;
    applySide();
  }

  function toggleKb() {
    var was = kbOpen();
    if (was) kbFoldedHere = true;
    try { localStorage.setItem(kbKey(), was ? "folded" : "open"); } catch (e) { /* this view only */ }
    refused = false;
    if (kbOpen()) setSide(false);  // unfolding the knowledge base is asking to see it
    applyKb();
    renderChecklist();
  }

  // The left column folded to a narrow strip on a wide screen, so that the conversation is wider; remembered
  // by the browser, apart for --chat-first. It starts unfolded. Narrow screens keep it below the conversation.
  function sideKey() { return state && state.chat_first ? "kb-client-side-folded" : "kb-client-side-folded-full"; }

  function sideFolded() {
    try { return localStorage.getItem(sideKey()) === "1"; } catch (e) { return false; }
  }

  function setSide(folded) {
    try {
      if (folded) localStorage.setItem(sideKey(), "1"); else localStorage.removeItem(sideKey());
    } catch (e) { /* this view only */ }
    applySide();
  }

  function applySide() {
    var folded = !!state && sideFolded();
    document.body.classList.toggle("side-folded", folded);
    $("side-strip-label").textContent = t(kbOpen() || job ? "side_label_kb" : "side_label_skills");
    $("side-strip").title = t("side_unfold");
    $("side-strip").setAttribute("aria-label", t("side_unfold"));
    $("side-strip").setAttribute("aria-expanded", folded ? "false" : "true");
    $("side-fold").title = t("side_fold");
    $("side-fold").setAttribute("aria-label", t("side_fold"));
    $("side-fold").setAttribute("aria-expanded", folded ? "false" : "true");
    show($("side-fold"), !!state);
  }

  function chatBar(a) {
    if (a.workdir !== undefined) chat.workdir = a.workdir || "";
    if (a.recent) chat.recent = a.recent;
    if (a.models) chat.models = a.models;
    $("workdir").textContent = chat.workdir || t("workdir_none");
    show($("workdir-note"), !!(state && state.chat_first && chat.workdir));
    var sel = $("workdir-recent");
    sel.textContent = "";
    sel.appendChild(el("option", { value: "" }, t("workdir_recent")));
    chat.recent.filter(function (d) { return d !== chat.workdir; }).forEach(function (d) {
      sel.appendChild(el("option", { value: d }, d));
    });
    show(sel, sel.options.length > 1);
    var m = $("model");
    var keep = chat.model;
    m.textContent = "";
    m.appendChild(el("option", { value: "" }, t("model_default")));
    chat.models.forEach(function (x) { m.appendChild(el("option", { value: x.id }, x.name + "  (" + x.id + ")")); });
    chat.model = chat.models.some(function (x) { return x.id === keep; }) ? keep : "";
    m.value = chat.model;
    show(m, chat.models.length > 1);
  }

  function setWorkdir(path) {
    if (!path) return;
    api("POST", "/api/chat/workdir", { path: path }).catch(function (e) { note(String(e.message), "error"); });
  }

  function sessionsCard() {
    api("POST", "/api/chat/sessions", {}).then(function (r) {
      var c = card("sessions", t("sessions_title"));
      var current = shown().session;
      var list = r.sessions.filter(function (x) { return x.id !== current; });
      if (!list.length) c.appendChild(el("p", { "class": "hint" }, t("sessions_none")));
      list.forEach(function (x) {
        var when = typeof x.updated === "number" && x.updated ? new Date(x.updated > 1e12 ? x.updated : x.updated * 1000).toLocaleString() : "";
        var b = el("button", { type: "button", "class": "quiet session" }, (x.title || t("session_untitled")) + (when ? "  \u00b7  " + when : "")
          + (r.open && r.open[x.id] ? "  " + t("session_open") : ""));
        b.addEventListener("click", function () {
          dropCard("sessions");
          api("POST", "/api/chat/open", { session: x.id }).then(function (o) { chatLoad(o.win); })
            .catch(function (e) { note(String(e.message), "error"); });
        });
        c.appendChild(b);
      });
      buttonRow(c, [[t("close"), "quiet", function () { dropCard("sessions"); }]]);
      c.scrollIntoView({ block: "nearest" });
    }).catch(function (e) { note(String(e.message), "error"); });
  }

  var DIFF_LINES = 400;

  function diffFold(diff) {
    var lines = diff.replace(/\n$/, "").split("\n");
    var pre = el("pre", { "class": "diff" });
    lines.slice(0, DIFF_LINES).forEach(function (l) {
      var cls = /^(\+\+\+|---)/.test(l) ? "head" : l[0] === "+" ? "add" : l[0] === "-" ? "del" : l.indexOf("@@") === 0 ? "hunk" : "";
      pre.appendChild(el("span", cls ? { "class": cls } : {}, l + "\n"));
    });
    if (lines.length > DIFF_LINES) pre.appendChild(el("span", { "class": "hunk" }, t("diff_more", { n: lines.length - DIFF_LINES })));
    return fold(t("diff_show"), pre);
  }

  // Allow everything on the page: the client answers every request itself, until it is switched off or
  // the client quits. Switching it on also answers the waiting cards.
  function setAllowAll(on) {
    if (on && !window.confirm(t("allow_all_confirm"))) return;
    api("POST", "/api/chat/allow_all", { on: on, win: chat.win }).catch(function (e) { note(String(e.message), "error"); });
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

  // ---------- source view ----------
  // A source link in an answer opens its paragraph with the two before and after it (GET /api/context), above
  // the conversation; the libraries are tried in order and the first that holds the source shows it.

  function sourceName(link) { return link.split("/").pop(); }

  function openContext(link, anchor) {
    var libs = localLibs().map(function (l) { return l.id; });
    var list = $("source-list");
    list.textContent = "";
    $("source-title").textContent = t("source_around", { name: sourceName(link), n: anchor.slice(1) });
    show($("source-view"), true);
    function tryLib(k) {
      if (k >= libs.length) { list.appendChild(el("p", { "class": "warn" }, t("source_missing"))); return; }
      api("GET", "/api/context?lib=" + encodeURIComponent(libs[k]) + "&link=" + encodeURIComponent(link) +
          "&anchor=" + encodeURIComponent(anchor)).then(function (got) {
        got.paragraphs.forEach(function (p) {
          var d = el("div", { "class": "source-para" + (p.hit ? " hit" : "") });
          d.appendChild(el("span", { "class": "hint" }, "\u00a7" + p.anchor.slice(1) + " "));
          d.appendChild(document.createTextNode(p.text));
          list.appendChild(d);
        });
        var hit = list.querySelector(".hit");
        if (hit) hit.scrollIntoView({ block: "nearest" });
      }).catch(function (e) {
        if (e.status === 404) tryLib(k + 1);
        else list.appendChild(el("p", { "class": "warn" }, String(e.message)));
      });
    }
    tryLib(0);
  }

  $("source-close").addEventListener("click", function () { show($("source-view"), false); });

  // ---------- quick search ----------
  // A message that starts with one of QUICK_WORDS, or any message of a window whose Search the knowledge base
  // switch is on, is not sent to the assistant: POST /api/quick lists what the libraries' indexes hold for it
  // at once and streams a short summary from one call to the model, numbered [n] after the passages. The
  // result stays on this page (not in the conversation); Deep search and Give to the assistant send it on.

  // Only words that ask for a search: a message starting with "explain" or "is there" goes to the assistant.
  var QUICK_WORDS = ["搜索一下", "搜一下", "搜索", "查找", "知识库里", "search for", "search", "look up"
  ].sort(function (a, b) { return b.length - a.length; });
  var QUICK_KEY = "kb-client-quick";

  function quickOn() {
    try { return !!JSON.parse(localStorage.getItem(QUICK_KEY) || "{}")[chat.win]; } catch (e) { return false; }
  }

  function setQuickOn(on) {
    try {
      var all = JSON.parse(localStorage.getItem(QUICK_KEY) || "{}");
      if (on) all[chat.win] = 1; else delete all[chat.win];
      localStorage.setItem(QUICK_KEY, JSON.stringify(all));
    } catch (e) { /* this view only */ }
  }

  // The words to search for when the message is a quick search, else null.
  function quickQuery(text) {
    if (!localLibs().length) return null;
    var s = text.trim(), low = s.toLowerCase();
    for (var i = 0; i < QUICK_WORDS.length; i++) {
      var w = QUICK_WORDS[i];
      if (low.indexOf(w) === 0 && (!/^[a-z]/.test(w) || !/[a-z0-9]/.test(low.charAt(w.length)))) {
        var rest = s.slice(w.length).replace(/^[\s:：,，、]+/, "");
        if (rest) return rest;
        break;
      }
    }
    return $("quick-switch").checked ? s : null;
  }

  function quickWhy(ev) {
    var key = "quick_" + ev.reason;
    if (ev.reason === "http" && (T.en["quick_http_" + ev.status])) key = "quick_http_" + ev.status;
    return t(key, { status: ev.status, detail: ev.detail || "" }) + (key === "quick_http" && ev.detail ? " " + ev.detail : "");
  }

  function quick(text, query) {
    var win = chat.win;
    var mine = el("div", { "class": "msg user" });
    mine.appendChild(el("div", { "class": "text" }, text));
    var box = el("div", { "class": "msg assistant quick" });
    var head = el("p", { "class": "hint quick-head" }, t("quick_searching"));
    var summary = el("div", { "class": "text quick-summary" });
    var status = el("p", { "class": "hint" });
    var list = el("div", { "class": "quick-items" });
    var passages = fold("", list);
    passages.hidden = true;
    var buttons = el("div", { "class": "quick-buttons" });
    var deep = el("button", { type: "button", "class": "quiet small" }, t("quick_deep"));
    var hand = el("button", { type: "button", "class": "quiet small" }, t("quick_assistant"));
    deep.addEventListener("click", function () { quickSend(t("quick_deep_text", { q: text.trim() })); });
    hand.addEventListener("click", function () { quickSend(text); });
    buttons.appendChild(deep);
    buttons.appendChild(hand);
    [head, summary, status, passages, buttons].forEach(function (x) { box.appendChild(x); });
    (chat.quick[win] = chat.quick[win] || []).push(mine, box);
    if (chat.win === win) { $("messages").appendChild(mine); $("messages").appendChild(box); scrollChat(); }

    var items = [], raw = "", bad = [];
    function showItem(n) {
      passages.open = true;
      var row = list.querySelector("[data-n='" + n + "']");
      if (!row) return;
      Array.prototype.forEach.call(list.querySelectorAll(".quick-item.hit"), function (r) { r.classList.remove("hit"); });
      row.classList.add("hit");
      row.scrollIntoView({ block: "nearest" });
    }
    function drawSummary() {
      summary.textContent = "";
      raw.split(/\n+/).forEach(function (line) {
        if (!line.trim()) return;
        var p = el("p");
        line.split(/(\[\d+(?:\s*[,，、]\s*\d+)*\])/).forEach(function (part, i) {
          if (i % 2 === 0) { if (part) p.appendChild(document.createTextNode(part)); return; }
          part.slice(1, -1).split(/\s*[,，、]\s*/).forEach(function (n) {
            var k = Number(n), ok = k >= 1 && k <= items.length;
            var c = el("button", { type: "button", "class": "cite" + (ok ? "" : " bad") }, "[" + n + "]");
            if (ok) c.addEventListener("click", function () { showItem(k); });
            p.appendChild(c);
          });
        });
        summary.appendChild(p);
      });
    }
    function drawItems(got) {
      items = got.items;
      head.textContent = t("quick_head", { k: got.keywords.join(lang === "zh" ? "、" : ", ") });
      passages.firstChild.textContent = t("quick_passages", { n: items.length });
      passages.hidden = !items.length;
      items.forEach(function (x) {
        var row = el("div", { "class": "quick-item", "data-n": String(x.n) });
        var meta = el("div", { "class": "hint" }, "[" + x.n + "] " + t("quick_" + x.kind) +
          (x.kind === "status" ? "" : " · " + sourceName(x.link) + (x.anchor ? " §" + x.anchor.slice(1) : "")) +
          (x.date ? " · " + x.date : "") + " · " + x.label +
          (x.review ? " · " + t("quick_review") : "") +
          (x.hits < x.of ? " · " + t("quick_some", { h: x.hits, k: x.of }) : ""));
        if (x.link) {
          var open = el("button", { type: "button", "class": "quiet small" }, t("quick_open"));
          open.addEventListener("click", function () { openContext(x.link, x.anchor); });
          meta.appendChild(document.createTextNode(" "));
          meta.appendChild(open);
        }
        row.appendChild(meta);
        if (x.conclusion) row.appendChild(el("div", { "class": "quick-conclusion" }, x.conclusion));
        row.appendChild(el("div", {}, x.text));
        list.appendChild(row);
      });
      if (!items.length) {
        status.textContent = t("quick_none");
        deep.className = "primary small";
      } else {
        status.textContent = t("quick_summarising");
      }
    }
    function handle(ev) {
      if (ev.type === "hits") drawItems(ev);
      else if (ev.type === "text") { raw += ev.text; drawSummary(); }
      else if (ev.type === "done") {
        bad = ev.bad || [];
        if (items.length) status.textContent = t("quick_note") + (bad.length ? " " + t("quick_bad", { n: bad.join(", ") }) : "");
        if (!ev.empty && !raw.trim()) status.textContent = t("quick_failed", { why: t("quick_bad_reply") });
      } else if (ev.type === "error") {
        status.textContent = t("quick_failed", { why: quickWhy(ev) });
        status.className = "warn";
        passages.open = true;
        deep.className = "primary small";
      }
      if (chat.win === win) scrollChat();
    }
    fetch("/api/quick", {
      method: "POST", headers: { "X-Token": token, "Content-Type": "application/json" },
      body: JSON.stringify({ text: query, model: chat.model || "" })
    }).then(function (r) {
      if (!r.ok) return r.json().then(function (d) { throw new Error(d.error || r.status); });
      var reader = r.body.getReader(), dec = new TextDecoder(), buf = "";
      function pump() {
        return reader.read().then(function (x) {
          buf += dec.decode(x.value || new Uint8Array(0), { stream: !x.done });
          var lines = buf.split("\n");
          buf = x.done ? "" : lines.pop();
          lines.forEach(function (l) { if (l.trim()) handle(JSON.parse(l)); });
          if (!x.done) return pump();
        });
      }
      return pump();
    }).catch(function (e) {
      handle({ type: "error", reason: "lost", detail: String(e.message) });
    });
  }

  function quickSend(text) {
    if (!chat.ready) { note(t("quick_not_ready"), "error"); return; }
    say(text);
  }

  $("quick-switch").addEventListener("change", function () { setQuickOn($("quick-switch").checked); });

  // ---------- client-run ingest ----------
  // The client runs kb-ingest's scripts itself; the assistant only writes cards, in windows of the client's own.

  var ING_ITEMS = 300;
  var ing = { lib: null, plan: null, state: null, timer: null, material: "" };

  function openIngest(lib) {
    ing.lib = lib;
    ing.plan = null;
    $("ingest-title").textContent = t("ingest_title", { lib: lib.label });
    show($("ingest"), true);
    $("ingest").scrollIntoView({ behavior: "smooth", block: "start" });
    drawIngestForm();
    loadIngest();
  }

  function ingestSoon() {
    clearTimeout(ing.timer);
    ing.timer = setTimeout(loadIngest, 300);
  }

  function loadIngest() {
    return api("GET", "/api/ingest").then(function (st) {
      ing.state = st;
      drawIngestStrip();
      drawIngestRun();
      drawBackfill();
      drawAuto();
    }).catch(function () {});
  }

  function rulesNow() {
    var folders = [];
    Array.prototype.forEach.call(document.querySelectorAll("#ingest-form input[data-folder]"), function (c) {
      if (c.checked) folders.push(c.getAttribute("data-folder"));
    });
    var all = document.querySelector("#ingest-form input[data-all]");
    var since = document.querySelector("#ingest-form input[type=date]");
    return { folders: all && all.checked ? [] : folders, since: since ? since.value : "" };
  }

  function drawIngestForm() {
    var box = $("ingest-form");
    box.textContent = "";
    var row = el("div", { "class": "row" });
    row.appendChild(el("span", {}, t("ingest_material")));
    row.appendChild(el("code", {}, ing.material || t("ingest_none")));
    var choose = el("button", { type: "button", "class": "quiet small" }, t("ingest_choose"));
    choose.addEventListener("click", function () {
      openBrowser(ing.material || (state && state.home) || "", function (path) {
        ing.material = path;
        ing.plan = null;
        drawIngestForm();
        listPlan([]);
      });
    });
    row.appendChild(choose);
    box.appendChild(row);
    var p = ing.plan;
    if (ing.material && p) {
      box.appendChild(el("h3", {}, t("ingest_rules")));
      box.appendChild(el("p", { "class": "hint" }, t("ingest_rules_hint")));
      var folders = el("div", { "class": "ingest-folders" });
      var allL = el("label");
      var all = el("input", { type: "checkbox", "data-all": "1" });
      all.checked = !p.rules.folders.length;
      allL.appendChild(all);
      allL.appendChild(document.createTextNode(" " + t("ingest_all_folders")));
      folders.appendChild(allL);
      p.folders.forEach(function (f) {
        var l = el("label");
        var c = el("input", { type: "checkbox", "data-folder": f.folder });
        c.checked = p.rules.folders.indexOf(f.folder) >= 0;
        c.disabled = !f.folder;
        l.appendChild(c);
        l.appendChild(document.createTextNode(" " + (f.folder || t("ingest_top")) + " (" + f.files + ")"));
        folders.appendChild(l);
        c.addEventListener("change", function () { if (c.checked) all.checked = false; listPlan(); });
      });
      all.addEventListener("change", function () { listPlan(); });
      box.appendChild(folders);
      var sr = el("div", { "class": "row" });
      sr.appendChild(el("span", {}, t("ingest_since")));
      var since = el("input", { type: "date", value: p.rules.since || "" });
      since.addEventListener("change", function () { listPlan(); });
      sr.appendChild(since);
      box.appendChild(sr);
      box.appendChild(el("p", {}, t("ingest_listed", { total: p.total, important: p.important, rest: p.total - p.important })));
      if (p.other) box.appendChild(el("p", { "class": "hint" }, t("ingest_other", { n: p.other })));
      var go = el("div", { "class": "row" });
      go.appendChild(el("span", {}, t("ingest_parallel")));
      var par = choiceSelect([1, 2, 3, 4].slice(0, (ing.state && ing.state.parallel_max) || 4).map(function (n) {
        return [String(n), String(n)]; }), "1");
      go.appendChild(par);
      var start = el("button", { type: "button", "class": "primary small" }, t("ingest_start"));
      start.disabled = !p.total || (ing.state && ing.state.run && ["running", "stopping", "waiting"].indexOf(ing.state.run.state) >= 0);
      var msg = el("span", { "class": "hint" });
      start.addEventListener("click", function () {
        start.disabled = true;
        api("POST", "/api/ingest/start", { library: ing.lib.id, material: ing.material, rules: rulesNow(),
                                           parallel: Number(par.value) }).then(function () {
          ing.plan = null;
          drawIngestForm();
          loadIngest();
        }).catch(function (e) { start.disabled = false; msg.textContent = String(e.message); });
      });
      go.appendChild(start);
      go.appendChild(msg);
      box.appendChild(go);
    }
  }

  function listPlan(folders) {
    var rules = folders ? { folders: folders, since: "" } : rulesNow();
    api("POST", "/api/ingest/plan", { library: ing.lib.id, material: ing.material, rules: rules }).then(function (p) {
      ing.plan = p;
      drawIngestForm();
    }).catch(function (e) { $("ingest-form").appendChild(el("p", { "class": "warn" }, String(e.message))); });
  }

  function runDone(r) {
    var counts = r.counts || {}, done = 0;
    ["carded", "filed", "duplicate", "older", "failed", "empty"].forEach(function (k) { done += counts[k] || 0; });
    return done;
  }

  function runLine(r) {
    return t("ingest_progress", { label: r.label, done: runDone(r), total: r.total }) + " \u00b7 " +
      t("ingest_state_" + r.state) + (r.step && r.state !== "done" ? " \u00b7 " + t("ingest_step_" + r.step) : "");
  }

  function runBar(r) {
    var bar = el("div", { "class": "ingest-bar" });
    var fill = el("span");
    fill.style.width = (r.total ? Math.round(100 * runDone(r) / r.total) : 0) + "%";
    bar.appendChild(fill);
    return bar;
  }

  function pendingButton() {
    var sh = el("button", { type: "button", "class": "quiet small" }, t("ingest_show_pending"));
    sh.addEventListener("click", function () { loadPending(); $("pending").scrollIntoView({ behavior: "smooth", block: "start" }); });
    return sh;
  }

  // Stop while the run works; Continue and Discard once it stopped or failed. Errors are shown in errBox.
  function runButtons(r, row, errBox) {
    function warn(e) { errBox.appendChild(el("p", { "class": "warn" }, String(e.message))); }
    if (["running", "waiting"].indexOf(r.state) >= 0) {
      var stop = el("button", { type: "button", "class": "quiet small" }, t("ingest_stop"));
      stop.addEventListener("click", function () { api("POST", "/api/ingest/stop", {}).then(loadIngest).catch(function () {}); });
      row.appendChild(stop);
    }
    if (r.state === "stopped" || r.state === "failed") {
      var cont = el("button", { type: "button", "class": "primary small" }, t("ingest_continue"));
      cont.addEventListener("click", function () { api("POST", "/api/ingest/continue", {}).then(loadIngest).catch(warn); });
      row.appendChild(cont);
      var drop = el("button", { type: "button", "class": "quiet small" }, t("ingest_discard"));
      drop.addEventListener("click", function () {
        if (!window.confirm(t("ingest_discard_ask"))) return;
        api("POST", "/api/ingest/discard", {}).then(loadIngest).catch(warn);
      });
      row.appendChild(drop);
    }
  }

  // The run in one line above the conversation, from the page's start on: a run left stopped when the client
  // quit can be continued without opening the ingest panel. A finished run's line stays until it is hidden.
  function drawIngestStrip() {
    var box = $("ingest-strip");
    box.textContent = "";
    var r = ing.state && ing.state.run;
    if (!r || r.state === "done" && ing.hidden === r.id) { show(box, false); oneAgentNote(); return; }
    var head = el("div", { "class": "row" });
    head.appendChild(el("strong", {}, runLine(r)));
    if (r.state === "waiting") head.appendChild(pendingButton());
    runButtons(r, head, box);
    var lib = ((state && state.libraries) || []).filter(function (l) { return l.id === r.library && l.root && l.exists; })[0];
    if (lib) {
      var more = el("button", { type: "button", "class": "quiet small" }, t("ingest_details"));
      more.addEventListener("click", function () { openIngest(lib); });
      head.appendChild(more);
    }
    if (r.state === "done") {
      var hide = el("button", { type: "button", "class": "quiet small" }, t("ingest_close"));
      hide.addEventListener("click", function () { ing.hidden = r.id; drawIngestStrip(); });
      head.appendChild(hide);
    }
    box.appendChild(head);
    box.appendChild(runBar(r));
    if (r.state === "done" && r.summary) {
      box.appendChild(el("p", { "class": "hint" }, t("ingest_summary", { filed: r.summary.filed || 0, carded: r.summary.carded || 0, topics: r.summary.topics || 0 })));
    } else if (r.state === "failed" && r.reason) box.appendChild(el("p", { "class": "warn" }, r.reason));
    show(box, true);
    oneAgentNote();
  }

  function drawIngestRun() {
    var box = $("ingest-run");
    box.textContent = "";
    var r = ing.state && ing.state.run;
    if (!r) return;
    var counts = r.counts || {};
    box.appendChild(el("h3", {}, runLine(r)));
    box.appendChild(runBar(r));
    box.appendChild(el("p", { "class": "hint" }, Object.keys(counts).map(function (k) { return t("ist_" + k) + " " + counts[k]; }).join(" \u00b7 ")));
    if (r.reason) box.appendChild(el("p", { "class": r.state === "failed" ? "warn" : "hint" }, r.reason));
    if (r.state === "waiting") {
      var w = el("p", { "class": "warn" }, t("ingest_waiting") + " ");
      w.appendChild(pendingButton());
      box.appendChild(w);
    }
    if (r.state === "done" && r.summary) {
      box.appendChild(el("p", {}, t("ingest_summary", { filed: r.summary.filed || 0, carded: r.summary.carded || 0, topics: r.summary.topics || 0 })));
    }
    var row = el("div", { "class": "row" });
    runButtons(r, row, box);
    box.appendChild(row);
    if (["running", "waiting"].indexOf(r.state) >= 0) box.appendChild(el("p", { "class": "hint" }, t("ingest_long")));
    var d = el("details");
    d.appendChild(el("summary", {}, r.material));
    var ul = el("ul", { "class": "ingest-items" });
    r.items.slice(0, ING_ITEMS).forEach(function (it) {
      var li = el("li", { "class": "st-" + it.status });
      li.appendChild(el("span", { "class": "st" }, t("ist_" + it.status) + (it.cards ? " " + it.cards : "")));
      li.appendChild(el("span", { "class": "p" }, it.path + (it.reason ? " \u00b7 " + it.reason : "")));
      ul.appendChild(li);
    });
    d.appendChild(ul);
    if ((r.missing || []).length) {
      d.appendChild(el("p", { "class": "hint" }, t("ingest_missing", { n: r.missing.length })));
      var ml = el("ul", { "class": "ingest-items" });
      r.missing.slice(0, ING_ITEMS).forEach(function (m) { ml.appendChild(el("li", {}, m.rel)); });
      d.appendChild(ml);
    }
    if (r.log) d.appendChild(el("p", { "class": "hint log-where" }, t("ingest_log") + " " + r.log));
    box.appendChild(d);
  }

  function drawBackfill() {
    var box = $("ingest-backfill");
    box.textContent = "";
    var bf = ing.lib && ing.state && ing.state.backfill[ing.lib.id];
    if (!bf) return;
    box.appendChild(el("h3", {}, t("backfill_title")));
    box.appendChild(el("p", { "class": "hint" }, t("backfill_hint")));
    box.appendChild(el("p", {}, bf.state === "off" ? t("bfs_off")
      : t("backfill_state", { state: t("bfs_" + bf.state), left: bf.left, written: bf.written, held: bf.held })));
    var row = el("div", { "class": "row" });
    function act(label, on) {
      var b = el("button", { type: "button", "class": "quiet small" }, t(label));
      b.addEventListener("click", function () {
        var body = { library: ing.lib.id, on: on };
        if (on === true && use && use.checked && ing.plan) body.rules = rulesNow();
        api("POST", "/api/backfill", body).then(loadIngest).catch(function (e) { box.appendChild(el("p", { "class": "warn" }, String(e.message))); });
      });
      row.appendChild(b);
    }
    var use = null;
    if (bf.state === "off" || bf.state === "done") act("backfill_on", true);
    if (bf.state === "idle" || bf.state === "working") act("backfill_pause", "pause");
    if (bf.state === "paused") act("backfill_resume", true);
    if (bf.state !== "off") act("backfill_off", false);
    if (ing.plan && (bf.state === "off" || bf.state === "done")) {
      var l = el("label", { "class": "hint" });
      use = el("input", { type: "checkbox" });
      use.checked = true;
      l.appendChild(use);
      l.appendChild(document.createTextNode(" " + t("backfill_use_rules")));
      row.appendChild(l);
    }
    box.appendChild(row);
  }

  function drawAuto() {
    var box = $("ingest-auto");
    box.textContent = "";
    var a = ing.lib && ing.state && ing.state.auto && ing.state.auto[ing.lib.id];
    if (!a) return;
    box.appendChild(el("h3", {}, t("auto_title")));
    var l = el("label");
    var c = el("input", { type: "checkbox" });
    c.checked = !!a.on;
    l.appendChild(c);
    l.appendChild(document.createTextNode(" " + t("auto_on")));
    c.addEventListener("change", function () {
      api("POST", "/api/auto", { library: ing.lib.id, on: c.checked }).then(loadIngest).catch(function () { c.checked = !c.checked; });
    });
    box.appendChild(l);
    box.appendChild(el("p", { "class": "hint" }, t("auto_hint", { filed: a.filed, not_filed: a.not_filed })));
    if (a.on) {
      var r = el("div", { "class": "row" });
      r.appendChild(el("span", {}, t("auto_drop")));
      r.appendChild(el("code", {}, a.drop));
      var cp = el("button", { type: "button", "class": "quiet small" }, t("copy_path"));
      cp.addEventListener("click", function () { copyText(a.drop, cp); });
      r.appendChild(cp);
      box.appendChild(r);
      if (a.waiting) box.appendChild(el("p", {}, t("auto_waiting", { n: a.waiting })));
    }
    if (a.last) box.appendChild(el("p", { "class": "hint" }, t("auto_last", { at: a.last.at, state: t("ingest_state_" + a.last.state), files: a.last.files })));
  }

  // ---------- health check ----------
  // The client runs ingest.py's read-only check itself; findings are listed by kind, at most 50 each.

  var HEALTH_ROWS = 50;

  function openHealth(lib) {
    var box = $("health-body");
    $("health-title").textContent = t("health_title", { lib: lib.label });
    box.textContent = t("health_running");
    show($("health"), true);
    $("health").scrollIntoView({ behavior: "smooth", block: "start" });
    api("GET", "/api/check?lib=" + encodeURIComponent(lib.id)).then(function (got) {
      drawHealth(got);
    }).catch(function (e) { box.textContent = String(e.message); });
  }

  function drawHealth(got) {
    var box = $("health-body");
    box.textContent = "";
    box.appendChild(el("p", { "class": got.problems ? "warn" : "good" },
      t("health_summary", { sources: got.sources, uncarded: got.uncarded, problems: got.problems })));
    if (!got.problems) { box.appendChild(el("p", { "class": "hint" }, t("health_none"))); return; }
    var groups = [
      ["quotes", got.quotes.map(function (q) { return q.cards + "  " + q.link; })],
      ["links", got.links.map(function (x) { return x.file + "  [[" + x.link + "]]"; })],
      ["missing", got.pages.missing], ["stale", got.pages.stale], ["extra", got.pages.extra],
      ["unpaired", got.unpaired], ["review", got.status.review], ["not_current", got.status.not_current],
      ["pending", got.pending.map(function (p) { return p.run + " (" + p.days + ")"; })]
    ];
    groups.forEach(function (g) {
      if (!g[1].length) return;
      var d = el("details", { "class": "health-group" });
      d.appendChild(el("summary", {}, t("hk_" + g[0]) + ": " + g[1].length));
      var ul = el("ul", { "class": "pending-items" });
      g[1].slice(0, HEALTH_ROWS).forEach(function (row) { ul.appendChild(el("li", {}, row)); });
      if (g[1].length > HEALTH_ROWS) ul.appendChild(el("li", { "class": "hint" }, t("health_more", { n: g[1].length - HEALTH_ROWS })));
      d.appendChild(ul);
      box.appendChild(d);
    });
    if (got.pages.missing.length || got.pages.stale.length || got.pages.extra.length) {
      box.appendChild(el("p", { "class": "hint" }, t("health_fix_pages")));
    }
  }

  // ---------- ingest stages ----------
  // The stage comes from the skill script a tool step runs (agent.py stage_script), never from the
  // model's wording, so it costs no tokens and cannot drift.

  var STAGES = ["convert", "check", "file", "pages"];
  var SCRIPT_STAGE = {
    "pick_materials": "convert", "kb_batch make": "convert", "kb_batch split": "convert",
    "ingest topics": "check", "quote_check verify": "check", "ingest retopic": "check", "ingest add": "check",
    "quote_check write": "file", "ingest file": "file", "ingest pages": "pages"
  };
  var stages = { current: "", shown: "", hideTimer: null };

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
    $("ingest-cli").textContent = cliCommand();
    drawStages();
    oneAgentNote();
  }

  // "Quit OpenCode in a terminal before filing" matters only while material is being filed: the stages of an
  // ingest in the conversation, or the client's own run, are showing.
  function oneAgentNote() {
    var r = ing.state && ing.state.run;
    var running = !!r && /^(running|stopping|waiting)$/.test(r.state);
    show($("chat-one-agent"), !$("stages").hidden || running);
  }

  // The command that opens OpenCode in the work folder, for a terminal of the user's own.
  function cliCommand() {
    var d = chat.workdir || "";
    return d ? "cd '" + d.replace(/'/g, "'\\''") + "' && opencode" : "opencode";
  }

  // What holds the write lock: its window when it has one, else the step panel.
  function showLock() {
    var lock = chat.lock;
    if (!lock) return;
    if (lock.win) { showWindow(lock.win); return; }
    $("step").scrollIntoView({ behavior: "smooth", block: "start" });
  }

  // Once the assistant has been idle for two minutes, the stages fold away until the next ingest run.
  function stagesIdle() {
    clearTimeout(stages.hideTimer);
    if (!stages.current) return;
    stages.hideTimer = setTimeout(function () {
      show($("stages"), false);
      stages.current = ""; stages.shown = "";
      oneAgentNote();
    }, 120000);
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

  // Shows the window win (the current one when not given) from the server's state, and follows the stream.
  function chatLoad(win) {
    return api("GET", "/api/chat/state" + (win ? "?win=" + encodeURIComponent(win) : "")).then(function (st) {
      clearChat();
      chat.win = st.agent.win || "";
      chat.windows = st.agent.windows || [];
      chat.lock = st.agent.lock || null;
      lockUpgrade();
      delete chat.unread[chat.win];
      st.history.forEach(showPart);
      (chat.quick[chat.win] || []).forEach(function (b) { $("messages").appendChild(b); });
      $("quick-switch").checked = quickOn();
      chatAgent(st.agent);
      chatBar(st.agent);
      chat.allowAll = !!st.agent.allow_all;
      chat.busy = st.agent.status && st.agent.status !== "idle";
      (st.agent.permissions || []).forEach(permissionCard);
      (st.agent.questions || []).forEach(questionCard);
      compactTurns();
      chatEnable();
      if (chat.source) chat.source.close();
      chat.source = new EventSource("/api/chat/events?after=" + st.seq + "&t=" + encodeURIComponent(token));
      chat.source.onmessage = function (m) { chatEvent(JSON.parse(m.data)); };
    }).catch(function (e) {
      if (win && e.status === 404) return chatLoad();  // that window was closed meanwhile
      throw e;
    });
  }

  function chatStart() {
    var a = state.agent;
    if (!a.program) { chatInfo(t("chat_no_program")); chatEnable(); return; }
    api("POST", "/api/chat/start", {}).then(function () { return chatLoad(); }).catch(function (e) { chatInfo(String(e.message)); });
  }

  function say(text, material) {
    if (!text.trim()) return;
    var body = { text: text, win: chat.win };
    if (material && material.length) body.material = material;
    if (chat.model) body.model = chat.model;
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
    if (name === "note") noteCard();
  }

  // Where a log is, with Copy path and what the log holds.
  function logWhere(box, label, path) {
    box.textContent = "";
    if (!path) return;
    box.appendChild(document.createTextNode(label + " "));
    box.appendChild(el("code", {}, path));
    var copy = el("button", { type: "button", "class": "quiet small" }, t("copy_path"));
    copy.addEventListener("click", function () { copyText(path, copy); });
    box.appendChild(copy);
    box.appendChild(el("span", { "class": "log-note" }, t("log_hint")));
  }

  // ---------- skills ----------
  // The skills OpenCode reads (GET /api/skills). Every skill can be changed (backed up first, then a
  // request is put in the box for the assistant) and restored from a backup; the knowledge-base skills
  // are only upgraded (install.upgrade). Skills can be imported or created. The request is never sent by itself.

  var skills = { list: [], folder: "" };

  function loadSkills() {
    return api("GET", "/api/skills").then(function (r) {
      skills.list = r.skills || [];
      skills.folder = r.folder || "";
      drawSkills();
    }).catch(function () {});
  }

  function fillInput(text) {
    $("input").value = text;
    $("input").focus();
    $("chat").scrollIntoView({ block: "nearest" });
  }

  function skillItem(sk) {
    var li = el("li", { "class": "skill" + (sk.kb ? " kb" : "") + (sk.used ? "" : " shadowed") });
    var head = el("div", { "class": "skill-head" });
    head.appendChild(el("strong", {}, sk.name));
    if (sk.version) head.appendChild(el("span", { "class": "badge" }, t("skill_version", { v: sk.version })));
    li.appendChild(head);
    var d = el("details", { "class": "skill-desc" });
    var end = /^[\s\S]*?[.。](?=\s|$)/.exec(sk.description);
    var first = end ? end[0] : sk.description;
    d.appendChild(el("summary", {}, first.length > 140 ? first.slice(0, 140) + "…" : first));
    d.appendChild(el("p", {}, sk.description));
    li.appendChild(d);
    if (sk.triggers && sk.triggers.length) {
      var tr = el("p", { "class": "skill-triggers" }, t("skill_triggers"));
      sk.triggers.slice(0, 4).forEach(function (q) { tr.appendChild(el("span", { "class": "trigger" }, q)); });
      li.appendChild(tr);
    }
    if (!sk.used) li.appendChild(el("p", { "class": "hint" }, t("skill_shadowed", { folder: sk.folder })));
    var row = el("div", { "class": "skill-actions" });
    function btn(label, cls, fn) {
      var b = el("button", { type: "button", "class": "small " + cls }, label);
      b.addEventListener("click", fn);
      row.appendChild(b);
    }
    if (sk.used && sk.triggers && sk.triggers.length) {
      btn(t("skill_try"), "quiet", function () { fillInput(t("try_req", { phrase: sk.triggers[0] })); });
    }
    // The knowledge-base skills are changed only by an upgrade, offered while this client's release is newer.
    if (sk.used && !sk.kb) {
      btn(t("skill_modify"), "quiet", function () { modifyCard(sk); });
      if (sk.backups) btn(t("skill_restore_btn"), "quiet", function () { startAction("skill_restore", sk.dir); });
    }
    if (sk.kb) {
      btn(t("skill_upgrade"), "quiet upgrade", function () {
        if (!window.confirm(t("skill_upgrade_hint"))) return;
        startAction("skill_upgrade");
      });
      if (sk.version && sk.release && compareVersions(sk.version, sk.release) >= 0) {
        var up = row.lastChild;
        up.disabled = true;
        up.classList.add("latest");  // setBusy leaves it off
        up.title = t("skill_latest", { v: sk.release });
      }
    }
    li.appendChild(row);
    return li;
  }

  // Dotted version numbers compared part by part as numbers (1.20.10 > 1.20.2); -1, 0 or 1.
  function compareVersions(a, b) {
    var x = String(a).split("."), y = String(b).split(".");
    for (var i = 0; i < Math.max(x.length, y.length); i++) {
      var p = parseInt(x[i] || "0", 10) || 0, q = parseInt(y[i] || "0", 10) || 0;
      if (p !== q) return p < q ? -1 : 1;
    }
    return 0;
  }

  function drawSkills() {
    var ul = $("skills");
    ul.textContent = "";
    var groups = [[t("skill_kb_group"), skills.list.filter(function (x) { return x.kb; })],
                  [t("skill_other_group"), skills.list.filter(function (x) { return !x.kb; })]];
    groups.forEach(function (g) {
      if (!g[1].length) return;
      ul.appendChild(el("li", { "class": "skill-group" }, g[0]));
      g[1].forEach(function (sk) { ul.appendChild(skillItem(sk)); });
    });
    show($("skills-empty"), skills.list.length === 0);
    setBusy(job !== null);
    drawSkillRows();
  }

  // The details under the knowledge-base skills chip: where each skill was found, which are missing,
  // and the folders looked in.
  function drawSkillPop() {
    var pop = $("skill-pop");
    var chip = $("kb-skills-chip");
    if (chip) chip.setAttribute("aria-expanded", pop.hidden ? "false" : "true");
    if (pop.hidden || !state) return;
    var ks = state.kb_skills || { ok: false, found: [], missing: [], checked: [] };
    pop.textContent = "";
    pop.appendChild(el("p", { "class": "pop-title" }, t("kb_skills_title")));
    var ul = el("ul");
    ks.found.forEach(function (x) {
      ul.appendChild(el("li", { "class": "good" }, "\u2713 " + t("kb_skills_found", { name: x.name, version: x.version || "?", folder: x.folder })));
    });
    ks.missing.forEach(function (name) { ul.appendChild(el("li", { "class": "bad" }, "! " + t("kb_skills_not_found", { name: name }))); });
    pop.appendChild(ul);
    pop.appendChild(el("p", { "class": "hint" }, t("kb_skills_checked")));
    var cl = el("ul", { "class": "hint" });
    ks.checked.forEach(function (f) { cl.appendChild(el("li", {}, f)); });
    pop.appendChild(cl);
    var row = el("div", { "class": "buttons" });
    if (!ks.ok) {
      var go = el("button", { type: "button", "class": "primary small" }, t("kb_skills_install"));
      go.disabled = job !== null;
      go.addEventListener("click", function () {
        show(pop, false);
        try { localStorage.setItem(kbKey(), "open"); } catch (e) { /* this view only */ }
        startAction("setup");
      });
      row.appendChild(go);
    }
    var close = el("button", { type: "button", "class": "quiet small" }, t("close"));
    close.addEventListener("click", function () { show(pop, false); drawSkillPop(); });
    row.appendChild(close);
    pop.appendChild(row);
  }

  function firstSentence(text) {
    var end = /^[\s\S]*?[.。](?=\s|$)/.exec(text || "");
    return end ? end[0] : text || "";
  }

  // The read-only list beside the conversation: one line per skill in use, opened for the whole description
  // and the phrases that start it. A filter appears past eight skills.
  function drawSkillRows() {
    var used = skills.list.filter(function (x) { return x.used; });
    var box = $("skills-filter");
    box.placeholder = t("skills_filter");
    box.setAttribute("aria-label", t("skills_filter"));
    show(box, used.length > 8);
    var q = used.length > 8 ? box.value.trim().toLowerCase() : "";
    var shown = used.filter(function (sk) {
      return !q || [sk.name, sk.description].concat(sk.triggers || []).join("\n").toLowerCase().indexOf(q) >= 0;
    });
    var ul = $("skill-rows");
    ul.textContent = "";
    [[t("skill_kb_group"), shown.filter(function (x) { return x.kb; })],
     [t("skill_other_group"), shown.filter(function (x) { return !x.kb; })]].forEach(function (g) {
      if (!g[1].length) return;
      ul.appendChild(el("li", { "class": "skill-group" }, g[0]));
      g[1].forEach(function (sk) {
        var li = el("li", { "class": "skill-row" + (sk.kb ? " kb" : "") });
        var d = el("details");
        var sum = el("summary");
        sum.appendChild(el("strong", { "class": "skill-name" }, sk.name));
        sum.appendChild(el("span", { "class": "skill-line", title: sk.description || "" }, firstSentence(sk.description)));
        d.appendChild(sum);
        d.appendChild(el("p", { "class": "skill-full" }, sk.description || ""));
        if (sk.triggers && sk.triggers.length) {
          var tr = el("p", { "class": "skill-triggers" }, t("skill_triggers"));
          sk.triggers.slice(0, 6).forEach(function (phrase) { tr.appendChild(el("span", { "class": "trigger" }, phrase)); });
          d.appendChild(tr);
        }
        li.appendChild(d);
        ul.appendChild(li);
      });
    });
    var empty = $("skill-rows-empty");
    empty.textContent = used.length ? t("skills_no_match") : t("skills_none_found");
    show(empty, shown.length === 0);
  }

  function modifyCard(sk) {
    var id = "modify-" + sk.dir;
    var c = card(id, t("modify_title", { name: sk.name }));
    c.appendChild(el("p", { "class": "hint" }, t("modify_tips")));
    c.appendChild(el("p", { "class": "card-label" }, t("modify_how")));
    ["triggers", "steps", "examples", "output", "other"].forEach(function (k, i) {
      var label = el("label", { "class": "choice" });
      var r = el("input", { type: "radio", name: id, value: k });
      if (i === 0) r.checked = true;
      label.appendChild(r);
      label.appendChild(el("span", {}, t("modify_" + k)));
      c.appendChild(label);
    });
    c.appendChild(el("p", { "class": "card-label" }, t("modify_detail")));
    var box = el("textarea", { rows: "3", spellcheck: "false" });
    c.appendChild(box);
    buttonRow(c, [[t("ok_cancel"), "quiet", function () { dropCard(id); }],
                  [t("modify_go"), "primary", function () {
                    var how = c.querySelector("input[name='" + id + "']:checked");
                    var detail = box.value.trim();
                    if (!detail) { box.focus(); return; }
                    dropCard(id);
                    startAction("skill_backup", sk.dir, function () {
                      fillInput(t("modify_req", { name: sk.name, folder: sk.folder,
                        how: t("modify_" + (how ? how.value : "other")), detail: detail }));
                    });
                  }]]);
    c.scrollIntoView({ block: "nearest" });
    box.focus();
  }

  function newSkill() {
    startAction("skill_new", null, function (log) {
      var m = /^skill: (\S+)$/m.exec(log);
      if (m) fillInput(t("new_req", { name: m[1], folder: skills.folder + "/" + m[1] }));
    });
  }

  // ---------- start ----------

  translate();
  $("check-toggle").addEventListener("click", foldChecklist);
  $("kb-toggle").addEventListener("click", toggleKb);
  $("lock-view").addEventListener("click", showLock);
  $("ingest-cli-copy").addEventListener("click", function () { copyText(cliCommand(), $("ingest-cli-copy")); });
  $("side-fold").addEventListener("click", function () { setSide(true); });
  $("side-strip").addEventListener("click", function () { setSide(false); });
  $("workdir-change").addEventListener("click", function () {
    openBrowser(chat.workdir || (state && state.home) || "", setWorkdir);
  });
  $("workdir-recent").addEventListener("change", function () {
    var v = $("workdir-recent").value;
    $("workdir-recent").value = "";
    setWorkdir(v);
  });
  $("model").addEventListener("change", function () { chat.model = $("model").value; });
  $("sessions").addEventListener("click", sessionsCard);
  $("skill-new").addEventListener("click", newSkill);
  $("skill-import").addEventListener("click", function () { startAction("skill_import"); });
  $("skills-filter").addEventListener("input", drawSkillRows);
  $("step-toggle").addEventListener("click", function () { foldStep(!$("log").hidden); });
  $("forget").addEventListener("click", function () {
    if (!window.confirm(t("forget_confirm"))) return;
    api("POST", "/api/chat/forget", {}).then(refresh).catch(function (e) { note(String(e.message), "error"); });
  });
  $("graph-close").addEventListener("click", closeGraph);
  $("health-close").addEventListener("click", function () { show($("health"), false); });
  $("ingest-close").addEventListener("click", function () { show($("ingest"), false); });
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
    if (!text.trim()) return;
    var q = quickQuery(text);
    if (q !== null) { $("input").value = ""; quick(text, q); return; }
    if (!chat.ready) return;
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
    api("POST", "/api/chat/stop", { win: chat.win }).catch(function () {});
  });
  $("chat-terminal").addEventListener("click", function () {
    if (!window.confirm(t("terminal_confirm"))) return;
    api("POST", "/api/chat/terminal", { win: chat.win }).then(function (r) {
      note(t("terminal_opened", { name: r.terminal }), "auto");
    }).catch(function (e) {
      note(e.status === 409 ? t(String(e.message).indexOf("terminal") >= 0 ? "terminal_none" : "terminal_no_session")
        : String(e.message), "error");
    });
  });
  $("chat-allow-all").addEventListener("click", function () { setAllowAll(!chat.allowAll); });
  $("chat-new").addEventListener("click", function () {
    api("POST", "/api/chat/new", { win: chat.win }).catch(function (e) { note(String(e.message), "error"); });
  });
  chatEnable();
  if (!token) { result("error", t("no_token")); return; }
  refresh().then(function () { if (state) { chatStart(); loadSkills(); loadIngest(); } });
  setInterval(function () { if (!job) refresh(); else api("GET", "/api/state").catch(function () {}); }, 20000);
})();
