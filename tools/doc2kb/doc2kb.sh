#!/bin/bash
# doc2kb.sh - turn Office, PDF and mail files into a Markdown knowledge base
#
# Two ways to run it:
#   1) without arguments -> desktop dialogs (folder batch / chosen files / incremental tasks)
#      ./doc2kb.sh
#   2) with arguments    -> incremental command-line mode, no desktop needed, fit for crontab
#      ./doc2kb.sh -s SOURCE -o OUTPUT -d 7      # first run, sets the watermark
#      ./doc2kb.sh -s SOURCE -o OUTPUT           # later runs carry on from there
#
# Needs: python3 and doc2kb_core.py in the same folder.
#        The dialogs also need zenity; the command-line mode does not.
#        Run it with bash, not sh.
#
# Archives: documents inside .zip and .tar (.tar.gz, .tar.bz2, .tar.xz) files are processed
# as if the archive were a folder ("pack.zip/a/x.docx"). Members are unpacked into a
# private temporary folder only, never next to the archive.
#
# Language: messages and output labels are Chinese when DOC2KB_LANG=zh or the locale
# (LC_ALL, LC_MESSAGES, LANG) starts with zh, English otherwise. DOC2KB_LANG=en forces English.
#
# Command-line mode: scans SOURCE for documents changed since the last run (or within
# the last N days) and merges them into one dated md. With nothing new it exits quietly
# and writes no empty file.
#
# What counts as changed: the latest of the file system modification time, the file
# system change time and the document's own time. Files newly copied into the folder
# and edited files are both found, even when a copied file was last edited long ago.
# The "Document last modified" shown in the md header is still the document's own time,
# which says how current the content is; that is a different thing.
#
# Time range (one of):
#   default           watermark: documents changed after the last successful run
#   -d N              window: documents changed in the last N days (ignores the watermark)
#   -t DATE           from DATE, YYYY-MM-DD or "YYYY-MM-DD HH:MM" (ignores the watermark)
#
# Every successful run moves the watermark to its own start time, so after one run with
# -d N, plain runs (no time option) carry on by themselves.
#
# Other options:
#   -i                export pictures (default: text only, faster)
#   -I                do not export pictures (the default; to say it explicitly)
#   -E                do not expand embedded workbooks into the text
#   -x SUFFIX         output name suffix, default "incremental" ("增量" in Chinese)
#   -n                only report which files would be processed (dry run)
#   -h                show this help
#
# Without -i the text keeps its [Image NNN] anchors but no picture files are written,
# which keeps cron runs fast and small.
#
# Every short option has a long form (--days / --since / --images / --no-images /
# --no-inline / --name-suffix / --dry-run). Input methods and web pages often turn -- into
# a dash (— or –); the script turns those back into --, but short options avoid the problem.
#
# Exit codes: 0 done (also when nothing was new)  1 option or environment error
#             2 processing failed  3 first run without a time range (no watermark yet)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CORE="$SCRIPT_DIR/doc2kb_core.py"

# ---------------- language ----------------
UI_LANG="${DOC2KB_LANG:-}"
if [ "$UI_LANG" != "zh" ] && [ "$UI_LANG" != "en" ]; then
    case "${LC_ALL:-${LC_MESSAGES:-${LANG:-}}}" in
        zh*) UI_LANG=zh ;;
        *)   UI_LANG=en ;;
    esac
fi
export DOC2KB_LANG="$UI_LANG"

# t ENGLISH CHINESE: the text in the interface language
t() { if [ "$UI_LANG" = "zh" ]; then printf '%s' "$2"; else printf '%s' "$1"; fi; }
LP="$(t " (" "（")"; RP="$(t ")" "）")"

TITLE="$(t "Documents to knowledge base" "文档转知识库")"
# core's output file names in the interface language
REPORT_FILE="$(t "_batch-report.txt" "_批量处理报告.txt")"
IMGLIST_FILE="$(t "_image-list.md" "_图片清单.md")"

# stat_of KEY TEXT: value of a "STAT<TAB>KEY<TAB>value" line printed by the core
stat_of() { printf '%s\n' "$2" | awk -F'\t' -v k="$1" '$1=="STAT" && $2==k {print $3; exit}'; }

# ================================================================
#   Command-line incremental mode (with arguments; no desktop, cron friendly)
# ================================================================
if [ $# -gt 0 ]; then

usage() {
    if [ "$UI_LANG" = "zh" ]; then
        cat <<'HELP'
doc2kb.sh — 文档转知识库

用法:
  ./doc2kb.sh                               不带参数：图形界面（需要 zenity）
  ./doc2kb.sh -s 源目录 -o 输出目录 [选项]    命令行增量模式，可放进 crontab

扫描源目录，把「上次运行之后」或「最近 N 天内」变动过的文档
提取合并成一个带日期的 md 文件。无新增时静默退出，不产生空文件。

增量判定:
  取文件系统修改时间、文件系统状态变更时间、文档内部属性时间三者中最晚的一个，
  因此「新拷入的文件」和「已有文件被改动」都能捕获。
  md 头部展示的「文档最后修改」仍是文档内部属性时间，代表内容本身的新旧。

时间范围（二选一）:
  默认              水位模式：处理上次成功运行之后变动的文档
  -d N              窗口模式：处理最近 N 天内变动的文档（忽略已有水位）
  -t DATE           指定起点，YYYY-MM-DD 或 "YYYY-MM-DD HH:MM"（忽略已有水位）
  任何一次成功运行都会把水位推进到本次运行时刻，首次用 -d N 跑一遍后裸跑即可接续。

其他选项:
  -i                导出图片（默认不导，只要文字，速度快）
  -I                不导出图片（默认行为）
  -E                不把嵌入的 Excel 展开进正文
  -x 后缀           输出文件名后缀，默认「增量」
  -n                只报告会处理哪些文件，不实际生成
  -h                显示帮助

  每个短选项都有长选项（--days / --since / --images / --no-images / --no-inline /
  --name-suffix / --dry-run），但中文输入法容易把 -- 转成破折号，手工敲命令建议用短选项；
  脚本也会把破折号（— –）还原成 --。

退出码: 0 正常（含无新增）  1 参数或环境错误  2 处理失败  3 首次运行未指定时间范围

crontab 示例（每天 18:30 跑一次）:
  30 18 * * * /home/user/tools/doc2kb.sh -s /home/user/文档 -o /home/user/tools/output/wd >> /home/user/tools/output/wd/cron.out 2>&1
  编辑: crontab -e      查看: crontab -l
  crontab 环境变量极简，路径一律写绝对路径；需要中文时在命令前加 DOC2KB_LANG=zh。

日常用法（增量）:
  第一次（建立水位，先拉最近 30 天）   ./doc2kb.sh -s 源目录 -o 输出目录 -d 30
  以后每次（裸跑）                     ./doc2kb.sh -s 源目录 -o 输出目录
  日常一律裸跑，不要再带 -d。带 -d 会重新按天数计算，同一批文档会被重新扫描
  （正文已入库的只列路径对照，不重复收录）。

目录移动 / 改名后:
  正文没变的文档不会重复收录，只在增量文件索引区列出路径对照，
  依据是输出目录里的正文指纹库 .doc2kb_watch_fp。
  早先生成的大增量文件可用 doc2kb_dedup.py 清理并建立指纹库:
    python3 doc2kb_dedup.py 输出目录/xxx_增量.md -n   # 先试运行

全量:
  不带参数运行 ./doc2kb.sh，选「目录批量」。增量与全量的输出目录建议分开。

输出文件名:
  <源目录名>_YYYYMMDD_增量.md；同一天多次运行自动带上时分，如 文档_20260804-1105_增量.md
HELP
    else
        sed -n '2,/^$/p' "${BASH_SOURCE[0]}" | grep '^#' | sed 's/^# \{0,1\}//'
        cat <<'HELP'

crontab example (every day at 18:30):
  30 18 * * * /home/user/tools/doc2kb.sh -s /home/user/Documents -o /home/user/tools/output/wd >> /home/user/tools/output/wd/cron.out 2>&1
  edit: crontab -e      list: crontab -l
  cron has a minimal environment: use absolute paths.

Everyday use (incremental):
  first run (sets the watermark, last 30 days)   ./doc2kb.sh -s SOURCE -o OUTPUT -d 30
  every later run (no time option)               ./doc2kb.sh -s SOURCE -o OUTPUT
  Do not keep adding -d: it counts days again and scans the same documents again
  (text already filed is only listed with its paths, not filed twice).

After moving or renaming folders:
  Documents whose text did not change are not filed again; the incremental file's index
  lists old and new paths, based on the text fingerprint file .doc2kb_watch_fp in OUTPUT.
  Large incremental files made before that can be cleaned up with doc2kb_dedup.py,
  which also builds the fingerprint file:
    python3 doc2kb_dedup.py OUTPUT/xxx_incremental.md -n   # dry run first

Full runs:
  Run ./doc2kb.sh without arguments and choose "Folder batch". Keep incremental and full
  output in separate folders; mixing them breaks nothing but is hard to tell apart.

Output names:
  <source folder>_YYYYMMDD_incremental.md; a second run on the same day adds the time,
  as in Documents_20260804-1105_incremental.md
HELP
    fi
    exit 0
}

SRC=""
OUT=""
DAYS=""
SINCE=""
NOIMG="--no-images"   # cron runs want text only: faster
NOINLINE=""
SUFFIX="$(t "incremental" "增量")"
DRYRUN=0


# ---------------- option clean-up ----------------
# Input methods turn -- into a dash (— – ——); turn it back so "—days" works.
ARGS=()
for a in "$@"; do
    case "$a" in
        —*|–*)
            a="--${a#"${a%%[!—–]*}"}" ;;
    esac
    ARGS+=("$a")
