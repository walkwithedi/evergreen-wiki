## Which file to download / 下载哪个文件

| File | Use it for |
| --- | --- |
| `kb-note-<version>.zip`, `kb-query-<version>.zip`, `kb-incremental-<version>.zip` | claude.ai or the Claude apps: upload each in Settings > Capabilities > Skills. 在 claude.ai 或 Claude App 的设置里逐个上传。 |
| the same ending in `-zh.zip` | the same with Chinese trigger phrases. 中文口令版，中文用户上传这三个。 |
| `evergreen-wiki-v<version>.zip` | everything: skills, `install.py` (setup, backup, rollback, move, uninstall), tools/desktop-setup (Linux desktop dialogs), tools/kb-client (the same steps in the browser; double-click kb-client.desktop at the top of the folder), tools/doc2kb, sample library, docs. For terminal agents without git, computers without network, or the desktop tool. 完整包：没有 git、电脑不能联网或用 Linux 桌面弹窗、浏览器页面安装时用这个（双击最上层的 kb-client.desktop 打开页面）。 |
| `doc2kb-v<version>.zip` | the document converter alone. 只要文档转换器时用。 |

How the pieces fit and which path to take: [README](https://github.com/walkwithedi/evergreen-wiki#how-it-fits-together) / [中文说明](https://github.com/walkwithedi/evergreen-wiki/blob/main/README.zh-CN.md#整体结构与下载).
