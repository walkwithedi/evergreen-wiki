#!/usr/bin/env python3
"""Build the workbench bundle from a repository zip.

The bundle holds, at its top level, the workbench entry (tools/workbench/启动OpenCode工作台.desktop,
listed first and executable) and the repository folder evergreen-wiki/ exactly as in the
repository zip. The entry finds the wizard in evergreen-wiki/tools/workbench/ next to it.

Usage:
  python3 scripts/build_workbench.py dist/evergreen-wiki-v3.0.0.zip dist/workbench-bundle-v3.0.0.zip

Exit code 2 when the repository zip lacks the entry or a tool the wizard needs.
"""
import argparse
import logging
import os
import sys
import zipfile

log = logging.getLogger("build_workbench")
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s.%(funcName)s:%(lineno)d - %(message)s"
PREFIX = "evergreen-wiki/"
LAUNCHER = "启动OpenCode工作台.desktop"
NEEDED = ("tools/workbench/wk_web.py", "tools/workbench/" + LAUNCHER, "tools/opencode-setup/ca_web.py",
          "tools/kb-client/kb_client.py")


def build(src, dest):
    with zipfile.ZipFile(src) as z:
        names = set(z.namelist())
        missing = [n for n in NEEDED if PREFIX + n not in names]
        if missing:
            log.error("%s lacks %s", src, ", ".join(missing))
            raise SystemExit(2)
        launcher = z.getinfo(PREFIX + "tools/workbench/" + LAUNCHER)
        os.makedirs(os.path.dirname(os.path.abspath(dest)), exist_ok=True)
        with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as out:
            top = zipfile.ZipInfo(LAUNCHER, launcher.date_time)
            top.external_attr = 0o100755 << 16
            top.compress_type = zipfile.ZIP_DEFLATED
            out.writestr(top, z.read(launcher))
            for info in z.infolist():
                out.writestr(info, z.read(info))
    log.info("built %s from %s", dest, src)
    print(f"built: {dest}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("src", help="the repository zip (evergreen-wiki-<version>.zip)")
    ap.add_argument("dest", help="the bundle to write (workbench-bundle-<version>.zip)")
    ap.add_argument("--log-level", default=os.environ.get("LOG_LEVEL", "INFO").upper(),
                    choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    a = ap.parse_args()
    logging.basicConfig(level=a.log_level, format=LOG_FORMAT, stream=sys.stderr)
    build(a.src, a.dest)


if __name__ == "__main__":
    main()
