# evergreen-wiki（常青知识库）

由 AI 助手持续维护的知识库：内容保持现行有效、每条结论都有来源、方便助手检索。三个 skill 管理一个 Markdown 文件夹，可以放在 Google Drive，也可以放在本地（可直接作为 Obsidian 库打开）。

| skill | 口令 | 作用 |
| --- | --- | --- |
| kb-note | 「记一下」 | 把对话中的零碎信息存为一份来源并抽出核对过的卡片，马上可查 |
| kb-ingest | 「入库」「加到知识库」「新建知识库」 | 把文档抽成卡片（一条结论附它依据的来源原句），由脚本逐句核对原句，归档来源和卡片，旧版移入归档，重建主题页；也负责新建知识库 |
| kb-query | 直接提问 | 先在知识库检索再作答，每条事实后附来源原句和链接，不凭记忆回答 |

## 为什么这样设计

助手直接在一堆文档里找答案，返回的是最匹配的那份，可能是过时的方案；它写的总结也可能和文档原意走样。evergreen-wiki 让每个回答都落在脚本在来源里找到过的一句原话上：

- **没有原句就没有卡片。** 库里每条结论都是一张卡片：结论、它依据的原句、指向来源那一段的链接。写入前由脚本逐句到来源里核对，改过字的原句一律拒绝。
- **回答引原句。** 回答里的每条事实后面都跟着来源原句和链接。弱档由脚本挑出回答能用的卡片，回复前再逐条核对引文。
- **名称即版本。** 同一份文件的新版本沿用旧名，旧版的来源和卡片移入归档；换了名字的新版本由脚本提出候选，经你确认。什么都不删除。
- **改动由你决定。** 新主题、新实体、新版本、新版本去掉或改变的结论，以及状态卡的每次改写，都先放进一个预览请你确认（也可以在浏览器客户端里用表单回答）。
- **弱档与强档。** 推理能力有限的模型（弱档，例如通过 OpenCode 运行的本地模型）把一切机械工作交给脚本：主题页由脚本生成，回答依据由脚本挑选。强模型（Claude、ChatGPT）自己撰写主题页和回答，由脚本核对每处引用。
- **没有代码环境不写库。** 写库需要 Python 跑核对脚本；没有时只读取和回答，什么都不写。

入库前先在本地把 Word、Excel、PowerPoint、PDF 和邮件转成批文件：纯文本，每份文档一个来源编号，每段带锚点，按知识库的档位切成合适的大小。一轮入库完成后，材料才能查到。

方法论见 [docs/methodology.zh-CN.md](docs/methodology.zh-CN.md)，设计与实现步骤见 [docs/design-2.0.md](docs/design-2.0.md)（英文）。

## 整体结构与下载

由四部分组成，都是放在你电脑或 Google Drive 里的普通文件：

- 技能（kb-note、kb-query、kb-ingest）：助手加载的说明和脚本，具体工作由它们完成。
- 知识库：一个 Markdown 文件夹，里面有配置（`_kb.json`）、规范和状态卡，以及来源、卡片、主题页各自的文件夹。可以有多个，比如每个团队或项目一个。
- 注册表（`kb-libraries.json`）：登记你有哪些知识库，以及每个库的 id、名称、范围和位置。技能靠它决定每次请求用哪个库。
- 助手每次都会读的指令文件（CLAUDE.md、AGENTS.md、GEMINI.md 或项目指令）里的一行：告诉助手你有知识库，让它先查库，再凭记忆回答。

```text
你 --提问--> 助手 --读取--> 指令里的一行（「我有知识库：……」）
               |
               +-- 技能（kb-query、kb-note、kb-ingest）
                     +-- 注册表 kb-libraries.json：用哪个库、在哪里
                     +-- 知识库文件夹：规范、状态卡、Sources/、Cards/、Topics/
```

入库时选的资料本身留在原处，不移动也不修改；库里保存的是转换后的文本（Sources/）。

安装程序 `install.py` 负责把这些装好，以后还能备份、回滚、移动知识库和卸载。[tools/kb-client](tools/kb-client/README.zh-CN.md) 在浏览器页面里完成同样的步骤。[tools/doc2kb](tools/doc2kb/README.zh-CN.md) 是独立的文档转换器，在桌面或定时任务里把整个目录的文档增量转换成带索引的 Markdown。

