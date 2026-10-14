#!/usr/bin/env bash
# Test Hub MCP · 启动脚本（魔搭托管可用此作为启动入口）
set -euo pipefail

export HOST="${HOST:-0.0.0.0}"
export PORT="${PORT:-8000}"
export MCP_TRANSPORT="${MCP_TRANSPORT:-streamable-http}"

echo "[testhub-mcp] transport=${MCP_TRANSPORT} host=${HOST} port=${PORT}"
exec python3 server.py
