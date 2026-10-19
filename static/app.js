/* AgentBase 底座前端：设置门户 + API 调试控制台 + /dev 调试聊天。
 * 原生 JS，无构建步骤；模块边界由 #region 标记（tests_js 依赖）。
 */

// ═════════════════════ 全局状态 ═════════════════════
let currentCompanyId = null;
let workspaces = [];
let currentLang = 'zh';
let currentRoute = { view: 'settings', page: 'home' };
let _debugEl = null;
let _settingsEl = null;
let _routeSeq = 0;
let _branding = { workspaces: { term: '工作区', term_en: 'Workspace', mode: 'single' } };
let _settingsCache = null;

// #region i18n —— 文案集中管理；新增 key 必须 zh/en 同时存在
const I18N = {
    zh: {
        'nav.settings': '设置', 'nav.debug': '调试', 'nav.section': '底座',
        'debug.title': '调试 / 示例', 'debug.banner': '开发调试用：仅用于验证后端 API，不是业务界面。',
        'debug.placeholder': '输入消息，验证 /chat/stream …', 'debug.send': '发送', 'debug.stop': '停止',
        'debug.clear': '清屏', 'debug.raw': '原始 SSE 事件', 'debug.probe': 'API 自检',
        'debug.empty': '还没有消息。发送一条消息验证 SSE 全链路。',
        'settings.title': '设置', 'settings.home': '设置', 'settings.back': '← 返回设置',
        'settings.save': '保存', 'settings.saved': '已保存', 'settings.loading': '加载中…',
        'settings.load_failed': '加载失败', 'settings.readonly': '只读',
        'settings.group.models': '模型与 API Key', 'settings.group.models_desc': '选择 Provider、填写 Key、设置默认模型',
        'settings.group.agent_behavior': 'Agent 行为', 'settings.group.agent_behavior_desc': 'MoA、YOLO 与审批规则',
        'settings.group.workspaces': '工作区', 'settings.group.workspaces_desc': '称呼、单/多、自定义字段与实例',
        'settings.group.agent': '智能体与提示词', 'settings.group.agent_desc': 'Agent 身份与 system prompt',
        'settings.group.business': '业务与方向', 'settings.group.business_desc': '使用方向、品牌与 onboarding 字段',
        'settings.group.skills': 'Skill 包与扩展', 'settings.group.skills_desc': '技能包、MCP、plugins、toolsets',
        'settings.group.files': '文件与目录', 'settings.group.files_desc': 'work_dirs 与文件上传',
        'settings.group.system': '系统', 'settings.group.system_desc': '服务、更新、备份、日志与 cron',
        'settings.group.developer': '开发者', 'settings.group.developer_desc': 'API 调试控制台与接口文档',
        'models.providers': 'Provider', 'models.configured': '已配置', 'models.not_configured': '未配置',
        'models.key_placeholder': '填写 API Key', 'models.default_model': '默认模型',
        'models.provider': 'Provider', 'models.model': '模型名', 'models.restart_hint': '保存后需重启服务生效',
        'behavior.moa': 'MoA（多模型协作）', 'behavior.yolo': 'YOLO 模式', 'behavior.approvals': '审批拒绝规则',
        'behavior.enabled': '已开启', 'behavior.disabled': '已关闭', 'behavior.none': '（无）',
        'workspaces.term': '称呼', 'workspaces.term_en': '英文称呼', 'workspaces.mode': '模式',
        'workspaces.mode_single': '单工作区', 'workspaces.mode_multi': '多工作区',
        'workspaces.create_default': '启动时自动创建默认工作区', 'workspaces.fields': '自定义字段',
        'workspaces.add_field': '添加字段', 'workspaces.instances': '实例',
        'workspaces.new': '新建', 'workspaces.delete': '删除', 'workspaces.switch': '切换',
        'workspaces.no_instances': '暂无实例',
        'agent.name': '工作区名称', 'agent.identity': 'Agent 身份（Markdown）',
        'agent.system_prompt': '全局 system prompt 覆盖', 'agent.priority': '优先级：Agent 身份 > 全局 system.md > business prompt_overrides > 内置默认',
        'business.direction': '使用方向', 'business.name': '业务名称', 'business.tagline': '标语',
        'business.brand_title': '前端标题', 'business.welcome': '欢迎语',
        'business.onboarding': 'Onboarding 字段', 'business.apply': '应用推荐',
        'business.recommend': '推荐', 'business.recommended_pack': '推荐技能包',
        'business.direction_hint': '切换方向不会自动覆盖配置；点击“应用推荐”后再保存。',
        'skills.packs': '技能包', 'skills.install_path': '本地 pack 目录（含 pack.yaml）',
        'skills.install': '安装', 'skills.activate': '启用', 'skills.remove': '卸载',
        'skills.active': '已启用', 'skills.update': '更新技能内容',
        'skills.extensions': '扩展（只读）', 'skills.mcp': 'MCP servers', 'skills.plugins': 'Plugins',
        'skills.toolsets': '启用的 toolsets', 'skills.no_packs': '尚未安装技能包',
        'files.work_dirs': '工作目录分类', 'files.upload': '上传文件', 'files.subdir': '目标目录',
        'files.choose': '选择文件', 'files.data_root': '数据目录',
        'system.service': '服务', 'system.running': '运行中', 'system.autostart': '开机自启',
        'system.quit': '退出服务', 'system.update': '检查并更新', 'system.restart': '重启服务',
        'system.backup': '备份数据', 'system.logs': '日志', 'system.log_select': '选择日志',
        'system.refresh': '刷新', 'system.cron': '定时任务（机器级）',
        'system.confirm_quit': '确定退出服务？退出后定时任务会停止。',
        'system.no_jobs': '暂无任务',
        'dev.token': 'Session Token', 'dev.copy': '复制', 'dev.copied': '已复制',
        'dev.openapi': 'OpenAPI', 'dev.swagger': 'Swagger UI', 'dev.docs': 'API 文档',
        'dev.endpoints': '端点', 'dev.search': '搜索端点…', 'dev.console': '调试控制台',
        'dev.send': '发送请求', 'dev.response': '响应', 'dev.workspace': 'Workspace ID',
        'dev.body': 'JSON 请求体', 'dev.path_params': '路径参数',
        'dev.token_note': 'token 随服务重启轮换',
        'toast.request_timeout': '请求超时', 'toast.no_workspace': '请先选择工作区',
        'toast.copied': '已复制', 'toast.save_failed': '保存失败',
        'license.trial': '试用中', 'license.expired': '许可证已到期', 'license.activate': '激活',
        'license.activated': '激活成功', 'license.activate_fail': '激活失败',
        'license.enter_code': '请输入激活码',
        'update.confirm': '本次更新内容：', 'update.backup_note': '更新前会自动备份；完成后服务会重启。现在更新吗？',
        'update.restarting': '正在重启…', 'update.done': '更新完成', 'update.failed': '更新失败',
        'common.close': '关闭', 'common.cancel': '取消', 'common.confirm': '确定',
    },
    en: {
        'nav.settings': 'Settings', 'nav.debug': 'Debug', 'nav.section': 'Base',
        'debug.title': 'Debug / Example', 'debug.banner': 'For development only: verifies backend APIs, not a business UI.',
        'debug.placeholder': 'Send a message to verify /chat/stream …', 'debug.send': 'Send', 'debug.stop': 'Stop',
        'debug.clear': 'Clear', 'debug.raw': 'Raw SSE events', 'debug.probe': 'API probe',
        'debug.empty': 'No messages yet. Send one to verify the SSE pipeline.',
        'settings.title': 'Settings', 'settings.home': 'Settings', 'settings.back': '← Back to settings',
        'settings.save': 'Save', 'settings.saved': 'Saved', 'settings.loading': 'Loading…',
        'settings.load_failed': 'Failed to load', 'settings.readonly': 'Read-only',
        'settings.group.models': 'Models & API Keys', 'settings.group.models_desc': 'Provider, keys and default model',
        'settings.group.agent_behavior': 'Agent behaviour', 'settings.group.agent_behavior_desc': 'MoA, YOLO and approvals',
        'settings.group.workspaces': 'Workspaces', 'settings.group.workspaces_desc': 'Term, mode, custom fields and instances',
        'settings.group.agent': 'Agent & prompts', 'settings.group.agent_desc': 'Agent identity and system prompt',
        'settings.group.business': 'Business & direction', 'settings.group.business_desc': 'Direction, branding and onboarding fields',
        'settings.group.skills': 'Skill packs & extensions', 'settings.group.skills_desc': 'Packs, MCP, plugins, toolsets',
        'settings.group.files': 'Files & directories', 'settings.group.files_desc': 'work_dirs and uploads',
        'settings.group.system': 'System', 'settings.group.system_desc': 'Service, updates, backup, logs and cron',
        'settings.group.developer': 'Developer', 'settings.group.developer_desc': 'API console and reference',
        'models.providers': 'Providers', 'models.configured': 'Configured', 'models.not_configured': 'Not configured',
        'models.key_placeholder': 'API Key', 'models.default_model': 'Default model',
        'models.provider': 'Provider', 'models.model': 'Model name', 'models.restart_hint': 'Restart required after saving',
        'behavior.moa': 'MoA (multi-model)', 'behavior.yolo': 'YOLO mode', 'behavior.approvals': 'Approval deny rules',
        'behavior.enabled': 'Enabled', 'behavior.disabled': 'Disabled', 'behavior.none': '(none)',
        'workspaces.term': 'Term', 'workspaces.term_en': 'English term', 'workspaces.mode': 'Mode',
        'workspaces.mode_single': 'Single', 'workspaces.mode_multi': 'Multiple',
        'workspaces.create_default': 'Create a default workspace on boot', 'workspaces.fields': 'Custom fields',
        'workspaces.add_field': 'Add field', 'workspaces.instances': 'Instances',
        'workspaces.new': 'New', 'workspaces.delete': 'Delete', 'workspaces.switch': 'Switch',
        'workspaces.no_instances': 'No instances',
        'agent.name': 'Workspace name', 'agent.identity': 'Agent identity (Markdown)',
        'agent.system_prompt': 'Global system prompt override', 'agent.priority': 'Priority: identity > global system.md > business prompt_overrides > built-in default',
        'business.direction': 'Usage direction', 'business.name': 'Business name', 'business.tagline': 'Tagline',
        'business.brand_title': 'UI title', 'business.welcome': 'Welcome text',
        'business.onboarding': 'Onboarding fields', 'business.apply': 'Apply recommendation',
        'business.recommend': 'Recommendation', 'business.recommended_pack': 'Recommended pack',
        'business.direction_hint': 'Switching direction does not overwrite config; apply the recommendation, then save.',
        'skills.packs': 'Skill packs', 'skills.install_path': 'Local pack directory (contains pack.yaml)',
        'skills.install': 'Install', 'skills.activate': 'Activate', 'skills.remove': 'Remove',
        'skills.active': 'Active', 'skills.update': 'Update skill content',
        'skills.extensions': 'Extensions (read-only)', 'skills.mcp': 'MCP servers', 'skills.plugins': 'Plugins',
        'skills.toolsets': 'Enabled toolsets', 'skills.no_packs': 'No packs installed',
        'files.work_dirs': 'Work directories', 'files.upload': 'Upload file', 'files.subdir': 'Target directory',
        'files.choose': 'Choose file', 'files.data_root': 'Data directory',
        'system.service': 'Service', 'system.running': 'Running', 'system.autostart': 'Autostart',
        'system.quit': 'Quit service', 'system.update': 'Check & update', 'system.restart': 'Restart service',
        'system.backup': 'Backup data', 'system.logs': 'Logs', 'system.log_select': 'Select log',
        'system.refresh': 'Refresh', 'system.cron': 'Cron jobs (machine level)',
        'system.confirm_quit': 'Quit the service? Cron jobs will stop.',
        'system.no_jobs': 'No jobs',
        'dev.token': 'Session Token', 'dev.copy': 'Copy', 'dev.copied': 'Copied',
        'dev.openapi': 'OpenAPI', 'dev.swagger': 'Swagger UI', 'dev.docs': 'API reference',
        'dev.endpoints': 'Endpoints', 'dev.search': 'Search endpoints…', 'dev.console': 'Console',
        'dev.send': 'Send request', 'dev.response': 'Response', 'dev.workspace': 'Workspace ID',
        'dev.body': 'JSON body', 'dev.path_params': 'Path parameters',
        'dev.token_note': 'Token rotates when the service restarts',
        'toast.request_timeout': 'Request timed out', 'toast.no_workspace': 'Select a workspace first',
        'toast.copied': 'Copied', 'toast.save_failed': 'Save failed',
        'license.trial': 'Trial', 'license.expired': 'License expired', 'license.activate': 'Activate',
        'license.activated': 'Activated', 'license.activate_fail': 'Activation failed',
        'license.enter_code': 'Enter activation code',
        'update.confirm': 'What changed:', 'update.backup_note': 'A backup is created first; the service restarts afterwards. Update now?',
        'update.restarting': 'Restarting…', 'update.done': 'Update complete', 'update.failed': 'Update failed',
        'common.close': 'Close', 'common.cancel': 'Cancel', 'common.confirm': 'Confirm',
    },
};
// #endregion i18n

