# opencode-setup: OpenCode configuration

[中文](README.zh-CN.md)

Sets up OpenCode on a Kylin workstation from one personal API key (AK): the key is put into the OpenCode configuration already on the computer, a test request must pass before anything is written, OpenCode's network downloads at start-up are switched off, and a first start is checked. Every write is backed up first and can be rolled back.

The endpoint, models and every other setting come from the existing configuration; this tool only replaces the key. Steps 1 and 2 of the [workbench wizard](../workbench/README.md) are this page. The page and the terminal menu are in Chinese.

## Files

| File | Role |
| --- | --- |
| `启动OpenCode配置.desktop` | Double-click entry: opens a terminal running `ca_web.py` and the configuration page in the default browser. |
| `ca_web.py` | Local server for the page; each button runs a sub-command of `codeagent-setup.sh` and streams its output. Python 3 standard library only. |
| `web/` | The page (`index.html`, `app.js`, `style.css`); nothing is loaded from the network. |
| `codeagent-setup.sh` | The script holding all configuration logic. Without arguments it shows a terminal menu; sub-commands run one step. |
| `ca_config.py` | Helper called by the script: reads JSON with comments, replaces the key in place, sends the test request. Python 3 standard library only. |

## Requirements

- Kylin, bash 4.4+, python3 (the system one; no packages to install).
- Node 22 or later; the script says how to switch otherwise.
- opencode installed (without it the key is still replaced, but the first start cannot be checked).
- An existing OpenCode configuration: `~/.config/opencode/opencode.jsonc` (or `opencode.json`) whose provider `options` hold `baseURL` and `apiKey` (any placeholder) and that lists the models. Without it, setup stops and writes nothing.
- The model endpoint is reachable. With a proxy set, internal endpoints belong in `no_proxy`.

## Local hints

Two hints can be worded for the computer: where to get an AK, and how to switch the Node version. Put one per line into `~/.config/opencode-setup/hints.conf` (or the file named by `CA_HINTS`):

```
AK_HINT=<where the key is issued>
NODE_HINT=<how to switch the Node version>
```

Lines starting with `#` are comments; other keys are ignored. The file is only read, never run, and is not shipped with the tool. The menu and the page show the same hints; without the file they use general wording.

## Start-up downloads

At start-up opencode checks for updates, installs default plugins, fetches the online model list and downloads language servers. On an internal network these may ask for an account, so a new computer prompts for a user name and password on first start. The script:

1. writes a marked block to the end of `~/.bashrc` that switches these downloads off (`OPENCODE_DISABLE_AUTOUPDATE`, `OPENCODE_DISABLE_DEFAULT_PLUGINS`, `OPENCODE_DISABLE_MODELS_FETCH`, `OPENCODE_DISABLE_LSP_DOWNLOAD`); one block only, `~/.bashrc` backed up first, removable through rollback;
2. lets opencode answer one sentence in the background (at most 180 seconds) without a terminal, so an account prompt fails at once instead of waiting; on failure it picks out the lines about accounts, git, npm, proxies and certificates and keeps the full output in `~/.config/opencode/codeagent-setup-selfcheck.log` (mode 600).

Open a new terminal after setup so the `~/.bashrc` block takes effect.

## Using the page

1. Double-click `启动OpenCode配置.desktop` (trust it the first time), or run `python3 ca_web.py` in this folder.
2. The left column shows the state: Node, opencode, the configuration (the key's first and last four characters and its length, or only asterisks for a key of ten characters or fewer), proxy.
3. The right column has three steps: check; paste the AK; set up (replace the key, test, switch off downloads, check the first start). Output appears below with a verdict at the end.
4. Also: test again, cancel the running step, quit. The server stops two minutes after the page is closed.

Options: `--port N`, `--no-browser`, `--idle SECONDS` (0 never stops; default 120), `--log-level` (default WARNING, or `LOG_LEVEL`).

The buttons run `check`, `setup -y` and `test -y`, so a failed test writes nothing. The server listens on 127.0.0.1 only and needs a random token in every request; the key travels from the page to the script in the environment variable `CA_AK`, never on a command line or in the log; one step runs at a time.

## Using the terminal

```bash
cd tools/opencode-setup
./codeagent-setup.sh            # menu
./codeagent-setup.sh check      # check
./codeagent-setup.sh setup      # set up
./codeagent-setup.sh test       # test and first-start check
./codeagent-setup.sh rollback   # restore the latest backup
./codeagent-setup.sh -h         # help
```

`-y` answers every question with yes (a failed test then gives up; whether `rollback -y` also removes the `~/.bashrc` block is set by `CA_ROLLBACK_ENV=yes|no`, default yes). For non-interactive runs give the key in `CA_AK` (`read -rs CA_AK; export CA_AK`), never on the command line. Backups are `<file>.bak.<date-time>` (mode 600); a rollback keeps the current file as `.before-rollback`.

## Troubleshooting

- HTTP 401: wrong or expired key. 403: the key has no access to the model. 404: wrong endpoint or model name.
- No OpenCode configuration: put one at `~/.config/opencode/opencode.jsonc` with the provider's `baseURL`, `apiKey` and models.
- No apiKey in options: add `options.apiKey` (any placeholder) and retry. A key written as `{env:NAME}` or `{file:PATH}` is not rewritten; change the variable or the file.
- Connection fails with a proxy set: add the internal host to `no_proxy`.
- Still asked for a password: start opencode from a new terminal; otherwise run the test again and follow the verdict, or read the self-check log.
- Another `opencode.json` next to the configuration: opencode merges them; move the stale one away.
- node or opencode not found although they run in a terminal: the script looks in PATH, in `~/.bashrc` (PATH and aliases) and in `~/.opencode/bin`, `~/.local/bin`, `~/.npm-global/bin` and `~/.nvm`; run `type node opencode` to see where they are.

## Versions

Released with evergreen-wiki under the repository's version; changes are in CHANGELOG.md.

- 3.0.0: moved into evergreen-wiki as `tools/opencode-setup/`. The hints on where to get a key and how to switch Node are general and can be reworded in a local hints file; the `~/.bashrc` block and the self-check log keep their names, so configured workstations need nothing redone.
