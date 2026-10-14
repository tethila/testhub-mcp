"""纯函数单测：html_to_markdown / truncate（不依赖外网）。"""
from core import html_to_markdown, truncate


def test_html_to_markdown_basic():
    src = (
        "<html><head><title>x</title><style>.a{}</style></head><body>"
        "<h1>Hi</h1><script>evil()</script><p>Hello <b>world</b></p>"
        "<a href='https://a.com'>A</a></body></html>"
    )
    md = html_to_markdown(src)
    assert "# Hi" in md
    assert "Hello world" in md
    assert "[A](https://a.com)" in md
    assert "evil()" not in md  # script 被剔除
    assert ".a{}" not in md  # style 被剔除


def test_headings_and_lists():
    md = html_to_markdown("<h2>标题</h2><ul><li>甲</li><li>乙</li></ul>")
    assert "## 标题" in md
    assert "- 甲" in md and "- 乙" in md


def test_entities_decoded_and_ws_normalized():
    md = html_to_markdown("<p>a &amp; b</p><p></p><p></p><p>c</p>")
    assert "a & b" in md
    assert "\n\n\n" not in md


def test_empty_html():
    assert html_to_markdown("") == ""


def test_truncate_first_chunk():
    chunk, more = truncate("abcdefghij", max_length=4, start_index=0)
    assert chunk == "abcd"
    assert more is True


def test_truncate_last_chunk():
    chunk, more = truncate("abcdefghij", max_length=4, start_index=8)
    assert chunk == "ij"
    assert more is False


def test_truncate_middle_chunk():
    chunk, more = truncate("abcdefghij", max_length=3, start_index=4)
    assert chunk == "efg"
    assert more is True


def test_truncate_empty():
    assert truncate("", 5, 0) == ("", False)
