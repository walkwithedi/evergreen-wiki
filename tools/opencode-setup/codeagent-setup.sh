#!/usr/bin/env bash
# codeagent-setup.sh — 麒麟工作站 OpenCode 配置：输入个人 AK，配好 OpenCode
#
# 用法：
#   双击「启动OpenCode配置」     在浏览器页面里操作（ca_web.py，推荐）
#   ./codeagent-setup.sh            进入终端交互菜单
#   ./codeagent-setup.sh <子命令>   直接执行某一步：
#     check     环境检查（Node 版本、opencode、配置现状）
#     setup     一键配置：替换本机 OpenCode 配置中的 AK、连通测试、关闭启动时联网下载、首次启动自检
#     test      连通测试与首次启动自检
#     rollback  恢复最近一次备份
#
# 接口地址与模型取自本机已有的 OpenCode 配置，本工具只替换其中的 AK。
# 依赖：bash 4.4+、python3（只用标准库）。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HELPER="$SCRIPT_DIR/ca_config.py"
OC_DIR="${OPENCODE_CONF_DIR:-$HOME/.config/opencode}"
OC_FILE=""
BASHRC="${CA_BASHRC:-$HOME/.bashrc}"
SELFCHECK_LOG="$OC_DIR/codeagent-setup-selfcheck.log"

ASSUME_YES=0
AK=""

NODE_MAJOR="22"
# 两处提示的默认写法；本机可在提示文件里改成自己的说法（见 load_hints），提示文件不随工具分发
AK_HINT="个人 AK（API Key）向模型服务的管理方申请"
NODE_HINT="用 nvm 或系统自带的软件管理切换 Node 版本"
HINTS_FILE="${CA_HINTS:-${XDG_CONFIG_HOME:-$HOME/.config}/opencode-setup/hints.conf}"

# opencode 启动时会联网检查更新、安装默认插件、拉取在线模型清单、下载语言服务器，
# 内网环境下这些动作可能在终端里要求输入账号密码。以下环境变量逐项关闭，写进 ~/.bashrc 的标记段。
ENV_BEGIN="# >>> codeagent-setup：opencode 启动时不联网下载 >>>"
ENV_END="# <<< codeagent-setup <<<"
ENV_VARS=(OPENCODE_DISABLE_AUTOUPDATE OPENCODE_DISABLE_DEFAULT_PLUGINS OPENCODE_DISABLE_MODELS_FETCH OPENCODE_DISABLE_LSP_DOWNLOAD)

if [ -t 2 ]; then
  C_OK=$'\033[32m'; C_WARN=$'\033[33m'; C_ERR=$'\033[31m'; C_B=$'\033[1m'; C_0=$'\033[0m'
else
  C_OK=""; C_WARN=""; C_ERR=""; C_B=""; C_0=""
fi
info(){ printf '%s\n' "$*" >&2; }
ok(){ printf '%s[通过]%s %s\n' "$C_OK" "$C_0" "$*" >&2; }
warn(){ printf '%s[注意]%s %s\n' "$C_WARN" "$C_0" "$*" >&2; }
err(){ printf '%s[错误]%s %s\n' "$C_ERR" "$C_0" "$*" >&2; }
die(){ err "$*"; exit 1; }
title(){ printf '\n%s== %s ==%s\n' "$C_B" "$*" "$C_0" >&2; }
py(){ python3 "$HELPER" "$@"; }

usage(){ sed -n '2,13p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; cat <<'EOF'

选项：
  -y      不逐项确认（连通测试失败时直接放弃写入）
  -h      显示帮助

环境变量：
  CA_AK         非交互运行时直接提供 AK（不建议写进 shell 历史）
  CA_BASHRC     写入启动设置的 shell 配置文件，默认 ~/.bashrc
  CA_ROLLBACK_ENV  rollback 带 -y 时是否删除 ~/.bashrc 中的启动设置：yes 或 no（默认 yes）
  CA_HINTS      提示文件，默认 ~/.config/opencode-setup/hints.conf（AK 申请位置、Node 切换方法）
  LOG_LEVEL     辅助脚本日志级别 DEBUG / INFO / WARNING / ERROR
EOF
}

