"""
core.py · 纯函数核心（无网络、无第三方依赖，可单测）

  · html_to_markdown : 尽力把 HTML 转成可读 markdown
  · truncate         : 分段截断（配合 start_index 分块读取）
"""
from __future__ import annotations

import html as _html
import re

# 需要整块丢弃的标签
_DROP_BLOCK = re.compile(
    r"(?is)<(script|style|noscript|template|svg|iframe|head)\b[^>]*>.*?</\1\s*>"
)
_TAG = re.compile(r"(?s)<[^>]+>")
_MULTI_WS = re.compile(r"[ \t\f\v]+")
_TRAILING_WS = re.compile(r"[ \t]+\n")
_MULTI_NL = re.compile(r"\n{3,}")


def _strip_tags(fragment: str) -> str:
    """去掉片段里的标签并反转义。"""
    return _html.unescape(_TAG.sub("", fragment or "")).strip()


def html_to_markdown(html: str) -> str:
    """把 HTML 转成尽量可读的 markdown 文本。

    不追求完美渲染，只保证：正文可读、链接保留、脚本/样式剔除。
    """
    if not html:
        return ""

    text = _DROP_BLOCK.sub(" ", html)

    # 标题 h1-h6
    for level in range(1, 7):
        pattern = re.compile(rf"(?is)<h{level}\b[^>]*>(.*?)</h{level}\s*>")

        def _h(m, _l=level):
            return "\n" + ("#" * _l) + " " + _strip_tags(m.group(1)) + "\n"

        text = pattern.sub(_h, text)

    # 链接
    text = re.sub(
        r"(?is)<a\b[^>]*href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a\s*>",
        lambda m: "[" + _strip_tags(m.group(2)) + "](" + m.group(1).strip() + ")",
        text,
    )
    # 图片（仅保留 alt）
    text = re.sub(
        r"(?is)<img\b[^>]*alt=[\"']([^\"']*)[\"'][^>]*>",
        lambda m: "![" + m.group(1) + "]",
        text,
    )
    # 列表项
    text = re.sub(r"(?is)<li\b[^>]*>(.*?)</li\s*>", lambda m: "\n- " + _strip_tags(m.group(1)), text)
    # 表格单元格
    text = re.sub(r"(?is)</t[dh]\s*>", " | ", text)
    # 块级标签 → 换行
    text = re.sub(
        r"(?i)</?(p|div|br|tr|section|article|header|footer|ul|ol|table|tbody|thead|blockquote)\b[^>]*>",
        "\n",
        text,
    )
    # 去掉剩余标签
    text = _TAG.sub("", text)
    text = _html.unescape(text)

    # 归一化空白
    text = _MULTI_WS.sub(" ", text)
    text = _TRAILING_WS.sub("\n", text)
    text = _MULTI_NL.sub("\n\n", text)
    return text.strip()


def truncate(text: str, max_length: int = 5000, start_index: int = 0):
    """按 [start_index, start_index+max_length) 截取，返回 (片段, 是否还有更多)。"""
    text = text or ""
    max_length = max(1, int(max_length))
    start_index = max(0, int(start_index))
    chunk = text[start_index : start_index + max_length]
    has_more = (start_index + max_length) < len(text)
    return chunk, has_more