function t(key, params) {
    const table = I18N[currentLang] || I18N.zh;
    let text = table[key] || I18N.zh[key] || key;
    if (params) {
        Object.keys(params).forEach(function(k) {
            text = text.replace('{' + k + '}', params[k]);
        });
    }
    return text;
}

function switchLang(lang) {
    if (lang === currentLang) return;
    currentLang = lang;
    try { localStorage.setItem('agentbase_lang', lang); } catch(_) {}
    applyStaticCopy();
    if (currentRoute.view === 'settings') {
        const el = _settingsEl;
        if (el) renderSettingsRoute(currentRoute.page, el);
    }
}

function initLang() {
    let lang = 'zh';
    try { lang = localStorage.getItem('agentbase_lang') || 'zh'; } catch(_) {}
    currentLang = lang;
    const sel = document.getElementById('lang-select');
    if (sel) sel.value = lang;
    applyStaticCopy();
}

function applyStaticCopy() {
    document.getElementById('nav-label-settings').textContent = t('nav.settings');
    document.getElementById('nav-label-debug').textContent = t('nav.debug');
    document.getElementById('nav-section-main').textContent = t('nav.section');
    document.title = (_branding.title && _branding.title !== 'AgentBase')
        ? _branding.title + ' · AgentBase' : 'AgentBase';
    const updateBtn = document.getElementById('system-update-btn');
    if (updateBtn) updateBtn.title = t('system.update');
    const restartBtn = document.getElementById('system-restart-btn');
    if (restartBtn) restartBtn.title = t('system.restart');
}

// ═════════════════════ 基础工具 ═════════════════════
function toast(msg) {
    const box = document.getElementById('toast-container');
    if (!box) return;
    const el = document.createElement('div');
    el.className = 'toast';
    el.textContent = String(msg || '');
    box.appendChild(el);
    setTimeout(function() { el.remove(); }, 3500);
}

function showModal(id) {
    const el = document.getElementById(id);
    if (el) el.classList.remove('hidden');
}

function hideModal(id) {
    const el = document.getElementById(id);
    if (el) el.classList.add('hidden');
}

// #region html-escape-utils —— 这段被 tests_js/esc.test.js 按标记整体抽取测试，勿删标记
// HTML 转义表：& < > 三个是文本上下文必需，" 和 ' 是属性上下文必需
// （不转引号时，值里的一个 " 就能闭合 value="..." 并注入新属性）
const _ESC_MAP = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };

