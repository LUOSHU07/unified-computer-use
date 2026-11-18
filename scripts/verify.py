"""端到端自检：协议往返 + 浏览器→记事本跨域 + CLI 冒烟。exit 0 = 通过。"""
import json
import os
import subprocess
import sys

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)

# 输出统一 UTF-8，避免管道/重定向下 GBK 控制台乱码
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


def fail(msg: str) -> None:
    print("FAIL:", msg)
    sys.exit(1)


# 1. 协议往返
from protocol import Action, action_to_dict, action_from_dict
a = Action(type="read")
if action_from_dict(action_to_dict(a)) != a:
    fail("协议往返不一致")
print("协议往返: OK")

# 2. 运行时 e2e：浏览器读标题 → 记事本写入 → 读回一致
from runtime import UnifiedRuntime
subprocess.run(["taskkill", "/F", "/IM", "Notepad.exe"], capture_output=True)
work = os.path.join(SCRIPTS, "..", ".ucu-verify")
rt = UnifiedRuntime(work_dir=work, headless=True)
try:
    title = rt.execute(Action(type="navigate", target="data:text/html,<title>ucu-verify-title</title>")).text
    rt.execute(Action(type="navigate", target=r"C:\Windows\System32\notepad.exe",
                      meta={"driver": "desktop", "class_name": "Notepad"}))
    rt.execute(Action(type="fill", value=title, meta={"driver": "desktop"}))
    read_back = rt.execute(Action(type="read", meta={"driver": "desktop"})).text
    if read_back != title:
        fail(f"读回不一致: {read_back!r} != {title!r}")
    print("运行时 e2e: MATCH", repr(read_back))
finally:
    rt.close()

# 3. CLI 冒烟
r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "ucu.py"), "doctor"],
                   capture_output=True, text=True, encoding="utf-8")
if r.returncode != 0 or '"ok": true' not in r.stdout:
    fail(f"ucu doctor 失败: {r.stdout}{r.stderr}")
print("CLI doctor: OK")

r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "ucu.py"), "run",
                    "--json", '{"type":"evaluate","value":"1+1"}'],
                   capture_output=True, text=True, encoding="utf-8")
out = json.loads(r.stdout)
if r.returncode != 0 or not out.get("ok"):
    fail(f"ucu run 失败: {r.stdout}{r.stderr}")
print("CLI run: OK ->", out["observation"]["text"])

print("VERIFY OK")