done
set -- "${ARGS[@]}"

# ---------------- options ----------------
while [ $# -gt 0 ]; do
    case "$1" in
        -s|--source)         SRC="$2"; shift 2 ;;
        -o|--output)         OUT="$2"; shift 2 ;;
        -d|--days)           DAYS="$2"; shift 2 ;;
        -t|--since)          SINCE="$2"; shift 2 ;;
        -I|--no-images)      NOIMG="--no-images"; shift ;;
        -i|--images)         NOIMG=""; shift ;;
        -E|--no-inline)      NOINLINE="--no-inline"; shift ;;
        -x|--name-suffix)    SUFFIX="$2"; shift 2 ;;
        -n|--dry-run)        DRYRUN=1; shift ;;
        -h|--help)           usage ;;
        *) echo "$(t "unknown option" "未知参数"): $1" >&2; exit 1 ;;
    esac
done

[ -z "$SRC" ] && { t "missing -s SOURCE (-h for help)" "缺少 -s 源目录（用 -h 查看帮助）" >&2; echo >&2; exit 1; }
[ -z "$OUT" ] && { t "missing -o OUTPUT (-h for help)" "缺少 -o 输出目录（用 -h 查看帮助）" >&2; echo >&2; exit 1; }
[ -d "$SRC" ] || { echo "$(t "source folder not found" "源目录不存在"): $SRC" >&2; exit 1; }
[ -f "$CORE" ] || { echo "$(t "core script not found" "找不到核心脚本"): $CORE" >&2; exit 1; }
command -v python3 >/dev/null 2>&1 || { t "python3 not found" "未找到 python3" >&2; echo >&2; exit 1; }

if [ -n "$DAYS" ] && ! echo "$DAYS" | grep -qE '^[0-9]+$'; then
    echo "$(t "-d/--days must be a positive integer" "-d/--days 应为正整数"): $DAYS" >&2; exit 1
fi
if [ -n "$DAYS" ] && [ -n "$SINCE" ]; then
    t "-d/--days and -t/--since cannot be used together" "-d/--days 与 -t/--since 不能同时使用" >&2; echo >&2; exit 1
fi

mkdir -p "$OUT" 2>/dev/null || { echo "$(t "cannot create the output folder" "无法创建输出目录"): $OUT" >&2; exit 1; }
[ -w "$OUT" ] || { echo "$(t "output folder not writable" "输出目录不可写"): $OUT" >&2; exit 1; }

SRC="$(cd "$SRC" && pwd)"
OUT="$(cd "$OUT" && pwd)"

# The source folder name prefixes the output name; spaces and brackets become underscores.
SRC_TAG="$(basename "$SRC")"
SRC_TAG="$(printf '%s' "$SRC_TAG" | sed -E 's/[[:space:]]+/_/g; s/[(){}]|\[|\]/_/g; s/（|）|【|】|［|］/_/g; s/_+/_/g; s/^_//; s/_$//')"
SRC_TAG="${SRC_TAG#_}"; SRC_TAG="${SRC_TAG%_}"
[ -n "$SRC_TAG" ] && SRC_TAG="${SRC_TAG}_"

STATE="$OUT/.doc2kb_watch_state"
DONE_LIST="$OUT/.doc2kb_watch_done"
# Text fingerprints of filed documents. Files found again after a folder move or rename are
# not filed again when their text is unchanged; the incremental file lists their paths.
FP_DB="$OUT/.doc2kb_watch_fp"
LOG="$OUT/_watch.log"
NOW_TS=$(date '+%Y-%m-%d %H:%M')
NOW_EPOCH=$(date +%s)

log() {
    printf '%s  %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >> "$LOG"
}

# ---------------- start of the time range ----------------
MODE=""
USE_STATE=0

if [ -n "$SINCE" ]; then
    MODE="$(t "from date" "指定起点")"
elif [ -n "$DAYS" ]; then
    SINCE=$(date -d "$DAYS days ago" '+%Y-%m-%d %H:%M' 2>/dev/null)
    if [ -z "$SINCE" ]; then
        t "cannot compute the date: this system's date has no -d option" "无法计算日期，本系统 date 命令不支持 -d 参数" >&2; echo >&2
        exit 1
    fi
    MODE="$(t "last ${DAYS} days" "最近 ${DAYS} 天")"
