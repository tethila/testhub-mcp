# testhub-mcp

> **公共测试工具空间**（Test Hub）—— 一个面向**所有项目**的远程测试工具 MCP。
> 基于 [Model Context Protocol](https://modelcontextprotocol.io) 的 `streamable-http` 远程服务，可托管在 [魔搭 ModelScope MCP 广场](https://modelscope.cn/mcp)。

[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](#)
[![MCP](https://img.shields.io/badge/MCP-streamable--http-green)](#)
[![License](https://img.shields.io/badge/license-MIT-lightgrey)](#)

---

## 它解决什么

AI Agent 要跑测试，常常得**自己装环境**——费时、费流量、还常因硬件不够跑不起来。

`testhub-mcp` 把常用测试能力做成**远程工具（Tool as a Service）**：Agent 只要连上这个 MCP，就能直接调用，**零安装**。

## 工具（v0.1）

| 工具 | 作用 | 关键参数 |
|---|---|---|
| **`http_request`** | 对任意公网 URL 发 HTTP 请求（接口测试 / 连通性） | `url` `method` `headers` `body` `timeout` `follow_redirects` |
| **`fetch_page`** | 抓取网页内容，默认转 markdown | `url` `max_length` `start_index` `raw` |

<details>
<summary><b>http_request 返回示例</b></summary>

```json
{
  "ok": true,
  "status": 200,
  "headers": { "content-type": "application/json" },
  "body": "{\"hello\":\"world\"}",
  "elapsed_ms": 123.4,
  "final_url": "https://api.example.com/v1/ping",
  "truncated": false
}
```
</details>

<details>
<summary><b>fetch_page 返回示例</b></summary>

```json
{
  "ok": true,
  "url": "https://example.com/",
  "status": 200,
  "content": "# Example Domain\n\nThis domain is for use in ...",
  "start_index": 0,
  "has_more": true,
  "total_length": 12345,
  "next_start_index": 5000
}
```
</details>

> 内容过长时用 `start_index` **分块读取**（与魔搭官方 `fetch` 对齐）。

## 快速开始（本地）

```bash
pip install -r requirements.txt
python3 server.py                      # 默认监听 0.0.0.0:8000，端点 /mcp
# 或
MCP_TRANSPORT=sse PORT=8000 ./run.sh   # 以 SSE 方式启动，端点为 /sse
```

自测：

```bash
pip install -r requirements-dev.txt
pytest -q
```

## 接入（客户端 / Agent）

把下面这段填进任意支持 MCP 的客户端（Cherry Studio / Claude Code / 自研 Agent 等）：

```json
{
  "mcpServers": {
    "testhub": {
      "type": "streamable_http",
      "url": "https://mcp.api-inference.modelscope.net/<YOUR-DEPLOY-ID>/mcp"
    }
  }
}
```

详见 [`examples/`](examples/)：`mcp.remote.json`（远程）· `mcp.local.json`（本地）。

## 部署到魔搭（托管）

1. 把本仓库推到 **GitHub**；
2. 打开 <https://modelscope.cn/mcp> → 右上 **「创建MCP」** → **「GitHub 快速创建」**；
3. 托管类型选 **「可托管部署」**，填入本仓库地址 `https://github.com/tethila/testhub-mcp`；
4. **服务配置 config** 填（⚠️ 这就是平台的「启动命令」，必须带 `command`）：
   ```json
   {"mcpServers":{"testhub-mcp":{"command":"python","args":["-m","server"]}}}
   ```
   （拼起来即 `python -m server`；平台会拉取本仓库并用 `pyproject.toml` 安装依赖）
5. 提交后平台自动完成「拉代码 → uv 装依赖 → 部署到函数计算 → 生成 URL」，得到 **长期 URL**，填回客户端即可。

> ⚠️ 魔搭托管要求 `streamable-http` 或 `sse`，且服务需监听平台注入的 `PORT` 环境变量（本仓库已适配）。
> 若用 `uvx` 方式，可写：`{"mcpServers":{"testhub-mcp":{"command":"uvx","args":["--from","git+https://github.com/tethila/testhub-mcp","testhub-mcp"]}}}`

## 安全（重要）

作为**公共**工具，内置 **SSRF 防护**（见 [`security.py`](security.py)）：

- 仅允许 `http` / `https`；
- 域名解析出的**任一 IP** 落在内网/保留网段即**拒绝**；
- 覆盖 **云元数据地址** `169.254.169.254`、回环、私有段、链路本地、组播等；
- 单次响应体上限 **512 KB**，请求超时可控；
- **不保存任何数据**、不硬编码凭证、无状态。

> 部署到公网前，请根据你的环境再复核一遍策略与限流。

## 目录结构

```
testhub-mcp/
├── server.py            # MCP 服务入口（工具定义）
├── security.py          # SSRF 防护
├── core.py              # 纯函数：HTML→Markdown、截断
├── run.sh               # 启动脚本（托管入口）
├── requirements.txt
├── requirements-dev.txt
├── examples/            # 客户端接入配置
└── tests/               # 单测（离线可跑）
```

## 路线图

- [x] v0.1 `http_request` · `fetch_page`
- [ ] v0.2 `check_url`（DNS/端口/证书/重定向）· `assert_json` · `regex_extract`
- [ ] v0.3 重测试（`run_pytest` / 浏览器冒烟）—— 需独立算力节点

## 许可

MIT