// HTML 文本 / 属性转义。转义后仅做还原，不丢内容；对 null/undefined/0 返回空串（沿用原语义）
function esc(s) {
    return String(s || '').replace(/[&<>"']/g, function (ch) { return _ESC_MAP[ch]; });
}

// 内联事件处理器（onclick="fn('...')"）里的 JS 字面量转义
// 先用 JSON.stringify 得到带引号的合法 JS 串，再整体做 HTML 属性转义。
// 顺序不可颠倒：浏览器会先解码 HTML 实体，再把结果交给 JS 解析器
function escJs(s) {
    return esc(JSON.stringify(String(s || '')));
}
// #endregion html-escape-utils

// #region modal-utils —— 这段被 tests_js/modal.test.js 按标记整体抽取测试，勿删标记
// 静态模版弹窗白名单：它们在 app.html 里写死，动态清理时必须跳过。
// 新增静态弹窗要同步加进来，否则会被 _removeDynamicModals 当作动态弹窗删掉。
const _STATIC_MODAL_IDS = new Set(['workspace-modal']);
// 安全移除动态弹窗（跳过静态模版弹窗避免误删 HTML 中的 modal-backdrop 骨架）
function _removeDynamicModals() {
    document.querySelectorAll('.modal-backdrop').forEach(function(e) {
        if (!_STATIC_MODAL_IDS.has(e.id)) e.remove();
    });
}
// #endregion modal-utils

// ═════════════════════ API ═════════════════════
let _authRecovering = false;

// 把请求体里 id 类字段的空字符串规范化为 null，避免后端 422 int_parsing
function normalizeBody(body) {
    if (!body || typeof body !== 'object') return body;
    var out = {};
    var idFields = ['library_id', 'customer_id', 'workspace_id'];
    for (var k in body) {
        if (body[k] === '' && (idFields.indexOf(k) >= 0 || /(^|_)(id|ids)$/i.test(k))) {
            out[k] = null;
        } else {
            out[k] = body[k];
        }
    }
    return out;
}

// #region api-opts —— 这段被 tests_js/api-opts.test.js 按标记整体抽取测试，勿删标记
// 构造请求选项：鉴权头 + body 编码。
// FormData（文件上传）必须原样透传且不设 Content-Type —— 否则会丢掉 multipart 的 boundary。
function _buildApiOpts(method, body, token, companyId) {
    const opts = { method: method, headers: {} };
    if (token) opts.headers['X-Hermes-Session-Token'] = token;
    if (companyId) opts.headers['X-Workspace-ID'] = String(companyId);
    if (body instanceof FormData) {
        opts.body = body;
    } else if (body) {
        opts.headers['Content-Type'] = 'application/json';
        opts.body = JSON.stringify(normalizeBody(body));
    }
    return opts;
}
// #endregion api-opts

async function api(method, path, body) {
    const opts = _buildApiOpts(method, body, TOKEN, currentCompanyId);
    const ctrl = new AbortController();
    const tid = setTimeout(function() { ctrl.abort(); }, 120000);
    opts.signal = ctrl.signal;
    try {
        const r = await fetch(path, opts);
        clearTimeout(tid);
        if (!r.ok) {
            const err = await r.json().catch(function() { return {}; });
            const msg = err.detail || ('HTTP ' + r.status);
            if (r.status === 401) {
                const recovered = await recoverAuth(method, path, body);
                if (recovered !== null) return recovered;
                toast(t('toast.no_workspace'));
            } else if (r.status === 402) {
                showLicenseExpired(msg);
            } else {
                toast(msg);
            }
            return null;
        }
        return r.json();
    } catch (e) {
        clearTimeout(tid);
        if (e.name === 'AbortError') { toast(t('toast.request_timeout')); return null; }
        throw e;
    }
}

async function recoverAuth(method, path, body) {
    if (_authRecovering) return null;
    _authRecovering = true;
    try {
        const fresh = await fetch('/agentbase?_=' + Date.now(), { cache: 'no-store' });
        if (fresh.ok) {
            const html = await fresh.text();
            const m = html.match(/(?:const|let|var)\s+TOKEN\s*=\s*"([^"]+)"/);
            if (m && m[1] && m[1] !== TOKEN) {
                TOKEN = m[1];
                const retry = await api(method, path, body);
                if (retry !== null) return retry;
            }
        }
        await loadWorkspaces();
        return null;
    } catch (_) {
        return null;
    } finally {
        _authRecovering = false;
    }
}

// #region cron-task-line
function _cronTaskLine(t) {
    const unknown = !!(t && t.unknown_schedule);
    const missed = !!(t && t.missed);
    const color = missed ? 'var(--accent-red)' : 'var(--text-muted)';
    const mark = unknown ? '?' : (missed ? '⚠' : '○');
    // scheduled 为 null（未知调度）时不能直接渲染，否则界面上出现 "null"
    const when = unknown ? '调度未知' : (t.scheduled || '');
    let suffix = '';
    if (missed) suffix = '<span style="color:var(--accent-red);font-size:11px;">（已过时）</span>';
    else if (unknown) suffix = '<span style="color:var(--text-muted);font-size:11px;">（无法解析调度时间）</span>';
    return `<div style="display:flex;align-items:center;gap:8px;padding:3px 0;font-size:13px;">`
        + `<span style="color:${color};">${mark}</span>`
        + `<span style="font-weight:500;color:${missed ? 'var(--accent-red)' : ''};">${esc(t.name)}</span>`
        + `<span style="color:var(--text-muted);font-size:11px;">${esc(when)}</span>`
        + suffix + `</div>`;
}
// #endregion cron-task-line

// #region sse-outcome
/**
 * 流结束后的分类与兜底文案。判据是「有没有收到 done」：
 *   - done 是服务端在 finally 里必发的事件（agentbase/api/chat.py），收到它说明
 *     服务端走完了整个流程 —— 此时还没有内容，就是服务端一侧没能给出来。
 *   - 没收到 done 说明连接中途断了 —— 属于网络/客户端侧。
 * 历史 bug：两者（外加 agent 线程静默死亡）都显示同一句「Agent 未返回有效回复」，
 * 用户既不知道原因也不知道该做什么。
 */
function _sseStreamOutcome(sawResponse, sawDone) {
    if (sawResponse) return { kind: 'response' };
    if (sawDone) {
        return { kind: 'silent', message: '⚠️ 服务端未能给出回复（请求已结束但内容为空）。请重试一次；若反复出现，请把这条消息发给技术支持。' };
    }
    return { kind: 'interrupted', message: '⚠️ 连接中断，未收到回复。请检查网络后重试。' };
}
// #endregion sse-outcome

// #region stream-guard —— 这段被 tests_js/stream-guard.test.js 按标记整体抽取测试，勿删标记
// 聊天流的归属记账：记录「当前这条流属于哪个工作区」。
// 存在的理由：sendDebugMsg 里的 AbortController 是局部变量，切换工作区时无人能中止它，
// 旧流跑完后又会往页面写内容；归属记账让切换工作区能统一作废旧流。
let _chatStream = null;  // { cid, ctl }

// 开始一条属于 cid 的聊天流，返回它的 AbortController
function _beginChatStream(cid) {
    const ctl = new AbortController();
    _chatStream = { cid: cid, ctl: ctl };
    return ctl;
}

// 作废当前聊天流（切换工作区时调用），保证旧流不再往页面写内容
function _abortChatStream() {
    if (_chatStream) {
        _chatStream.ctl.abort();
        _chatStream = null;
    }
}

// 流收尾时清理自己那条（仅当它仍是当前流，避免误清用户切工作区后新建的流）
function _endChatStream(ctl) {
    if (_chatStream && _chatStream.ctl === ctl) _chatStream = null;
}

// 该工作区的流是否仍是当前活跃流（旧流据此丢弃输出）
function _chatStreamBelongsTo(cid) {
    return !!_chatStream && _chatStream.cid === cid;
}
// #endregion stream-guard

// #region route-utils
const SETTINGS_PAGES = ['home', 'models', 'agent-behavior', 'workspaces', 'agent',
    'business', 'skills', 'files', 'system', 'developer'];

function parseHashRoute(hash) {
    const raw = String(hash || '').replace(/^#\/?/, '');
    if (raw === 'dev') return { view: 'debug', page: 'dev' };
    const parts = raw.split('/').filter(Boolean);
    if (parts[0] === 'settings') {
        const page = parts[1] || 'home';
        return { view: 'settings', page: SETTINGS_PAGES.indexOf(page) >= 0 ? page : 'home' };
    }
    return { view: 'settings', page: 'home' };
}

function routeHash(route) {
    if (route.view === 'debug') return '#/dev';
    return '#/settings' + (route.page && route.page !== 'home' ? '/' + route.page : '');
}
// #endregion route-utils

// ═════════════════════ 路由与视图 ═════════════════════
function navigateTo(hash) {
    if (location.hash === hash) {
        showRoute(parseHashRoute(hash));
    } else {
        location.hash = hash;
    }
}

function _setActiveNav(view) {
    document.querySelectorAll('.nav-item').forEach(function(el) {
        el.classList.toggle('active', el.getAttribute('data-view') === view);
    });
}

function showRoute(route) {
    currentRoute = route;
    _routeSeq += 1;
    const main = document.getElementById('main-content');
    if (!main) return;
    _setActiveNav(route.view);

    if (route.view === 'debug') {
        if (_settingsEl) _settingsEl.style.display = 'none';
        if (!_debugEl) {
            _debugEl = document.createElement('div');
            _debugEl.id = 'view-debug';
            _debugEl.className = 'debug-view';
            main.appendChild(_debugEl);
            renderDebugViewInto(_debugEl);
        }
        _debugEl.style.display = '';
        return;
    }

    if (_debugEl) _debugEl.style.display = 'none';
    if (!_settingsEl) {
        _settingsEl = document.createElement('div');
        _settingsEl.id = 'view-settings';
        _settingsEl.className = 'settings-view';
        main.appendChild(_settingsEl);
    }
    _settingsEl.style.display = '';
    renderSettingsRoute(route.page, _settingsEl);
}

function renderSettingsRoute(page, container) {
    const seq = _routeSeq;
    container.innerHTML = '<div class="settings-loading">' + esc(t('settings.loading')) + '</div>';
    const render = SETTINGS_RENDERERS[page] || SETTINGS_RENDERERS.home;
    Promise.resolve(render(container, seq)).catch(function(err) {
        if (seq !== _routeSeq) return;
        container.innerHTML = '<div class="settings-page"><p>' + esc(t('settings.load_failed')) + ': ' + esc(err && err.message) + '</p></div>';
    });
}

async function loadBranding() {
    try {
        const data = await (await fetch('/api/agentbase/branding', { cache: 'no-store' })).json();
        _branding = data || _branding;
        document.title = data.title === 'AgentBase' ? 'AgentBase' : (data.title + ' · AgentBase');
        document.getElementById('brand-logo').textContent = data.title || 'AgentBase';
        _branding.workspaces = data.workspaces || _branding.workspaces;
    } catch (_) { /* 品牌失败不阻断 */ }
}

async function loadWorkspaces() {
    const prev = currentCompanyId;
    workspaces = await api('GET', '/api/agentbase/workspaces') || [];
    const sel = document.getElementById('workspace-select');
    if (sel) {
        sel.innerHTML = workspaces.map(function(w) {
            return '<option value="' + w.id + '"' + (w.id === prev ? ' selected' : '') + '>' + esc(w.name) + '</option>';
        }).join('');
    }
    _applyWorkspaceVisibility();
}

function _workspaceTerm() {
    const ws = (_branding && _branding.workspaces) || {};
    if (currentLang === 'en' && ws.term_en) return ws.term_en;
    return ws.term || '工作区';
}

function _applyWorkspaceVisibility() {
    const wrap = document.getElementById('workspace-select-wrap');
    if (!wrap) return;
    const mode = (_branding.workspaces && _branding.workspaces.mode) || 'single';
    // 单工作区：隐藏选择器；多工作区或没有实例（兜底创建）时显示
    wrap.style.display = (mode === 'multi' || workspaces.length !== 1) ? '' : 'none';
}

async function onWorkspaceChange(id) {
    const cid = Number(id);
    if (!cid) return;
    _abortChatStream();
    const resp = await api('POST', '/api/agentbase/workspaces/' + cid + '/switch', {});
    if (resp) {
        currentCompanyId = cid;
        saveState();
        if (_debugEl) {
            _debugEl.innerHTML = '';
            renderDebugViewInto(_debugEl);
        }
    }
}

function saveState() {
    try {
        if (currentCompanyId) sessionStorage.setItem('agentbase_cid', String(currentCompanyId));
        else sessionStorage.removeItem('agentbase_cid');
    } catch (_) {}
}

function loadSavedCid() {
    try {
        const raw = sessionStorage.getItem('agentbase_cid');
        return raw ? Number(raw) : null;
    } catch (_) { return null; }
}

// ═════════════════════ 工作区实例管理 ═════════════════════
function showWorkspaceModal() {
    const title = _workspaceTerm();
    document.getElementById('workspace-modal-title').textContent = title + ' 设置';
    document.getElementById('workspace-create-title').textContent = '新建' + title;
    document.getElementById('workspace-create-btn').textContent = '创建' + title;
    loadWorkspaceListUI();
    showModal('workspace-modal');
}

function loadWorkspaceListUI() {
    const box = document.getElementById('workspace-list-ui');
    if (!box) return;
    if (!workspaces.length) {
        box.innerHTML = '<p style="color:var(--text-muted);font-size:13px;">' + esc(t('workspaces.no_instances')) + '</p>';
        return;
    }
    box.innerHTML = workspaces.map(function(w) {
        return '<div style="display:flex;align-items:center;gap:8px;padding:8px 0;border-bottom:1px solid var(--border-light);">'
            + '<div style="flex:1;"><div style="font-weight:600;font-size:13px;">' + esc(w.name) + '</div>'
            + '<div style="font-size:11px;color:var(--text-muted);">' + esc(w.slug) + '</div></div>'
            + '<button class="btn btn-xs" onclick="switchWorkspaceFromModal(' + w.id + ')">' + esc(t('workspaces.switch')) + '</button>'
            + '<button class="btn btn-danger btn-xs" onclick="deleteWorkspace(' + w.id + ')">' + esc(t('workspaces.delete')) + '</button>'
            + '</div>';
    }).join('');
}

async function switchWorkspaceFromModal(id) {
    await onWorkspaceChange(id);
    hideModal('workspace-modal');
    renderSettingsRoute('workspaces', _settingsEl);
}

function autoSlug() {
    const name = (document.getElementById('co-name') || {}).value || '';
    const slugEl = document.getElementById('co-slug');
    if (!slugEl) return;
    if (!name.trim()) { slugEl.value = ''; return; }
    slugEl.value = name.toLowerCase().replace(/[^a-z0-9\s-]/g, '')
        .replace(/[\s_]+/g, '-').replace(/--+/g, '-').replace(/^-|-$/g, '') || '';
}

async function createWorkspace() {
    const name = ((document.getElementById('co-name') || {}).value || '').trim();
    if (!name) { toast(t('workspaces.term') + ' *'); return; }
    const body = { name: name };
    const slug = ((document.getElementById('co-slug') || {}).value || '').trim();
    if (slug) body.slug = slug;
    const resp = await api('POST', '/api/agentbase/workspaces', body);
    if (resp && resp.id) {
        toast(t('settings.saved'));
        document.getElementById('co-name').value = '';
        document.getElementById('co-slug').value = '';
        await loadWorkspaces();
        currentCompanyId = resp.id;
        saveState();
        hideModal('workspace-modal');
        if (_settingsEl) renderSettingsRoute(currentRoute.page, _settingsEl);
    }
}

async function deleteWorkspace(id) {
    if (!confirm(t('workspaces.delete') + '?')) return;
    // 后端要求二次确认头，api() 不支持自定义头，直接 fetch
    let resp = null;
    try {
        const r = await fetch('/api/agentbase/workspaces/' + id, {
            method: 'DELETE',
            headers: {
                'X-Hermes-Session-Token': TOKEN,
                'X-Workspace-ID': String(currentCompanyId || id),
                'X-Confirm-Delete': 'yes',
            },
        });
        resp = r.ok ? await r.json() : null;
        if (!r.ok) toast('HTTP ' + r.status);
    } catch (err) {
        toast(err.message || String(err));
    }
    if (resp) {
        if (currentCompanyId === id) currentCompanyId = null;
        await loadWorkspaces();
        if (!currentCompanyId && workspaces.length === 1) {
            currentCompanyId = workspaces[0].id;
            saveState();
        }
        loadWorkspaceListUI();
        if (_settingsEl) renderSettingsRoute(currentRoute.page, _settingsEl);
    }
}

// ═════════════════════ 设置页 ═════════════════════
const SETTINGS_GROUPS = [
    { page: 'models', icon: '🧠', title: 'settings.group.models', desc: 'settings.group.models_desc' },
    { page: 'agent-behavior', icon: '🎛️', title: 'settings.group.agent_behavior', desc: 'settings.group.agent_behavior_desc' },
    { page: 'workspaces', icon: '🗂️', title: 'settings.group.workspaces', desc: 'settings.group.workspaces_desc' },
    { page: 'agent', icon: '🤖', title: 'settings.group.agent', desc: 'settings.group.agent_desc' },
    { page: 'business', icon: '🧭', title: 'settings.group.business', desc: 'settings.group.business_desc' },
    { page: 'skills', icon: '🧩', title: 'settings.group.skills', desc: 'settings.group.skills_desc' },
    { page: 'files', icon: '📁', title: 'settings.group.files', desc: 'settings.group.files_desc' },
    { page: 'system', icon: '🛠️', title: 'settings.group.system', desc: 'settings.group.system_desc' },
    { page: 'developer', icon: '🧪', title: 'settings.group.developer', desc: 'settings.group.developer_desc' },
];

function settingsShell(pageTitle, bodyHtml) {
    return '<div class="settings-page">'
        + '<div class="settings-back"><a onclick="navigateTo(\'#/settings\')">' + esc(t('settings.back')) + '</a></div>'
        + '<h2 class="settings-page-title">' + esc(pageTitle) + '</h2>'
        + bodyHtml + '</div>';
}

async function renderSettingsHome(container, seq) {
    const results = await Promise.all([
        api('GET', '/api/agentbase/settings'),
        api('GET', '/api/agentbase/business/config'),
        api('GET', '/api/agentbase/skill-packs'),
        api('GET', '/api/agentbase/system/service-status'),
    ]);
    if (seq !== _routeSeq) return;
    const [settings, business, packs, service] = results;
    const meta = {
        models: settings ? (settings.active && (settings.active.provider || '—') + ' / ' + (settings.active.model || '—')) : '—',
        'agent-behavior': settings && settings.moa ? (settings.moa.enabled ? t('behavior.enabled') : t('behavior.disabled')) : '—',
        workspaces: business && business.config ? (business.config.workspaces.term + ' · ' + business.config.workspaces.mode) : '—',
        agent: currentCompanyId ? ('#' + currentCompanyId) : '—',
        business: business && business.config ? (business.config.business_name + ' · ' + business.config.usage_direction) : '—',
        skills: packs ? (packs.active || t('skills.no_packs')) : '—',
        files: business && business.config ? (business.config.work_dirs || []).map(function(d) { return d.name; }).join(', ') : '—',
        system: service ? (service.running ? t('system.running') : '—') : '—',
        developer: 'API',
    };
    container.innerHTML = '<div class="settings-page">'
        + '<h2 class="settings-page-title">' + esc(t('settings.title')) + '</h2>'
        + '<div class="settings-home">'
        + SETTINGS_GROUPS.map(function(g) {
            return '<div class="settings-item" onclick="navigateTo(\'#/settings/' + g.page + '\')">'
                + '<div class="settings-item-icon">' + g.icon + '</div>'
                + '<div class="settings-item-text"><div class="settings-item-title">' + esc(t(g.title)) + '</div>'
                + '<div class="settings-item-desc">' + esc(t(g.desc)) + '</div></div>'
                + '<div class="settings-item-meta">' + esc(meta[g.page] || '') + '</div>'
                + '<div class="settings-item-chevron">›</div></div>';
        }).join('')
        + '</div></div>';
}

// ── 模型与 API Key ──
async function renderSettingsModels(container, seq) {
    const data = await api('GET', '/api/agentbase/settings');
    if (seq !== _routeSeq) return;
    if (!data) { container.innerHTML = settingsShell(t('settings.group.models'), '<p>' + esc(t('settings.load_failed')) + '</p>'); return; }
    _settingsCache = data;
    const providers = (data.providers || []).filter(function(p) { return (p.key_env_vars || []).length; });
    const rows = providers.map(function(p) {
        const envInputs = (p.key_env_vars || []).map(function(env) {
            return '<div class="settings-field-row"><input type="password" id="key-' + esc(p.id) + '-' + esc(env) + '" placeholder="' + esc(env) + '">'
                + '<button class="btn" onclick="saveProviderKey(\'' + escJs(p.id) + '\',\'' + escJs(env) + '\')">' + esc(t('settings.save')) + '</button></div>';
        }).join('');
        return '<details class="settings-section"><summary><span>' + esc(p.name || p.id) + '</span>'
            + '<span class="pill ' + (p.has_key ? 'pill-ok' : 'pill-muted') + '">' + esc(p.has_key ? t('models.configured') : t('models.not_configured')) + '</span></summary>'
            + envInputs + '</details>';
    }).join('') || '<p>' + esc(t('settings.load_failed')) + '</p>';

    const modelOptions = (data.providers || []).map(function(p) {
        return '<option value="' + esc(p.id) + '"' + (p.id === (data.active || {}).provider ? ' selected' : '') + '>' + esc(p.name || p.id) + '</option>';
    }).join('');

    container.innerHTML = settingsShell(t('settings.group.models'),
        '<div class="settings-section"><h3>' + esc(t('models.providers')) + '</h3>' + rows + '</div>'
        + '<div class="settings-section"><h3>' + esc(t('models.default_model')) + '</h3>'
        + '<div class="settings-field-row"><select id="default-provider">' + modelOptions + '</select>'
        + '<input id="default-model" value="' + esc((data.active || {}).model || '') + '" placeholder="deepseek-chat">'
        + '<button class="btn btn-primary" onclick="saveDefaultModel()">' + esc(t('settings.save')) + '</button></div>'
        + '<p class="settings-hint">' + esc(t('models.restart_hint')) + '</p></div>');
}

async function saveProviderKey(providerId, envVar) {
    const el = document.getElementById('key-' + providerId + '-' + envVar);
    const value = ((el && el.value) || '').trim();
    if (!value) return;
    const retry = await api('POST', '/api/agentbase/settings/keys', { keys: { [envVar]: value } });
    if (retry) {
        toast(t('settings.saved'));
        el.value = '';
        if (_settingsEl) renderSettingsRoute('models', _settingsEl);
    }
}

async function saveDefaultModel() {
    const provider = (document.getElementById('default-provider') || {}).value || '';
    const model = ((document.getElementById('default-model') || {}).value || '').trim();
    if (!provider || !model) { toast(t('settings.save') + ' *'); return; }
    const resp = await api('POST', '/api/agentbase/settings/model', { provider: provider, model: model });
    if (resp) toast(t('settings.saved') + ' · ' + t('models.restart_hint'));
}

// ── Agent 行为 ──
async function renderSettingsAgentBehavior(container, seq) {
    const data = await api('GET', '/api/agentbase/settings');
    if (seq !== _routeSeq) return;
    if (!data) { container.innerHTML = settingsShell(t('settings.group.agent_behavior'), '<p>' + esc(t('settings.load_failed')) + '</p>'); return; }
    const behavior = data.agent_behavior || {};
    const deny = (behavior.approvals_deny || []);
    container.innerHTML = settingsShell(t('settings.group.agent_behavior'),
        '<div class="settings-section"><h3>' + esc(t('behavior.yolo')) + '</h3>'
        + '<span class="pill ' + (behavior.yolo ? 'pill-ok' : 'pill-muted') + '">' + esc(behavior.yolo ? t('behavior.enabled') : t('behavior.disabled')) + '</span></div>'
        + '<div class="settings-section"><h3>' + esc(t('behavior.approvals')) + '</h3>'
        + (deny.length ? '<pre class="settings-pre">' + esc(deny.join('\n')) + '</pre>' : '<p class="settings-hint">' + esc(t('behavior.none')) + '</p>') + '</div>'
        + '<div class="settings-section"><h3>' + esc(t('behavior.moa')) + '</h3>'
        + '<p class="settings-hint">' + esc(t('models.restart_hint')) + '</p>'
        + '<label class="settings-checkbox"><input type="checkbox" id="moa-toggle" ' + (data.moa && data.moa.enabled ? 'checked' : '')
        + (data.moa_available ? '' : ' disabled') + ' onchange="setMoa(this.checked)"> ' + esc(t('behavior.enabled')) + '</label>'
        + (data.moa && data.moa.presets && data.moa.presets.length ? '<p class="settings-hint">' + esc(data.moa.presets.join(', ')) + '</p>' : '')
        + '</div>');
}

async function setMoa(enabled) {
    const resp = await api('POST', '/api/agentbase/settings/moa', { enabled: enabled });
    if (resp) toast(t('settings.saved') + ' · ' + t('models.restart_hint'));
    if (_settingsEl) renderSettingsRoute('agent-behavior', _settingsEl);
}

// ── 工作区语义与实例 ──
async function renderSettingsWorkspaces(container, seq) {
    const [business, list] = await Promise.all([
        api('GET', '/api/agentbase/business/config'),
        api('GET', '/api/agentbase/workspaces'),
    ]);
    if (seq !== _routeSeq) return;
    if (!business) { container.innerHTML = settingsShell(t('settings.group.workspaces'), '<p>' + esc(t('settings.load_failed')) + '</p>'); return; }
    const ws = (business.config && business.config.workspaces) || {};
    const fields = ws.fields || [];
    const fieldRows = fields.map(function(f, i) { return workspaceFieldRow(f, i); }).join('');
    const instances = (list || []).map(function(w) {
        return '<div class="settings-list-row"><span>' + esc(w.name) + ' <span class="pill pill-muted">' + esc(w.slug) + '</span></span>'
            + '<span><button class="btn btn-xs" onclick="switchWorkspaceFromModal(' + w.id + ')">' + esc(t('workspaces.switch')) + '</button> '
            + '<button class="btn btn-danger btn-xs" onclick="deleteWorkspace(' + w.id + ')">' + esc(t('workspaces.delete')) + '</button></span></div>';
    }).join('') || '<p class="settings-hint">' + esc(t('workspaces.no_instances')) + '</p>';

    container.innerHTML = settingsShell(t('settings.group.workspaces'),
        '<div class="settings-section"><div class="settings-form-grid">'
        + '<label>' + esc(t('workspaces.term')) + '<input id="ws-term" value="' + esc(ws.term || '') + '"></label>'
        + '<label>' + esc(t('workspaces.term_en')) + '<input id="ws-term-en" value="' + esc(ws.term_en || '') + '"></label>'
        + '<label>' + esc(t('workspaces.mode')) + '<select id="ws-mode"><option value="single"' + (ws.mode === 'single' ? ' selected' : '') + '>' + esc(t('workspaces.mode_single')) + '</option>'
        + '<option value="multi"' + (ws.mode === 'multi' ? ' selected' : '') + '>' + esc(t('workspaces.mode_multi')) + '</option></select></label>'
        + '<label class="settings-checkbox"><input type="checkbox" id="ws-create-default" ' + (ws.create_default ? 'checked' : '') + '> ' + esc(t('workspaces.create_default')) + '</label>'
        + '</div></div>'
        + '<div class="settings-section"><h3>' + esc(t('workspaces.fields')) + '</h3><div id="ws-fields">' + fieldRows + '</div>'
        + '<button class="btn" onclick="addWorkspaceField()">+ ' + esc(t('workspaces.add_field')) + '</button></div>'
        + '<div class="settings-actions"><button class="btn btn-primary" onclick="saveWorkspacesConfig()">' + esc(t('settings.save')) + '</button></div>'
        + '<div class="settings-section"><h3>' + esc(t('workspaces.instances')) + '</h3>' + instances
        + '<button class="btn" onclick="showWorkspaceModal()">+ ' + esc(t('workspaces.new')) + '</button></div>');
}

function workspaceFieldRow(field, index) {
    return '<div class="settings-field-row" data-ws-field="' + index + '">'
        + '<input class="ws-field-key" value="' + esc((field && field.key) || '') + '" placeholder="key">'
        + '<input class="ws-field-label" value="' + esc((field && field.label) || '') + '" placeholder="label">'
        + '<button class="btn btn-danger btn-xs" onclick="this.parentNode.remove()">×</button></div>';
}

function addWorkspaceField() {
    const box = document.getElementById('ws-fields');
    if (!box) return;
    const div = document.createElement('div');
    div.className = 'settings-field-row';
    div.innerHTML = '<input class="ws-field-key" placeholder="key"><input class="ws-field-label" placeholder="label">'
        + '<button class="btn btn-danger btn-xs" onclick="this.parentNode.remove()">×</button>';
    box.appendChild(div);
}

async function saveWorkspacesConfig() {
    const fields = Array.from(document.querySelectorAll('[data-ws-field], #ws-fields > .settings-field-row')).map(function(row) {
        return {
            key: (row.querySelector('.ws-field-key') || {}).value || '',
            label: (row.querySelector('.ws-field-label') || {}).value || '',
            type: 'text',
        };
    }).filter(function(f) { return f.key.trim(); });
    const payload = {
        workspaces: {
            term: (document.getElementById('ws-term') || {}).value || '工作区',
            term_en: (document.getElementById('ws-term-en') || {}).value || 'Workspace',
            mode: (document.getElementById('ws-mode') || {}).value || 'single',
            create_default: !!(document.getElementById('ws-create-default') || {}).checked,
            fields: fields,
        },
    };
    const resp = await api('PUT', '/api/agentbase/business/config', payload);
    if (resp) {
        toast(t('settings.saved'));
        await loadBranding();
        _applyWorkspaceVisibility();
        if (_settingsEl) renderSettingsRoute('workspaces', _settingsEl);
    }
}

// ── 智能体与提示词 ──
async function renderSettingsAgent(container, seq) {
    if (!currentCompanyId) {
        container.innerHTML = settingsShell(t('settings.group.agent'), '<p>' + esc(t('toast.no_workspace')) + '</p>');
        return;
    }
    const [ws, identity, business] = await Promise.all([
        api('GET', '/api/agentbase/workspaces/' + currentCompanyId),
        api('GET', '/api/agentbase/workspaces/' + currentCompanyId + '/agent-identity'),
        api('GET', '/api/agentbase/business/config'),
    ]);
    if (seq !== _routeSeq) return;
    const promptOverride = (business && business.config && business.config.prompt_overrides && business.config.prompt_overrides.system) || '';
    container.innerHTML = settingsShell(t('settings.group.agent'),
        '<div class="settings-section"><label>' + esc(t('agent.name')) + '<input id="agent-ws-name" value="' + esc((ws && ws.name) || '') + '"></label>'
        + '<button class="btn" onclick="saveWorkspaceName()">' + esc(t('settings.save')) + '</button></div>'
        + '<div class="settings-section"><h3>' + esc(t('agent.identity')) + '</h3>'
        + '<textarea id="agent-identity" rows="12">' + esc((identity && identity.agent_identity_md) || '') + '</textarea>'
        + '<button class="btn btn-primary" onclick="saveWorkspaceIdentity()">' + esc(t('settings.save')) + '</button></div>'
        + '<div class="settings-section"><h3>' + esc(t('agent.system_prompt')) + '</h3>'
        + '<textarea id="agent-system-prompt" rows="8">' + esc(promptOverride) + '</textarea>'
        + '<button class="btn" onclick="saveSystemPromptOverride()">' + esc(t('settings.save')) + '</button>'
        + '<p class="settings-hint">' + esc(t('agent.priority')) + '</p></div>');
}

async function saveWorkspaceName() {
    if (!currentCompanyId) return;
    const name = ((document.getElementById('agent-ws-name') || {}).value || '').trim();
    if (!name) return;
    const resp = await api('PUT', '/api/agentbase/workspaces/' + currentCompanyId, { name: name });
    if (resp) { toast(t('settings.saved')); await loadWorkspaces(); renderSettingsRoute('agent', _settingsEl); }
}

async function saveWorkspaceIdentity() {
    if (!currentCompanyId) return;
    const md = (document.getElementById('agent-identity') || {}).value || '';
    const resp = await api('PUT', '/api/agentbase/workspaces/' + currentCompanyId + '/agent-identity', { agent_identity_md: md });
    if (resp) toast(t('settings.saved'));
}

async function saveSystemPromptOverride() {
    const text = (document.getElementById('agent-system-prompt') || {}).value || '';
    const resp = await api('PUT', '/api/agentbase/business/config', { prompt_overrides: { system: text } });
    if (resp) toast(t('settings.saved'));
}

// ── 业务与方向 ──
async function renderSettingsBusiness(container, seq) {
    const data = await api('GET', '/api/agentbase/business/config');
    if (seq !== _routeSeq) return;
    if (!data) { container.innerHTML = settingsShell(t('settings.group.business'), '<p>' + esc(t('settings.load_failed')) + '</p>'); return; }
    _settingsCache = data;
    const cfg = data.config || {};
    const currentDirection = cfg.usage_direction || 'general';
    const options = (data.directions || []).map(function(d) {
        return '<option value="' + esc(d.id) + '"' + (d.id === currentDirection ? ' selected' : '') + '>' + esc(currentLang === 'en' ? d.label_en : d.label) + '</option>';
    }).join('');
    const fields = (cfg.onboarding_fields || []).map(function(f, i) {
        return '<div class="settings-field-row" data-onboarding-field="' + i + '">'
            + '<input class="ob-key" value="' + esc(f.key) + '" placeholder="key">'
            + '<input class="ob-label" value="' + esc(f.label) + '" placeholder="label">'
            + '<input class="ob-example" value="' + esc(f.example || '') + '" placeholder="example">'
            + '<button class="btn btn-danger btn-xs" onclick="this.parentNode.remove()">×</button></div>';
    }).join('');

    container.innerHTML = settingsShell(t('settings.group.business'),
        '<div class="settings-section"><h3>' + esc(t('business.direction')) + '</h3>'
        + '<select id="business-direction" onchange="renderDirectionRecommendation()">' + options + '</select>'
        + '<p class="settings-hint">' + esc(t('business.direction_hint')) + '</p>'
        + '<div id="direction-recommend" class="settings-recommend"></div></div>'
        + '<div class="settings-section"><div class="settings-form-grid">'
        + '<label>' + esc(t('business.name')) + '<input id="business-name" value="' + esc(cfg.business_name || '') + '"></label>'
        + '<label>' + esc(t('business.tagline')) + '<input id="business-tagline" value="' + esc(cfg.tagline || '') + '"></label>'
        + '<label>' + esc(t('business.brand_title')) + '<input id="brand-title" value="' + esc((cfg.branding || {}).title || '') + '"></label>'
        + '<label>' + esc(t('business.welcome')) + '<input id="brand-welcome" value="' + esc((cfg.branding || {}).welcome || '') + '"></label>'
        + '</div></div>'
        + '<div class="settings-section"><h3>' + esc(t('business.onboarding')) + '</h3><div id="onboarding-fields">' + fields + '</div>'
        + '<button class="btn" onclick="addOnboardingField()">+ ' + esc(t('workspaces.add_field')) + '</button></div>'
        + '<div class="settings-actions"><button class="btn btn-primary" onclick="saveBusinessConfig()">' + esc(t('settings.save')) + '</button></div>');
    renderDirectionRecommendation();
}

function _currentDirectionPreset() {
    const sel = document.getElementById('business-direction');
    const id = sel ? sel.value : 'general';
    const directions = (_settingsCache && _settingsCache.directions) || [];
    return directions.find(function(d) { return d.id === id; }) || null;
}

function renderDirectionRecommendation() {
    const preset = _currentDirectionPreset();
    const box = document.getElementById('direction-recommend');
    if (!box) return;
    if (!preset) { box.innerHTML = ''; return; }
    const fields = (preset.onboarding_fields || []).map(function(f) { return f.label; }).join('、');
    box.innerHTML = '<div class="settings-recommend-head">' + esc(t('business.recommend')) + ': ' + esc(currentLang === 'en' ? preset.label_en : preset.label) + '</div>'
        + '<p>' + esc(currentLang === 'en' ? preset.description_en : preset.description) + '</p>'
        + '<p><strong>' + esc(t('business.name')) + ':</strong> ' + esc(currentLang === 'en' ? preset.default_business_name_en : preset.default_business_name) + '</p>'
        + (fields ? '<p><strong>' + esc(t('business.onboarding')) + ':</strong> ' + esc(fields) + '</p>' : '')
        + '<p><strong>' + esc(t('workspaces.mode')) + ':</strong> ' + esc(preset.workspaces.mode) + '</p>'
        + (preset.recommended_skill_pack ? '<p><strong>' + esc(t('business.recommended_pack')) + ':</strong> ' + esc(preset.recommended_skill_pack)
            + ' — ' + esc(currentLang === 'en' ? preset.recommended_skill_pack_reason_en : preset.recommended_skill_pack_reason) + '</p>' : '')
        + '<button class="btn" onclick="applyDirectionRecommendation()">' + esc(t('business.apply')) + '</button>';
}

function applyDirectionRecommendation() {
    const preset = _currentDirectionPreset();
    if (!preset) return;
    const nameEl = document.getElementById('business-name');
    if (nameEl) nameEl.value = currentLang === 'en' ? preset.default_business_name_en : preset.default_business_name;
    const box = document.getElementById('onboarding-fields');
    if (box && preset.onboarding_fields) {
        box.innerHTML = preset.onboarding_fields.map(function(f, i) {
            return '<div class="settings-field-row" data-onboarding-field="' + i + '">'
                + '<input class="ob-key" value="' + esc(f.key) + '" placeholder="key">'
                + '<input class="ob-label" value="' + esc(currentLang === 'en' ? (f.label_en || f.label) : f.label) + '" placeholder="label">'
                + '<input class="ob-example" value="' + esc(currentLang === 'en' ? (f.example_en || f.example) : f.example) + '" placeholder="example">'
                + '<button class="btn btn-danger btn-xs" onclick="this.parentNode.remove()">×</button></div>';
        }).join('');
    }
    toast(t('settings.saved'));
}

function addOnboardingField() {
    const box = document.getElementById('onboarding-fields');
    if (!box) return;
    const div = document.createElement('div');
    div.className = 'settings-field-row';
    div.innerHTML = '<input class="ob-key" placeholder="key"><input class="ob-label" placeholder="label">'
        + '<input class="ob-example" placeholder="example"><button class="btn btn-danger btn-xs" onclick="this.parentNode.remove()">×</button>';
    box.appendChild(div);
}

async function saveBusinessConfig() {
    const fields = Array.from(document.querySelectorAll('#onboarding-fields > .settings-field-row')).map(function(row) {
        return {
            key: ((row.querySelector('.ob-key') || {}).value || '').trim(),
            label: ((row.querySelector('.ob-label') || {}).value || '').trim(),
            example: ((row.querySelector('.ob-example') || {}).value || '').trim(),
        };
    }).filter(function(f) { return f.key && f.label; });
    if (!fields.length) { toast(t('business.onboarding') + ' *'); return; }
    const payload = {
        business_name: ((document.getElementById('business-name') || {}).value || '').trim(),
        tagline: ((document.getElementById('business-tagline') || {}).value || '').trim(),
        usage_direction: (document.getElementById('business-direction') || {}).value || 'general',
        onboarding_fields: fields,
        branding: {
            title: ((document.getElementById('brand-title') || {}).value || '').trim(),
            welcome: ((document.getElementById('brand-welcome') || {}).value || '').trim(),
        },
    };
    const resp = await api('PUT', '/api/agentbase/business/config', payload);
    if (resp) {
        toast(t('settings.saved'));
        await loadBranding();
        applyStaticCopy();
    }
}

// ── Skill 包与扩展 ──
async function renderSettingsSkills(container, seq) {
    const [packs, settings] = await Promise.all([
        api('GET', '/api/agentbase/skill-packs'),
        api('GET', '/api/agentbase/settings'),
    ]);
    if (seq !== _routeSeq) return;
    const rows = ((packs && packs.packs) || []).map(function(p) {
        const active = packs.active === p.path;
        return '<div class="settings-list-row"><span>' + esc(p.name) + (active ? ' <span class="pill pill-ok">' + esc(t('skills.active')) + '</span>' : '') + '</span>'
            + '<span>' + (active ? '' : '<button class="btn btn-xs" onclick="activatePack(\'' + escJs(p.name) + '\')">' + esc(t('skills.activate')) + '</button> ')
            + '<button class="btn btn-danger btn-xs" onclick="removePack(\'' + escJs(p.name) + '\')">' + esc(t('skills.remove')) + '</button></span></div>';
    }).join('') || '<p class="settings-hint">' + esc(t('skills.no_packs')) + '</p>';
    const ext = (settings && settings.extensions) || {};
    const mcp = (ext.mcp_servers || []).map(function(s) { return s.name + (s.enabled ? '' : ' (off)'); }).join(', ') || t('behavior.none');
    const plugins = ((ext.plugins || {}).enabled || []).join(', ') || t('behavior.none');
    const toolsets = (ext.toolsets || []).join(', ') || t('behavior.none');

    container.innerHTML = settingsShell(t('settings.group.skills'),
        '<div class="settings-section"><h3>' + esc(t('skills.packs')) + '</h3>' + rows
        + '<div class="settings-field-row"><input id="pack-install-path" placeholder="' + esc(t('skills.install_path')) + '">'
        + '<button class="btn" onclick="installPack()">' + esc(t('skills.install')) + '</button></div></div>'
        + '<div class="settings-actions"><button class="btn" onclick="updateSkills(event)">' + esc(t('skills.update')) + '</button></div>'
        + '<div class="settings-section"><h3>' + esc(t('skills.extensions')) + '</h3>'
        + '<p><strong>MCP:</strong> ' + esc(mcp) + '</p><p><strong>Plugins:</strong> ' + esc(plugins) + '</p>'
        + '<p><strong>Toolsets:</strong> ' + esc(toolsets) + '</p></div>');
}

async function installPack() {
    const path = ((document.getElementById('pack-install-path') || {}).value || '').trim();
    if (!path) return;
    const resp = await api('POST', '/api/agentbase/skill-packs/install', { path: path });
    if (resp) { toast(t('settings.saved')); renderSettingsRoute('skills', _settingsEl); }
}

async function activatePack(name) {
    const resp = await api('POST', '/api/agentbase/skill-packs/activate', { name: name });
    if (resp) { toast(t('settings.saved')); renderSettingsRoute('skills', _settingsEl); }
}

async function removePack(name) {
    if (!confirm(t('skills.remove') + ' ' + name + '?')) return;
    const resp = await api('DELETE', '/api/agentbase/skill-packs/' + encodeURIComponent(name), null);
    if (resp) { toast(t('settings.saved')); renderSettingsRoute('skills', _settingsEl); }
}

async function updateSkills(event) {
    const btn = event && (event.currentTarget || event.target);
    if (btn) btn.disabled = true;
    try {
        const resp = await api('POST', '/api/agentbase/skills/update', {});
        if (resp && resp.ok) toast(t('settings.saved'));
    } finally {
        if (btn) btn.disabled = false;
    }
}

// ── 文件与目录 ──
async function renderSettingsFiles(container, seq) {
    const data = await api('GET', '/api/agentbase/business/config');
    if (seq !== _routeSeq) return;
    const cfg = (data && data.config) || {};
    const dirs = (cfg.work_dirs || []).map(function(d, i) {
        return '<div class="settings-field-row" data-work-dir="' + i + '">'
            + '<input class="wd-name" value="' + esc(d.name || '') + '" placeholder="documents">'
            + '<input class="wd-desc" value="' + esc(d.description || '') + '" placeholder="description">'
            + '<button class="btn btn-danger btn-xs" onclick="this.parentNode.remove()">×</button></div>';
    }).join('');
    const dirNames = (cfg.work_dirs || []).map(function(d) { return '<option value="' + esc(d.name) + '">' + esc(d.name) + '</option>'; }).join('');
    container.innerHTML = settingsShell(t('settings.group.files'),
        '<div class="settings-section"><h3>' + esc(t('files.work_dirs')) + '</h3><div id="work-dirs">' + dirs + '</div>'
        + '<button class="btn" onclick="addWorkDir()">+ ' + esc(t('workspaces.add_field')) + '</button></div>'
        + '<div class="settings-actions"><button class="btn btn-primary" onclick="saveWorkDirs()">' + esc(t('settings.save')) + '</button></div>'
        + '<div class="settings-section"><h3>' + esc(t('files.upload')) + '</h3>'
        + '<div class="settings-field-row"><select id="upload-subdir">' + dirNames + '</select>'
        + '<input type="file" id="upload-file">'
        + '<button class="btn btn-primary" onclick="uploadFile()">' + esc(t('files.upload')) + '</button></div>'
        + '<p class="settings-hint">' + esc(t('files.data_root')) + ': ~/.agentbase</p></div>');
}

function addWorkDir() {
    const box = document.getElementById('work-dirs');
    if (!box) return;
    const div = document.createElement('div');
    div.className = 'settings-field-row';
    div.innerHTML = '<input class="wd-name" placeholder="documents"><input class="wd-desc" placeholder="description">'
        + '<button class="btn btn-danger btn-xs" onclick="this.parentNode.remove()">×</button>';
    box.appendChild(div);
}

async function saveWorkDirs() {
    const dirs = Array.from(document.querySelectorAll('#work-dirs > .settings-field-row')).map(function(row) {
        return {
            name: ((row.querySelector('.wd-name') || {}).value || '').trim(),
            description: ((row.querySelector('.wd-desc') || {}).value || '').trim(),
        };
    }).filter(function(d) { return d.name; });
    if (!dirs.length) { toast(t('files.work_dirs') + ' *'); return; }
    const resp = await api('PUT', '/api/agentbase/business/config', { work_dirs: dirs });
    if (resp) { toast(t('settings.saved')); renderSettingsRoute('files', _settingsEl); }
}

async function uploadFile() {
    const input = document.getElementById('upload-file');
    const subdir = (document.getElementById('upload-subdir') || {}).value || '';
    if (!input || !input.files || !input.files.length) { toast(t('files.choose')); return; }
    const body = new FormData();
    body.append('subdir', subdir);
    Array.from(input.files).forEach(function(f) { body.append('files', f); });
    const resp = await api('POST', '/api/agentbase/upload-files', body);
    if (resp) { toast(t('settings.saved')); input.value = ''; }
}

// ── 系统 ──
async function renderSettingsSystem(container, seq) {
    const [service, logs, jobs] = await Promise.all([
        api('GET', '/api/agentbase/system/service-status'),
        api('GET', '/api/agentbase/system/logs'),
        currentCompanyId ? api('GET', '/api/agentbase/cron/jobs') : Promise.resolve([]),
    ]);
    if (seq !== _routeSeq) return;
    const logOptions = ((logs && logs.files) || []).map(function(name) { return '<option value="' + esc(name) + '">' + esc(name) + '</option>'; }).join('');
    const cronRows = (jobs || []).map(function(j) {
        return '<div class="settings-list-row"><span>' + esc(j.name || j.id) + '</span><span class="settings-hint">' + esc(j.schedule || '') + '</span></div>';
    }).join('') || '<p class="settings-hint">' + esc(t('system.no_jobs')) + '</p>';

    container.innerHTML = settingsShell(t('settings.group.system'),
        '<div class="settings-section"><h3>' + esc(t('system.service')) + '</h3>'
        + '<p><span class="pill ' + (service && service.running ? 'pill-ok' : 'pill-muted') + '">' + esc(service && service.running ? t('system.running') : '—') + '</span></p>'
        + '<label class="settings-checkbox"><input type="checkbox" id="autostart-toggle" ' + (service && service.autostart ? 'checked' : '') + ' onchange="setAutostart(this.checked)"> ' + esc(t('system.autostart')) + '</label>'
        + '<div class="settings-actions"><button class="btn" onclick="doSystemUpdate(event)">' + esc(t('system.update')) + '</button>'
        + '<button class="btn" onclick="doSystemRestart(event)">' + esc(t('system.restart')) + '</button>'
        + '<button class="btn" onclick="backupNow()">' + esc(t('system.backup')) + '</button>'
        + '<button class="btn btn-danger" onclick="quitService()">' + esc(t('system.quit')) + '</button></div></div>'
        + '<div class="settings-section"><h3>' + esc(t('system.logs')) + '</h3>'
        + '<div class="settings-field-row"><select id="log-file">' + logOptions + '</select>'
        + '<input id="log-lines" type="number" min="1" max="500" value="200" style="max-width:100px;">'
        + '<button class="btn" onclick="loadLogs()">' + esc(t('system.refresh')) + '</button></div>'
        + '<pre id="log-output" class="settings-pre">' + esc(t('system.log_select')) + '</pre></div>'
        + '<div class="settings-section"><h3>' + esc(t('system.cron')) + '</h3>' + cronRows + '</div>');
}

async function setAutostart(enabled) {
    const resp = await api('POST', '/api/agentbase/system/autostart', { enabled: enabled });
    if (!resp || !resp.ok) {
        toast((resp && resp.error) || t('toast.save_failed'));
        const el = document.getElementById('autostart-toggle');
        if (el) el.checked = !enabled;
        return;
    }
    toast(t('settings.saved'));
}

async function quitService() {
    if (!confirm(t('system.confirm_quit'))) return;
    const resp = await api('POST', '/api/agentbase/system/quit', {});
    if (resp) toast(t('system.confirm_quit'));
}

async function backupNow() {
    const resp = await api('POST', '/api/agentbase/system/backup', {});
    if (resp && resp.ok) toast((resp.file || t('settings.saved')));
}

async function loadLogs() {
    const name = ((document.getElementById('log-file') || {}).value || '');
    const lines = ((document.getElementById('log-lines') || {}).value || '200');
    const out = document.getElementById('log-output');
    if (!name || !out) return;
    const resp = await api('GET', '/api/agentbase/system/logs?name=' + encodeURIComponent(name) + '&lines=' + encodeURIComponent(lines));
    if (!resp) return;
    out.textContent = (resp.lines || []).join('\n') + (resp.truncated ? '\n… (truncated)' : '');
}

// ── 开发者：API 控制台 ──
async function renderSettingsDeveloper(container, seq) {
    const [meta, docs] = await Promise.all([
        api('GET', '/api/agentbase/meta/endpoints'),
        api('GET', '/api/agentbase/meta/api-docs'),
    ]);
    if (seq !== _routeSeq) return;
    const endpoints = (meta && meta.endpoints) || [];
    container.innerHTML = settingsShell(t('settings.group.developer'),
        '<div class="settings-section"><h3>' + esc(t('dev.token')) + '</h3>'
        + '<div class="settings-field-row"><input id="dev-token" value="' + esc(TOKEN) + '" readonly>'
        + '<button class="btn" onclick="copyDevToken()">' + esc(t('dev.copy')) + '</button></div>'
        + '<p class="settings-hint">' + esc(t('dev.token_note')) + '</p>'
        + '<p><a href="/docs" target="_blank" rel="noopener">' + esc(t('dev.swagger')) + '</a> · '
        + '<a href="/openapi.json" target="_blank" rel="noopener">' + esc(t('dev.openapi')) + '</a></p></div>'
        + '<div class="settings-section"><h3>' + esc(t('dev.console')) + '</h3>'
        + '<div class="settings-field-row"><input id="dev-search" placeholder="' + esc(t('dev.search')) + '" oninput="filterEndpoints()"></div>'
        + '<div id="dev-endpoint-list" class="settings-endpoints">' + endpoints.map(function(e, i) {
            return '<div class="settings-endpoint" data-path="' + esc(e.path) + '" onclick="selectEndpoint(' + i + ')">'
                + '<span class="pill pill-muted">' + esc(e.method) + '</span> <code>' + esc(e.path) + '</code>'
                + '<span class="settings-hint">' + esc(e.summary || '') + '</span></div>';
        }).join('') + '</div>'
        + '<div id="dev-console" class="settings-console"></div></div>'
        + '<div class="settings-section"><h3>' + esc(t('dev.docs')) + '</h3>'
        + '<div id="api-docs" class="api-doc">' + (docs ? DOMPurify.sanitize(marked.parse(docs.content || '')) : '<p>' + esc(t('settings.load_failed')) + '</p>') + '</div></div>');
    window._devEndpoints = endpoints;
}

function filterEndpoints() {
    const q = ((document.getElementById('dev-search') || {}).value || '').toLowerCase();
    document.querySelectorAll('#dev-endpoint-list .settings-endpoint').forEach(function(el) {
        el.style.display = el.textContent.toLowerCase().indexOf(q) >= 0 ? '' : 'none';
    });
}

function selectEndpoint(index) {
    const endpoints = window._devEndpoints || [];
    const e = endpoints[index];
    const box = document.getElementById('dev-console');
    if (!e || !box) return;
    const pathParams = (e.path_params || []).map(function(p) {
        return '<label>' + esc(p) + '<input id="console-param-' + esc(p) + '" placeholder="{ ' + esc(p) + ' }"></label>';
    }).join('');
    box.innerHTML = '<h4>' + esc(e.method) + ' ' + esc(e.path) + '</h4>'
        + '<div class="settings-form-grid">' + pathParams
        + '<label>' + esc(t('dev.workspace')) + '<input id="console-workspace" value="' + esc(currentCompanyId || '') + '"></label></div>'
        + (e.has_body ? '<label>' + esc(t('dev.body')) + '<textarea id="console-body" rows="6">{\n  \n}</textarea></label>' : '')
        + '<button class="btn btn-primary" onclick="sendConsoleRequest(' + index + ')">' + esc(t('dev.send')) + '</button>'
        + '<pre id="console-output" class="settings-pre"></pre>';
}

async function sendConsoleRequest(index) {
    const endpoints = window._devEndpoints || [];
    const e = endpoints[index];
    if (!e) return;
    let path = e.path;
    (e.path_params || []).forEach(function(p) {
        const el = document.getElementById('console-param-' + p);
        path = path.replace('{' + p + '}', encodeURIComponent((el && el.value) || ''));
    });
    const bodyEl = document.getElementById('console-body');
    let body = null;
    if (bodyEl && bodyEl.value.trim()) {
        try { body = JSON.parse(bodyEl.value); } catch (err) {
            document.getElementById('console-output').textContent = 'JSON 解析失败: ' + err.message;
            return;
        }
    }
    const workspaceEl = document.getElementById('console-workspace');
    const ws = workspaceEl && workspaceEl.value ? workspaceEl.value : currentCompanyId;
    const headers = { 'X-Hermes-Session-Token': TOKEN };
    if (ws && e.requires_workspace) headers['X-Workspace-ID'] = String(ws);
    const opts = { method: e.method, headers: headers };
    if (body) {
        headers['Content-Type'] = 'application/json';
        opts.body = JSON.stringify(body);
    }
    const out = document.getElementById('console-output');
    try {
        const resp = await fetch(path, opts);
        const text = await resp.text();
        let pretty = text;
        try { pretty = JSON.stringify(JSON.parse(text), null, 2); } catch (_) {}
        out.textContent = 'HTTP ' + resp.status + '\n\n' + pretty;
    } catch (err) {
        out.textContent = '请求失败: ' + err.message;
    }
}

function copyDevToken() {
    const el = document.getElementById('dev-token');
    if (!el) return;
    navigator.clipboard.writeText(el.value).then(function() { toast(t('dev.copied')); });
}

// ═════════════════════ 调试页 ═════════════════════
function renderDebugViewInto(container) {
    container.innerHTML = '<div class="debug-banner">' + esc(t('debug.banner')) + '</div>'
        + '<div class="debug-toolbar"><strong>' + esc(t('debug.title')) + '</strong>'
        + '<span class="settings-hint">' + esc(t('debug.probe')) + ': </span>'
        + '<button class="btn btn-xs" onclick="debugProbe(\'/api/status\')">/api/status</button>'
        + '<button class="btn btn-xs" onclick="debugProbe(\'/api/agentbase/workspaces\')">/workspaces</button>'
        + '<button class="btn btn-xs" onclick="clearDebug()">' + esc(t('debug.clear')) + '</button></div>'
        + '<div id="debug-messages" class="debug-messages"><p class="settings-hint">' + esc(t('debug.empty')) + '</p></div>'
        + '<div class="debug-input-row"><textarea id="debug-input" rows="3" placeholder="' + esc(t('debug.placeholder')) + '"></textarea>'
        + '<button class="btn btn-primary" id="debug-send" onclick="sendDebugMsg()">' + esc(t('debug.send')) + '</button>'
        + '<button class="btn" id="debug-stop" onclick="stopDebugStream()" disabled>' + esc(t('debug.stop')) + '</button></div>'
        + '<div class="debug-raw"><details><summary>' + esc(t('debug.raw')) + '</summary><pre id="debug-raw-log"></pre></details></div>';
}

function _debugMessages() { return document.getElementById('debug-messages'); }

function clearDebug() {
    const box = _debugMessages();
    if (box) box.innerHTML = '<p class="settings-hint">' + esc(t('debug.empty')) + '</p>';
    const raw = document.getElementById('debug-raw-log');
    if (raw) raw.textContent = '';
}

function _appendDebug(role, text) {
    const box = _debugMessages();
    if (!box) return;
    if (box.querySelector('.settings-hint')) box.innerHTML = '';
    const div = document.createElement('div');
    div.className = 'debug-msg debug-' + role;
    div.textContent = text;
    box.appendChild(div);
    box.scrollTop = box.scrollHeight;
}

function _appendDebugRaw(type, data) {
    const raw = document.getElementById('debug-raw-log');
    if (!raw) return;
    raw.textContent += 'event: ' + type + '\n' + JSON.stringify(data) + '\n\n';
    raw.scrollTop = raw.scrollHeight;
}

async function debugProbe(path) {
    try {
        const resp = await fetch(path, { headers: { 'X-Hermes-Session-Token': TOKEN } });
        const text = await resp.text();
        _appendDebug('probe', 'GET ' + path + ' → HTTP ' + resp.status + '\n' + text.slice(0, 2000));
    } catch (err) {
        _appendDebug('error', 'GET ' + path + ' → ' + err.message);
    }
}

function stopDebugStream() {
    _abortChatStream();
}

async function sendDebugMsg() {
    const input = document.getElementById('debug-input');
    const sendBtn = document.getElementById('debug-send');
    const stopBtn = document.getElementById('debug-stop');
    const query = ((input && input.value) || '').trim();
    if (!query) return;
    if (!currentCompanyId) { toast(t('toast.no_workspace')); return; }
    input.value = '';
    if (sendBtn) sendBtn.disabled = true;
    if (stopBtn) stopBtn.disabled = false;
    _appendDebug('user', query);

    const cid = currentCompanyId;
    const ctl = _beginChatStream(cid);
    let sawResponse = false;
    let sawDone = false;
    let assistantText = '';
    let assistantEl = null;

    try {
        const resp = await fetch('/api/agentbase/chat/stream', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Hermes-Session-Token': TOKEN,
                'X-Workspace-ID': String(cid),
            },
            body: JSON.stringify({ query: query, language: currentLang }),
            signal: ctl.signal,
        });
        if (!resp.ok) {
            const text = await resp.text().catch(function() { return ''; });
            _appendDebug('error', 'HTTP ' + resp.status + ' ' + text.slice(0, 500));
            return;
        }
        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let eventType = null;
        while (true) {
            const read = await reader.read();
            if (read.done) break;
            buffer += decoder.decode(read.value, { stream: true });
            const frames = buffer.split('\n\n');
            buffer = frames.pop();
            for (const frame of frames) {
                if (!frame.trim() || frame.startsWith(':')) continue;
                let dataLine = null;
                frame.split('\n').forEach(function(line) {
                    if (line.startsWith('event: ')) eventType = line.slice(7);
                    else if (line.startsWith('data: ')) dataLine = line.slice(6);
                });
                if (!eventType || dataLine === null) continue;
                let data = {};
                try { data = JSON.parse(dataLine); } catch (_) { data = { raw: dataLine }; }
                _appendDebugRaw(eventType, data);
                if (!_chatStreamBelongsTo(cid)) return;
                if (eventType === 'response') {
                    sawResponse = true;
                    assistantText = data.text || '';
                    if (!assistantEl) assistantEl = _appendDebug('assistant', '');
                    const last = _debugMessages().lastElementChild;
                    if (last) last.textContent = assistantText;
                } else if (eventType === 'tool_start') {
                    _appendDebug('tool', '▶ ' + (data.name || 'tool'));
                } else if (eventType === 'tool_complete') {
                    _appendDebug('tool', '✓ ' + (data.name || 'tool'));
                } else if (eventType === 'thinking') {
                    _appendDebug('thinking', data.message || 'thinking…');
                } else if (eventType === 'error') {
                    _appendDebug('error', data.message || 'error');
                } else if (eventType === 'done') {
                    sawDone = true;
                }
            }
            if (sawDone) break;
        }
        const outcome = _sseStreamOutcome(sawResponse, sawDone);
        if (outcome.kind !== 'response') _appendDebug('error', outcome.message);
    } catch (err) {
        if (err.name === 'AbortError') _appendDebug('error', t('debug.stop'));
        else _appendDebug('error', err.message || String(err));
    } finally {
        _endChatStream(ctl);
        if (sendBtn) sendBtn.disabled = false;
        if (stopBtn) stopBtn.disabled = true;
    }
}