confirm(){
  [ "$ASSUME_YES" = 1 ] && return 0
  local ans
  read -r -p "$1 [y/N] " ans
  [[ "$ans" =~ ^[Yy]$ ]]
}

pause(){ [ -t 0 ] && read -r -p "按回车返回菜单……" _ || true; }

# 提示文件：每行「AK_HINT=文字」或「NODE_HINT=文字」，# 开头为注释，其他行忽略；只读取，不执行
load_hints(){
  [ -f "$HINTS_FILE" ] || return 0
  local line key val
  while IFS= read -r line || [ -n "$line" ]; do
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    key="${line%%=*}"; val="${line#*=}"
    [ "$key" != "$line" ] && [ -n "$val" ] || continue
    case "$key" in
      AK_HINT) AK_HINT="$val" ;;
      NODE_HINT) NODE_HINT="$val" ;;
    esac
  done < "$HINTS_FILE"
}

# AK 只显示前 4 位…后 4 位与长度，便于核对是哪一把；10 位及以下全部打星号
mask(){
  local s="$1"
  if [ "${#s}" -le 10 ]; then printf '%s' "${s//?/*}"; else printf '%s…%s（共 %d 位）' "${s:0:4}" "${s: -4}" "${#s}"; fi
}

ask_ak(){
  [ -n "$AK" ] && return 0
  if [ -n "${CA_AK:-}" ]; then
    AK="$CA_AK"
  else
    [ -t 0 ] || die "不是交互终端，请用环境变量 CA_AK 提供 AK"
    info "$AK_HINT。"
    read -r -s -p "请粘贴个人 AK（输入时不显示）：" AK; echo >&2
  fi
  AK="${AK//[[:space:]]/}"
  [ -n "$AK" ] || die "AK 为空"
  info "已读入 AK：$(mask "$AK")"
}

detect_oc_file(){
  if [ -f "$OC_DIR/opencode.jsonc" ]; then OC_FILE="$OC_DIR/opencode.jsonc"
  elif [ -f "$OC_DIR/opencode.json" ]; then OC_FILE="$OC_DIR/opencode.json"
  else OC_FILE="$OC_DIR/opencode.jsonc"
  fi
}

backup(){
  [ -f "$1" ] || return 0
  local bak
  bak="$1.bak.$(date +%Y%m%d-%H%M%S)"
  cp -p "$1" "$bak"
  chmod 600 "$bak"
  info "已备份原文件：$bak"
}

new_tmp(){
  mkdir -p "$1"
  (umask 077 && mktemp "$1/.codeagent-setup.XXXXXX")
}

# 用临时文件替换正式文件：先备份，再改名，权限 600
install_file(){
  local tmp="$1" dest="$2"
  backup "$dest"
  mv -f "$tmp" "$dest"
  chmod 600 "$dest"
  ok "已写入 $dest（权限 600，仅本人可读写）"
}

latest_backup(){
  find "$(dirname "$1")" -maxdepth 1 -name "$(basename "$1").bak.*" ! -name "*.restored" \
    -type f -print 2>/dev/null | sort | tail -n 1
}

# ---------- 命令查找 ----------