else
    USE_STATE=1
    MODE="$(t "watermark" "水位")"
    if [ -f "$STATE" ]; then
        SINCE=$(grep -m1 '^last_run=' "$STATE" 2>/dev/null | cut -d= -f2-)
    fi
    if [ -z "$SINCE" ]; then
        {
            t "First run: there is no watermark yet." "首次运行、尚无水位记录。"; echo
            t "Give a starting range with -d N or -t DATE;" "请先用 -d N 或 -t DATE 指定初始范围，"; echo
            t "otherwise every document in the folder would be taken at once." "否则会把目录下全部历史文档一次性纳入。"; echo
            echo "$(t "for example" "例如"):  $0 -s '$SRC' -o '$OUT' -d 7"
            t "After that, runs without a time option carry on by themselves." "跑过一次之后，以后不带时间参数即可自动接续。"; echo
        } >&2
        log "$(t "first run without a watermark; stopped (give -d or -t)" "首次运行缺少水位，已退出（需先指定 -d 或 -t）")"
        exit 3
    fi
fi

# ---------------- dry count: which files this run would take ----------------
SCAN_OUT=$(python3 "$CORE" --batch "$SRC" --scan-only \
    --time-basis newest --since "$SINCE" --lang "$UI_LANG" 2>&1)
RC=$?
if [ $RC -ne 0 ]; then
    t "scan failed:" "扫描失败:" >&2; echo >&2
    echo "$SCAN_OUT" >&2
    log "$(t "scan failed (from $SINCE)" "扫描失败（起点 $SINCE）"): $(echo "$SCAN_OUT" | head -1)"
    exit 2
fi

N_FILT=$(printf '%s\n' "$SCAN_OUT" | grep -c '^FILTERED')
N_LEGACY=$(printf '%s\n' "$SCAN_OUT" | grep -c '^LEGACY')

# candidates: relative path and change time
CAND="$OUT/.doc2kb_watch_cand.$$"
printf '%s\n' "$SCAN_OUT" | grep '^OK' | cut -f2,4 > "$CAND"

# leave out files already processed with the same change time (runs in the same minute)
ONLY_LIST="$OUT/.doc2kb_watch_only.$$"
if [ "$USE_STATE" = "1" ] && [ -s "$DONE_LIST" ]; then
    # grep -v returns 1 when everything is left out: a normal result, not a failure
    grep -vxF -f "$DONE_LIST" "$CAND" > "$CAND.new" 2>/dev/null
    if [ $? -gt 1 ]; then
        cp -f "$CAND" "$CAND.new"      # fall back to all only on a real grep error
    fi
    cut -f1 "$CAND.new" > "$ONLY_LIST"
    rm -f "$CAND.new"
else
    cut -f1 "$CAND" > "$ONLY_LIST"
