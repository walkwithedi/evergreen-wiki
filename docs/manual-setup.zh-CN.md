# 手动配置

[快速上手](../README.zh-CN.md#快速上手) 会替你完成下面所有步骤：在终端运行 `python3 install.py`，或在助手里说「开始使用知识库」。本页适用于想逐步手动操作、以后追加知识库，或想了解引导程序写了什么的情况。

[English](manual-setup.md)

## 1. 安装技能

- Claude Code：`/plugin marketplace add walkwithedi/evergreen-wiki`，然后 `/plugin install evergreen-wiki@evergreen-wiki`。
- claude.ai 或 Claude App：从 [Releases](../../../releases) 下载带 -zh 的 kb-note、kb-query、kb-incremental 三个 zip，在设置的 Skills 页面逐个上传。
- 其他支持 Agent Skills 的助手：`python3 install.py --target agents --locale zh`（也可用 `--target gemini`、`opencode`、`codex`、`claude-code` 或 `--dest <文件夹>`）；`--force` 替换已安装的版本，`--dry-run` 只预览。

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

claude.ai 上把注册表粘贴进项目指令即可，也可以用 `python3 scripts/build_skill.py --config 我的注册表.json --locale zh` 打私人 zip（不要公开）。

范围（scope）很重要：助手靠它判断一条记录或一个问题属于哪个库。每个库写一句话，各库范围不要重叠。

## 4. 告诉助手你有知识库

在助手每次都会读的指令里（CLAUDE.md、AGENTS.md、GEMINI.md 或 claude.ai 项目指令）加一行：

```text
我有知识库：生活（我和家人：证件、健康、保险、财务、住房）；工作（团队项目、决策、负责人、规范）。相关问题先用 kb-query 查知识库，再查代码或凭记忆回答；要记录用 kb-note。
```

不加的话，听起来不像私人事务的问题（如「支付接口限流是多少」）可能会被当作代码或常识问题直接回答。`init_library.py instructions --file <文件> --apply` 会按注册表写入或更新这一行，文件其余内容不动。各助手对应的文件见[英文版](manual-setup.md#4-tell-your-assistant-the-libraries-exist)的表格。

## 5. 使用

说「记一下」、上传材料说「增量整理」，或直接提问。
