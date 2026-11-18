"""ucu daemon：常驻进程，持有浏览器 + 桌面运行时状态，跨客户端连接复用。

线协议：TCP 127.0.0.1，长度前缀 JSON（4 字节大端长度 + UTF-8 JSON）。
- 请求：动作 dict（同 protocol.action_to_dict）。
- 响应：{"ok": true, "observation": {...}} 或 {"ok": false, "error": "..."}。

意义：避免每个动作都付浏览器/应用启动成本（实测浏览器 ~1s、记事本 ~3.4s）。
"""
from __future__ import annotations

import json
import os
import socket
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from protocol import action_from_dict, observation_to_dict
from runtime import UnifiedRuntime


def _recv_exact(conn: socket.socket, n: int) -> bytes:
    buf = b""
    while len(buf) < n:
        chunk = conn.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("对端关闭连接")
        buf += chunk
    return buf


def recv_msg(conn: socket.socket) -> dict:
    (length,) = struct.unpack(">I", _recv_exact(conn, 4))
    return json.loads(_recv_exact(conn, length).decode("utf-8"))


def send_msg(conn: socket.socket, obj: dict) -> None:
    data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    conn.sendall(struct.pack(">I", len(data)) + data)


def serve(port: int, work_dir: str, headless: bool = True) -> None:
    rt = UnifiedRuntime(work_dir, headless=headless)
    print(f"[ucu] daemon listening on 127.0.0.1:{port} (workdir={work_dir})", flush=True)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(("127.0.0.1", port))
        srv.listen(8)
        while True:
            conn, _ = srv.accept()
            with conn:
                try:
                    req = recv_msg(conn)
                    a = action_from_dict(req)
                    obs = rt.execute(a)
                    resp = {"ok": True, "observation": observation_to_dict(obs)}
                except Exception as e:  # 错误统一回给客户端，不写死 daemon
                    resp = {"ok": False, "error": f"{type(e).__name__}: {e}"}
                try:
                    send_msg(conn, resp)
                except OSError:
                    pass  # 客户端已断开（如探活连接），忽略


def call(port: int, action_dict: dict, timeout: float = 30.0) -> dict:
    """向运行中的 daemon 发一个动作，返回响应 dict。"""
    with socket.create_connection(("127.0.0.1", port), timeout=timeout) as conn:
        send_msg(conn, action_dict)
        return recv_msg(conn)
