"""
PDF 逐页判断：哪些页需要走 vision，以及把页渲染成 PNG。

**通用能力**（任务书 v2 §4.4：`tech_drawing.py` 的通用部分 KEEP）。
不含任何业务提示词或图纸结构化提取 —— 那些属于业务 skill。

判断标准（参考 upload-2 文件处理手册）：
  文字稀疏（< 500 字符）**且**页面有内嵌图片 → 该页需要视觉读图。

> 这是初筛规则，不是万能判据：矢量图纸可能没有内嵌位图、乱码文字层也可能
> 字符数很高。调用方在拿不准时应允许进入视觉识别或标记为「需复核」。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - 仅类型检查
    import fitz

_log = logging.getLogger(__name__)

# 少于 50 字符判定为扫描件（整份文档级别）
MIN_TEXT_CHARS = 50
# 图纸页常见「标题栏有文字 + 主体是扫描图」：文字超过 MIN_TEXT_CHARS 但远少于
# 一份正常文档，这类页也必须读图，否则主体内容会被当成「已提取」而丢掉。
SPARSE_TEXT_CHARS = 500
DEFAULT_DPI = 200
MAX_IMAGE_BYTES = 5 * 1024 * 1024


def detect_pdf_type(doc: fitz.Document) -> str:
    """判断整份 PDF 是文字层还是扫描件（粗判，仅用于概览）。

    逐页精细判断请用 `pages_needing_vision()`。
    """
    total_chars = sum(len(page.get_text()) for page in doc)
    return "text" if total_chars >= MIN_TEXT_CHARS else "image"


def pages_needing_vision(doc: fitz.Document) -> list[int]:
    """返回需要视觉读图的页下标（0 基）。

    按页判断而不是整份二选一：常见「标题栏有文字层 + 主体是扫描图」，
    整份判成文字层会让扫描的主体内容被丢掉。
    """
    return [
        index
        for index, page in enumerate(doc)
        if len(page.get_text().strip()) < SPARSE_TEXT_CHARS and page.get_images()
    ]


def extract_text(doc: fitz.Document) -> str:
    """从文字层 PDF 提取全部文字，按页分段（保留页码便于追溯）。"""
    pages = []
    for i, page in enumerate(doc):
        text = page.get_text().strip()
        if text:
            pages.append(f"--- Page {i+1} ---\n{text}")
    return "\n\n".join(pages) if pages else ""


def render_pages(
    doc: fitz.Document,
    dpi: int = DEFAULT_DPI,
    only: list[int] | None = None,
) -> list[bytes]:
    """将 PDF 页渲染为 PNG 字节流（用于 vision）。

    ``only`` 给定时只渲染这些页下标（0 基），用于混合型 PDF 只送扫描页。
    单页超过 MAX_IMAGE_BYTES 时降分辨率重试一次。
    """
    images = []
    for index, page in enumerate(doc):
        if only is not None and index not in only:
            continue
        pix = page.get_pixmap(dpi=dpi)
        img_bytes = pix.tobytes("png")
        if len(img_bytes) > MAX_IMAGE_BYTES:
            pix = page.get_pixmap(dpi=100)
            img_bytes = pix.tobytes("png")
        images.append(img_bytes)
    return images