### 下载哪个文件

[Releases](../../releases) 页面上每个版本都带这些文件：

| 文件 | 是什么 | 用途 |
| --- | --- | --- |
| `kb-note-<版本>.zip`、`kb-query-<版本>.zip`、`kb-ingest-<版本>.zip` | 每个一个技能，英文口令 | 上传到 claude.ai 或 Claude App |
| 同名但以 `-zh.zip` 结尾 | 同样的技能，中文口令 | 同上，中文用户用这三个 |
| 同名但以 `-chatgpt.zip` 结尾 | 每个技能的提示词（`<技能>-prompt.md`，不超过 8000 字符）和文件包（`<技能>-files.zip`） | ChatGPT：提示词放进自定义 GPT 的指令，文件包作为知识文件上传；或者把三个技能的文件都上传到一个项目，在项目指令里写明提问、随手记、入库各按哪份提示词做。写库需要 Python 工具和该 Drive 文件夹的写权限 |
| `evergreen-wiki-v<版本>.zip` | 完整仓库：技能、带备份/回滚/移动/卸载命令的 `install.py`、tools/kb-client、tools/doc2kb、示例知识库和文档 | 没有 git 时给终端助手安装、电脑不能联网时安装，或在 Linux 桌面上用浏览器页面安装 |
| `doc2kb-v<版本>.zip` | 只有文档转换器 | 只想把文档目录转成 Markdown，不装技能 |

### 按情况选择

