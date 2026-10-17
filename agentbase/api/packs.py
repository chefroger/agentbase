"""
Skill Pack 管理 API（任务书 v2 §4.6「小白的自扩展路径」）。

第一期支持**本地目录安装**：
  - 安装：把本地 pack 目录复制到 `$AGENT_HOME/skill-packs/<name>/`
  - 启用：把 `business.yaml.skill_pack` 指向它并热加载注册表
  - 卸载：删除目录；若正被使用则先清空配置

远程 URL 安装涉及执行第三方代码，另行设计（不在本接口里）。
"""

from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agentbase import business_config

router = APIRouter(tags=["skill-packs"])

_NAME_OK = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.")


def _packs_root() -> Path:
    root = business_config.agent_home() / "skill-packs"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _validate_name(name: str) -> str:
    name = (name or "").strip()
    if not name or name in (".", "..") or any(c not in _NAME_OK for c in name):
        raise HTTPException(status_code=400, detail="非法的 pack 名称")
    return name


class InstallPayload(BaseModel):
    path: str = Field(..., description="本地 pack 目录（含 pack.yaml）")
    name: str | None = Field(None, description="目标名称（省略时取 pack.yaml 的 name）")


class ActivatePayload(BaseModel):
    name: str


def _pack_name_from_manifest(src: Path) -> str:
    try:
        import yaml

        data = yaml.safe_load((src / "pack.yaml").read_text(encoding="utf-8")) or {}
        return str(data.get("name") or "").strip()
    except Exception:
        return ""


def _write_active_pack(value: str) -> None:
    """更新 business.yaml 的 skill_pack（保留其它字段）。"""
    import yaml

    path = business_config.config_path()
    data: dict = {}
    if path.is_file():
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except Exception:
            data = {}
    if not isinstance(data, dict):
        data = {}
    data["skill_pack"] = value
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    business_config.reload()


def _reload_registry() -> int:
    try:
        from agentbase.skill_registry import load_active_pack

        return load_active_pack()
    except Exception:
        return 0


@router.get("/skill-packs")
def list_packs() -> dict:
    root = _packs_root()
    active_raw = str(business_config.get("skill_pack") or "").strip()
    active = Path(active_raw).expanduser() if active_raw else None
    if active is not None and not active.is_absolute():
        active = business_config.agent_home() / active.name if active.parent.name == "skill-packs" else active

    packs = []
    for d in sorted(root.iterdir()) if root.is_dir() else []:
        if not d.is_dir() or not (d / "pack.yaml").is_file():
            continue
        packs.append({"name": d.name, "path": str(d)})

    return {
        "packs": packs,
        "active": str(active) if active is not None else "",
        "packs_root": str(root),
    }


@router.post("/skill-packs/install")
def install_pack(payload: InstallPayload) -> dict:
    src = Path(payload.path).expanduser().resolve()
    if not src.is_dir() or not (src / "pack.yaml").is_file():
        raise HTTPException(status_code=400, detail="目录不存在或缺少 pack.yaml")

    name = _validate_name(payload.name or _pack_name_from_manifest(src) or src.name)
    dst = _packs_root() / name
    if dst.exists():
        raise HTTPException(status_code=409, detail=f"pack 已存在：{name}")

    shutil.copytree(src, dst)
    return {"ok": True, "name": name, "path": str(dst)}


@router.post("/skill-packs/activate")
def activate_pack(payload: ActivatePayload) -> dict:
    name = _validate_name(payload.name)
    target = _packs_root() / name
    if not (target / "pack.yaml").is_file():
        raise HTTPException(status_code=404, detail=f"pack 不存在：{name}")

    _write_active_pack(str(target))
    count = _reload_registry()
    return {"ok": True, "name": name, "skills": count}


@router.delete("/skill-packs/{name}")
def remove_pack(name: str) -> dict:
    name = _validate_name(name)
    target = _packs_root() / name
    if not target.is_dir():
        raise HTTPException(status_code=404, detail=f"pack 不存在：{name}")

    active_raw = str(business_config.get("skill_pack") or "")
    if active_raw and Path(active_raw).resolve() == target.resolve():
        _write_active_pack("")
        _reload_registry()

    shutil.rmtree(target)
    return {"ok": True, "name": name}
