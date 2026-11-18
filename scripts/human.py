"""人机协作层。

三种原语统一进入动作空间（见 protocol.py 的 ACTION_TYPES）：
- borrow_confirm：借用现有窗口/标签页前的人工确认门（安全边界）。
- request_help：请求人工完成页面内步骤（验证码/登录/确认）。
- cooperate：人与 agent 在同一窗口/标签页协同。

实现"提出请求"（raise/落盘）路径，非阻塞；阻塞式人工裁决为已知局限，见 SKILL.md。
"""
from __future__ import annotations

import os

from protocol import Action, Observation


class HumanInTheLoop:
    def __init__(self, work_dir: str):
        self.work_dir = work_dir
        os.makedirs(work_dir, exist_ok=True)

    def execute(self, a: Action) -> Observation:
        handlers = {
            "request_help": self._request_help,
            "borrow_confirm": self._borrow_confirm,
            "cooperate": self._cooperate,
        }
        fn = handlers.get(a.type)
        if fn is None:
            raise ValueError(f"human layer 不支持动作: {a.type}")
        return fn(a)

    def _request_help(self, a: Action) -> Observation:
        prompt = a.value or ""
        path = os.path.join(self.work_dir, "help_request.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(prompt)
        return Observation(kind="help", text=f"请求已提出: {prompt}", artifact=path)

    def _borrow_confirm(self, a: Action) -> Observation:
        # 真实实现应阻塞征求人工；当前用 meta.allow 模拟人工裁决（测试/脚本钩子）。
        # 默认 allow=False → 拒绝，保证安全边界默认闭合。
        if not a.meta.get("allow", False):
            raise PermissionError(f"人工拒绝借用: {a.target}")
        return Observation(kind="text", text=f"borrow granted: {a.target}")

    def _cooperate(self, a: Action) -> Observation:
        return Observation(kind="cooperate", text=a.value or a.target or "")
