# evergreen-wiki（常青知识库）

离线私有化知识库：在内网和信创环境（麒麟 + OpenCode）下，用 DeepSeek、Qwen 等私有部署的大模型维护文档知识库。三个 skill 管理一个 Markdown 文件夹（可直接作为 Obsidian 库打开）；凡是能按规则机械完成的步骤都交给脚本，所以能力一般的模型也够用。每个回答都附经脚本核对的原文出处，可溯源、不编造；只用 Python 标准库，不联网。

| skill | 口令 | 作用 |
| --- | --- | --- |
| kb-note | 「记一下」 | 把对话中的零碎信息存为一份来源并抽出核对过的卡片，马上可查 |
| kb-ingest | 「入库」「加到知识库」「新建知识库」 | 把文档抽成卡片（一条结论附它依据的来源原句），由脚本逐句核对原句，归档来源和卡片，旧版移入归档，重建主题页；也负责新建知识库 |
| kb-query | 直接提问 | 先在知识库检索再作答，每条事实后附来源原句和链接，不凭记忆回答 |

[English](README.md)

## 为什么这样设计

助手直接在一堆文档里找答案，返回的是最匹配的那份，可能是过时的方案；它写的总结也可能和文档原意走样。evergreen-wiki 让每个回答都落在脚本在来源里找到过的一句原话上：

- **离线可用。** 只用 Python 3.8 标准库、bash 和本机打开的网页；不联网，不装任何包。
- **没有原句就没有卡片。** 库里每条结论都是一张卡片：结论、它依据的原句、指向来源那一段的链接。写入前由脚本逐句到来源里核对，改过字的原句一律拒绝。
- **回答引原句。** 回答能用哪些卡片由脚本挑出；回答里的每条事实后面都跟着来源原句和链接，回复前由脚本逐条核对。
- **机械工作交给脚本。** 主题页由脚本根据卡片生成；新版本候选、实体合并和冲突清单都由脚本算出。模型只负责抽卡片和组织回复。
- **名称即版本。** 同一份文件的新版本沿用旧名，旧版的来源和卡片移入归档；换了名字的新版本由脚本提出候选，经你确认。什么都不删除。
- **改动由你决定。** 新主题、新实体、新版本、新版本去掉或改变的结论，以及状态卡的每次改写，都先放进一个预览请你确认，也可以在浏览器客户端里用表单回答。

文档入库前先在本机转换成批文件（Word、Excel、PowerPoint、PDF、邮件）：纯文本，每份文档一个来源编号，每段带锚点，每批最多 2 万字符。一次入库归档完成后，材料才能查到。

方法论见 [docs/methodology.zh-CN.md](docs/methodology.zh-CN.md)，本版本的设计见 [docs/design-3.0.md](docs/design-3.0.md)（英文）。

## 整体结构与下载

- skill（kb-note、kb-query、kb-ingest）：OpenCode 加载的说明和脚本，具体工作由它们完成。
- 知识库：一个 Markdown 文件夹，含设置（`_kb.json`）、规范、状态卡，以及放来源、卡片、主题页的子文件夹。可以建多个，例如每个团队或项目一个。
- 注册表（`~/.config/kb/kb-libraries.json`）：知识库清单，记每个库的 id、名称、范围和文件夹。skill 靠它为每次请求选库。
- OpenCode 的 `AGENTS.md` 里的一行：告诉助手你有知识库，让它先查库再凭记忆回答。

```text
你 --提问--> OpenCode --读取--> AGENTS.md 里的一行（「我有知识库：……」）
               |
               +-- skill（kb-query、kb-note、kb-ingest）
                     +-- 注册表 kb-libraries.json：用哪个库，在哪里
                     +-- 知识库文件夹：规范、状态卡、Sources/、Cards/、Topics/
```

入库时选的资料来源留在原处不动；知识库在 Sources/ 里保存转换后的文本。

每次发版，[Releases](../../releases) 页面附三个文件：

| 文件 | 用途 |
| --- | --- |
| `workbench-bundle-v<版本>.zip` | 工作站用：解压后双击最上层的入口，配置 OpenCode 的个人 AK，并打开知识库客户端 |
| `evergreen-wiki-v<版本>.zip` | 完整仓库：skill、`install.py`、tools/workbench、tools/opencode-setup、tools/kb-client、tools/doc2kb、示例知识库和文档（工作台发行包内容相同，只是最上层多一个入口） |
| `doc2kb-v<版本>.zip` | 只要文档转换器时用 |

## 快速开始

### 在工作站上（推荐）

1. 把 `workbench-bundle-v<版本>.zip` 拷到工作站上解压。
2. 双击最上层的 `启动OpenCode工作台.desktop`（第一次选信任）。浏览器页面按三步走：检查 Node、opencode 和 OpenCode 配置；粘贴个人 AK，测试通过才写入；打开工作台。
3. 在工作台里展开「知识库」，选「安装与建库」：把三个 skill 装到 OpenCode，问两个问题（知识库文件夹、收什么内容），给出预览，确认前什么都不写。
4. 入库在对话里提出（「入库」并写明文件或文件夹路径）；需要你决定的事项在「等待确认」里回答；直接在对话里提问。

