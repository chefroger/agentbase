"""
设置页 API —— provider / API Key / 默认模型 / MoA 状态。

设计约束（任务书 v2 §4.6 / §10.11）：
  - API Key 只写 `$AGENT_HOME/.env`，由 Hermes provider 注册表的 `api_key_env_vars` 读取；
  - **接口永不返回 Key 明文**，只返回「是否已配置」；
  - 默认模型写入 `$AGENT_HOME/config.yaml` 的 `model` 段（经 Hermes 自己的 save_config，
    保留用户其它配置）；
  - 用户永不需跑 CLI。
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agentbase import business_config

router = APIRouter(tags=["settings"])


class KeysPayload(BaseModel):
    keys: dict[str, str] = Field(default_factory=dict, description="env 变量名 → Key")


class ModelPayload(BaseModel):
    provider: str = Field(..., min_length=1)
    model: str = Field(..., min_length=1)


def _env_path() -> Path:
    return business_config.agent_home() / ".env"


def _read_env() -> dict[str, str]:
    path = _env_path()
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        out[k.strip()] = v.strip()
    return out


def _write_env(updates: dict[str, str]) -> None:
    """更新 .env：保留其它行与注释，只增改目标键。文件权限 0600。"""
    path = _env_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []

    pending = dict(updates)
    out: list[str] = []
    for line in existing:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            k = stripped.partition("=")[0].strip()
            if k in pending:
                out.append(f"{k}={pending.pop(k)}")
                continue
        out.append(line)

    for k, v in pending.items():
        out.append(f"{k}={v}")

    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass


@router.get("/settings")
def get_settings() -> dict:
    """返回设置页所需的全部状态（不含任何 Key 明文）。"""
    from agentbase.hermes_compat import current_model_config, list_provider_records

    providers = list_provider_records()
    active_provider, active_model = current_model_config()

    configured = sum(1 for p in providers if p.get("has_key"))
    return {
        "providers": [
            {
                "id": p.get("id"),
                "name": p.get("name"),
                "has_key": bool(p.get("has_key")),
                "key_env_vars": p.get("key_env_vars") or [],
                "models": (p.get("models") or [])[:40],
            }
            for p in providers
        ],
        "active": {"provider": active_provider, "model": active_model},
        "configured_provider_count": configured,
        "moa_available": configured >= 2,
        "moa_hint": "MoA 会同时调用多个模型，token 消耗约为 N 倍。",
        "work_dirs": business_config.work_dir_names(),
    }


@router.post("/settings/keys")
def save_keys(payload: KeysPayload) -> dict:
    """保存 provider API Key 到 `$AGENT_HOME/.env`。"""
    updates = {
        str(k).strip(): str(v).strip()
        for k, v in payload.keys.items()
        if str(k).strip() and str(v).strip()
    }
    if not updates:
        raise HTTPException(status_code=400, detail="没有要保存的 Key")
    _write_env(updates)
    return {"ok": True, "saved": sorted(updates)}


@router.post("/settings/model")
def save_model(payload: ModelPayload) -> dict:
    """设置默认 provider / 模型（写入 config.yaml 的 model 段）。"""
    try:
        from hermes_cli.config import load_config, save_config

        config = load_config()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"读取配置失败：{exc}") from exc

    model_cfg = config.get("model")
    if not isinstance(model_cfg, dict):
        model_cfg = {}
    model_cfg["provider"] = payload.provider
    model_cfg["default"] = payload.model
    config["model"] = model_cfg

    try:
        save_config(config, merge_existing=True)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"保存配置失败：{exc}") from exc

    return {"ok": True, "provider": payload.provider, "model": payload.model}
