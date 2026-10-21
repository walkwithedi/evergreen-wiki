# opencode-setup：OpenCode 配置

[English](README.md)

在麒麟工作站上只输入个人 AK 就能用上 OpenCode：把 AK 替换进本机已有的 OpenCode 配置，先发一条测试请求，通过才写入；再关闭 opencode 启动时的联网下载，并做一次首次启动自检。写入前自动备份，随时可以回滚。

接口地址、模型等其他设置取自本机已有的配置，本工具不保存、不生成这些内容，只替换配置里的 AK。

双击启动入口，在浏览器页面里点几下就能配好；习惯终端的也可以用交互菜单，两者行为一致。[工作台向导](../workbench/README.zh-CN.md)的第 1、2 步就是这个页面。

## 目录内容

| 文件 | 说明 |
| --- | --- |
| `启动OpenCode配置.desktop` | 双击入口：打开一个终端窗口运行 `ca_web.py`，并在默认浏览器中打开配置页面。 |
| `ca_web.py` | 本地服务：提供配置页面，页面上的每个按钮以子进程运行 `codeagent-setup.sh` 的对应子命令，输出逐行显示在页面上。只用 Python 3 标准库。 |
| `web/` | 配置页面（`index.html`、`app.js`、`style.css`），纯本地 HTML、JavaScript 和 CSS，不从网络加载任何内容。 |
| `codeagent-setup.sh` | 主脚本，全部配置逻辑在这里。不带参数运行进入终端交互菜单；也可以带子命令直接执行某一步。 |
| `ca_config.py` | 辅助脚本，由主脚本调用：读带注释的 JSON 配置、原位替换 AK、发送测试请求。只用 Python 3 标准库。 |

## 运行环境要求

- 麒麟，bash 4.4 及以上、python3（系统自带即可，不需要安装第三方包）。
- Node 主版本 22 及以上。版本不对时脚本会提示切换。
- 已安装 opencode。没装也能替换 AK，只是无法做首次启动自检。
- 本机已有 OpenCode 配置：`~/.config/opencode/opencode.jsonc`（或 `opencode.json`），其中服务商的 `options` 里有 `baseURL` 和 `apiKey`（`apiKey` 可先填任意占位），并列出模型。没有配置时一键配置直接提示并退出，不写任何文件。
- 本机能访问模型接口。设置了代理的，内网接口地址需要加进 `no_proxy`。

## 本机提示

两处提示可以换成本机的说法：去哪里申请 AK，以及怎样切换 Node 版本。在 `~/.config/opencode-setup/hints.conf`（或环境变量 `CA_HINTS` 指定的文件）里每行写一项：

```
AK_HINT=个人 AK 在模型服务的个人设置页面查看
NODE_HINT=打开软件中心切换 Node 版本
```

`#` 开头的行是注释，其他键忽略。脚本只读取这个文件，不执行其中的内容；文件不随工具分发。终端菜单和浏览器页面显示同样的提示，没有这个文件时用通用说法。

## 第一次启动要求输入用户名和密码

原因：opencode 启动时会检查自动更新、安装默认插件、拉取在线模型清单、下载语言服务器，还会检查配置目录 `~/.config/opencode` 下的插件依赖 `@opencode-ai/plugin`。这些动作在内网里可能要求账号，新机器第一次启动时就会出现用户名和密码提示。

脚本分两步处理：

1. 关闭联网动作：一键配置时在 `~/.bashrc` 末尾写入一段带标记的设置，新开的终端里 opencode 启动时不再做这些下载：

   ```
   # >>> codeagent-setup：opencode 启动时不联网下载 >>>
   export OPENCODE_DISABLE_AUTOUPDATE=1
   export OPENCODE_DISABLE_DEFAULT_PLUGINS=1
   export OPENCODE_DISABLE_MODELS_FETCH=1
   export OPENCODE_DISABLE_LSP_DOWNLOAD=1
   # <<< codeagent-setup <<<
   ```

   重复配置只保留一段；写入前备份 `~/.bashrc`；终端菜单「恢复备份」时可以选择一并删除这段设置。

2. 自检：一键配置的最后，脚本以后台方式让 opencode 回答一句话（最长 180 秒）。运行时不连接终端，并关闭 git 的账号提示，所以遇到账号密码提示时会直接失败，不会卡住。失败时脚本会摘出输出里与账号、git、npm、代理、证书有关的行，判断提示的来源，完整输出保存在 `~/.config/opencode/codeagent-setup-selfcheck.log`（权限 600）。

配置完成后要关闭当前终端、重新打开一个，再启动 opencode，`~/.bashrc` 里的设置才会生效。

## 使用方法：浏览器页面（推荐）

1. 双击 `启动OpenCode配置.desktop`。第一次双击时桌面可能询问是否信任或运行，选信任并启动。会打开一个终端窗口（显示页面地址），并在默认浏览器中打开配置页面。双击后只打开了文本时，在本文件夹打开终端运行 `python3 ca_web.py`。
2. 页面左侧是本机现状：Node、opencode、OpenCode 配置（AK 只显示前 4 位、后 4 位和位数，10 位及以下全部打星号）、代理，绿色为就绪，黄色、红色按卡片上的提示处理。
3. 右侧按三步操作：环境检查；粘贴个人 AK（密码框，旁边是申请位置的提示）；一键配置（替换 AK、连通测试、关闭联网下载、首次启动自检）。每一步的输出显示在下方，标记为通过、注意、错误的行分别着色，结束时给出结论；配置完成后按提示关闭终端、重新打开后启动 opencode。
4. 其他操作：连通测试与自检。恢复备份只在终端菜单里（菜单 4）。「取消这一步」结束正在运行的步骤，「退出」停止服务。关闭页面后服务在 2 分钟后自动停止。本机没有 OpenCode 配置时，一键配置按钮不可用。