详见 [tools/workbench](tools/workbench/README.zh-CN.md)、[tools/opencode-setup](tools/opencode-setup/README.zh-CN.md)、[tools/kb-client](tools/kb-client/README.zh-CN.md)。

### 在终端里

```bash
cd evergreen-wiki            # 解压后的仓库
python3 install.py
```

安装程序会问语言，把三个 skill 装到 OpenCode 的 skill 文件夹，新建并登记一个知识库，给你看过那一行后写进 OpenCode 的 AGENTS.md。重启 OpenCode，说「记一下：……」。

以后在同一个文件夹里：`python3 install.py backup`、`rollback`、`move <知识库 id> --to <文件夹>`、`uninstall`。替换 skill、注册表或指令文件前都会先备份；知识库文件夹从不放进备份，移动时所有文件复制核对无误后才改注册表，卸载时除非你逐个选中，否则保留知识库。详见 [docs/manual-setup.zh-CN.md](docs/manual-setup.zh-CN.md)。

可以先在虚构的[示例知识库](examples/)上试一遍。想逐步手工安装或查看注册表格式，见 [docs/manual-setup.zh-CN.md](docs/manual-setup.zh-CN.md)。

## 知识库的样子

```text
work-kb/
  _kb.json                 设置：语言、时区、批大小、名称
  00_Spec.md               分区与主题、术语修正、文件夹名称、收录范围
  00_Status-Card.md        当前有效的事实，每条链接到来源段落
  Sources/<文件夹>/        每份来源文档一个 Markdown 文件，放在它原来所在的文件夹里，段落带锚点 ^p1、^p2……
  Cards/<文件夹>/          每份来源一个卡片文件：结论、原句、链接、主题、日期
  Topics/                  每个主题一页，由卡片生成，新的在前；更早年份各有一页
  Archive/                 来源和卡片的旧版本，文件夹结构相同
  _index/                  脚本维护的检索索引，由文件生成，可以删除
  _pending/                入库等你决定的事项（归档完成后删除）
```

所有名称都可以在 `_kb.json` 里改。随手记和其他来源一样（「随手记 <YYYYMMDD-HHMM> <标题>」）。规范的表 E 是实体别名表；状态卡里引用了出新版本的来源的条目，会带上待复核标记（⏳），核对后才去掉。

## 从旧版本来

- main 上的新版本（将作为 4.0 发布）：知识库把每份来源放在它原来所在的文件夹里（schema 3）。2.0、3.0 建的知识库（schema 2，来源都在一个文件夹里）不读取、不迁移；可以继续用 [v3.0.0](../../releases/tag/v3.0.0)，或者新建知识库，把材料重新入库。
- 2.0.x：2.0 建的本地知识库在 3.0 里原样可用；其中的 `tier`（档位）设置会被读入并忽略，主题页一律由脚本生成。Google Drive 上的知识库和 ChatGPT 版 skill 请继续用 [v2.0.0](../../releases/tag/v2.0.0)，它不再更新。
- 1.x：schema 1 的知识库不迁移，skill 遇到时会说明并停下。可以继续用 [v1.22.1](../../releases/tag/v1.22.1)，或者在空文件夹里新建知识库，把材料重新入库。

## 兼容性

| 环境 | 状态 |
| --- | --- |
| 麒麟，OpenCode 加私有部署模型 | 支持的环境。脚本、安装程序、工作台和 kb-client 在 CI 中用 Python 3.8 测试（在 Ubuntu 上代替麒麟），OpenCode 和模型接口用假接口；发版前在工作站上做一次端到端实测 |
| 其他从 `~/.agents/skills` 或 `~/.claude/skills` 读取 Agent Skills 的助手 | 可能可用，未测试 |

脚本需要 Python 3.8 及以上，只用标准库。没有 Python 时 skill 可以查阅和回答，但不写任何内容。

## 工具

- [tools/workbench](tools/workbench/README.zh-CN.md)：工作站上的三步向导（环境检查、填 AK 并自检、打开工作台），发行包的入口启动的就是它。
- [tools/opencode-setup](tools/opencode-setup/README.zh-CN.md)：只输入个人 AK 就配好 OpenCode，关闭它启动时的联网下载并做首次启动自检，有网页和终端菜单两种用法。
- [tools/kb-client](tools/kb-client/README.zh-CN.md)：在浏览器里用的知识库客户端，由本机提供页面：在选定的工作文件夹里和 OpenCode 对话，查看知识库和技能，安装与建库、备份、回滚、移动、卸载，等待确认。
- [tools/doc2kb](tools/doc2kb/README.zh-CN.md)：独立的文档转换器，可在桌面对话框或定时任务里增量转换。每次发版另附 `doc2kb-v<版本>.zip`。

## 开发

```bash
git config core.hooksPath .githooks       # 每个克隆执行一次：每次提交前跑全部检查
python3 scripts/run_checks.py             # 一次跑完下面所有检查
python3 -m unittest discover -s tests     # 脚本测试
python3 scripts/check_repo.py             # skill 一致性
python3 scripts/sync_shared.py            # 改了 shared/ 后复制到各 skill 和工具
python3 scripts/sensitive_scan.py         # 个人信息检查
```

见 [CONTRIBUTING.md](CONTRIBUTING.md)。许可证：[MIT](LICENSE)。
