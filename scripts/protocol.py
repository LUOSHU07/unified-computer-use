"""统一动作 / 观察协议。

设计目标：同一套 schema 覆盖浏览器与桌面应用——
- token 高效：动作用 @eN 引用定位，观察用 @eN 引用 + 文件路径，而非整树倾倒。
- 语义定位：target 同时支持 @ref / 语义定位器(role:text) / 原生选择器。
- 人机协作：request_help / borrow_confirm / cooperate 三种原语进入动作空间。
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any

# 动作类型（统一动作空间）
ACTION_TYPES = {
    "navigate",       # 浏览器：打开 URL；桌面：启动/激活应用
    "click",          # 点击 target
    "fill",           # 向 target 输入 value
    "read",           # 读取文本：浏览器=页面/标题文本，桌面=控件 ValuePattern
    "press",          # 键盘按键 value（组合键）
    "screenshot",     # 截图到 artifact
    "snapshot",       # 产出带 @eN 引用的可交互快照
    "observe",        # 产出语义化 VOM 观察（含感知探针）
    "evaluate",       # 浏览器：执行 JS；桌面：执行 PowerShell/查询
    "request_help",   # 请求人工完成页面内步骤（验证码/登录）
    "borrow_confirm", # 借用现有窗口/标签页前的人工确认门
    "cooperate",      # 人与 agent 在同一窗口/标签页协同
}

# 观察类型
OBSERVATION_TYPES = {"snapshot", "screenshot", "text", "help", "cooperate", "none"}


@dataclass
class Ref:
    """可交互元素的引用（省 token 定位的核心）。"""
    id: str                     # "@e1"
    kind: str                   # button/textbox/link/checkbox/...
    name: str = ""              # 无障碍名称
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class Action:
    """统一动作。target 可填：@eN 引用 / 语义定位器(如 role=button name=保存) / CSS 选择器 / URL。"""
    type: str
    target: str | None = None
    value: str | None = None
    artifact: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class Observation:
    """统一观察。text 存结构文本，refs 存 @eN 引用，artifact 存文件路径（截图等）。"""
    kind: str
    text: str = ""
    refs: list[Ref] = field(default_factory=list)
    artifact: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)


# ---- 序列化（供 CLI / daemon / 日志复用）----

def action_to_dict(a: Action) -> dict[str, Any]:
    return asdict(a)


def action_from_dict(d: dict[str, Any]) -> Action:
    if d.get("type") not in ACTION_TYPES:
        raise ValueError(f"unknown action type: {d.get('type')}")
    return Action(
        type=d["type"],
        target=d.get("target"),
        value=d.get("value"),
        artifact=d.get("artifact"),
        meta=d.get("meta") or {},
    )


def observation_to_dict(o: Observation) -> dict[str, Any]:
    return asdict(o)


def observation_from_dict(d: dict[str, Any]) -> Observation:
    refs = [Ref(**r) for r in d.get("refs", [])]
    return Observation(
        kind=d["kind"],
        text=d.get("text", ""),
        refs=refs,
        artifact=d.get("artifact"),
        meta=d.get("meta", {}),
    )


# ---- 常用构造器 ----

def navigate(url: str) -> Action:
    return Action(type="navigate", target=url)


def click(target: str) -> Action:
    return Action(type="click", target=target)


def fill(target: str, text: str) -> Action:
    return Action(type="fill", target=target, value=text)


def read(target: str | None = None) -> Action:
    return Action(type="read", target=target)


def press(keys: str) -> Action:
    return Action(type="press", value=keys)


def screenshot(path: str) -> Action:
    return Action(type="screenshot", artifact=path)


def snapshot() -> Action:
    return Action(type="snapshot")


def evaluate(js: str) -> Action:
    return Action(type="evaluate", value=js)


def request_help(prompt: str) -> Action:
    return Action(type="request_help", value=prompt)


def borrow_confirm(target: str, allow: bool = False) -> Action:
    return Action(type="borrow_confirm", target=target, meta={"allow": allow})


def cooperate(context: str) -> Action:
    return Action(type="cooperate", value=context)
