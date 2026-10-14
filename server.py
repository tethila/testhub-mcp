"""
Test Hub MCP (testhub-mcp) v0.1
================================
公共测试工具空间 —— 一个面向**所有项目**的远程测试工具 MCP。

工具（第一版）：
  · http_request —— 对公网 URL 发 HTTP 请求（接口测试/连通性）
  · fetch_page   —— 抓取网页内容（默认转 markdown）

传输：streamable-http（默认挂载在 /mcp），亦支持 sse。
兼容：**同时支持 mcp 1.x（FastMCP）与 2.x（MCPServer）**。
安全：内置 SSRF 防护（见 security.py）。

本地运行：
    pip install -r requirements.txt
    python3 server.py            # 默认 0.0.0.0:8000，端点 /mcp

部署：推到 GitHub → 魔搭 modelscope.cn/mcp → 「创建MCP」→「GitHub 快速创建」→ 可托管部署。
"""
from __future__ import annotations

import os
import time
from typing import Any, Optional

import httpx

from core import html_to_markdown, truncate
from security import UnsafeUrlError, validate_url

VERSION = "0.1.0"
MAX_BODY_BYTES = 512 * 1024          # 单次抓取上限 512KB
DEFAULT_TIMEOUT = 15                  # 秒
USER_AGENT = f"testhub-mcp/{VERSION} (+https://modelscope.cn/mcp)"
ALLOWED_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}

HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8000"))


def _build_server():
    """兼容 mcp 1.x / 2.x：返回 (server, run_kwargs, variant)。"""
    try:
        from mcp.server.fastmcp import FastMCP  # mcp 1.x

        server = FastMCP("testhub-mcp", host=HOST, port=PORT)
        return server, {}, "mcp 1.x · FastMCP"
    except ImportError:
        pass

    try:
        from mcp.server.mcpserver import MCPServer  # mcp 2.x
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(
            "缺少依赖：请先 `pip install -r requirements.txt`（需要 mcp 包）"
        ) from exc

    server = MCPServer("testhub-mcp")
    return server, {"host": HOST, "port": PORT}, "mcp 2.x · MCPServer"


mcp, _RUN_KWARGS, SDK_VARIANT = _build_server()


def _decode(raw: bytes, encoding: Optional[str]) -> str:
    try:
        return raw.decode(encoding or "utf-8", errors="replace")
    except (LookupError, TypeError):
        return raw.decode("utf-8", errors="replace")


@mcp.tool()
def http_request(
    url: str,
    method: str = "GET",
    headers: Optional[dict] = None,
    body: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT,
    follow_redirects: bool = True,
) -> dict:
    """对任意**公网** URL 发起 HTTP 请求（用于接口测试 / 连通性检查）。

    参数:
      url: 目标地址（仅 http/https，公网；内网地址会被拒绝）
      method: GET/POST/PUT/PATCH/DELETE/HEAD/OPTIONS
      headers: 自定义请求头（可选）
      body: 请求体字符串（可选）
      timeout: 超时秒数（默认 15）
      follow_redirects: 是否跟随重定向（默认 true）

    返回: {ok, status, headers, body, elapsed_ms, final_url, truncated} 或 {ok:false, error}
    """
    try:
        validate_url(url)
    except UnsafeUrlError as exc:
        return {"ok": False, "error": f"URL 被安全策略拒绝：{exc}"}

    verb = (method or "GET").upper()
    if verb not in ALLOWED_METHODS:
        return {"ok": False, "error": f"不支持的 method：{verb}"}

    req_headers = {"User-Agent": USER_AGENT}
    if headers:
        req_headers.update({str(k): str(v) for k, v in dict(headers).items()})

    started = time.perf_counter()
    try:
        with httpx.Client(timeout=timeout, follow_redirects=bool(follow_redirects)) as client:
            resp = client.request(
                verb,
                url,
                headers=req_headers,
                content=body.encode("utf-8") if isinstance(body, str) else body,
            )
    except Exception as exc:  # noqa: BLE001 - 统一转成结构化错误
        return {"ok": False, "error": f"请求失败：{type(exc).__name__}: {exc}"}

    elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
    raw = resp.content
    truncated = len(raw) > MAX_BODY_BYTES

    return {
        "ok": True,
        "status": resp.status_code,
        "headers": dict(resp.headers),
        "body": _decode(raw[:MAX_BODY_BYTES], resp.encoding),
        "elapsed_ms": elapsed_ms,
        "final_url": str(resp.url),
        "truncated": truncated,
    }


@mcp.tool()
def fetch_page(
    url: str,
    max_length: int = 5000,
    start_index: int = 0,
    raw: bool = False,
) -> dict:
    """抓取网页内容。默认把 HTML 转成 markdown；raw=true 返回原始 HTML。

    参数:
      url: 目标地址（仅 http/https，公网）
      max_length: 返回的最大字符数（默认 5000）
      start_index: 从第几个字符开始（默认 0，用于分块读取）
      raw: 返回未转换的原始 HTML（默认 false）

    返回: {ok, url, status, content, start_index, has_more, total_length[, next_start_index]}
          或 {ok:false, error}
    """
    try:
        validate_url(url)
    except UnsafeUrlError as exc:
        return {"ok": False, "error": f"URL 被安全策略拒绝：{exc}"}

    try:
        with httpx.Client(timeout=DEFAULT_TIMEOUT, follow_redirects=True) as client:
            resp = client.get(url, headers={"User-Agent": USER_AGENT})
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"抓取失败：{type(exc).__name__}: {exc}"}

    html_text = _decode(resp.content[:MAX_BODY_BYTES], resp.encoding)
    content = html_text if raw else html_to_markdown(html_text)
    chunk, has_more = truncate(content, max_length=max_length, start_index=start_index)

    result = {
        "ok": True,
        "url": str(resp.url),
        "status": resp.status_code,
        "content": chunk,
        "start_index": start_index,
        "has_more": has_more,
        "total_length": len(content),
    }
    if has_more:
        result["next_start_index"] = start_index + max(1, int(max_length))
    return result


def main() -> None:
    transport = os.environ.get("MCP_TRANSPORT", "streamable-http")
    print(f"[testhub-mcp] SDK={SDK_VARIANT} transport={transport} host={HOST} port={PORT}", flush=True)
    mcp.run(transport=transport, **_RUN_KWARGS)


if __name__ == "__main__":
    main()
