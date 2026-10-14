# evergreen-wiki（常青知识库）

由 AI 助手持续维护的知识库：内容保持现行有效、每条结论都有来源、方便助手检索。三个 skill 管理一个 Markdown 文件夹，可以放在 Google Drive，也可以放在本地（可直接作为 Obsidian 库打开）。

| skill | 口令 | 作用 |
| --- | --- | --- |
| kb-note | 「记一下」 | 把对话中的零碎信息存为随手记，日后批量入库 |
| kb-incremental | 「增量整理」「整理随手记」「归档旧版」「体检」「新建知识库」 | 分区、查重、版本判定，每份材料只保留一个现行版本，事实变化时更新状态卡，定期体检 |
| kb-query | 直接提问 | 先在知识库检索再作答，注明依据文件，不凭记忆回答 |

入库前先把上传的 Word、Excel、PowerPoint、PDF 和邮件转换成 Markdown，助手读文本而不是二进制文件，省 token、更快。转换效果不好的文件（扫描件、几乎全是图片的文档）改读原件；一批材料图片较多时，由你决定是否读图。每个知识库在 `_kb.json` 里单独开关，新建的知识库默认打开。

文件夹里材料多时分批入库。助手先清点（各子目录的文件数、类型、大小、哪些已在库中），给出分批计划；你确认开始后，按子目录逐批处理，每批完成报一行进度，全部完成后一次性重写汇总文件，并列出需要你审阅的事项。进度保存在库里，可以在两批之间停下，以后新开对话说「继续入库」接着做。每批大小在 `_kb.json` 的 `intake` 里设置。

## 整体结构与下载

由四部分组成，都是放在你电脑或 Google Drive 里的普通文件：

- 技能（kb-note、kb-query、kb-incremental）：助手加载的说明和脚本，具体工作由它们完成。
- 知识库：一个 Markdown 文件夹，里面有配置（`_kb.json`）、规范、状态卡和文件索引。可以有多个，比如一个生活库、一个工作库。
- 注册表（`kb-libraries.json`）：登记你有哪些知识库，以及每个库的 id、名称、范围和位置。技能靠它决定每次请求用哪个库。
- 助手每次都会读的指令文件（CLAUDE.md、AGENTS.md、GEMINI.md 或项目指令）里的一行：告诉助手你有知识库，让它先查库，再凭记忆回答。

```text
你 --提问--> 助手 --读取--> 指令里的一行（「我有知识库：……」）
               |
               +-- 技能（kb-query、kb-note、kb-incremental）
                     +-- 注册表 kb-libraries.json：用哪个库、在哪里
                     +-- 知识库文件夹：Markdown 文件、状态卡、文件索引
                           （+ Sources/：已入库材料的原件副本，本地库开启时才有）
```

本地库可以把每份入库材料的原件复制一份保存在库里的原件文件夹（Sources，可改名），文件名与收录其正文的主题文件相同，并从主题文件链接过去（`_kb.json` 的 `sources.keep`；新建工作库默认开启，生活库默认关闭，因为原件不做打码）。入库时选的资料本身留在原处，不移动也不修改。

安装程序 `install.py` 负责把这些装好，以后还能备份、回滚、移动知识库和卸载。[tools/kb-client](tools/kb-client/README.zh-CN.md) 在浏览器页面里完成同样的步骤。[tools/doc2kb](tools/doc2kb/README.zh-CN.md) 是独立的文档转换器，在桌面或定时任务里把整个目录的文档增量转换成带索引的 Markdown。

### 下载哪个文件

[Releases](../../releases) 页面上每个版本都带这些文件：

| 文件 | 是什么 | 用途 |
| --- | --- | --- |
| `kb-note-<版本>.zip`、`kb-query-<版本>.zip`、`kb-incremental-<版本>.zip` | 每个一个技能，英文口令 | 上传到 claude.ai 或 Claude App |
| 同名但以 `-zh.zip` 结尾 | 同样的技能，中文口令 | 同上，中文用户用这三个 |
| `evergreen-wiki-v<版本>.zip` | 完整仓库：技能、带备份/回滚/移动/卸载命令的 `install.py`、tools/kb-client、tools/doc2kb、示例知识库和文档 | 没有 git 时给终端助手安装、电脑不能联网时安装，或在 Linux 桌面上用浏览器页面安装 |
| `doc2kb-v<版本>.zip` | 只有文档转换器 | 只想把文档目录转成 Markdown，不装技能 |

### 按情况选择

