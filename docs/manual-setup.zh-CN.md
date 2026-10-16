# 手动配置

[快速上手](../README.zh-CN.md#快速上手) 会替你完成下面所有步骤：在终端运行 `python3 install.py`，或在助手里说「开始使用知识库」。本页适用于想逐步手动操作、以后追加知识库，或想了解引导程序写了什么的情况。

[English](manual-setup.md)

## 1. 安装技能

- Claude Code：`/plugin marketplace add walkwithedi/evergreen-wiki`，然后 `/plugin install evergreen-wiki@evergreen-wiki`。
- claude.ai 或 Claude App：从 [Releases](../../../releases) 下载带 -zh 的 kb-note、kb-query、kb-incremental 三个 zip，在设置的 Skills 页面逐个上传。
- 其他支持 Agent Skills 的助手：`python3 install.py --target agents --locale zh`（也可用 `--target gemini`、`opencode`、`codex`、`claude-code` 或 `--dest <文件夹>`）；`--descriptions <文件>` 用自己的技能描述（每个技能一行，格式同 `locales/zh/descriptions.json`），`--force` 替换已安装的版本，`--dry-run` 只预览。安装向导（`python3 install.py`）可用 `--agent <目标>` 和 `--preset life|work` 免答这两题，也可用 `--descriptions`。向导里选到已有知识库的文件夹（含 `_kb.json` 或 `00_` 开头的规范文件）时，先给预览，再按原样登记，不改动任何文件；之后对助手说「初始化 <库名>」，由助手按库内规范补齐配置。

## 2. 建库

对助手说「新建知识库」。它会问三个问题：放在哪里（Drive 文件夹或本地文件夹）、用哪个预设（工作或生活）、库里收什么内容；语言、时区等自动推断。之后给出完整预览，确认后才写入。中文库的标题与文件名长度阈值自动取 55/80。

在终端里也可以直接用技能所用的同一个脚本：

```bash
python3 skills/kb-incremental/scripts/init_library.py plan  --root ~/kb/life --preset life --language zh
python3 skills/kb-incremental/scripts/init_library.py write --root ~/kb/life --preset life --language zh --scope "我和家人：证件、健康、保险、财务、住房"
```

文件夹里已有 Markdown 文件时脚本会拒绝写入；已有的知识库请对助手说「初始化」并指明该库，走已有库分支，不会覆盖任何文件。

已有中文知识库的，在 `_kb.json` 的 names 里写上库内实际的中文文件名与文件夹名（如 00_当前有效状态卡.md、归档、随手记、_旧），无须改名迁移。

## 3. 登记

注册表是一个小 JSON 文件，列出每个库及其范围，格式见[英文版](manual-setup.md#3-register-your-libraries)。放在 `~/.config/kb/kb-libraries.json`（Windows 为 `%APPDATA%\kb\kb-libraries.json`，或用环境变量 `KB_LIBRARIES` 指定）。`init_library.py register --id ... --label ... --scope ... --type local|gdrive --root ...` 可追加条目，id 或文件夹重复时会拒绝。

claude.ai 上由首次引导把注册表存进 Drive（第一个库文件夹里的 kb-libraries.json），项目指令里只需一行含 `registry: Google Drive folder <文件夹 ID>, file kb-libraries.json` 的话；也可以把整段 JSON 粘贴进项目指令，或者用 `python3 scripts/build_skill.py --config 我的注册表.json --locale zh` 打私人 zip（不要公开）。

范围（scope）很重要：助手靠它判断一条记录或一个问题属于哪个库。每个库写一句话，各库范围不要重叠。

## 4. 告诉助手你有知识库

在助手每次都会读的指令里（CLAUDE.md、AGENTS.md、GEMINI.md 或 claude.ai 项目指令）加一行：

```text
我有知识库：生活（我和家人：证件、健康、保险、财务、住房）；工作（工作目标与计划、项目与事务、会议与决策、制度流程、报表等工作资料）。相关问题先用 kb-query 查知识库，再查代码或凭记忆回答；要记录用 kb-note。新对话开始时，如知识库有未完成的分批入库，先提醒是否继续。
```

不加的话，听起来不像私人事务的问题（如「支付接口限流是多少」）可能会被当作代码或常识问题直接回答。`init_library.py instructions --file <文件> --apply` 会按注册表写入或更新这一行，文件其余内容不动。各助手对应的文件见[英文版](manual-setup.md#4-tell-your-assistant-the-libraries-exist)的表格。

## 5. 使用

说「记一下」、上传材料说「增量整理」，或直接提问。

## 6. 备份、回滚、移动、卸载

在 evergreen-wiki 文件夹里运行。每个命令都先列出要做的事，问过你才改动；加 `--lang zh` 显示中文提示。

- `python3 install.py backup [--note 说明]`：备份已安装的技能、所有含知识库说明行的指令文件、注册表和安装记录。安装程序在替换技能、往注册表加库或写入说明行之前也会自动备份一次。
- `python3 install.py rollback [--id 编号]`：恢复一次备份。恢复前先把现状再备份一次，所以回滚本身也能撤销。
- `python3 install.py move <库 id> --to <文件夹>`：把一个已登记的本机知识库移到该文件夹下，库文件夹名不变。只搬知识库本身，放原始文件的文件夹留在原处：入库时资料从哪里选都可以。先复制，再逐个文件比对大小和 SHA-256（空文件夹和符号链接也比对），全部一致才把注册表改到新位置；不一致时清掉复制出的内容，其余都不动。以下情况拒绝移动：分批入库没做完；新位置在库里面、不是空文件夹或已登记为别的库；磁盘空间不够。最后才问是否删除原文件夹，默认保留，要输入「删除」才删，删除前再比对一次。移动前请退出助手，移动后重开；Obsidian 里改为打开新位置。
- `python3 install.py uninstall`：从安装用过的每个文件夹删除三个技能，删去指令文件里的知识库说明行（其余内容不动，删空的文件一并删除），删除注册表（其中登记的全部库）以及安装记录和全部备份。知识库文件夹默认保留：要删时先选「是」，再逐个确认（默认否），最后输入「删除」。保留下来的库里，浏览器客户端的运行状态（`_Runtime` 文件夹：自动入库开关、入库进度）默认一并删除，回答「否」则保留；知识文件一律不动。只有含 `_kb.json` 或 `00_` 开头规范文件的文件夹才会列出；符号链接、根目录、家目录及其上级、包含本程序或助手设置的文件夹从不列出。插件方式安装的用 `/plugin` 卸载。

安装记录和备份存放在 `~/.config/evergreen-wiki/`（Windows 为 `%APPDATA%\evergreen-wiki`；可用 `XDG_CONFIG_HOME` 改位置）。知识库文件夹从不进备份：移动之后再回滚到移动前的备份，只恢复注册表登记，所以只在原文件夹还在时才这样回滚。
