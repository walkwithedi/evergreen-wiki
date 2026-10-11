# evergreen-wiki（常青知识库）

由 AI 助手持续维护的知识库：内容保持现行有效、每条结论都有来源、方便助手检索。三个 skill 管理一个 Markdown 文件夹，可以放在 Google Drive，也可以放在本地（可直接作为 Obsidian 库打开）。

| skill | 口令 | 作用 |
| --- | --- | --- |
| kb-note | 「记一下」 | 把对话中的零碎信息存为随手记，日后批量入库 |
| kb-incremental | 「增量整理」「整理随手记」「归档旧版」「体检」「新建知识库」 | 分区、查重、版本判定，每份材料只保留一个现行版本，事实变化时更新状态卡，定期体检 |
| kb-query | 直接提问 | 先在知识库检索再作答，注明依据文件，不凭记忆回答 |

中文口令需要安装中文变体：claude.ai 上传 Releases 中带 -zh 的 zip；终端里运行 `python3 install.py`，第一题选中文即可。

## 快速上手

按你使用助手的地方选一条路径。两条路径都只问三个问题（建哪类库、放在哪里、收什么内容），写入前先给预览，确认后才写。

### 在终端里（Claude Code、Codex、Gemini CLI、OpenCode）

```bash
git clone https://github.com/walkwithedi/evergreen-wiki && cd evergreen-wiki
python3 install.py
```

安装向导会问语言和助手，装好三个技能，建一个本地知识库（可以是 Obsidian 库），登记到注册表，并在给你看过那一行之后，告诉助手你有这个知识库。重启助手后说「记一下：……」即可。

习惯用插件的 Claude Code 用户：`/plugin marketplace add walkwithedi/evergreen-wiki`，再 `/plugin install evergreen-wiki@evergreen-wiki`，重启后说「开始使用知识库」。

### 在 claude.ai 或 Claude App 里（Google Drive）

1. 从 [Releases](../../releases) 下载带 -zh 的 kb-note、kb-query、kb-incremental 三个 zip，在设置的 Skills 页面逐个上传。
2. 连接 Google Drive，为知识库新建一个空文件夹，并为知识库开一个项目（Project）。
3. 在项目里说「开始使用知识库」。助手会问三个问题，给出预览，把知识库写进那个文件夹，最后给你一行文字，粘贴进项目指令并保存，然后在项目里新开一个对话。这一行指向保存在 Drive 里的知识库清单，以后再加库不用再粘贴；整理好的材料在你确认预览后直接写进 Drive，不用自己下载上传。

可以先在虚构的[示例知识库](examples/)上试用。想逐步手动操作，或需要注册表格式，见 [docs/manual-setup.zh-CN.md](docs/manual-setup.zh-CN.md)。

方法论与设计理由见 [docs/methodology.md](docs/methodology.md)（英文）。许可证：MIT。
