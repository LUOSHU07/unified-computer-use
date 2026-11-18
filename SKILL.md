---
name: unified-computer-use
description: >-
  Drive a local browser (Edge/Chrome via Playwright) and Windows desktop apps
  (via UI Automation) through one unified JSON Action/Observation protocol with
  human-in-the-loop gates. Use when the task requires operating a real GUI —
  clicking, filling, navigating, snapshotting elements, reading screen text, or
  borrowing a human's window — instead of an API, file edit, or pure text output.
  Not for API/HTTP requests, file operations, or code generation without a GUI.
---

# 统一 Computer-Use 运行时

让 agent 通过一套 JSON 协议操作本地浏览器（Edge/Chrome）与 Windows 桌面应用，动作与观察跨域统一，并带人机协作门。

## 何时用

- 任务要求**真实操作 GUI**：点按钮、填表单、读页面/控件文本、截图。
- 需要**跨浏览器与桌面**的统一动作（如"网页读数据 → 记事本写入"）。
- 需要**人机协作**：借用现有窗口前确认、请求人工完成验证码/登录。

**不要用**（近邻非触发）：纯 API/HTTP 调用、文件读写、文本生成/代码编写等不涉及 GUI 的任务。

## 快速开始

入口是 `scripts/ucu.py`（CLI，JSON 进 / JSON 出，任何能跑 shell 的 agent 都能调）：

```bash
# 依赖自检
python scripts/ucu.py doctor

# 单次 in-process：stdout 输出 {"ok":true,"observation":{...}}
python scripts/ucu.py run --json '{"type":"navigate","target":"https://example.com"}'
python scripts/ucu.py run --driver desktop --json '{"type":"read"}'
echo '{"type":"snapshot"}' | python scripts/ucu.py run
```

动作字段与 `@eN` 定位规则见 `references/action-protocol.md`。

## 两种运行模式

1. **in-process（默认）**：`ucu run`，每次拉起运行时、用完即关。无状态、无残留，但启动成本高（浏览器 ~1s、桌面应用 ~3s）。
2. **daemon 常驻（多动作/长任务推荐）**：
   ```bash
   # 在独立持久终端里启动（不能在受限沙箱的 Job Object 里跑，它不允许 breakaway）
   python scripts/ucu.py serve --port 52810
   # 其它进程发动作，浏览器/应用状态跨调用复用
   python scripts/ucu.py call --json '{"type":"navigate","target":"https://example.com"}'
   python scripts/ucu.py call --json '{"type":"snapshot"}'
   ```

## 安全规则（必须遵守）

- **borrow_confirm 默认拒绝**：操作真实窗口/标签页前先 `borrow_confirm`，未显式 allow 即 `PermissionError`。
- **不碰真实默认 profile**：浏览器驱动用 Playwright 独立实例，不注入用户的日常登录态。
- **request_help**：验证码/登录/需要人工判断的步骤，发 `request_help` 交回人工，不硬闯。
- **错误统一返回**：所有异常转为 `{"ok":false,"error":"..."}`（exit 1），agent 据此判读，不要靠猜。

## 局限（已知）

- 桌面驱动为 Windows UIA；macOS/Linux 桌面需另接后端（浏览器部分跨平台）。
- 阻塞式人工确认（borrow 的实时"等待人点同意"）未实现，当前用 `meta.allow` 模拟裁决。
- daemon 需在**能 breakaway 的持久宿主**里运行；受限沙箱（Job Object 不允许 breakaway）只能 in-process。
- 桌面 snapshot 只枚举直接子控件（Win11 记事本返回 0 条属正常现象）。

## 验证

```bash
python scripts/verify.py   # 协议往返 + 浏览器→记事本 e2e + CLI 冒烟，exit 0 = 通过
```