// ═════════════════════ 许可证 / 更新 / 重启 ═════════════════════
async function loadLicenseStatus() {
    try {
        const r = await fetch('/api/agentbase/license/status');
        const data = await r.json();
        const bar = document.getElementById('license-bar');
        if (!bar) return;
        if (data.status === 'expired' || data.status === 'tampered') {
            bar.style.display = 'block';
            bar.innerHTML = '⚠️ ' + esc(t('license.expired')) + ' · <a href="#" onclick="activateLicense();return false;">' + esc(t('license.activate')) + '</a>';
        } else if (data.status === 'trial') {
            bar.style.display = 'block';
            bar.textContent = '⏳ ' + t('license.trial') + ' · ' + data.days_remaining + 'd';
        } else {
            bar.style.display = 'none';
        }
    } catch (_) {}
}

async function activateLicense() {
    const code = prompt(t('license.enter_code'));
    if (!code) return;
    const resp = await api('POST', '/api/agentbase/license/activate', { code: code });
    if (resp && resp.ok) { toast(resp.message || t('license.activated')); loadLicenseStatus(); }
    else toast((resp && resp.error) || t('license.activate_fail'));
}

function showLicenseExpired(msg) {
    toast(msg || t('license.expired'));
}

async function _confirmUpdate() {
    let latest = '';
    try {
        const st = await (await fetch('/api/status?_=' + Date.now(), { cache: 'no-store' })).json();
        latest = st.latest_version || '';
    } catch (_) {}
    let notes = '修复与稳定性改进';
    try {
        const c = await api('GET', '/api/agentbase/system/changelog?latest=' + encodeURIComponent(latest));
        if (c && c.notes) notes = c.notes;
    } catch (_) {}
    return confirm(t('update.confirm') + '\n\n' + notes + '\n\n' + t('update.backup_note'));
}