| 你的情况 | 怎么做 |
| --- | --- |
| 用 claude.ai 或 Claude App，知识库放 Google Drive | 上传三个带 -zh 的技能 zip，见[在 claude.ai 或 Claude App 里](#在-claudeai-或-claude-app-里google-drive) |
| 用 Claude Code | 插件或安装程序，见[在终端里](#在终端里claude-codecodexgemini-cliopencode) |
| 用 Codex、Gemini CLI、OpenCode 等支持 Agent Skills 的助手 | 安装程序，见[在终端里](#在终端里claude-codecodexgemini-cliopencode) |
| 电脑不能联网 | 把 `evergreen-wiki-v<版本>.zip` 拷过去，再用安装程序或桌面工具 |
| Linux 桌面，不用终端 | `evergreen-wiki-v<版本>.zip`，再用弹窗，见[在 Linux 桌面上](#在-linux-桌面上不用终端) |
| 只想把文档转成 Markdown | `doc2kb-v<版本>.zip`，见 [tools/doc2kb](tools/doc2kb/README.zh-CN.md) |
| 想先试试 | 虚构的[示例知识库](examples/) |

中文口令需要安装中文变体：claude.ai 上传 Releases 中带 -zh 的 zip；终端里运行 `python3 install.py`，第一题选中文即可。

## 快速上手

按你使用助手的地方选一条路径。每条路径都只问三个问题（建哪类库、放在哪里、收什么内容），写入前先给预览，确认后才写。

### 在终端里（Claude Code、Codex、Gemini CLI、OpenCode）

```bash
git clone https://github.com/walkwithedi/evergreen-wiki && cd evergreen-wiki
python3 install.py
```

安装向导会问语言和助手，装好三个技能，建一个本地知识库（可以是 Obsidian 库），登记到注册表，并在给你看过那一行之后，告诉助手你有这个知识库。重启助手后说「记一下：……」即可。

习惯用插件的 Claude Code 用户：`/plugin marketplace add walkwithedi/evergreen-wiki`，再 `/plugin install evergreen-wiki@evergreen-wiki`，重启后说「开始使用知识库」。

电脑不能联网时：在别处从 [Releases](../../releases) 下载 evergreen-wiki-v<版本>.zip，拷过去解压，在文件夹里运行 `python3 install.py`；只需要 Python 3.8 及以上，不用装别的。

以后在同一文件夹里还可以运行：`python3 install.py backup`（备份）、`rollback`（回滚）、`move <库 id> --to <文件夹>`（移动知识库）、`uninstall`（卸载）。替换技能、注册表或指令文件前会先自动备份；知识库文件夹从不进备份，移动时逐个文件核对一致后才改注册表，卸载时除非逐个勾选，否则一律保留。详见 [docs/manual-setup.zh-CN.md](docs/manual-setup.zh-CN.md#6-备份回滚移动卸载)。

### 在 Linux 桌面上（不用终端）

1. 从 [Releases](../../releases) 下载 `evergreen-wiki-v<版本>.zip` 并解压。
2. 在最上层文件夹里双击 `kb-client.desktop`（知识库）；第一次双击时选信任并启动。页面会在默认浏览器中打开。
3. 选「安装与建库」：选助手、装技能、建知识库，并告诉助手你有这个库。备份、回滚、移动知识库和卸载也在同一个页面上；页面会列出已登记的知识库，装好并配置了 OpenCode 时，还能在页面上直接和它对话。

需要 Python 3.8 及以上和一个浏览器。详见 [tools/kb-client](tools/kb-client/README.zh-CN.md)。

### 在 claude.ai 或 Claude App 里（Google Drive）

1. 从 [Releases](../../releases) 下载带 -zh 的 kb-note、kb-query、kb-incremental 三个 zip，在设置的 Skills 页面逐个上传。
2. 连接 Google Drive，为知识库新建一个空文件夹，并为知识库开一个项目（Project）。
3. 在项目里说「开始使用知识库」。助手会问三个问题，给出预览，把知识库写进那个文件夹，最后给你一行文字，粘贴进项目指令并保存，然后在项目里新开一个对话。这一行指向保存在 Drive 里的知识库清单，以后再加库不用再粘贴；整理好的材料在你确认预览后直接写进 Drive，不用自己下载上传。

可以先在虚构的[示例知识库](examples/)上试用。想逐步手动操作，或需要注册表格式，见 [docs/manual-setup.zh-CN.md](docs/manual-setup.zh-CN.md)。

方法论与设计理由见 [docs/methodology.md](docs/methodology.md)（英文）。许可证：MIT。
