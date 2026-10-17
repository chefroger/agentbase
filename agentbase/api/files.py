"""
文件上传 API（通用能力）。

原 `api/libraries.py` 的 `/upload-files` 端点：业务侧「文档库」逻辑已剥离，
但「把文件上传到 workspace 数据目录」是框架默认能力（任务书 v2 §4.6）。
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from agentbase.api.deps import require_company

router = APIRouter(tags=["files"])

_MAX_FILE_BYTES = 100 * 1024 * 1024  # 单文件 100MB 上限
_PATH_TRAVERSAL = re.compile(r"\.\.|^[/\\]|[<>:\"|?*]")


@router.post("/upload-files")
async def upload_to_work_dir(
    subdir: str = Form(),
    files: list[UploadFile] = File(),  # noqa: B008
    x_company_id: int = Depends(require_company),
):
    """上传文件到 workspace 数据目录的指定子目录。

    保留浏览器传来的相对路径结构；做路径穿越、空文件、大小上限校验。
    """
    from agentbase import company as _co
    from agentbase.company import _WORK_DIR_CATEGORIES, _setup_work_directory
    from agentbase.company.workdir import _get_desktop_path

    valid_subdirs = frozenset(name for name, _ in _WORK_DIR_CATEGORIES)
    if subdir not in valid_subdirs:
        raise HTTPException(status_code=400, detail=f"无效的子目录: {subdir}")

    co = _co.get(x_company_id)
    if not co:
        raise HTTPException(status_code=404, detail="workspace 不存在")

    work_dir = None
    tc = _co.get_trade_company(x_company_id)
    if tc and tc.get("extra1"):
        import json as _json

        try:
            saved = Path(_json.loads(tc["extra1"]).get("work_dir", ""))
            if saved.is_dir():
                work_dir = saved
        except Exception:
            pass

    if work_dir is None:
        # 必须用 workdir._get_desktop_path()：OneDrive 重定向桌面时自己猜路径会找错目录
        cleaned = re.sub(r'[<>:"/\\|?*]', "-", co["name"]).strip()
        candidate = _get_desktop_path() / cleaned
        work_dir = candidate if candidate.is_dir() else None
        if work_dir is None:
            work_dir, _ = _setup_work_directory(co["name"], co["slug"])
        try:
            import json as _json

            _co.update_trade_company(
                x_company_id, extra1=_json.dumps({"work_dir": str(work_dir)})
            )
        except Exception:
            pass

    target_dir = work_dir / subdir
    target_dir.mkdir(parents=True, exist_ok=True)

    uploaded = []
    for f in files:
        rel = getattr(f, "filename", "") or ""
        if not rel:
            rel = os.path.basename(f.filename or "untitled")

        safe_parts = []
        for part in Path(rel).parts:
            if _PATH_TRAVERSAL.search(part):
                cleaned = re.sub(r"[<>:\"|?*]", "_", part.replace("..", "_"))
                safe_parts.append("_sanitized_" + cleaned)
            else:
                safe_parts.append(part)
        safe_parts = [p for p in safe_parts if p and p != "."] or ["untitled"]

        dest = target_dir.joinpath(*safe_parts)
        try:
            dest.resolve().relative_to(work_dir.resolve())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"路径穿越拒绝: {rel}")

        if "\0" in rel:
            raise HTTPException(status_code=400, detail="文件名含非法字符")

        dest.parent.mkdir(parents=True, exist_ok=True)
        size = getattr(f, "size", None)
        if size is not None and size > _MAX_FILE_BYTES:
            raise HTTPException(status_code=413, detail=f"文件过大: {rel} ({size} bytes)")

        chunks = []
        total = 0
        while True:
            chunk = await f.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > _MAX_FILE_BYTES:
                raise HTTPException(status_code=413, detail=f"文件过大: {rel}")
            chunks.append(chunk)
        content = b"".join(chunks)
        if not content:
            raise HTTPException(status_code=400, detail=f"空文件: {rel}")
        dest.write_bytes(content)
        uploaded.append(str(dest.relative_to(work_dir)))

    return {
        "uploaded": len(uploaded),
        "files": uploaded,
        "target_path": str(target_dir),
    }