fi
# Files that failed last time (relative path<TAB>failures so far). They are older than the
# watermark and missing from the scan, so they are added here; the core does not
# date-filter files named with --only.
RETRY_LIST="$OUT/.doc2kb_watch_retry"
# src_exists REL: the file is still there; for a document inside an archive
# ("pack.zip/a/x.docx") the archive holding it counts
src_exists() {
    local p="$1"
    while [ -n "$p" ] && [ "$p" != "." ]; do
        [ -f "$SRC/$p" ] && return 0
        case "$p" in */*) p="${p%/*}" ;; *) return 1 ;; esac
    done
    return 1
}
MAX_TRIES=3
if [ -s "$RETRY_LIST" ]; then
    while IFS=$'\t' read -r rrel _; do
        [ -n "$rrel" ] && src_exists "$rrel" && printf '%s\n' "$rrel"
    done < "$RETRY_LIST" >> "$ONLY_LIST"
    sort -u -o "$ONLY_LIST" "$ONLY_LIST"
fi
N_NEW=$(grep -c . "$ONLY_LIST" 2>/dev/null)
N_NEW=${N_NEW:-0}

# Record this run: the processed list leaves out failed files; failures are counted and
# given up after MAX_TRIES. Argument: the failed relative paths, one per line, maybe empty.
record_done() {
    local failed="$1" tmp="$RETRY_LIST.$$" frel n
    if [ -n "$failed" ]; then
        printf '%s\n' "$failed" | awk -F'\t' 'NR==FNR{f[$0]=1;next} !($1 in f)' - "$CAND" > "$DONE_LIST"
    else
        cp -f "$CAND" "$DONE_LIST" 2>/dev/null
    fi
    : > "$tmp"
    while IFS= read -r frel; do
        [ -n "$frel" ] || continue
        n=$(awk -F'\t' -v k="$frel" '$1==k{print $2; exit}' "$RETRY_LIST" 2>/dev/null)
        n=$(( ${n:-0} + 1 ))
        if [ "$n" -ge "$MAX_TRIES" ]; then
            log "$(t "giving up after ${n} failures (taken again once the file changes)" "放弃重试（已失败 ${n} 次，文件改动后会重新纳入）"): $frel"
        else
            printf '%s\t%s\n' "$frel" "$n" >> "$tmp"
            log "$(t "failed, retried next run (failure ${n})" "处理失败，下次运行重试（第 ${n} 次失败）"): $frel"
        fi
    done <<< "$failed"
    mv -f "$tmp" "$RETRY_LIST"
}

cleanup_tmp() { rm -f "$CAND" "$CAND.new" "$ONLY_LIST"; }
trap cleanup_tmp EXIT

if [ "$DRYRUN" = "1" ]; then
    echo "$(t "mode" "模式"): $MODE    $(t "from" "起点"): $SINCE"
    echo "$(t "to process" "新增待处理"): $N_NEW$(t "" " 份")    $(t "older than the start" "早于起点"): $N_FILT$(t "" " 份")    $(t "legacy format" "旧格式"): $N_LEGACY$(t "" " 份")"
    if [ "$N_NEW" -gt 0 ]; then
        echo "---"
        cat "$ONLY_LIST"
    fi
    exit 0
fi

# ---------------- nothing new: exit quietly ----------------
if [ "$N_NEW" -eq 0 ]; then
    log "$(t "nothing new" "无新增")$LP$(t "mode" "模式")=$MODE $(t "from" "起点")=$SINCE $(t "older" "早于起点")=$N_FILT $(t "legacy" "旧格式")=$N_LEGACY$RP"
    # move the watermark: this range has been checked
    printf 'last_run=%s\n' "$NOW_TS" > "$STATE"
    record_done ""
    exit 0
fi

# ---------------- this run's incremental md ----------------
NAME="${SRC_TAG}$(date '+%Y%m%d')_${SUFFIX}"
if [ -e "$OUT/${NAME}.md" ]; then
    NAME="${SRC_TAG}$(date '+%Y%m%d-%H%M')_${SUFFIX}"
fi

# shellcheck disable=SC2086  # NOIMG and NOINLINE are empty or one option each
RUN_OUT=$(python3 "$CORE" --batch "$SRC" -o "$OUT" \
    --time-basis newest --since "$SINCE" --only "$ONLY_LIST" --lang "$UI_LANG" \
    --merge --merge-name "$NAME" --fp-db "$FP_DB" $NOIMG $NOINLINE 2>&1)
RC=$?

ELAPSED=$(( $(date +%s) - NOW_EPOCH ))

if [ $RC -eq 10 ]; then
    # in the scan but gone when processed (rare: usually a file just moved away)
    log "$(t "nothing new (empty on second look)" "无新增（复查后为空）")$LP$(t "mode" "模式")=$MODE $(t "from" "起点")=$SINCE$RP"
    printf 'last_run=%s\n' "$NOW_TS" > "$STATE"
    record_done ""
    exit 0
fi

if [ $RC -ne 0 ]; then
    t "processing failed:" "处理失败:" >&2; echo >&2
    echo "$RUN_OUT" >&2
    log "$(t "processing failed" "处理失败")$LP$(t "mode" "模式")=$MODE $(t "from" "起点")=$SINCE $(t "to process" "待处理")=$N_NEW$RP: $(echo "$RUN_OUT" | tail -1)"
    # the watermark stays, so the next run tries this range again
    exit 2
fi

# name the report and image list after this batch so the next run does not overwrite them
REPORT_OUT="${NAME}_$(t "report.txt" "报告.txt")"
IMGLIST_OUT="${NAME}_$(t "image-list.md" "图片清单.md")"
for pair in "$REPORT_FILE:$REPORT_OUT" "$IMGLIST_FILE:$IMGLIST_OUT"; do
    from="$OUT/${pair%%:*}"
    to="$OUT/${pair##*:}"
    [ -f "$from" ] && mv -f "$from" "$to"
done

# figures from the core's STAT lines
CHARS=$(stat_of chars "$RUN_OUT")
WRITTEN=$(stat_of written "$RUN_OUT")
DEDUP=$(stat_of dup "$RUN_OUT")
[ -n "$WRITTEN" ] && N_NEW="$WRITTEN"
IMGS=$(stat_of images "$RUN_OUT")
FAILN=$(stat_of failed "$RUN_OUT")
MOVED=$(stat_of moved "$RUN_OUT")
MOVED=${MOVED:-0}

if [ "${WRITTEN:-}" = "0" ] && [ "$MOVED" = "0" ]; then
    # only retried files that failed again: no empty incremental file; the report stays (with reasons)
    rm -f "$OUT/${NAME}.md" "$OUT/$IMGLIST_OUT"
    log "$(t "no new documents; only ${FAILN:-0} retried files failed again" "无新增文档，仅重试失败 ${FAILN:-0} 份")$LP$(t "report" "报告")$(t ": " "：")$REPORT_OUT$(t ", " "，")$(t "mode" "模式")=$MODE $(t "from" "起点")=$SINCE $(t "time" "耗时")=${ELAPSED}s$RP"
else
    log "$(t "wrote" "生成") ${NAME}.md$LP$(t "mode" "模式")=$MODE $(t "from" "起点")=$SINCE $(t "documents" "文档")=${N_NEW} $(t "duplicates" "重复略去")=${DEDUP:-0} $(t "moved" "位置变动略去")=${MOVED} $(t "characters" "字符")=${CHARS:-0} $(t "images" "图片")=${IMGS:-0} $(t "failed" "失败")=${FAILN:-0} $(t "time" "耗时")=${ELAPSED}s$RP"
fi

# move the watermark (after any successful run, so plain runs carry on); failed files go to the retry list
printf 'last_run=%s\n' "$NOW_TS" > "$STATE"
record_done "$(printf '%s\n' "$RUN_OUT" | grep $'^FAILED\t' | cut -f2)"

if [ "${WRITTEN:-}" = "0" ] && [ "$MOVED" = "0" ]; then
    t "No new documents; the ${FAILN:-0} retried files failed again, see $OUT/$REPORT_OUT" \
      "无新增文档；重试的 ${FAILN:-0} 份仍失败，详见 $OUT/$REPORT_OUT"; echo
elif [ "$MOVED" -gt 0 ] 2>/dev/null; then
    t "Wrote $OUT/${NAME}.md (${N_NEW} documents, ${CHARS:-0} characters; ${MOVED} more were only moved and are listed with their paths; ${DEDUP:-0} duplicates left out)" \
      "已生成: $OUT/${NAME}.md（${N_NEW} 份文档，${CHARS:-0} 字符；另有 ${MOVED} 份正文已入库、仅位置变动，只列路径对照；重复略去 ${DEDUP:-0} 份）"; echo
elif [ -n "$DEDUP" ] && [ "$DEDUP" -gt 0 ] 2>/dev/null; then
    t "Wrote $OUT/${NAME}.md (${N_NEW} documents, ${CHARS:-0} characters; ${DEDUP} duplicates left out)" \
      "已生成: $OUT/${NAME}.md（${N_NEW} 份文档，${CHARS:-0} 字符；另有 ${DEDUP} 份重复已略去）"; echo
else
    t "Wrote $OUT/${NAME}.md (${N_NEW} documents, ${CHARS:-0} characters)" \
      "已生成: $OUT/${NAME}.md（${N_NEW} 份文档，${CHARS:-0} 字符）"; echo
fi
exit 0

fi
# ================ desktop dialogs (no arguments) ================


# ---------- environment ----------
if ! command -v zenity >/dev/null 2>&1; then
    t "zenity not found; install it: sudo apt install zenity" "未找到 zenity，请安装: sudo apt install zenity"; echo
    exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
    zenity --error --title="$TITLE" --text="$(t "python3 not found" "未找到 python3")"
    exit 1
fi

if [ ! -f "$CORE" ]; then
    zenity --error --title="$TITLE" \
        --text="$(t "Core script not found:\n$CORE\n\nKeep doc2kb_core.py in the same folder as this script\n(the name has an underscore, not a space)." \
                    "找不到核心脚本:\n$CORE\n\n请把 doc2kb_core.py 和本脚本放在同一目录\n（注意文件名是下划线，不是空格）。")"
    exit 1
fi

HAS_POPPLER=0
command -v pdftotext >/dev/null 2>&1 && HAS_POPPLER=1

TMPDIR_WORK=$(mktemp -d)
cleanup() { rm -rf "$TMPDIR_WORK"; }
trap cleanup EXIT

M_BATCH="$(t "Folder batch" "目录批量")"
M_FILES="$(t "Chosen files" "指定文件")"
M_WATCH="$(t "Incremental tasks" "增量监控")"

# ---------- 0. mode ----------
MODE=$(zenity --list --radiolist \
    --title="$TITLE — $(t "Mode" "选择模式")" \
    --text="$(t "What do you want to process?" "要处理什么？")" \
    --column="$(t "Pick" "选择")" --column="$(t "Mode" "模式")" --column="$(t "Description" "说明")" \
    TRUE  "$M_BATCH" "$(t "Choose a folder; every document in it is found, you confirm, then all are processed" "选一个目录，递归找出全部文档，确认后批量处理")" \
    FALSE "$M_FILES" "$(t "Choose one or more files (Ctrl for several)" "手工选择一个或多个文件（Ctrl 多选）")" \
    FALSE "$M_WATCH" "$(t "Manage and run incremental tasks: only documents changed since the last run" "管理并运行增量任务，只处理上次之后修改的文档")" \
    --height=270 --width=640 2>/dev/null)
[ $? -ne 0 ] && exit 0
[ -z "$MODE" ] && exit 0

FILTER="$(t "Office / PDF / mail / archives" "Office / PDF / 邮件 / 压缩包") | *.docx *.xlsx *.xlsm *.pptx *.pdf *.eml *.DOCX *.XLSX *.PPTX *.PDF *.EML *.zip *.ZIP *.tar *.tgz *.tar.gz *.tbz2 *.tar.bz2 *.txz *.tar.xz"

# ================================================================
#                        incremental tasks
# ================================================================
if [ "$MODE" = "$M_WATCH" ]; then

    # runs reuse this script's command-line mode
    WATCH="${BASH_SOURCE[0]}"

    CONF_DIR="$HOME/.config/doc2kb"
    CONF="$CONF_DIR/watch_tasks.conf"
    mkdir -p "$CONF_DIR" 2>/dev/null
    [ -f "$CONF" ] || : > "$CONF"

    B_ALL="$(t "Run all" "全部执行")"
    B_ADD="$(t "Add" "新增")"
    B_EDIT="$(t "Edit" "编辑")"
    B_DEL="$(t "Delete" "删除")"

    # ---------- tasks file ----------
    # one task per line: name<TAB>source folder<TAB>output folder
    task_count() { grep -c '.' "$CONF" 2>/dev/null || echo 0; }

    add_task() {
        local name src out
        name=$(zenity --entry --title="$TITLE — $(t "New task" "新增任务")" \
            --text="$(t "A name for this task" "给这条任务起个名字（便于识别）")" 2>/dev/null) || return 1
        [ -z "$name" ] && return 1
        name=$(printf '%s' "$name" | tr -d '\t')
        if awk -F'\t' -v n="$name" '$1==n{f=1} END{exit !f}' "$CONF"; then
            zenity --error --text="$(t "A task named \"$name\" exists already" "任务名「$name」已存在")" 2>/dev/null
            return 1
        fi
        src=$(zenity --file-selection --directory \
            --title="$TITLE — $(t "Source folder (the documents to watch)" "选择源目录（要监控的文档目录）")" 2>/dev/null) || return 1
        [ -z "$src" ] && return 1
        out=$(zenity --file-selection --directory \
            --title="$TITLE — $(t "Output folder (for the incremental md files)" "选择输出目录（增量 md 存放处）")" 2>/dev/null) || return 1
        [ -z "$out" ] && return 1
        printf '%s\t%s\t%s\n' "$name" "$src" "$out" >> "$CONF"
        return 0
    }

    edit_task() {
        local old="$1" name src out oldsrc oldout
        oldsrc=$(awk -F'\t' -v n="$old" '$1==n{print $2; exit}' "$CONF")
        oldout=$(awk -F'\t' -v n="$old" '$1==n{print $3; exit}' "$CONF")
        name=$(zenity --entry --title="$TITLE — $(t "Edit task" "编辑任务")" \
            --text="$(t "Task name" "任务名")" --entry-text="$old" 2>/dev/null) || return 1
        [ -z "$name" ] && return 1
        name=$(printf '%s' "$name" | tr -d '\t')
        src=$(zenity --file-selection --directory \
            --title="$TITLE — $(t "Source folder (now: $oldsrc)" "源目录（当前: $oldsrc）")" \
            --filename="$oldsrc/" 2>/dev/null) || return 1
        out=$(zenity --file-selection --directory \
            --title="$TITLE — $(t "Output folder (now: $oldout)" "输出目录（当前: $oldout）")" \
            --filename="$oldout/" 2>/dev/null) || return 1
        awk -F'\t' -v OFS='\t' -v o="$old" -v n="$name" -v s="$src" -v u="$out" \
            '$1==o{$1=n; $2=s; $3=u} {print}' "$CONF" > "$CONF.tmp" \
            && mv -f "$CONF.tmp" "$CONF"
        return 0
    }

    del_task() {
        local name="$1"
        zenity --question --title="$TITLE" \
            --text="$(t "Delete the task \"$name\"?\n\nOnly the task is removed; md files already written stay." \
                        "确定删除任务「$name」？\n\n只删除任务配置，已生成的 md 文件不受影响。")" \
            2>/dev/null || return 1
        awk -F'\t' -v n="$name" '$1!=n' "$CONF" > "$CONF.tmp" \
            && mv -f "$CONF.tmp" "$CONF"
        return 0
    }

    # ---------- run tasks ----------
    run_tasks() {
        local list="$1" RESULT="$2" total i=0
        total=$(grep -c '.' "$list")
        [ "$total" -eq 0 ] && return 0
        : > "$RESULT"

        while IFS=$'\t' read -r name src out; do
            [ -z "$name" ] && continue
            i=$((i+1))
            echo $(( (i-1) * 100 / total ))
            echo "# [$i/$total] $name"

            if [ ! -d "$src" ]; then
                printf '%s: %s (%s)\n' "$name" "$(t "source folder not found" "源目录不存在")" "$src" >> "$RESULT"
                continue
            fi
            mkdir -p "$out" 2>/dev/null

            local o rc
            o=$(bash "$WATCH" -s "$src" -o "$out" 2>&1)
            rc=$?

            # first run without a watermark: start with the last 30 days
            if [ $rc -eq 3 ]; then
                echo "# [$i/$total] $name ($(t "first run, last 30 days" "首次运行，初始化最近 30 天"))"
                o=$(bash "$WATCH" -s "$src" -o "$out" -d 30 2>&1)
                rc=$?
                printf '%s: %s\n' "$name" "$(t "first run, started with the last 30 days" "首次运行，已初始化最近 30 天")" >> "$RESULT"
            fi

            if [ $rc -ne 0 ]; then
                printf '%s: %s — %s\n' "$name" "$(t "failed" "失败")" \
                    "$(printf '%s' "$o" | tail -1)" >> "$RESULT"
            elif [ -n "$o" ]; then
                printf '%s: %s\n' "$name" "$(printf '%s' "$o" | tail -1)" >> "$RESULT"
            else
                printf '%s: %s\n' "$name" "$(t "nothing new" "无新增")" >> "$RESULT"
            fi
        done < "$list"

        echo "100"; echo "# $(t "Done" "完成")"
    }

    # ---------- main loop ----------
    while true; do
        N_TASK=$(task_count)

        if [ "$N_TASK" -eq 0 ]; then
            zenity --question --title="$TITLE — $M_WATCH" \
                --text="$(t "There are no incremental tasks yet.\n\nA task remembers when it last ran and only processes documents changed since then.\n\nCreate one now?" \
                            "还没有任何增量任务。\n\n增量任务会记住上次运行时刻，每次只处理之后修改过的文档。\n\n现在新建一条？")" \
                --ok-label="$(t "New task" "新建任务")" --cancel-label="$(t "Back" "返回")" --width=440 2>/dev/null \
                || exit 0
            add_task
            continue
        fi

        LIST_ROWS=()
        while IFS=$'\t' read -r name src out; do
            [ -z "$name" ] && continue
            LIST_ROWS+=(FALSE "$name" "$src" "$out")
        done < "$CONF"

        SEL=$(zenity --list --radiolist \
            --title="$TITLE — $(t "Incremental tasks ($N_TASK)" "增量任务（共 $N_TASK 条）")" \
            --text="$(t "Pick a task to run, edit or delete it, or run all without picking." "选中一条后可执行/编辑/删除；不选也可直接「全部执行」。")" \
            --column="$(t "Pick" "选择")" --column="$(t "Task" "任务名")" --column="$(t "Source folder" "源目录")" --column="$(t "Output folder" "输出目录")" \
            "${LIST_ROWS[@]}" \
            --extra-button="$B_ALL" \
            --extra-button="$B_ADD" \
            --extra-button="$B_EDIT" \
            --extra-button="$B_DEL" \
            --ok-label="$(t "Run selected" "执行选中")" --cancel-label="$(t "Quit" "退出")" \
            --height=460 --width=880 2>/dev/null)
        RC=$?

        case "$SEL" in
            "$B_ADD") add_task; continue ;;
            "$B_EDIT"|"$B_DEL")
                PICK_ROWS=()
                while IFS=$'\t' read -r n s2 _; do
                    [ -z "$n" ] && continue
                    PICK_ROWS+=(FALSE "$n" "$s2")
                done < "$CONF"
                PICK=$(zenity --list --radiolist \
                    --title="$TITLE — $(t "Task to ${SEL,,}" "选择要${SEL}的任务")" \
                    --column="$(t "Pick" "选择")" --column="$(t "Task" "任务名")" --column="$(t "Source folder" "源目录")" \
                    "${PICK_ROWS[@]}" \
                    --height=400 --width=680 2>/dev/null)
                if [ -n "$PICK" ]; then
                    if [ "$SEL" = "$B_EDIT" ]; then edit_task "$PICK"
                    else del_task "$PICK"; fi
                fi
                continue ;;
            "$B_ALL")
                RUN_LIST=$(mktemp)
                cp -f "$CONF" "$RUN_LIST"
                ;;
            *)
                if [ $RC -ne 0 ]; then
                    exit 0
                fi
                if [ -z "$SEL" ]; then
                    zenity --warning --text="$(t "No task selected" "没有选中任务")" 2>/dev/null
                    continue
                fi
                RUN_LIST=$(mktemp)
                awk -F'\t' -v n="$SEL" '$1==n' "$CONF" > "$RUN_LIST"
                ;;
        esac

        RESFILE=$(mktemp)
        run_tasks "$RUN_LIST" "$RESFILE" | zenity --progress \
            --title="$TITLE — $(t "Running" "增量处理中")" \
            --text="$(t "Preparing..." "准备中...")" --percentage=0 \
            --auto-close --width=520 2>/dev/null
        rm -f "$RUN_LIST"

        if [ ! -s "$RESFILE" ]; then
            t "No task was run." "本次没有执行任何任务。" > "$RESFILE"; echo >> "$RESFILE"
        fi
        zenity --text-info --title="$TITLE — $(t "Results" "执行结果")" \
            --filename="$RESFILE" --width=700 --height=400 \
            --ok-label="$(t "Back to tasks" "返回任务列表")" --cancel-label="$(t "Quit" "退出")" 2>/dev/null
        RC2=$?
        rm -f "$RESFILE"
        [ $RC2 -ne 0 ] && exit 0
    done
fi

# ---------- 0.5 date filter ----------
SINCE_ARG=()
SINCE_DATE=""
zenity --question --title="$TITLE — $(t "Date filter" "日期过滤")" \
    --text="$(t "Only process documents changed after a date?\n\n(The document's own time is used when it has one, else the file system time.)" \
                "是否只处理某个日期之后修改的文档？\n\n（时间优先取文档内部属性，取不到时用文件系统时间）")" \
    --ok-label="$(t "Filter by date" "按日期过滤")" --cancel-label="$(t "No filter, process all" "不过滤，全部处理")" \
    --width=440 2>/dev/null

if [ $? -eq 0 ]; then
    # three months back by default
    DEF_Y=$(date -d '3 months ago' +%Y 2>/dev/null || date +%Y)
    DEF_M=$(date -d '3 months ago' +%m 2>/dev/null || date +%m)
    DEF_D=$(date -d '3 months ago' +%d 2>/dev/null || date +%d)
    SINCE_DATE=$(zenity --calendar \
        --title="$TITLE — $(t "Start date" "选择起始日期")" \
        --text="$(t "Only documents changed on or after this date" "只处理该日期（含当天）之后修改的文档")" \
        --year="$DEF_Y" --month="${DEF_M#0}" --day="${DEF_D#0}" \
        --date-format="%Y-%m-%d" 2>/dev/null)
    if [ -n "$SINCE_DATE" ]; then
        SINCE_ARG=(--since "$SINCE_DATE")
    fi
fi

# ================================================================
#                        folder batch
# ================================================================
if [ "$MODE" = "$M_BATCH" ]; then

    SRC_DIR=$(zenity --file-selection --directory \
        --title="$TITLE — $(t "Folder to process" "选择要处理的目录")" 2>/dev/null)
    [ -z "$SRC_DIR" ] && exit 0

    # --- scan ---
    SCAN="$TMPDIR_WORK/scan.tsv"
    ( python3 "$CORE" --batch "$SRC_DIR" --scan-only "${SINCE_ARG[@]}" --lang "$UI_LANG" \
        > "$SCAN" 2>"$TMPDIR_WORK/err" ) &
    SCAN_PID=$!
    (
        echo "10"; echo "# $(t "Scanning the folder..." "正在递归扫描目录...")"
        while kill -0 $SCAN_PID 2>/dev/null; do sleep 0.3; done
        echo "100"
    ) | zenity --progress --title="$TITLE" --text="$(t "Scanning..." "扫描中...")" \
            --percentage=0 --auto-close --no-cancel --width=380 2>/dev/null
    wait $SCAN_PID

    N_OK=$(grep -c '^OK' "$SCAN" 2>/dev/null || echo 0)
    N_LEGACY=$(grep -c '^LEGACY' "$SCAN" 2>/dev/null || echo 0)
    N_FILT=$(grep -c '^FILTERED' "$SCAN" 2>/dev/null || echo 0)

    if [ "$N_OK" -eq 0 ]; then
        MSG="$(t "No document to process in this folder." "在该目录下没有找到可处理的文档。")"
        [ "$N_FILT" -gt 0 ] && MSG="$MSG\n\n$(t "$N_FILT files were excluded as older than $SINCE_DATE." "有 $N_FILT 个文件因早于 $SINCE_DATE 被排除。")"
        [ "$N_LEGACY" -gt 0 ] && MSG="$MSG\n\n$(t "Found $N_LEGACY files in a legacy format (.doc/.xls/.ppt/.msg);\nsave them in a new format first." "但发现 $N_LEGACY 个旧版格式文件(.doc/.xls/.ppt/.msg)，\n需先另存为新格式。")"
        zenity --warning --title="$TITLE" --text="$MSG" --width=400 2>/dev/null
        exit 1
    fi

    # --- confirm the list (untick to leave out) ---
    LIST_ARGS=()
    while IFS=$'\t' read -r kind rel size; do
        [ "$kind" = "OK" ] || continue
        LIST_ARGS+=(TRUE "$rel" "$size")
    done < "$SCAN"

    TEXT="$(t "Found $N_OK documents" "共找到 $N_OK 个可处理文档")"
    [ "$N_LEGACY" -gt 0 ] && TEXT="$TEXT$(t "; $N_LEGACY legacy-format files will be skipped" "，另有 $N_LEGACY 个旧格式文件将被跳过")"
    TEXT="$TEXT$(t "." "。")"
    [ -n "$SINCE_DATE" ] && TEXT="$TEXT\n$(t "Date filter: changed after $SINCE_DATE only; $N_FILT excluded." "已按日期过滤：仅 $SINCE_DATE 之后修改，排除了 $N_FILT 个。")"
    TEXT="$TEXT\n$(t "Untick the files you do not want." "取消勾选可排除不想处理的文件。")"
    SEL=$(zenity --list --checklist \
        --title="$TITLE — $(t "Files to process" "确认要处理的文件")" \
        --text="$TEXT" \
        --column="$(t "Process" "处理")" --column="$(t "Relative path" "相对路径")" --column="$(t "Size" "大小")" \
        "${LIST_ARGS[@]}" \
        --separator=$'\n' --height=520 --width=760 2>/dev/null)
    [ $? -ne 0 ] && exit 0

    if [ -z "$SEL" ]; then
        zenity --warning --title="$TITLE" --text="$(t "No file ticked" "没有勾选任何文件")" 2>/dev/null
        exit 0
    fi

    ONLY="$TMPDIR_WORK/only.txt"
    printf '%s\n' "$SEL" > "$ONLY"
    N_SEL=$(grep -c . "$ONLY")

    if [ "$N_LEGACY" -gt 0 ]; then
        LEGACY_LIST=$(grep '^LEGACY' "$SCAN" | cut -f2 | head -10)
        zenity --warning --title="$TITLE" \
            --text="$(t "These legacy binary files cannot be processed; the report lists them under \"Need a new format first\":\n\n$LEGACY_LIST\n\nSave them as .docx/.xlsx/.pptx and run again." \
                        "以下旧版二进制文件无法处理，将记入报告的「需先转格式」清单：\n\n$LEGACY_LIST\n\n请用 WPS 另存为 .docx/.xlsx/.pptx 后重新运行。")" \
            --width=520 2>/dev/null
    fi

    if grep -qiE '\.pdf$' "$ONLY"; then
        if [ $HAS_POPPLER -eq 0 ]; then
            zenity --error --title="$TITLE" \
                --text="$(t "The selection holds PDF files, which need poppler-utils\n\nsudo apt install poppler-utils" "所选文件含 PDF，需要 poppler-utils\n\nsudo apt install poppler-utils")"
            exit 1
        fi
        zenity --warning --title="$TITLE" \
            --text="$(t "The selection holds PDF files.\n\nPDF is a lossy intermediate format: embedded workbooks are lost,\nvector graphics cannot be extracted and heading levels are gone.\n\nUse the original docx/pptx if you have it." \
                        "所选文件含 PDF。\n\nPDF 是有损中间格式：嵌入的 Excel 附件已丢失、\n矢量图无法提取、标题层级已丢失。\n\n如能拿到原始 docx/pptx，建议改用原始文件。")" \
            --width=440 2>/dev/null
    fi

    # --- output folder ---
    OUT_BASE=$(zenity --file-selection --directory \
        --title="$TITLE — $(t "Output folder (all md files go here)" "选择输出目录（md 将全部平铺在此）")" \
        --filename="$SRC_DIR/" 2>/dev/null)
    [ -z "$OUT_BASE" ] && exit 0
    [ -w "$OUT_BASE" ] || { zenity --error --text="$(t "Output folder not writable" "输出目录不可写")"; exit 1; }

    BATCH_MODE=1

# ================================================================
#                        chosen files
# ================================================================
else
    FILE_LIST=$(zenity --file-selection \
        --title="$TITLE — $(t "Choose files (several allowed)" "选择文件（可多选）")" \
        --file-filter="$FILTER" \
        --file-filter="$(t "All files" "所有文件") | *" \
        --multiple --separator="|" 2>/dev/null)
    [ -z "$FILE_LIST" ] && exit 0
    IFS='|' read -ra FILES <<< "$FILE_LIST"
    N_SEL=${#FILES[@]}

    for f in "${FILES[@]}"; do
        case "${f,,}" in
            *.doc|*.xls|*.ppt|*.msg)
                zenity --error --title="$TITLE" \
                    --text="$(t "Legacy binary format:\n$(basename "$f")\n\nSave it as .docx / .xlsx / .pptx / .eml first" "检测到旧版二进制格式:\n$(basename "$f")\n\n请先另存为 .docx / .xlsx / .pptx / .eml")"
                exit 1 ;;
        esac
    done

    HAS_PDF=0
    for f in "${FILES[@]}"; do
        case "${f,,}" in *.pdf) HAS_PDF=1 ;; esac
    done
    if [ $HAS_PDF -eq 1 ]; then
        if [ $HAS_POPPLER -eq 0 ]; then
            zenity --error --title="$TITLE" \
                --text="$(t "PDF files need poppler-utils\n\nsudo apt install poppler-utils" "处理 PDF 需要 poppler-utils\n\nsudo apt install poppler-utils")"
            exit 1
        fi
        zenity --warning --title="$TITLE" \
            --text="$(t "You chose PDF files.\n\nPDF is a lossy intermediate format:\n  • embedded workbooks are lost\n  • vector graphics cannot be extracted\n  • heading levels are gone\n\nIf you can get the original docx/pptx, use it instead." \
                        "你选择了 PDF 文件。\n\nPDF 是有损中间格式：\n  • 嵌入的 Excel 附件已经丢失\n  • 矢量图无法提取\n  • 标题层级已经丢失\n\n如果能拿到原始 docx/pptx，强烈建议改用原始文件。")" \
            --width=420 2>/dev/null
    fi

    OUT_BASE=$(zenity --file-selection --directory \
        --title="$TITLE — $(t "Output folder" "选择输出目录")" \
        --filename="$(dirname "${FILES[0]}")/" 2>/dev/null)
    [ -z "$OUT_BASE" ] && exit 0
    [ -w "$OUT_BASE" ] || { zenity --error --text="$(t "Output folder not writable" "输出目录不可写")"; exit 1; }

    BATCH_MODE=0
fi

# ---------- common options ----------
O_MERGE="$(t "Merge" "合并输出")"
O_KBB="$(t "KB batch files" "知识库批文件")"
O_INLINE="$(t "Expand workbooks" "内联Excel")"
O_NOIMG="$(t "Skip images" "跳过图片")"
O_NODEDUP="$(t "Keep duplicates" "不去重")"
O_SHEETS="$(t "Contact sheets" "合并拼图")"
OPTS=$(zenity --list --checklist \
    --title="$TITLE — $(t "Options" "选项")" \
    --text="$(t "$N_SEL files to process" "待处理 $N_SEL 个文件")" \
    --column="$(t "Pick" "选择")" --column="$(t "Option" "选项")" --column="$(t "Description" "说明")" \
    TRUE  "$O_MERGE"   "$(t "Index and all text in one md (untick: one md per document)" "索引与全部正文合并成单个 md（取消则每份一个 md）")" \
    FALSE "$O_KBB"     "$(t "Batch files for knowledge-base intake: source numbers, paragraph anchors, no pictures (replaces Merge)" "供知识库入库的批文件：来源编号、段落锚点、不导出图片（代替合并输出）")" \
    TRUE  "$O_INLINE"  "$(t "Expand workbooks embedded in docx into the text (recommended)" "把 docx 里嵌入的 Excel 附件展开到正文（推荐）")" \
    FALSE "$O_NOIMG"   "$(t "Export no picture files; the anchors stay; faster" "不导出图片文件，正文仍保留图锚点，处理更快")" \
    FALSE "$O_NODEDUP" "$(t "Keep every copy (by default files with the same text are kept once, the newest)" "保留全部副本（默认对正文相同的文件只保留最新一份）")" \
    FALSE "$O_SHEETS"  "$(t "Tile pictures 4×4 into numbered sheets for browsing" "把提取的图按 4×4 拼成大图，带编号，便于浏览")" \
    --separator="|" --height=360 --width=660 2>/dev/null)
[ $? -ne 0 ] && exit 0

has_opt() { printf '|%s|' "$OPTS" | grep -qF "|$1|"; }
RUN_ARGS=(--lang "$UI_LANG" "${SINCE_ARG[@]}")
KBB=0
if has_opt "$O_KBB"; then
    TIER=$(zenity --list --radiolist \
        --title="$TITLE — $(t "Tier" "档位")" \
        --text="$(t "Which assistant ingests these batch files?" "这些批文件交给哪一档模型入库？")" \
        --column="$(t "Pick" "选择")" --column="$(t "Tier" "档位")" --column="$(t "Description" "说明")" \
        TRUE  weak   "$(t "Models with limited reasoning, such as local models through OpenCode: 20,000 characters per batch" "推理能力有限的模型，如通过 OpenCode 运行的本地模型：每批 2 万字符")" \
        FALSE strong "$(t "Claude or ChatGPT clients: 100,000 characters per batch" "Claude、ChatGPT 客户端：每批 10 万字符")" \
        --height=260 --width=660 2>/dev/null)
    [ -z "$TIER" ] && exit 0
    KBB=1
    RUN_ARGS+=(--kb-batch --tier "$TIER")
elif has_opt "$O_MERGE"; then
    RUN_ARGS+=(--merge)
fi
has_opt "$O_INLINE" || RUN_ARGS+=(--no-inline)
NOIMG=0;  has_opt "$O_NOIMG" && NOIMG=1
[ "$KBB" = "1" ] && NOIMG=1
[ "$NOIMG" = "1" ] && [ "$KBB" = "0" ] && RUN_ARGS+=(--no-images)
has_opt "$O_NODEDUP" && RUN_ARGS+=(--no-dedup)
SHEETS=0; has_opt "$O_SHEETS" && SHEETS=1

if [ "$BATCH_MODE" = "1" ] && [ "$KBB" = "0" ] && ! has_opt "$O_MERGE"; then
    zenity --question --title="$TITLE" \
        --text="$(t "One md per document.\n\nResults already in the output folder are skipped by default (incremental).\nProcess everything again?" \
                    "检测到「每份独立」模式。\n\n输出目录中已有的结果默认会被跳过（增量）。\n是否强制全部重新处理？")" \
        --ok-label="$(t "Redo all" "强制重做")" --cancel-label="$(t "Skip existing" "跳过已有")" --width=400 2>/dev/null
    [ $? -eq 0 ] && RUN_ARGS+=(--force)
fi

# skipping images rules out contact sheets
if [ "$NOIMG" = "1" ] && [ "$SHEETS" = "1" ] && [ "$KBB" = "1" ]; then
    SHEETS=0
elif [ "$NOIMG" = "1" ] && [ "$SHEETS" = "1" ]; then
    zenity --warning --title="$TITLE" \
        --text="$(t "\"$O_NOIMG\" and \"$O_SHEETS\" conflict.\n\nThis run skips images and makes no contact sheets." "「跳过图片」与「合并拼图」冲突。\n\n本次将跳过图片，不生成拼图。")" 2>/dev/null
    SHEETS=0
fi

if [ "$SHEETS" = "1" ] && ! command -v montage >/dev/null 2>&1; then
    zenity --warning --title="$TITLE" \
        --text="$(t "Contact sheets need ImageMagick (montage), which was not found.\nThe option is skipped." "合并拼图需要 ImageMagick (montage 命令)，未检测到。\n该选项将被跳过。")" 2>/dev/null
    SHEETS=0
fi
[ "$SHEETS" = "1" ] && RUN_ARGS+=(--sheets)

# ---------- run ----------
LOG="$TMPDIR_WORK/run.log"
: > "$LOG"

# progress_from_output: turn the core's "[i/n] name" lines into zenity progress lines
progress_from_output() {
    while IFS= read -r line; do
        if [[ "$line" =~ ^\[([0-9]+)/([0-9]+)\][[:space:]]*(.*)$ ]]; then
            cur="${BASH_REMATCH[1]}"; tot="${BASH_REMATCH[2]}"
            echo $(( (cur - 1) * 100 / tot ))
            echo "# [$cur/$tot] ${BASH_REMATCH[3]}"
        fi
    done
}

if [ "$BATCH_MODE" = "1" ]; then
    (
        python3 -u "$CORE" --batch "$SRC_DIR" -o "$OUT_BASE" --only "$ONLY" "${RUN_ARGS[@]}" \
            2>&1 | tee "$LOG" | progress_from_output
        echo "100"; echo "# $(t "Writing the report and index..." "正在生成汇总与索引...")"
    ) | zenity --progress \
            --title="$TITLE — $(t "Processing" "批量处理中")" \
            --text="$(t "Preparing..." "准备中...")" --percentage=0 \
            --auto-close --width=560 2>/dev/null
    RC_RUN=$?
else
    FLIST="$TMPDIR_WORK/files.txt"
    : > "$FLIST"
    for f in "${FILES[@]}"; do printf '%s\n' "$f" >> "$FLIST"; done

    (
        python3 -u "$CORE" --files "$FLIST" -o "$OUT_BASE" "${RUN_ARGS[@]}" \
            2>&1 | tee "$LOG" | progress_from_output
        echo "100"; echo "# $(t "Writing the report..." "正在生成汇总...")"
    ) | zenity --progress \
            --title="$TITLE — $(t "Processing" "处理中")" \
            --text="$(t "Preparing..." "准备中...")" --percentage=0 \
            --auto-close --width=520 2>/dev/null
    RC_RUN=$?
fi

if [ $RC_RUN -ne 0 ]; then
    zenity --warning --title="$TITLE" \
        --text="$(t "Cancelled.\n\nFiles already processed and the report are saved in the output folder;\nthe next run skips them." "已取消。\n\n已处理完的文件和报告都已保存在输出目录，\n下次运行会自动跳过它们。")" \
        --width=420 2>/dev/null
    exit 1
fi

# ---------- result ----------
RESULT="$LOG"
if [ -f "$OUT_BASE/$REPORT_FILE" ]; then
    RESULT="$TMPDIR_WORK/result.txt"
    LOGS_HEAD="$(t "Log per document" "各文档处理日志")"
    {
        awk -v h="$LOGS_HEAD" '$0==h{exit} {print}' "$OUT_BASE/$REPORT_FILE"
        echo
        t "(The full log is in $REPORT_FILE in the output folder.)" "（完整日志见输出目录的 $REPORT_FILE）"; echo
    } > "$RESULT"
fi

zenity --text-info \
    --title="$TITLE — $(t "Result" "处理结果")" \
    --filename="$RESULT" \
    --width=760 --height=520 \
    --ok-label="$(t "Open output folder" "打开输出目录")" \
    --cancel-label="$(t "Close" "关闭")" 2>/dev/null
RC=$?

[ $RC -eq 0 ] && xdg-open "$OUT_BASE" >/dev/null 2>&1 &
exit 0
