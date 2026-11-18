"""ucu：统一 computer-use CLI（通用入口）。

用法示例：
  ucu run --json '{"type":"navigate","target":"https://example.com"}'
  ucu run --driver desktop --json '{"type":"read"}'
  echo '{"type":"snapshot"}' | ucu run
  ucu serve --port 52810                 # 常驻 daemon（另开一个持久终端）
  ucu call --json '{"type":"snapshot"}'  # 向 daemon 发动作
  ucu doctor                             # 依赖自检

约定：stdout 只输出一个 JSON 对象（成功=观察，失败=错误），exit 0/1。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

VERSION = "0.1.0"
DEFAULT_PORT = 52810


def _default_workdir() -> str:
    return os.path.join(tempfile.gettempdir(), "ucu-work")


def _load_action(args) -> dict:
    if getattr(args, "json_str", None):
        return json.loads(args.json_str)
    if getattr(args, "file", None):
        with open(args.file, "r", encoding="utf-8") as f:
            return json.load(f)
    # 无 --json / 无文件 → 从 stdin 读（管道或重定向）
    return json.load(sys.stdin)


def _emit_ok(observation: dict) -> int:
    print(json.dumps({"ok": True, "observation": observation}, ensure_ascii=False))
    return 0


def _emit_err(e: Exception) -> int:
    print(json.dumps({"ok": False, "error": f"{type(e).__name__}: {e}"}, ensure_ascii=False))
    return 1


def _cmd_run(args) -> int:
    from protocol import action_from_dict, observation_to_dict
    from runtime import UnifiedRuntime
    try:
        d = _load_action(args)
        if args.driver == "desktop":
            d.setdefault("meta", {})["driver"] = "desktop"
        elif args.driver == "browser":
            d.setdefault("meta", {})["driver"] = "browser"
        a = action_from_dict(d)
        rt = UnifiedRuntime(work_dir=args.workdir, headless=not args.headed)
        try:
            obs = rt.execute(a)
            return _emit_ok(observation_to_dict(obs))
        finally:
            rt.close()
    except Exception as e:
        return _emit_err(e)


def _cmd_serve(args) -> int:
    from daemon import serve
    try:
        serve(args.port, args.workdir, headless=not args.headed)
        return 0
    except Exception as e:
        return _emit_err(e)


def _cmd_call(args) -> int:
    from daemon import call
    try:
        d = _load_action(args)
        resp = call(args.port, d)
        print(json.dumps(resp, ensure_ascii=False))
        return 0 if resp.get("ok") else 1
    except Exception as e:
        return _emit_err(e)


def _cmd_doctor(args) -> int:
    checks = []
    checks.append(("python", sys.version.split()[0]))
    try:
        import playwright
        checks.append(("playwright", "ok"))
    except Exception as e:
        checks.append(("playwright", f"MISSING ({e})"))
    try:
        import uiautomation
        checks.append(("uiautomation", "ok"))
    except Exception as e:
        checks.append(("uiautomation", f"MISSING ({e})"))
    try:
        from drivers.browser import find_browser
        checks.append(("browser", find_browser()))
    except Exception as e:
        checks.append(("browser", f"MISSING ({e})"))
    print(json.dumps({"ok": True, "checks": checks}, ensure_ascii=False))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="ucu", description="统一 computer-use CLI（浏览器 + 桌面）")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="单次 in-process 执行动作")
    r.add_argument("--driver", choices=["auto", "browser", "desktop"], default="auto")
    r.add_argument("--workdir", default=_default_workdir())
    r.add_argument("--headed", action="store_true", help="有头模式（默认无头）")
    r.add_argument("--json", dest="json_str", default=None, help="动作 JSON 字符串")
    r.add_argument("file", nargs="?", default=None, help="动作 JSON 文件路径")

    s = sub.add_parser("serve", help="启动常驻 daemon")
    s.add_argument("--port", type=int, default=DEFAULT_PORT)
    s.add_argument("--workdir", default=_default_workdir())
    s.add_argument("--headed", action="store_true")

    c = sub.add_parser("call", help="向运行中的 daemon 发动作")
    c.add_argument("--port", type=int, default=DEFAULT_PORT)
    c.add_argument("--json", dest="json_str", default=None)
    c.add_argument("file", nargs="?", default=None)

    sub.add_parser("doctor", help="依赖自检")
    sub.add_parser("version", help="打印版本")

    args = p.parse_args(argv)
    if args.cmd == "run":
        return _cmd_run(args)
    if args.cmd == "serve":
        return _cmd_serve(args)
    if args.cmd == "call":
        return _cmd_call(args)
    if args.cmd == "doctor":
        return _cmd_doctor(args)
    if args.cmd == "version":
        print(VERSION)
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
