"""
API 层测试 — FastAPI 端点 + skill_router 匹配。

直接测试路由函数（不经过 HTTP），mock 外部 Hermes 依赖。
HTTP 层测试通过 run_server_smoke 验证即可。
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def setup_mocks():
    """模块级 mock Hermes 依赖。"""
    with patch.dict(sys.modules, {
        "hermes_cli": MagicMock(),
        "hermes_cli.config": MagicMock(),
        "hermes_cli.auth": MagicMock(),
        "hermes_cli.env_loader": MagicMock(),
        "hermes_cli.models": MagicMock(),
        "hermes_constants": MagicMock(),
        "run_agent": MagicMock(),
    }):
        import hermes_cli
        hermes_cli.__version__ = "0.13.0"

        from hermes_cli import env_loader
        env_loader.load_hermes_dotenv = MagicMock()

        import hermes_constants
        hermes_constants.get_hermes_home = MagicMock(return_value=Path("/tmp/.hermes"))

        from hermes_cli import config
        config.load_config = MagicMock(return_value={
            "model": {"provider": "openai", "default": "gpt-4o"}
        })

        from hermes_cli import auth
        class MockProviderConfig:
            auth_type = "api_key"
            api_key_env_vars = ["OPENAI_API_KEY"]
            display_name = "OpenAI"
            base_url_env_var = ""

        auth.PROVIDER_REGISTRY = {"openai": MockProviderConfig()}
        yield


@pytest.fixture
def test_db(monkeypatch, tmp_path, setup_mocks):
    """创建临时测试数据库（mock 桌面工作目录到 tmp_path）。"""
    db_path = tmp_path / "agentbase.db"

    import agentbase.database as _db
    original_db = _db._get_db_path
    _db._get_db_path = lambda: db_path

    from agentbase.database import SCHEMA_SQL, _add_spare_columns
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA_SQL)
    _add_spare_columns(conn)
    conn.commit()
    conn.close()

    # 桌面工作目录重定向到 tmp_path
    import agentbase.workspace as _co
    def _mock_setup(workspace_name, slug, suggested_name=""):
        wd = tmp_path / (suggested_name or workspace_name)
        wd.mkdir(parents=True, exist_ok=True)
        for cat_name, _ in _co._WORK_DIR_CATEGORIES:
            (wd / cat_name).mkdir(parents=True, exist_ok=True)
        return wd, True
    monkeypatch.setattr(_co, "_setup_work_directory", _mock_setup)

    yield db_path

    _db._get_db_path = original_db


@pytest.fixture
def workspace_id(test_db):
    """创建测试公司并返回 ID。"""
    from agentbase import workspace
    c = workspace.create(name="API Test Workspace", slug="api-test-workspace")
    return c["id"]


# ── Deps 测试 ──────────────────────────────────────────────────────────────


class TestDeps:
    """测试 API 依赖函数。"""

    def test_require_workspace_valid(self, workspace_id, setup_mocks):
        """有效的 X-Workspace-ID 返回 workspace_id。"""
        from agentbase.api.deps import require_workspace
        # 直接调用函数（绕过 FastAPI Header 依赖注入）
        result = require_workspace(str(workspace_id))
        assert result == workspace_id

    def test_require_workspace_missing(self, setup_mocks):
        """缺失 header → 401。"""
        from fastapi import HTTPException

        from agentbase.api.deps import require_workspace
        with pytest.raises(HTTPException) as exc_info:
            require_workspace("")
        assert exc_info.value.status_code == 401

    def test_require_workspace_invalid(self, setup_mocks):
        """无效 header → 401。"""
        from fastapi import HTTPException

        from agentbase.api.deps import require_workspace
        with pytest.raises(HTTPException) as exc_info:
            require_workspace("not-an-int")
        assert exc_info.value.status_code == 401

    def test_opt_workspace_missing(self, setup_mocks):
        """缺失 header → None。"""
        from agentbase.api.deps import opt_workspace
        assert opt_workspace("") is None
        assert opt_workspace(None) is None


class TestCronIsMachineLevel:
    """cron 端点是**机器级**资源，没有公司维度。

    审查曾标记 get_today_cron(cid) / get_active_jobs(cid)「要求公司头却从不使用」。
    核实结论：Hermes 的 cron 产物（~/.hermes/cron/jobs.json 与 output/）里没有任何
    公司标识，按公司过滤在数据模型上不可能。因此把「机器级」语义固化成测试：
    不同 cid 必须返回完全相同的数据；若将来真要按公司隔离，这个测试会先失败，
    提醒改动者那是产品级变更（需要 Hermes 侧给 job 打公司标签）。
    """

    @pytest.fixture
    def cron_with_jobs(self, monkeypatch, tmp_path):
        """把 cron 数据源指向临时目录，避免读真实 ~/.hermes。"""
        import agentbase.api.cron as cron_mod

        monkeypatch.setattr(cron_mod, "_JOBS_FILE", tmp_path / "jobs.json")
        monkeypatch.setattr(cron_mod, "_CRON_OUTPUT", tmp_path / "output")
        cron_mod._JOBS_FILE.write_text(
            json.dumps({"jobs": [
                {"name": "早安简报", "schedule": {"display": "0 9 * * *"}},
                {"name": "每日工作总结", "schedule": {"display": "0 17 * * *"}},
            ]}, ensure_ascii=False),
            encoding="utf-8",
        )
        return cron_mod

    def test_today_cron_identical_across_workspaces(self, cron_with_jobs):
        """不同公司的今日任务清单必须一致（cron 无公司维度）。"""
        # 位置传参：函数签名是 _cid（故意不使用），这里就是要证明它被忽略
        a = cron_with_jobs.get_today_cron(1)
        b = cron_with_jobs.get_today_cron(2)

        assert a == b, "cron 是机器级资源，不应随公司变化；若要按公司隔离需先改数据模型"

    def test_active_jobs_identical_across_workspaces(self, cron_with_jobs):
        """不同公司的活跃任务必须一致。"""
        a = cron_with_jobs.get_active_jobs(1)
        b = cron_with_jobs.get_active_jobs(999)

        assert a == b


class _FakeRequest:
    """只带 headers 的最小 Request 替身（require_session 只用到 request.headers）。"""

    def __init__(self, headers):
        self.headers = headers


class TestRequireSession:
    """require_session（session token 校验）的负向用例。

    此前这个依赖在全部测试里零覆盖：token 校验若被写反、或整段删掉，
    测试仍然全绿，而整站 API 会变成无鉴权。这里补上真实断言。
    """

    def test_rejects_wrong_token(self, setup_mocks):
        """token 不匹配 → 401。"""
        from fastapi import HTTPException

        from agentbase.api import deps

        deps.set_session_token("correct-token")
        with pytest.raises(HTTPException) as exc_info:
            deps.require_session(_FakeRequest({"X-Hermes-Session-Token": "wrong-token"}))
        assert exc_info.value.status_code == 401

    def test_rejects_missing_token(self, setup_mocks):
        """缺少 token header → 401。"""
        from fastapi import HTTPException

        from agentbase.api import deps

        deps.set_session_token("correct-token")
        with pytest.raises(HTTPException) as exc_info:
            deps.require_session(_FakeRequest({}))
        assert exc_info.value.status_code == 401

    def test_rejects_empty_token_when_server_token_empty(self, setup_mocks):
        """服务端 token 未初始化时不放行，返回 500（防御性：绝不能当成通过）。"""
        from fastapi import HTTPException

        from agentbase.api import deps

        deps.set_session_token("")
        with pytest.raises(HTTPException) as exc_info:
            deps.require_session(_FakeRequest({"X-Hermes-Session-Token": ""}))
        assert exc_info.value.status_code == 500

    def test_accepts_matching_token(self, setup_mocks):
        """token 匹配时放行（不抛异常）。"""
        from agentbase.api import deps

        deps.set_session_token("correct-token")
        deps.require_session(_FakeRequest({"X-Hermes-Session-Token": "correct-token"}))


# ── Router Assembly 测试 ────────────────────────────────────────────────────


class TestRouterAssembly:
    """测试路由组装和注册。"""

    @staticmethod
    def _flatten_routes(router):
        """递归展开嵌套的子路由。

        - fastapi <0.137: include_router 把子路由的每个 APIRoute 平铺到父 router.routes
        - fastapi >=0.137: 包成 _IncludedRouter，原始子 router 保留在 .original_router
        - Mount(子 app): 子 router 在 .routes 上
        """
        flat = []
        for r in router.routes:
            inner = getattr(r, "original_router", None) or (
                getattr(r, "routes", None) and r
            )
            if inner is not None and inner is not r:
                flat.extend(TestRouterAssembly._flatten_routes(inner))
            elif getattr(r, "routes", None):
                flat.extend(TestRouterAssembly._flatten_routes(r))
            else:
                flat.append(r)
        return flat

    def test_router_imports_and_registers(self, setup_mocks):
        """router 对象可正常导入且注册了所有端点类型。"""
        from agentbase.api import router
        assert router is not None

        all_routes = self._flatten_routes(router)

        # 应包含所有主要域
        key_routes = set()
        for route in all_routes:
            if hasattr(route, 'path'):
                p = route.path
                for keyword in ['workspaces', 'files', 'conversations',
                                'chat', 'memory', 'onboarding', 'models']:
                    if keyword in p:
                        key_routes.add(keyword)

        assert 'workspaces' in key_routes
        assert 'files' in key_routes
        assert 'chat' in key_routes

    def test_all_endpoints_registered(self, setup_mocks):
        """所有 endpoint 数量符合预期（至少 25 个）。"""
        from agentbase.api import router
        # 收集所有 HTTP 路由路径（递归展开嵌套子路由）
        endpoints = []
        for route in self._flatten_routes(router):
            if hasattr(route, 'path') and hasattr(route, 'methods'):
                for method in route.methods:
                    if method in ('GET', 'POST', 'PUT', 'DELETE'):
                        endpoints.append(f"{method} {route.path}")

        # 至少应有 25 个端点
        assert len(endpoints) >= 25, f"Expected >= 25 endpoints, got {len(endpoints)}"


# ── Skill Router Tests ──────────────────────────────────────────────────────


class TestCompanyEndpoints:
    """测试公司端点函数。"""

    def test_create_workspace(self, test_db, setup_mocks):
        from agentbase import workspace
        c = workspace.create(name="Endpoint Co", slug="endpoint-co")
        assert c["name"] == "Endpoint Co"
        assert c["slug"] == "endpoint-co"
        assert c["is_active"] is True

    def test_list_workspaces(self, test_db, workspace_id, setup_mocks):
        from agentbase import workspace
        workspaces = workspace.list_all()
        assert any(c["id"] == workspace_id for c in workspaces)

    def test_agent_identity(self, test_db, workspace_id, setup_mocks):
        from agentbase import workspace
        identity = workspace.get_agent_identity(workspace_id)
        assert isinstance(identity, str)  # may be empty, but should be a string

    def test_update_agent_identity(self, test_db, workspace_id, setup_mocks):
        from agentbase import workspace
        result = workspace.update_workspace_record(workspace_id, agent_identity_md="Test identity")
        assert result["agent_identity_md"] == "Test identity"


# ── Library Endpoint Functions ──────────────────────────────────────────────


class TestWorkDirUpload:
    """测试拖拽文件上传到公司工作目录子目录。"""

    @staticmethod
    def _run(coro):
        return asyncio.run(coro)

    def test_upload_single_file(self, test_db, workspace_id, setup_mocks, monkeypatch):
        """上传单个文件到指定子目录"""
        import io
        import tempfile

        from fastapi import UploadFile

        work_dir = Path(tempfile.mkdtemp(prefix="agentbase-work-test-"))
        monkeypatch.setattr("agentbase.workspace._setup_work_directory",
                           lambda name, slug, suggested_name="": (work_dir, True))
        monkeypatch.setattr("agentbase.workspace.get",
                           lambda cid: {"name": "Test", "slug": "test"})
        # 上传端点会读 agentbase_workspaces.extra1 取已保存的工作目录
        monkeypatch.setattr("agentbase.workspace.get_workspace_record",
                           lambda cid: {"extra1": None})
        monkeypatch.setattr("agentbase.workspace.update_workspace_record",
                           lambda cid, **kw: None)

        from agentbase.api.files import upload_to_work_dir

        f = UploadFile(filename="test.txt", file=io.BytesIO(b"hello world"))
        result = self._run(upload_to_work_dir(
            subdir="documents", files=[f], x_workspace_id=workspace_id,
        ))
        assert result["uploaded"] == 1
        assert "test.txt" in result["files"][0]
        assert (work_dir / "documents" / "test.txt").read_text() == "hello world"

    def test_upload_preserves_subdirs(self, test_db, workspace_id, setup_mocks, monkeypatch):
        """上传带子路径结构的文件"""
        import io
        import tempfile

        from fastapi import UploadFile

        work_dir = Path(tempfile.mkdtemp(prefix="agentbase-work-test-"))
        monkeypatch.setattr("agentbase.workspace._setup_work_directory",
                           lambda name, slug, suggested_name="": (work_dir, True))
        monkeypatch.setattr("agentbase.workspace.get",
                           lambda cid: {"name": "Test", "slug": "test"})
        # 上传端点会读 agentbase_workspaces.extra1 取已保存的工作目录
        monkeypatch.setattr("agentbase.workspace.get_workspace_record",
                           lambda cid: {"extra1": None})
        monkeypatch.setattr("agentbase.workspace.update_workspace_record",
                           lambda cid, **kw: None)

        from agentbase.api.files import upload_to_work_dir

        f1 = UploadFile(filename="sub/a.txt", file=io.BytesIO(b"aaa"))
        f2 = UploadFile(filename="sub/deep/b.txt", file=io.BytesIO(b"bbb"))
        result = self._run(upload_to_work_dir(
            subdir="documents", files=[f1, f2], x_workspace_id=workspace_id,
        ))
        assert result["uploaded"] == 2
        # result["files"] 的路径是相对于 work_dir 的，包含子目录前缀
        assert (work_dir / "documents" / "sub" / "a.txt").read_text() == "aaa"
        assert (work_dir / "documents" / "sub" / "deep" / "b.txt").read_text() == "bbb"

    def test_invalid_subdir_rejected(self, test_db, workspace_id, setup_mocks):
        """非法的子目录名应返回 400"""
        import io

        from fastapi import UploadFile

        from agentbase.api.files import upload_to_work_dir

        f = UploadFile(filename="test.txt", file=io.BytesIO(b"test"))
        with pytest.raises(Exception) as exc:
            self._run(upload_to_work_dir(
                subdir="../../../etc", files=[f], x_workspace_id=workspace_id,
            ))
        assert "400" in str(exc.value) or "无效" in str(exc.value)

    def test_path_traversal_sanitized(self, test_db, workspace_id, setup_mocks, monkeypatch):
        """含 ../ 的文件名应被 sanitize"""
        import io
        import tempfile

        from fastapi import UploadFile

        work_dir = Path(tempfile.mkdtemp(prefix="agentbase-work-test-"))
        monkeypatch.setattr("agentbase.workspace._setup_work_directory",
                           lambda name, slug, suggested_name="": (work_dir, True))
        monkeypatch.setattr("agentbase.workspace.get",
                           lambda cid: {"name": "Test", "slug": "test"})
        # 上传端点会读 agentbase_workspaces.extra1 取已保存的工作目录
        monkeypatch.setattr("agentbase.workspace.get_workspace_record",
                           lambda cid: {"extra1": None})
        monkeypatch.setattr("agentbase.workspace.update_workspace_record",
                           lambda cid, **kw: None)

        from agentbase.api.files import upload_to_work_dir

        f = UploadFile(filename="../escape.txt", file=io.BytesIO(b"bad"))
        result = self._run(upload_to_work_dir(
            subdir="documents", files=[f], x_workspace_id=workspace_id,
        ))
        assert result["uploaded"] == 1
        assert "escape.txt" in result["files"][0]
        written = work_dir / "报价单" / result["files"][0]
        assert written.resolve().is_relative_to(work_dir.resolve())


# ── Customer Endpoint Functions ─────────────────────────────────────────────


class TestConversationEndpoints:
    """测试对话端点函数。"""

    def test_save_conversation(self, test_db, workspace_id, setup_mocks):
        from agentbase import chat_memory
        conv = chat_memory.save(workspace_id, "Query", "Response",
                                 files_read=[{"file": "test.pdf", "pages": [1]}])
        assert conv["query"] == "Query"
        assert len(conv["files_read"]) == 1

    def test_list_conversations(self, test_db, workspace_id, setup_mocks):
        from agentbase import chat_memory
        chat_memory.save(workspace_id, "Q1", "A1")
        convs = chat_memory.list_by_workspace(workspace_id)
        assert len(convs) >= 1


# ── Onboarding Flow ─────────────────────────────────────────────────────────


class TestOnboardingFlow:
    """测试首次引导流程。"""

    def test_onboarding_status_new_db(self, test_db, setup_mocks):
        from agentbase import onboarding
        onboarding.reset_onboarding_flag()
        assert onboarding.is_onboarding_done() is False

    def test_create_first_workspace(self, test_db, setup_mocks):
        from agentbase import onboarding
        onboarding.reset_onboarding_flag()

        result = onboarding.create_first_workspace(
            workspace_name="Flow Test Co",
            contact_name="Alice",
            identity_data={
                "products": "Electronics",
                "differentiation": "OEM factory",
                "target_region": "Europe",
            },
        )
        assert result["workspace"]["name"] == "Flow Test Co"
        assert "Electronics" in result["agentbase_workspace"]["agent_identity_md"]
        assert onboarding.is_onboarding_done() is True

    def test_create_first_workspace_duplicate(self, test_db, workspace_id, setup_mocks):
        from agentbase import onboarding
        assert onboarding.is_onboarding_done() is True


class _FakeClient:
    """只带 client.host 的最小请求替身（回环判定只看它）。"""

    def __init__(self, host):
        self.client = type("C", (), {"host": host})()


class TestTradeUiTokenScope:
    """session token 只下发给本机回环客户端。

    token 是唯一凭据，而 /agentbase 页面本身无需鉴权即可获取 —— 一旦 --host 0.0.0.0，
    局域网内任意主机 fetch 该页就能拿到 token 并接管全部 API（含 /system/update）。
    """

    def test_loopback_clients_may_receive_token(self):
        from agentbase.app import _client_is_loopback

        for host in ("127.0.0.1", "::1", "::ffff:127.0.0.1"):
            assert _client_is_loopback(_FakeClient(host)) is True, host

    def test_remote_clients_are_not_loopback(self):
        from agentbase.app import _client_is_loopback

        for host in ("192.168.1.5", "10.0.0.7", "203.0.113.9", ""):
            assert _client_is_loopback(_FakeClient(host)) is False, host

    def test_remote_client_blocked_by_default(self, monkeypatch):
        from agentbase import app as app_mod

        monkeypatch.delenv("AGENTBASE_ALLOW_REMOTE_UI", raising=False)
        assert app_mod._client_may_receive_token(_FakeClient("192.168.1.5")) is False

    def test_remote_client_allowed_with_explicit_optin(self, monkeypatch):
        """显式开启后允许局域网使用（用户明确知道风险）。"""
        from agentbase import app as app_mod

        monkeypatch.setenv("AGENTBASE_ALLOW_REMOTE_UI", "1")
        assert app_mod._client_may_receive_token(_FakeClient("192.168.1.5")) is True
