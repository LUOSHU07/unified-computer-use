# 动作 / 观察协议参考

本文件是 `SKILL.md` 的稳定细节，字段与语义以 `scripts/protocol.py` 为准。

## Action（动作）

JSON 字段：`type`（必填）、`target`、`value`、`artifact`、`meta`。

| type | target | value | 浏览器语义 | 桌面语义 |
|---|---|---|---|---|
| `navigate` | URL | — | 打开页面，返回标题 | 启动应用（target=exe 路径，`meta.class_name` 指定窗口类名） |
| `click` | `@eN` / CSS / `role=…` | — | 点击元素 | 点击控件（InvokePattern，免鼠标） |
| `fill` | `@eN` / CSS | 文本 | 向元素输入 value | 向编辑区写入 value（`target` 忽略） |
| `read` | 可选 | — | 返回页面标题文本 | 读控件 ValuePattern 文本 |
| `press` | — | 组合键 | 键盘组合键 | 键盘组合键（预留） |
| `screenshot` | — | — | 截图到 `artifact` 路径 | （预留） |
| `snapshot` | — | — | 产出 `@eN` 可交互元素列表 | 枚举子控件产出 `@eN` |
| `observe` | — | — | 语义化 VOM 观察（预留） | （预留） |
| `evaluate` | — | JS | 执行 JS 返回结果 | （预留） |
| `request_help` | — | 提示语 | 请求人工完成页面步骤 | 同左 |
| `borrow_confirm` | 目标 | — | 借用标签页前确认门 | 借用窗口前确认门 |
| `cooperate` | — | 上下文 | 人机同窗口协同 | 同左 |

### 路由（`meta.driver`）

- `meta.driver == "desktop"` → 桌面驱动；其余（缺省）→ 浏览器驱动。
- `request_help` / `borrow_confirm` / `cooperate` 固定路由到人机层，与 `meta.driver` 无关。
- CLI 的 `--driver desktop` 等价于注入 `meta.driver="desktop"`。

### `@eN` 定位（省 token 核心）

1. 先 `snapshot` 拿引用表：`[1] button 保存` 等，同时返回 `refs` 数组。
2. 后续动作用 `@e1` 定位，避免每次重传整棵树。
3. `target` 三种写法等价可用：`@eN` 引用 / `role=button name=保存` / 原生 CSS 选择器。

## Observation（观察）

JSON 字段：`kind`、`text`、`refs`、`artifact`、`meta`。

- `kind`：`snapshot` / `screenshot` / `text` / `help` / `cooperate` / `none`。
- `refs`：`[{"id":"@e1","kind":"button","name":"保存","extra":{...}}]`。
- `artifact`：截图/快照落盘的文件路径（省 token：大内容走文件，不内联）。

## CLI 响应约定

- 成功：`{"ok": true, "observation": {...}}`，exit 0。
- 失败：`{"ok": false, "error": "Type: message"}`，exit 1。

## daemon 线协议（`scripts/daemon.py`）

TCP 127.0.0.1，长度前缀 JSON：4 字节大端长度 + UTF-8 JSON 体。请求=动作 dict，响应=上面的 CLI 响应格式。