async function _waitForRestartAndReload(prevStartedAt) {
    toast(t('update.restarting'));
    for (let i = 0; i < 120; i++) {
        await new Promise(function(res) { setTimeout(res, 1000); });
        try {
            const data = await (await fetch('/api/status?_=' + Date.now(), { cache: 'no-store' })).json();
            if (data && data.status === 'ok' && data.started_at !== prevStartedAt) {
                location.reload();
                return;
            }
        } catch (_) {}
    }
    location.reload();
}

async function _currentStartedAt() {
    try {
        const data = await (await fetch('/api/status?_=' + Date.now(), { cache: 'no-store' })).json();
        return data.started_at;
    } catch (_) { return null; }
}

async function doSystemUpdate(event) {
    if (!(await _confirmUpdate())) return;
    const btn = event && (event.currentTarget || event.target);
    if (btn) btn.disabled = true;
    const prev = await _currentStartedAt();
    const resp = await api('POST', '/api/agentbase/system/update', {});
    if (!resp || !resp.ok) {
        toast((resp && resp.error) || t('update.failed'));
        if (btn) btn.disabled = false;
        return;
    }
    await _waitForRestartAndReload(prev);
}

async function doSystemRestart(event) {
    if (!confirm(t('system.restart') + '?')) return;
    const btn = event && (event.currentTarget || event.target);
    if (btn) btn.disabled = true;
    const prev = await _currentStartedAt();
    const resp = await api('POST', '/api/agentbase/system/restart', {});
    if (!resp) { if (btn) btn.disabled = false; return; }
    await _waitForRestartAndReload(prev);
}

