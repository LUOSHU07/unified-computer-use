"""统一运行时门面：把浏览器 / 桌面 / 人机三层收进一个入口。

三者消费同一套 Action / Observation（见 protocol.py），由 execute() 按动作类型路由：
- 人机原语（request_help / borrow_confirm / cooperate）→ human
- 界面动作按 meta.driver 路由：'desktop' → desktop，其余（默认）→ browser
"""
from __future__ import annotations

from protocol import Action, Observation
from drivers.browser import BrowserDriver
from drivers.desktop import DesktopDriver
from human import HumanInTheLoop

_HUMAN_TYPES = {"request_help", "borrow_confirm", "cooperate"}


class UnifiedRuntime:
    def __init__(self, work_dir: str, headless: bool = True):
        self.browser = BrowserDriver(tmp_dir=f"{work_dir}/tmp", headless=headless)
        self.desktop = DesktopDriver()
        self.human = HumanInTheLoop(work_dir)

    def execute(self, a: Action) -> Observation:
        if a.type in _HUMAN_TYPES:
            return self.human.execute(a)
        if a.meta.get("driver") == "desktop":
            return self.desktop.execute(a)
        return self.browser.execute(a)

    def close(self):
        self.browser.close()
        self.desktop.close()