选项：`--port N`（默认自动选空闲端口）、`--no-browser`（只显示地址）、`--idle 秒数`（页面关闭这么久后停止，0 表示不自动停止，默认 120）、`--log-level`（默认 WARNING，可用环境变量 `LOG_LEVEL` 覆盖）。

页面上的按钮对应运行 `codeagent-setup.sh` 的 `check`、`setup -y`、`test -y` 子命令，所以连通测试不通过时同样不写入任何文件。

安全：

- 服务只监听 127.0.0.1，打开的地址带一个随机令牌；不带令牌或主机名不对的请求一律拒绝，浏览器里的其他网页无法调用本服务。只发送 `web/` 下三个固定文件。
- AK 只在页面与本机服务之间传递，经环境变量 `CA_AK` 交给子进程，不出现在命令行参数和服务日志里；页面现状只显示打码后的 AK；配置成功后页面清空 AK 输入框。
- 同一时间只运行一个步骤。

## 使用方法：终端菜单

```bash
cd tools/opencode-setup
./codeagent-setup.sh
```

进入菜单：

```
==== OpenCode 配置 ====
  1) 环境检查（Node 版本、opencode、现有配置）
  2) 一键配置 OpenCode（输入个人 AK）
  3) 连通测试与首次启动自检
  4) 恢复备份
  0) 退出
```

标准流程：

1. 选 1：确认 Node 是 v22，opencode 能找到，本机已有 OpenCode 配置。
2. 选 2：粘贴个人 AK（输入时不显示，回显时只显示前 4 位、后 4 位和位数）。脚本依次完成替换 AK、连通测试、写入配置、写入启动设置、首次启动自检，看到「opencode 可以正常对话」即完成。AK 到期或重新申请后，同样选 2 再做一次。
3. 关闭终端，重新打开一个，输入 `opencode` 启动。

其他功能：

- 连通测试与首次启动自检（菜单 3）：用当前配置测一次接口，可再做一次首次启动自检。
- 恢复备份（菜单 4）：每次写入前，原文件会备份为 `原文件名.bak.日期-时间`（权限 600）。恢复时用最近一次备份，当前文件另存为 `.before-rollback` 后缀；还可以选择删除 `~/.bashrc` 中的启动设置。

也可以不进菜单，直接执行某一步：

```bash
./codeagent-setup.sh check            # 环境检查
./codeagent-setup.sh setup            # 一键配置
./codeagent-setup.sh test             # 连通测试与首次启动自检
./codeagent-setup.sh rollback         # 恢复备份
./codeagent-setup.sh -h               # 完整帮助
```

`-y` 表示不逐项确认（连通测试失败时直接放弃写入；`rollback -y` 是否一并删除启动设置由环境变量 `CA_ROLLBACK_ENV=yes|no` 决定，默认 yes）。需要非交互运行时，可以用环境变量 `CA_AK` 提供 AK，例如 `read -rs CA_AK; export CA_AK`，不要把 AK 直接写在命令行里。

## 常见问题

- HTTP 401：AK 错误或已过期，重新申请或查看。HTTP 403：AK 没有该模型的权限。HTTP 404：配置里的接口地址或模型名不对。
- 提示本机还没有 OpenCode 配置：先把一份配置放到 `~/.config/opencode/opencode.jsonc`，里面要有服务商的 `baseURL`、`apiKey` 和模型。
- 提示 options 里没有 apiKey：给该服务商补上 `options.apiKey`（可先填任意占位）再重试。`apiKey` 写成 `{env:变量名}` 或 `{file:路径}` 时，本工具不改写，请直接改对应的环境变量或文件。
- 连接失败并提示设置了代理：内网地址需要加进 `no_proxy`，例如 `export no_proxy=$no_proxy,<内网域名>`。
- 启动 opencode 时仍要求输入用户名和密码：先确认是在配置完成后重新打开的终端里启动的；仍然出现时运行菜单 3 再做一次自检，按屏幕上的判断处理，或查看 `~/.config/opencode/codeagent-setup-selfcheck.log`。 <!-- sensitive-scan: ignore -->
- 环境检查提示另有 `opencode.json`：opencode 会合并同目录的多个配置文件，旧文件里的设置可能覆盖当前配置，确认无用后移走。
- 环境检查提示未找到 node 或 opencode，但终端里能直接运行：脚本会依次查当前 PATH、`~/.bashrc` 里的 PATH 与别名、家目录下的常见安装位置（`~/.opencode/bin`、`~/.local/bin`、`~/.npm-global/bin`、`~/.nvm`），找到后临时加入 PATH。仍然找不到时，在终端运行 `type node opencode` 查看实际位置。
- 环境检查提示配置文件权限为 664：按提示选 y，脚本会改为 600。

## 版本说明

随 evergreen-wiki 发版，版本号与仓库一致，变更记在仓库的 CHANGELOG.md。

- 4.0.0：AK 显示前 4 位、后 4 位和位数，10 位及以下全部打星号。
- 3.0.0：并入 evergreen-wiki 的 `tools/opencode-setup/`。AK 申请位置与 Node 切换方法的提示改为通用说法，可在本机提示文件里改写；`~/.bashrc` 标记段与自检日志的名称不变，已配置的工作站无须重做。
