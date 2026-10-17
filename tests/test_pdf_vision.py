"""PDF 逐页 vision 判断（通用能力，不含任何业务提示词）。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agentbase import pdf_vision


class _FakePage:
    def __init__(self, text, images=(), pixmap_bytes=b"png"):
        self._text = text
        self._images = list(images)
        self._pixmap_bytes = pixmap_bytes

    def get_text(self):
        return self._text

    def get_images(self):
        return self._images

    def get_pixmap(self, dpi=200):  # noqa: ARG002
        class _Pixmap:
            def __init__(self, data):
                self._data = data

            def tobytes(self, fmt):  # noqa: ARG002
                return self._data

        return _Pixmap(self._pixmap_bytes)


class _FakeDoc:
    def __init__(self, pages):
        self._pages = pages

    def __iter__(self):
        return iter(self._pages)

    def __len__(self):
        return len(self._pages)


def test_sparse_text_page_with_image_needs_vision():
    """标题栏只有少量文字、主体是扫描图的页也要读图。"""
    title_block = "零件名 舱口框架 图号 K-959.2 材料 铸钢 精度等级 12-7-0-0"
    doc = _FakeDoc([_FakePage(title_block, images=[("xref",)])])

    assert pdf_vision.pages_needing_vision(doc) == [0]


def test_dense_text_page_without_image_skips_vision():
    """文字充分的页不需要读图（省 token / 省时间）。"""
    doc = _FakeDoc([_FakePage("合同条款 " * 200 + "正文", images=[])])

    assert pdf_vision.pages_needing_vision(doc) == []


def test_sparse_text_without_image_skips_vision():
    """文字少但**没有内嵌图片**的页（如矢量线条图纸）不会被这条规则选中。

    这是已知的初筛局限：调用方在拿不准时仍可送 vision 或标记「需复核」。
    """
    doc = _FakeDoc([_FakePage("短文本", images=[])])

    assert pdf_vision.pages_needing_vision(doc) == []


def test_render_pages_only_selected_indices():
    """only 指定的页才渲染（混合型 PDF 只送扫描页）。"""
    doc = _FakeDoc([_FakePage("a"), _FakePage("b"), _FakePage("c")])

    assert len(pdf_vision.render_pages(doc)) == 3
    assert len(pdf_vision.render_pages(doc, only=[1])) == 1
    assert len(pdf_vision.render_pages(doc, only=[0, 2])) == 2


def test_render_pages_downscales_oversized_output(monkeypatch):
    """单页超过上限时降分辨率重试，而不是直接失败。"""
    monkeypatch.setattr(pdf_vision, "MAX_IMAGE_BYTES", 4)
    doc = _FakeDoc([_FakePage("a", pixmap_bytes=b"0123456789")])

    assert pdf_vision.render_pages(doc) == [b"0123456789"]


def test_extract_text_keeps_page_numbers():
    """提取文字时保留页码，便于回答时追溯原始证据。"""
    doc = _FakeDoc([_FakePage("第一页内容"), _FakePage("   "), _FakePage("第三页内容")])

    text = pdf_vision.extract_text(doc)
    assert "--- Page 1 ---" in text
    assert "--- Page 3 ---" in text
    assert "--- Page 2 ---" not in text  # 空页不输出


def test_detect_pdf_type():
    """整份文档的粗判：文字总量决定 text/image。"""
    assert pdf_vision.detect_pdf_type(_FakeDoc([_FakePage("x" * 100)])) == "text"
    assert pdf_vision.detect_pdf_type(_FakeDoc([_FakePage("x")])) == "image"