# 先查当前 PATH；找不到时用交互式 bash 再查一次（会加载 ~/.bashrc 里的 PATH 与别名，
# Node 版本切换工具、opencode 安装脚本通常写在那里）；最后查家目录下的常见安装位置。
# 找到后把所在目录加到本脚本的 PATH 前面，后续的版本查询与自检都能用上。
declare -A TOOL_PATH=() TOOL_BIN=()
TOOLS_LOCATED=0
locate_cmd(){
  local name="$1" p="" line cand
  p="$(command -v "$name" 2>/dev/null || true)"
  if [[ "$p" != /* ]]; then
    p=""
    line="$(LC_ALL=C bash -ic "printf '__CA__%s\n' \"\$(command -v $name)\"" </dev/null 2>/dev/null \
      | grep '^__CA__' | tail -n 1 || true)"
    line="${line#__CA__}"
    if [[ "$line" == /* ]]; then
      p="$line"
    elif [[ "$line" == alias* ]]; then
      line="${line#*=}"; line="${line//\'/}"; line="${line//\"/}"
      line="${line%% *}"; line="${line/#\~/$HOME}"
      [[ "$line" == /* ]] && p="$line"
    fi
  fi
  if [ -z "$p" ]; then
    for cand in "$HOME/.opencode/bin/$name" "$HOME/.local/bin/$name" "$HOME/.npm-global/bin/$name" \
      "$HOME/.bun/bin/$name" $(ls -d "$HOME"/.nvm/versions/node/*/bin/"$name" 2>/dev/null | sort -V -r); do
      if [ -x "$cand" ]; then p="$cand"; break; fi
    done
  fi
  [ -n "$p" ] && [ -x "$p" ] || return 1
  TOOL_BIN[$name]="$p"
  TOOL_PATH[$name]="$p"
  case ":$PATH:" in
    *":$(dirname "$p"):"*) ;;
    *) PATH="$(dirname "$p"):$PATH"; export PATH; TOOL_PATH[$name]="$p（不在当前 PATH 中，已临时加入）" ;;
  esac
}

locate_tools(){
  [ "$TOOLS_LOCATED" = 1 ] && return 0
  local t
  for t in node opencode; do locate_cmd "$t" || true; done
  TOOLS_LOCATED=1
}

has_tool(){ [ -n "${TOOL_PATH[$1]:-}" ]; }

# ---------- 启动设置（~/.bashrc 标记段） ----------

env_block_present(){ [ -f "$BASHRC" ] && grep -qxF "$ENV_BEGIN" "$BASHRC"; }

# 输出去掉标记段后的 ~/.bashrc 内容
bashrc_without_block(){
  awk -v b="$ENV_BEGIN" -v e="$ENV_END" '$0==b{skip=1;next} $0==e{skip=0;next} !skip' "$BASHRC"
}

# 写回 ~/.bashrc：用 cat 覆盖原文件，保留原有权限
write_bashrc(){
  local tmp="$1"
  cat "$tmp" > "$BASHRC"
  rm -f "$tmp"
}

apply_env_block(){
  title "关闭 opencode 启动时的联网下载"
  local tmp v
  [ -f "$BASHRC" ] || : > "$BASHRC"
  backup "$BASHRC"
  tmp="$(mktemp)"
  {
    bashrc_without_block
    echo "$ENV_BEGIN"
    echo "# 关闭自动更新、默认插件安装、在线模型清单与语言服务器下载，避免内网环境下启动 opencode 时要求输入账号密码"
    for v in "${ENV_VARS[@]}"; do echo "export $v=1"; done
    echo "$ENV_END"
  } > "$tmp"
  write_bashrc "$tmp"
  for v in "${ENV_VARS[@]}"; do export "$v=1"; done
  ok "已写入 $BASHRC 的 codeagent-setup 标记段（新开的终端生效，本次自检已临时生效）"
}

remove_env_block(){
  env_block_present || return 0
  local tmp
  backup "$BASHRC"
  tmp="$(mktemp)"
  bashrc_without_block > "$tmp"
  write_bashrc "$tmp"
  ok "已从 $BASHRC 删除 codeagent-setup 标记段"
}

# ---------- 环境检查 ----------

