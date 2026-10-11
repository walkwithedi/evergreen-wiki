# evergreen-wiki（常青知识库）

由 AI 助手持续维护的知识库：内容保持现行有效、每条结论都有来源、方便助手检索。三个 skill 管理一个 Markdown 文件夹，可以放在 Google Drive，也可以放在本地（可直接作为 Obsidian 库打开）。

| skill | 口令 | 作用 |
| --- | --- | --- |
| kb-note | 「记一下」 | 把对话中的零碎信息存为随手记，日后批量入库 |
| kb-incremental | 「增量整理」「整理随手记」「归档旧版」「体检」「新建知识库」 | 分区、查重、版本判定，每份材料只保留一个现行版本，事实变化时更新状态卡，定期体检 |
| kb-query | 直接提问 | 先在知识库检索再作答，注明依据文件，不凭记忆回答 |

中文口令需要安装中文变体：claude.ai 上传 Releases 中带 -zh 的 zip；其他环境用 `python3 install.py --target <目标> --locale zh`。

## 快速上手

1. 安装：Claude Code 用 `/plugin marketplace add walkwithedi/evergreen-wiki`；claude.ai 在设置的 Skills 页面上传 zip；Codex、Gemini CLI、OpenCode 等运行 `python3 install.py --target agents`。
2. 建库：对助手说「新建知识库」，按提问选择位置（Drive 文件夹或本地文件夹）、预设（工作库或生活库）、语言与时区，确认预览后写入。中文库的标题与文件名长度阈值自动取 55/80。
3. 登记：把各库写进注册表 `~/.config/kb/kb-libraries.json`（格式见英文 README）；claude.ai 可粘贴到项目指令，或用 `python3 scripts/build_skill.py --config 我的注册表.json --locale zh` 打私人 zip（不要公开）。
4. 告诉助手你有知识库（初始化时会主动提议）：在助手每次都会读的指令里（CLAUDE.md、AGENTS.md、GEMINI.md 或 claude.ai 项目指令）加一句，列出各库及其范围，并写明「相关问题先用 kb-query 查，记录用 kb-note」。不加的话，听起来不像私人事务的问题（如「支付接口限流是多少」）可能会被当作代码或常识问题直接回答。
5. 使用：说「记一下」、上传材料说「增量整理」，或直接提问。

已有中文知识库的，在 `_kb.json` 的 names 里写上库内实际的中文文件名与文件夹名（如 00_当前有效状态卡.md、归档、随手记、_旧），无须改名迁移。

方法论与设计理由见 [docs/methodology.md](docs/methodology.md)（英文）。许可证：MIT。
