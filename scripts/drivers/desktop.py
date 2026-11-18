"""桌面驱动：Windows UI Automation（uiautomation 库）。

要点（本环境实测）：
- 优先用 UIA 的 ValuePattern/InvokePattern 直接读写，避免鼠标/键盘模拟
  （SetCursorPos 在受限环境不可用，pywinauto 的 window(title_re=) 会挂起）。
- Windows 11 UWP 记事本的文本区是 Document 控件（RichEditD2DPT），
  支持 ValuePattern，可用 SetValue/Value 直接读写。
"""
from __future__ import annotations

import subprocess
import time

import uiautomation as auto

from protocol import Action, Observation, Ref


class DesktopDriver:
    def __init__(self):
        self.window = None

    def execute(self, a: Action) -> Observation:
        handlers = {
            "navigate": self._launch,      # 桌面语境下 = 启动应用
            "fill": self._fill,
            "read": self._read,
            "click": self._click,
            "snapshot": self._snapshot,
        }
        fn = handlers.get(a.type)
        if fn is None:
            raise ValueError(f"desktop driver 不支持动作: {a.type}")
        return fn(a)

    # ---- 实现 ----
    def _launch(self, a: Action) -> Observation:
        exe = a.target
        class_name = a.meta.get("class_name", "Notepad")
        subprocess.Popen(exe)
        time.sleep(3)
        self.window = auto.WindowControl(searchDepth=1, ClassName=class_name)
        if not self.window.Exists(5):
            raise RuntimeError(f"未找到窗口 class={class_name}")
        return Observation(kind="text", text=self.window.Name, meta={"exe": exe})

    def _doc(self):
        doc = self.window.DocumentControl(searchDepth=10)
        if not doc.Exists(3):
            doc = self.window.EditControl(searchDepth=10)
        if not doc.Exists(3):
            raise RuntimeError("未找到文本编辑控件")
        return doc

    def _fill(self, a: Action) -> Observation:
        doc = self._doc()
        doc.GetValuePattern().SetValue(a.value)
        return Observation(kind="text", text=f"typed {a.value}")

    def _read(self, a: Action) -> Observation:
        doc = self._doc()
        try:
            val = doc.GetValuePattern().Value
            return Observation(kind="text", text=val)
        except Exception:
            return Observation(kind="text", text=doc.Name, meta={"fallback": True})

    def _click(self, a: Action) -> Observation:
        # 按钮/菜单用 InvokePattern（无需鼠标）
        ctrl = self._by_target(a.target)
        if ctrl.GetInvokePattern():
            ctrl.GetInvokePattern().Invoke()
        return Observation(kind="text", text=f"clicked {a.target}")

    def _snapshot(self, a: Action) -> Observation:
        refs = []
        # 枚举直接子控件中的 Button / MenuItem / TabItem
        for c in self.window.GetChildren():
            ct = c.ControlTypeName
            if ct in ("ButtonControl", "MenuItemControl", "TabItemControl"):
                name = (c.Name or "").strip()[:40]
                if name:
                    refs.append(Ref(id=f"@e{len(refs)+1}", kind=ct.replace("Control", "").lower(), name=name))
        text = "\n".join(f"[{i+1}] {r.kind} {r.name}" for i, r in enumerate(refs[:20]))
        return Observation(kind="snapshot", text=text, refs=refs[:20], meta={"count": len(refs)})

    def _by_target(self, target: str):
        if target.startswith("@e"):
            idx = int(target[2:]) - 1
            pool = [c for c in self.window.GetChildren()
                    if c.ControlTypeName in ("ButtonControl", "MenuItemControl", "TabItemControl")]
            return pool[idx]
        return self.window.ButtonControl(searchDepth=10, Name=target)

    def close(self):
        if self.window is not None:
            try:
                self.window.GetWindowPattern().Close()
            except Exception:
                pass