check_env(){
  title "环境检查"
  command -v python3 >/dev/null 2>&1 || die "未找到 python3"
  [ -f "$HELPER" ] || die "缺少 $HELPER，请把整个目录一起拷贝"
  local v major
  if [ -r /etc/os-release ]; then info "系统：$(. /etc/os-release && echo "${PRETTY_NAME:-未知}")"; fi
  locate_tools
  if has_tool node; then
    v="$("${TOOL_BIN[node]}" -v 2>/dev/null || echo v0)"
    major="${v#v}"; major="${major%%.*}"
    if [[ "$major" =~ ^[0-9]+$ ]] && [ "$major" -ge "$NODE_MAJOR" ]; then
      ok "Node $v：${TOOL_PATH[node]}"
    else
      warn "Node 当前为 $v（${TOOL_PATH[node]}），需要 v$NODE_MAJOR 或以上：$NODE_HINT，选择 v$NODE_MAJOR 开头的版本，切换后重新打开终端"
    fi
  else
    warn "未找到 node：$NODE_HINT，选择 v$NODE_MAJOR 开头的版本"
  fi
  if has_tool opencode; then
    ok "opencode $("${TOOL_BIN[opencode]}" --version 2>/dev/null | head -n 1)：${TOOL_PATH[opencode]}"
  else
    warn "未找到 opencode 命令（配置仍可写入）。如果在终端里能直接运行，请运行 type opencode 查看实际位置"
  fi
  if [ -n "${https_proxy:-}${HTTPS_PROXY:-}${http_proxy:-}${HTTP_PROXY:-}" ]; then
    warn "设置了代理环境变量，内网接口地址可能需要加进 no_proxy"
  fi
  if env_block_present; then
    ok "已关闭 opencode 启动时的联网下载（$BASHRC 中的 codeagent-setup 标记段）"
  else
    warn "尚未关闭 opencode 启动时的联网下载，第一次启动可能要求输入账号密码；一键配置时会自动设置"
  fi
  detect_oc_file
  if [ -f "$OC_FILE" ]; then
    if [ "$(stat -c '%a' "$OC_FILE")" = 600 ]; then
      ok "$OC_FILE 权限 600"
    else
      warn "$OC_FILE 权限为 $(stat -c '%a' "$OC_FILE")，同组用户可读，其中含 AK"
      if [ -t 0 ] && confirm "现在改为 600（仅本人可读写）吗？"; then
        chmod 600 "$OC_FILE" && ok "已改为 600"
      fi
    fi
    py summary-opencode "$OC_FILE" || true
  else
    warn "本机还没有 OpenCode 配置：请先把一份配置放到 $OC_FILE（含接口地址、模型和 AK 字段），一键配置只替换其中的 AK"
  fi
  local f
  for f in opencode.json opencode.jsonc config.json; do
    if [ -f "$OC_DIR/$f" ] && [ "$OC_DIR/$f" != "$OC_FILE" ]; then
      warn "$OC_DIR/$f 也存在，opencode 会与 $OC_FILE 合并，其中的设置可能覆盖本脚本的配置"
    fi
  done
}

# ---------- 首次启动自检 ----------

# 无控制终端地运行命令：需要输入账号密码的程序拿不到终端，会直接失败而不是等待输入
run_detached(){
  if command -v setsid >/dev/null 2>&1 && setsid --help 2>&1 | grep -q -- '--wait'; then
    setsid --wait "$@"
  else
    "$@"
  fi
}