// ═════════════════════ 设置页渲染器表 ═════════════════════
const SETTINGS_RENDERERS = {
    home: renderSettingsHome,
    models: renderSettingsModels,
    'agent-behavior': renderSettingsAgentBehavior,
    workspaces: renderSettingsWorkspaces,
    agent: renderSettingsAgent,
    business: renderSettingsBusiness,
    skills: renderSettingsSkills,
    files: renderSettingsFiles,
    system: renderSettingsSystem,
    developer: renderSettingsDeveloper,
};

// ═════════════════════ 初始化 ═════════════════════
async function init() {
    initLang();
    await loadBranding();
    applyStaticCopy();
    loadLicenseStatus();

    try { await loadWorkspaces(); } catch (_) {}

    const saved = loadSavedCid();
    if (saved && workspaces.find(function(w) { return w.id === saved; })) {
        currentCompanyId = saved;
    } else if (workspaces.length === 1) {
        currentCompanyId = workspaces[0].id;
    }
    saveState();

    window.addEventListener('hashchange', function() {
        showRoute(parseHashRoute(location.hash));
    });

    const route = parseHashRoute(location.hash || '#/settings');
    if (!location.hash) location.hash = '#/settings';
    showRoute(route);
}

document.addEventListener('DOMContentLoaded', init);
