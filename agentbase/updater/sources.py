"""更新源适配器：新版从哪里来与「怎么换」解耦。

- GitSource     ：源码安装（`~/.agentbase/agentbase` 是 git checkout）。
- PackageSource ：单文件 exe / macOS .app，按 manifest 下载并原子替换产物。
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

MANIFEST_ENV = "AGENTBASE_UPDATE_MANIFEST"


class UpdateSource:
    name = "base"

    def snapshot(self) -> dict:
        """记录回滚所需的信息（写入 update-state.json）。"""
        return {}

    def prepare(self) -> None:
        """把新版放到运行位置；失败抛异常。"""
        raise NotImplementedError

    def rollback(self, snapshot: dict) -> None:
        """把代码/产物换回 snapshot 记录的状态。"""
        raise NotImplementedError

    def service_command(self, port: int | None = None) -> list[str]:
        raise NotImplementedError


class GitSource(UpdateSource):
    name = "git"

    def __init__(self, repo: Path | None = None):
        if repo is None:
            from agentbase.post_install.skills import get_agent_home

            repo = get_agent_home() / "agentbase"
        self.repo = Path(repo)

    def snapshot(self) -> dict:
        try:
            head = subprocess.run(
                ["git", "-C", str(self.repo), "rev-parse", "HEAD"],
                capture_output=True, text=True, timeout=15,
            )
            return {"old_head": head.stdout.strip() if head.returncode == 0 else ""}
        except (OSError, subprocess.TimeoutExpired):
            return {"old_head": ""}

    def prepare(self) -> None:
        from agentbase.post_install.update import update_agentbase

        result = update_agentbase()
        if not result.get("ok"):
            raise RuntimeError("; ".join(result.get("errors") or ["git 更新失败"]))

    def rollback(self, snapshot: dict) -> None:
        old_head = (snapshot or {}).get("old_head") or ""
        if not old_head:
            raise RuntimeError("缺少旧版本 commit，无法回滚代码")
        subprocess.run(
            ["git", "-C", str(self.repo), "reset", "--hard", old_head],
            check=True, capture_output=True, timeout=60,
        )
        # 依赖可能已随新版升级；旧版重新装一次（失败不阻塞，服务仍尝试启动）
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-e", ".", "--no-deps"],
            cwd=str(self.repo), capture_output=True, timeout=300,
        )

    def service_command(self, port: int | None = None) -> list[str]:
        cmd = [sys.executable, str(self.repo / "server.py"), "--no-browser"]
        if port:
            cmd += ["--port", str(port)]
        return cmd


class PackageSource(UpdateSource):
    name = "package"

    def __init__(self, executable: str | None = None, manifest: str | None = None):
        self.executable = Path(executable or sys.executable)
        self._manifest_ref = manifest or os.environ.get(MANIFEST_ENV, "")

    # ── manifest ──────────────────────────────────────────────────────────

    def _manifest_location(self) -> str:
        if self._manifest_ref:
            return self._manifest_ref
        local = self.executable.parent / "manifest.json"
        return str(local) if local.is_file() else ""

    def _load_manifest(self) -> dict:
        ref = self._manifest_location()
        if not ref:
            raise RuntimeError(
                "未配置更新源：请把 manifest.json 放在程序同目录，"
                f"或设置环境变量 {MANIFEST_ENV}"
            )
        if "://" in ref:
            with urllib.request.urlopen(ref, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        return json.loads(Path(ref).read_text(encoding="utf-8"))

    def _download(self, url: str, manifest_ref: str) -> Path:
        if "://" not in url:
            # 相对路径按 manifest 所在位置解析（本地分发/测试）
            base = Path(manifest_ref).parent
            return base / url
        fd, tmp = tempfile.mkstemp(prefix="agentbase-update-")
        os.close(fd)
        with urllib.request.urlopen(url, timeout=60) as resp, open(tmp, "wb") as out:
            shutil.copyfileobj(resp, out)
        return Path(tmp)

    # ── source API ────────────────────────────────────────────────────────

    def snapshot(self) -> dict:
        return {"old_artifact": str(self.executable)}

    def prepare(self) -> None:
        manifest = self._load_manifest()
        url = str(manifest.get("url") or "")
        expected = str(manifest.get("sha256") or "").lower()
        if not url or not expected:
            raise RuntimeError("manifest.json 缺少 url 或 sha256")

        new_file = self._download(url, self._manifest_location())
        try:
            digest = hashlib.sha256(new_file.read_bytes()).hexdigest()
            if digest != expected:
                raise RuntimeError(f"新版本校验失败（sha256 不匹配）：{digest[:12]}…")

            current = self.executable
            backup = current.with_name(current.name + ".old")
            try:
                backup.unlink(missing_ok=True)
            except OSError:
                pass
            # Windows 不允许覆盖正在运行的 exe，但允许重命名 —— 更新器本身
            # 就在运行旧 exe，所以先改名、再落新文件（任务书 §12 设计 0）。
            os.replace(current, backup)
            try:
                shutil.copy2(new_file, current)
                if os.name != "nt":
                    current.chmod(0o755)
            except Exception:
                os.replace(backup, current)
                raise
        finally:
            if new_file.name.startswith("agentbase-update-"):
                new_file.unlink(missing_ok=True)

    def rollback(self, snapshot: dict) -> None:
        backup = Path((snapshot or {}).get("old_artifact") or "")
        backup = backup.with_name(backup.name + ".old")
        if not backup.is_file():
            raise RuntimeError("找不到旧版本产物，无法回滚")
        os.replace(backup, self.executable)

    def service_command(self, port: int | None = None) -> list[str]:
        cmd = [str(self.executable), "--service", "--no-browser"]
        if port:
            cmd += ["--port", str(port)]
        return cmd

    def cleanup_old_artifact(self) -> None:
        """新版本成功启动后删掉 `.old`。"""
        old = self.executable.with_name(self.executable.name + ".old")
        try:
            old.unlink(missing_ok=True)
        except OSError:
            pass


def detect_source() -> UpdateSource:
    """打包产物没有 .git，走 PackageSource；源码安装走 GitSource。"""
    if getattr(sys, "frozen", False):
        return PackageSource()
    return GitSource()


def manifest_url_for(ref: str) -> str:
    """测试/诊断辅助：把本地路径或 URL 归一成可展示的形式。"""
    return urllib.parse.urlparse(ref).geturl() if "://" in ref else str(Path(ref))