first_start_check(){
  title "首次启动自检"
  locate_tools
  if ! has_tool opencode; then warn "未找到 opencode 命令，跳过自检"; return 0; fi
  local dir rc=0 hits
  dir="$(mktemp -d)"
  mkdir -p "$OC_DIR"
  (umask 077 && : > "$SELFCHECK_LOG")  # 先以 600 权限建好日志，后面的重定向只截断不改权限
  info "以后台方式运行一次 opencode（最长 180 秒）。遇到账号密码提示时会直接失败，不会等待输入……"
  (cd "$dir" && GIT_TERMINAL_PROMPT=0 GCM_INTERACTIVE=never \
    run_detached timeout 180 "${TOOL_BIN[opencode]}" run "只回复两个字母：OK") </dev/null >"$SELFCHECK_LOG" 2>&1 || rc=$?
  rmdir "$dir" 2>/dev/null || true
  hits="$(grep -n -i -E 'user ?name|password|passwd|用户名|密码|credential|login|auth|401|403|npm|registry|bun |git|proxy|certificate|ENOTFOUND|ECONNREFUSED|ETIMEDOUT' \
    "$SELFCHECK_LOG" | head -n 15 || true)"
  if [ "$rc" = 0 ]; then
    ok "opencode 可以正常对话：$(grep -v '^\s*$' "$SELFCHECK_LOG" | tail -n 1 | cut -c1-80)"
    return 0
  fi
  if [ "$rc" = 124 ]; then warn "opencode 运行超过 180 秒未结束"
  else warn "opencode 未能正常完成（退出码 $rc）"; fi
  if [ -n "$hits" ]; then
    info "输出中的相关行："
    printf '%s\n' "$hits" | sed 's/^/    /' >&2
    if grep -q -i -E 'git' <<<"$hits"; then
      info "判断：提示来自 git（访问代码仓库时需要账号）。"
    elif grep -q -i -E 'npm|registry|bun ' <<<"$hits"; then
      if env_block_present; then
        info "判断：提示来自 npm 下载（可能是缺少插件依赖、其他插件或自动更新）。关闭终端、重新打开一个让启动设置生效后再试；仍出现时在终端启动 opencode，按提示输入账号密码完成一次下载。"
      else
        info "判断：提示来自 npm 下载（可能是缺少插件依赖、其他插件或自动更新）。运行菜单 2 一键配置，写入启动设置后再试。"
      fi
    elif grep -q -i -E 'proxy' <<<"$hits"; then
      info "判断：代理服务器需要认证，内网接口地址可能需要加进 no_proxy。"
    fi
  fi
  info "完整输出已保存到 $SELFCHECK_LOG（仅本人可读），可发给维护者排查。"
}

# ---------- 配置 ----------

# 把 AK 原位替换进本机已有的 OpenCode 配置（接口地址、模型与其他设置不变），先测通再写入
replace_ak(){
  title "替换 AK"
  detect_oc_file
  [ -f "$OC_FILE" ] || die "本机还没有 OpenCode 配置：请先把一份配置放到 $OC_FILE（含接口地址、模型和 AK 字段），本工具只替换其中的 AK"
  ask_ak
  local tmp
  tmp="$(new_tmp "$OC_DIR")"
  printf '%s' "$AK" | py set-key-opencode "$OC_FILE" "$tmp" || { rm -f "$tmp"; die "替换 AK 失败"; }
  title "连通测试"
  if ! py probe-opencode "$tmp"; then
    if [ "$ASSUME_YES" = 1 ] || ! confirm "连通测试未通过，仍要写入吗？"; then
      rm -f "$tmp"
      die "已取消，原配置保持不变"
    fi
  fi
  install_file "$tmp" "$OC_FILE"
}

do_setup(){
  check_env
  replace_ak
  apply_env_block
  first_start_check
  title "完成"
  info "请关闭当前终端，重新打开一个终端后输入 opencode 启动。"
}

# 供浏览器页面（ca_web.py）读取的现状，每行「键<TAB>值」，查找方法与环境检查相同
do_status(){
  locate_tools
  detect_oc_file
  local v=""
  kv(){ printf '%s\t%s\n' "$1" "$2"; }
  has_tool node && v="$(timeout 10 "${TOOL_BIN[node]}" -v 2>/dev/null || true)"
  kv node "${TOOL_BIN[node]:-}"
  kv node_version "$v"
  kv node_major "$NODE_MAJOR"
  kv node_hint "$NODE_HINT"
  kv ak_hint "$AK_HINT"
  v=""
  has_tool opencode && v="$(timeout 10 "${TOOL_BIN[opencode]}" --version 2>/dev/null | head -n 1 || true)"
  kv opencode "${TOOL_BIN[opencode]:-}"
  kv opencode_version "$v"
  kv oc_file "$OC_FILE"
  kv oc_mode "$([ -f "$OC_FILE" ] && stat -c '%a' "$OC_FILE" || true)"
  kv env_block "$(env_block_present && echo 1 || echo 0)"
  kv bashrc "$BASHRC"
  kv proxy "${https_proxy:-${HTTPS_PROXY:-${http_proxy:-${HTTP_PROXY:-}}}}"
}

