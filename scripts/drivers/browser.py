"""浏览器驱动：Playwright 后端，复用本机 Edge / Chrome（自动探测）。

定位寻址：@eN 引用 / CSS 选择器 / role= 语义定位器。
"""
from __future__ import annotations

import os

from playwright.sync_api import sync_playwright

from protocol import Action, Observation, Ref

# 与 snapshot 共用的可交互元素枚举（JS 表达式）
_JS_ENUM = """
() => {
  const sels = 'a,button,input,textarea,select,[role="button"],[role="link"],[role="textbox"],[role="checkbox"]';
  const els = Array.from(document.querySelectorAll(sels)).filter(e => {
    const r = e.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  });
  return els.slice(0, 40).map(e => ({
    tag: e.tagName.toLowerCase(),
    role: e.getAttribute('role') || '',
    name: (e.getAttribute('aria-label') || e.innerText || e.placeholder || e.getAttribute('name') || '').trim().slice(0, 40),
    type: e.getAttribute('type') || '',
    id: e.id || ''
  }));
}
"""

_CANDIDATE_PATHS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]


def find_browser() -> str:
    """探测 Edge/Chrome 可执行文件。顺序：环境变量 → 常见路径 → 注册表。"""
    candidates = list(_CANDIDATE_PATHS)  # 局部复制，避免每次调用污染模块级列表
    # 1. 环境变量
    for var in ("UUC_BROWSER_PATH", "EDGE_PATH", "CHROME_PATH"):
        p = os.environ.get(var)
        if p and os.path.isfile(p):
            return p
    # 2. 常见安装路径
    user = os.environ.get("USERNAME", "")
    if user:
        candidates.append(rf"C:\Users\{user}\AppData\Local\Google\Chrome\Application\chrome.exe")
    for p in candidates:
        if os.path.isfile(p):
            return p
    # 3. Windows 注册表（仅 Windows）
    try:
        import winreg
        for hive, key in (
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe"),
        ):
            try:
                with winreg.OpenKey(hive, key) as k:
                    v, _ = winreg.QueryValueEx(k, None)
                    if v and os.path.isfile(v):
                        return v
            except OSError:
                continue
    except ImportError:
        pass
    raise FileNotFoundError("未找到 Edge/Chrome，请设置环境变量 UUC_BROWSER_PATH 指向浏览器可执行文件")


class BrowserDriver:
    def __init__(self, tmp_dir: str, headless: bool = True):
        self.tmp_dir = tmp_dir
        os.makedirs(tmp_dir, exist_ok=True)
        # 默认 Temp 目录在受限环境里对 Node 驱动 mkdtemp 可能报 EPERM，改用受控目录
        os.environ["TMP"] = tmp_dir
        os.environ["TEMP"] = tmp_dir
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(executable_path=find_browser(), headless=headless)
        self._page = self._browser.new_page()

    # ---- 动作分发 ----
    def execute(self, a: Action) -> Observation:
        handlers = {
            "navigate": self._navigate,
            "click": self._click,
            "fill": self._fill,
            "screenshot": self._screenshot,
            "snapshot": self._snapshot,
            "evaluate": self._evaluate,
        }
        fn = handlers.get(a.type)
        if fn is None:
            raise ValueError(f"browser driver 不支持动作: {a.type}")
        return fn(a)

    # ---- 各动作实现 ----
    def _navigate(self, a: Action) -> Observation:
        self._page.goto(a.target, timeout=30000)
        return Observation(kind="text", text=self._page.title(), meta={"url": self._page.url})

    def _click(self, a: Action) -> Observation:
        self._resolve(a.target).click()
        return Observation(kind="text", text=f"clicked {a.target}")

    def _fill(self, a: Action) -> Observation:
        self._resolve(a.target).fill(a.value)
        return Observation(kind="text", text=f"filled {a.target}")

    def _screenshot(self, a: Action) -> Observation:
        path = a.artifact or os.path.join(self.tmp_dir, "shot.png")
        self._page.screenshot(path=path)
        return Observation(kind="screenshot", artifact=path)

    def _snapshot(self, a: Action) -> Observation:
        items = self._page.evaluate(_JS_ENUM)
        refs = [
            Ref(id=f"@e{i+1}", kind=it["role"] or it["tag"], name=it["name"], extra={"tag": it["tag"], "type": it["type"]})
            for i, it in enumerate(items)
        ]
        text = "\n".join(f"[{i+1}] {r.kind} {r.name}" for i, r in enumerate(refs))
        return Observation(kind="snapshot", text=text, refs=refs, meta={"count": len(refs)})

    def _evaluate(self, a: Action) -> Observation:
        val = self._page.evaluate(a.value)
        return Observation(kind="text", text=str(val))

    # ---- 定位：@eN 引用 / CSS / role= 语义定位器 ----
    def _resolve(self, target: str):
        if target.startswith("@e"):
            idx = int(target[2:]) - 1
            handle = self._page.evaluate_handle(
                f"""() => {{
                  const sels = 'a,button,input,textarea,select,[role="button"],[role="link"],[role="textbox"],[role="checkbox"]';
                  const els = Array.from(document.querySelectorAll(sels)).filter(e => {{
                    const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0;
                  }});
                  return els[{idx}] || null;
                }}"""
            )
            el = handle.as_element()
            if el is None:
                raise ValueError(f"引用 {target} 无对应元素")
            return el
        # role=name=... 语义定位器 或 原生 CSS 选择器，均交给 Playwright locator
        return self._page.locator(target)

    def close(self):
        self._browser.close()
        self._pw.stop()
