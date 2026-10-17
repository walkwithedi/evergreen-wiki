# 手动配置

[快速开始](../README.zh-CN.md#快速开始) 会替你完成下面所有步骤：在工作站上用工作台，在终端运行 `python3 install.py`，或在 OpenCode 里说「开始使用知识库」。本页适用于想逐步手动操作、以后追加知识库，或想了解引导程序写了什么的情况。

[English](manual-setup.md)

## 1. 安装技能

`python3 install.py --target opencode --locale zh` 把三个技能复制到 `~/.config/opencode/skills`（也可用 `--target agents` 装到 `~/.agents/skills`、`--target claude-code` 装到 `~/.claude/skills`，OpenCode 也读这两处；或用 `--dest <文件夹>`）。`--descriptions <文件>` 用自己的技能描述（每个技能一行，格式同 `locales/zh/descriptions.json`），`--force` 替换已安装的版本，`--dry-run` 只预览。

安装向导（`python3 install.py`）可用 `--agent <目标>` 免答这一题，也可用 `--descriptions`。向导里选到已有知识库的文件夹（`_kb.json` 的 schema 为 2）时，先给预览，再按原样登记，不改动任何文件。1.x 知识库（schema 1）会被拒绝：可以继续用 1.x 版本，或在空文件夹里新建知识库，把材料重新入库。

## 2. 建库

对 OpenCode 说「新建知识库」。它会问两个问题：知识库文件夹放在哪里、库里收什么内容；语言、时区等自动推断。之后给出完整预览，确认后才写入。中文库的标题与文件名长度阈值自动取 55/80。

在终端里也可以直接用技能所用的同一个脚本：

```bash
python3 skills/kb-ingest/scripts/init_library.py plan  --root ~/kb/atlas --preset work --language zh
python3 skills/kb-ingest/scripts/init_library.py write --root ~/kb/atlas --preset work --language zh --scope "Atlas 项目的计划、会议纪要和报告"
```

文件夹里已有 Markdown 文件或 `_kb.json` 时脚本会拒绝写入。

## 3. 登记

注册表是一个小 JSON 文件，列出每个库及其范围，格式见[英文版](manual-setup.md#3-register-your-libraries)。放在 `~/.config/kb/kb-libraries.json`，或用环境变量 `KB_LIBRARIES` 指定。`init_library.py register --id ... --label ... --scope ... --root ...` 可追加条目，id 或文件夹重复时会拒绝。类型为 gdrive 的条目会被拒绝：Google Drive 上的库由 2.0.x 版本读取。

范围（scope）很重要：助手靠它判断一条记录或一个问题属于哪个库。每个库写一句话，各库范围不要重叠。

## 4. 告诉 OpenCode 你有知识库

在 `~/.config/opencode/AGENTS.md`（或某个项目的 AGENTS.md）里加一行：

```text
我有知识库：Atlas 项目（Atlas 项目的计划、会议纪要和报告）；工作（工作目标与计划、项目与事务、会议与决策、制度流程、报表等工作资料）。相关问题先用 kb-query 查知识库，再查代码或凭记忆回答；要记录用 kb-note；要入库用 kb-ingest。
```

不加的话，听起来不像私人事务的问题（如「支付接口限流是多少」）可能会被当作代码或常识问题直接回答。`init_library.py instructions --registry <注册表> --file <文件> --apply` 会按注册表写入或更新这一行，文件其余内容不动。OpenCode 没有 AGENTS.md 时会读 `~/.claude/CLAUDE.md`；知识库客户端会把这一行写到 OpenCode 实际会读的那个文件里。

## 5. 使用

说「记一下」、写明文件或文件夹路径说「入库」，或直接提问。

## 6. 备份、回滚、移动、卸载

在 evergreen-wiki 文件夹里运行。每个命令都先列出要做的事，问过你才改动；加 `--lang zh` 显示中文提示。

- `python3 install.py backup [--note 说明]`：备份已安装的技能、所有含知识库说明行的指令文件、注册表和安装记录。安装程序在替换技能、往注册表加库或写入说明行之前也会自动备份一次。
- `python3 install.py rollback [--id 编号]`：恢复一次备份。恢复前先把现状再备份一次，所以回滚本身也能撤销。
- `python3 install.py move <库 id> --to <文件夹>`：把一个已登记的本机知识库移到该文件夹下，库文件夹名不变。只搬知识库本身，放原始文件的文件夹留在原处：入库时资料从哪里选都可以。先复制，再逐个文件比对大小和 SHA-256（空文件夹和符号链接也比对），全部一致才把注册表改到新位置；不一致时清掉复制出的内容，其余都不动。以下情况拒绝移动：新位置在库里面、不是空文件夹或已登记为别的库；磁盘空间不够。最后才问是否删除原文件夹，默认保留，要输入「删除」才删，删除前再比对一次。移动前请退出 OpenCode，移动后重开；Obsidian 里改为打开新位置。
- `python3 install.py uninstall`：从安装用过的每个文件夹删除三个技能，删去指令文件里的知识库说明行（其余内容不动，删空的文件一并删除），删除注册表（其中登记的全部库）以及安装记录和全部备份。知识库文件夹默认保留：要删时先选「是」，再逐个确认（默认否），最后输入「删除」。只有含 `_kb.json` 或 `00_` 开头规范文件的文件夹才会列出；符号链接、根目录、家目录及其上级、包含本程序或助手设置的文件夹从不列出。

安装记录和备份存放在 `~/.config/evergreen-wiki/`（可用 `XDG_CONFIG_HOME` 改位置）。知识库文件夹从不进备份：移动之后再回滚到移动前的备份，只恢复注册表登记，所以只在原文件夹还在时才这样回滚。