do_test(){
  title "连通测试（使用当前配置）"
  detect_oc_file
  [ -f "$OC_FILE" ] || die "OpenCode 还没有配置，请先做一键配置"
  py probe-opencode "$OC_FILE" || true
  if env_block_present; then
    local v
    for v in "${ENV_VARS[@]}"; do export "$v=1"; done
  fi
  if [ "$ASSUME_YES" = 1 ] || ! [ -t 0 ] || confirm "再做一次首次启动自检吗？（最长 180 秒）"; then
    first_start_check
  fi
}

do_rollback(){
  title "恢复备份"
  detect_oc_file
  local latest
  latest="$(latest_backup "$OC_FILE")"
  if [ -z "$latest" ]; then
    info "没有 $OC_FILE 的备份"
  elif confirm "用 $latest 恢复 $OC_FILE 吗？"; then
    [ -f "$OC_FILE" ] && cp -p "$OC_FILE" "$OC_FILE.before-rollback.$(date +%Y%m%d-%H%M%S)"
    cp -p "$latest" "$OC_FILE"
    chmod 600 "$OC_FILE"
    mv -f "$latest" "$latest.restored"
    ok "已恢复 $OC_FILE"
  fi
  if env_block_present; then
    if [ "$ASSUME_YES" = 1 ] && [ "${CA_ROLLBACK_ENV:-yes}" = no ]; then
      info "保留 $BASHRC 中的启动设置"
    elif confirm "同时删除 $BASHRC 中的启动设置（恢复 opencode 启动时联网下载）吗？"; then
      remove_env_block
    fi
  fi
}

menu(){
  local ans
  while true; do
    printf '\n%s==== OpenCode 配置 ====%s\n' "$C_B" "$C_0" >&2
    info "  1) 环境检查（Node 版本、opencode、现有配置）"
    info "  2) 一键配置 OpenCode（输入个人 AK）"
    info "  3) 连通测试与首次启动自检"
    info "  4) 恢复备份"
    info "  0) 退出"
    read -r -p "请选择：" ans || exit 0
    # 每项在子 shell 中运行，出错只返回菜单，不退出脚本
    case "$ans" in
      1) (check_env) || true ;;
      2) (do_setup) || true ;;
      3) (do_test) || true ;;
      4) (do_rollback) || true ;;
      0|q|Q) exit 0 ;;
      "") continue ;;
      *) warn "无效选择：$ans"; continue ;;
    esac
    pause
  done
}

main(){
  local cmd="menu"
  if [ "$#" -gt 0 ] && [[ "$1" != -* ]]; then cmd="$1"; shift; fi
  while [ "$#" -gt 0 ]; do
    case "$1" in
      -y) ASSUME_YES=1 ;;
      -h|--help) usage; exit 0 ;;
      *) die "未知选项：$1（-h 查看帮助）" ;;
    esac
    shift
  done
  command -v python3 >/dev/null 2>&1 || die "未找到 python3"
  load_hints
  case "$cmd" in
    menu) [ -t 0 ] || die "菜单需要交互终端；非交互请用子命令（-h 查看帮助）"; menu ;;
    check) check_env ;;
    setup|all|opencode) do_setup ;;
    test) do_test ;;
    rollback) do_rollback ;;
    status) do_status ;;
    help) usage ;;
    *) die "未知子命令：$cmd（-h 查看帮助）" ;;
  esac
}

main "$@"