| 你的情况 | 怎么做 |
| --- | --- |
| 用 claude.ai 或 Claude App，知识库放 Google Drive | 上传三个带 -zh 的技能 zip，见[在 claude.ai 或 Claude App 里](#在-claudeai-或-claude-app-里google-drive) |
| 用 ChatGPT | 三个 `-chatgpt.zip`，见[在 ChatGPT 里](#在-chatgpt-里) |
| 用 Claude Code | 插件或安装程序，见[在终端里](#在终端里claude-codecodexgemini-cliopencode) |
| 用 Codex、Gemini CLI、OpenCode 等支持 Agent Skills 的助手 | 安装程序，见[在终端里](#在终端里claude-codecodexgemini-cliopencode) |
| 电脑不能联网 | 把 `evergreen-wiki-v<版本>.zip` 拷过去，再用安装程序或桌面工具 |
| Linux 桌面，不用终端 | `evergreen-wiki-v<版本>.zip`，再用弹窗，见[在 Linux 桌面上](#在-linux-桌面上不用终端) |
| 只想把文档转成 Markdown | `doc2kb-v<版本>.zip`，见 [tools/doc2kb](tools/doc2kb/README.zh-CN.md) |
| 想先试试 | 虚构的[示例知识库](examples/) |

中文口令需要安装中文变体：claude.ai 上传 Releases 中带 -zh 的 zip；终端里运行 `python3 install.py`，第一题选中文即可。

## 快速上手

按你使用助手的地方选一条路径。每条路径都只问两个问题（放在哪里、收什么内容），写入前先给预览，确认后才写。

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

1. 从 [Releases](../../releases) 下载带 -zh 的 kb-note、kb-query、kb-ingest 三个 zip，在设置的 Skills 页面逐个上传。
2. 连接 Google Drive，为知识库新建一个空文件夹，并为知识库开一个项目（Project）。
3. 在项目里说「开始使用知识库」。助手会问两个问题，给出预览，把知识库写进那个文件夹，最后给你一行文字，粘贴进项目指令并保存，然后在项目里新开一个对话。这一行指向保存在 Drive 里的知识库清单，以后再加库不用再粘贴；整理好的材料在你确认预览后直接写进 Drive，不用自己下载上传。

文档在你自己的电脑上转换：用 tools/doc2kb 或客户端的「生成批文件」做好批文件，在对话里上传并说「入库这些」。

### 在 ChatGPT 里

1. 从 [Releases](../../releases) 下载三个 `-chatgpt.zip` 并解压。
2. 每个技能建一个自定义 GPT（指令填 `<技能>-prompt.md`，知识文件上传 `<技能>-files.zip`）；或者把六个文件都上传到一个项目，在项目指令里写一句，例如：「提问按 kb-query-prompt.md，记录按 kb-note-prompt.md，入库按 kb-ingest-prompt.md。」
3. 打开 Python 工具。有 Drive 连接器就能读取和问答；写库还需要能写该 Drive 文件夹的工具，没有时什么都不写。

## 库的样子

```text
work-kb/
  _kb.json                 配置：语言、时区、档位、名称
  00_Spec.md               分区与主题、术语修正、文件夹名称、收录范围
  00_Status-Card.md        现行事实，每条链接到来源段落
  Sources/                 每份来源文档一个 Markdown 文件，段落带锚点 ^p1、^p2……
  Cards/                   每份来源一个卡片文件：结论、原句、链接、主题、日期
  Topics/                  每个主题一页，由卡片生成，新的在前
  Archive/                 来源和卡片的旧版本
  _pending/                入库等待你决定的事项（本地库；归档完成后删除）
```

所有名称都可以在 `_kb.json` 里改。随手记和其他来源一样，名为「随手记 <YYYYMMDD-HHMM> <短题>」。规范的表 E 是实体别名表；引用了已有新版本的来源的状态卡条目，会带待复核标记（⏳），核实后才去掉。

## 从 1.x 来

1.x 已冻结：最后一个版本 [v1.22.1](../../releases/tag/v1.22.1) 仍可下载，不再发布新的 1.x 版本。2.0 不迁移 1.x 知识库（schema 1），技能遇到时会说明并停下。可以继续用 1.x 版本，或者在空文件夹里新建 2.0 知识库，把材料重新入库。生活库及其预设只在 1.x 里有。

## 后端

| | Google Drive | 本地文件夹 |
| --- | --- | --- |
| 适用于 | 连了 Drive 连接器的 claude.ai 和 Claude App；装了 Drive MCP 服务的其他助手 | 能读写文件的任何助手（Claude Code、Codex、Gemini CLI、OpenCode、有文件权限的 Claude 桌面版） |
| 写入一次入库 | 脚本在暂存文件夹上运行，你确认预览后把改动的文件写回 Drive；旧文件先移进归档文件夹 | 你确认预览后，脚本直接写进文件夹 |
| 需要 | 代码环境，以及能写 Drive 的工具 | Python 3.8+ |
| Obsidian | 用 Google Drive 桌面版同步 | 把文件夹当作 vault 打开 |

详见 [docs/backends.md](docs/backends.md)（英文）。

## 兼容性

| 环境 | 状态 |
| --- | --- |
| Claude Code，本地后端 | 三个技能在示例知识库的副本上完整跑通：一次入库（强档，含一张被拒后重写的卡片、一个新主题、一个新实体、待定文件，以及一张 check-page 先拒后过的主题页）、一条随手记、两档提问（含 answer.py check），以及一个新版本把状态卡条目标为待复核，再经 status-check 更新 |
| claude.ai / Claude App，Drive 后端 | 通过暂存文件夹支持；尚未完整实测 |
| ChatGPT | 提示词版本已生成并经脚本检查；尚未完整实测 |
| Codex、Gemini CLI、OpenCode | 尚未验证，欢迎反馈 |

脚本需要 Python 3.8+，只用标准库。没有 Python 时技能可以查阅和回答，但不写任何内容。

## 工具

[tools/doc2kb](tools/doc2kb/README.zh-CN.md) 是独立的文档转换器：在 Linux 桌面对话框或定时任务里，把整个目录的 Office 文件、PDF 和邮件增量转换成一个带索引的 Markdown 知识库。每个版本都附带 `doc2kb-v<版本>.zip`。

[tools/kb-client](tools/kb-client/README.zh-CN.md) 在浏览器页面里运行安装程序及其备份、回滚、移动、卸载命令，页面由你自己的电脑提供，适合不用终端的人。它列出已登记的知识库和技能状态，能把一个文档文件夹生成批次文件，把入库等待的决定显示成表单（「待确认」，含待复核的状态卡条目），还能和 OpenCode 对话（入库、随手记、提问），权限请求在页面上回答。它随 evergreen-wiki 的 zip 一起提供。

可以先在虚构的[示例知识库](examples/)上试用。想逐步手动操作，或需要注册表格式，见 [docs/manual-setup.zh-CN.md](docs/manual-setup.zh-CN.md)。

许可证：MIT。
