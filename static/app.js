// ═════════════════════ STATE ═════════════════════
let workspaces = [];
let currentCompanyId = null;
let currentView = 'chat';       // chat | customers | tasks | directory | history
let currentChatContext = 'general';
let currentChatName = '今日简报';
let currentLibraryId = null;
let currentCustomerId = null;
let _currentConvId = null;       // 当前 AI 回复的 conversation_id，用于评分
let editingCustomerData = null; // for customer detail panel
let _onboardingStep = 1;          // 1 = welcome card, 2 = OSINT input + results
let _onboardingInputText = '';    // user-entered workspace name/website
let currentLang = 'zh';           // zh | en

// ═════════════════════ I18N ═════════════════════
const I18N = {
    zh: {
        'btn.cancel':'取消',
        'btn.close':'关闭',
        'btn.save':'保存',
        'chat.ph.general':'有什么可以帮你？',
        'chat.clr':'🗑️ 清屏',
        'guide.progress':'今日进度',
        'guide.rest':'当前时段暂无安排',
        'hist.confirm_delete':'确定删除这条对话记录？此操作不可恢复。',
        'hist.delete_fail':'删除失败',
        'hist.delete_title':'删除此对话',
        'hist.deleted':'对话已删除',
        'history.no_records':'暂无对话记录',
        'history.title':'对话记录',
        'import.confirm':'确认导入',
        'import.importing':'导入中...',
        'license.activate_btn':'🔑 输入激活码',
        'license.active':'已激活',
        'license.days_left':'剩余 {n} 天',
        'license.expired':'已到期',
        'license.expiring':'即将到期',
        'license.req_code':'申请码',
        'license.trial':'试用',
        'misc.thinking':'正在思考...',
        'modal.co.add_title':'添加新公司',
        'modal.co.contact':'联系人',
        'modal.co.contact_ph':'姓名',
        'modal.co.create':'创建公司',
        'modal.co.email':'邮箱',
        'modal.co.identity_label':'Agent 身份 (Markdown)',
        'modal.co.identity_ph':'粘贴 agent-identity.md 内容...',
        'modal.co.name':'公司名称 *',
        'modal.co.name_ph':'例如：我的业务',
        'modal.co.slug_ph':'自动生成',
        'modal.co.slug_tt':'由系统根据公司名称自动生成',
        'modal.co.tab_identity':'Agent 身份',
        'modal.co.tab_list':'公司列表',
        'modal.co.title':'🏢 公司设置',
        'modal.co.website':'网站',
        'nav.history':'对话记录',
        'nav.tasks':'定时任务',
        'quality.avg':'均分',
        'quality.rated':'近30天评分',
        'quality.worst':'待改进',
        'sys.restart_fail':'❌ 重启失败: ',
        'sys.restart_ok':'✅ 重启命令已发送，页面将在几秒后刷新',
        'sys.restart_timeout':'⚠️ 服务重启超时，请手动刷新页面',
        'sys.restart_toast':'🔄 正在重启服务...',
        'sys.restart_wait':'🔄 服务正在重启，页面即将刷新...',
        'sys.update_done':'✅ 更新完成。请点击"🔄 重启"以应用新版本。',
        'sys.update_done_restart':'✅ 系统更新完成！正在重启...',
        'sys.update_fail':'❌ 更新失败: ',
        'sys.update_network':'⚠️ 更新请求失败，请检查网络连接后重试',
        'sys.update_unknown':'⚠️ 更新结果未知，请检查网络后重试',
        'toast.activate_fail':'激活失败',
        'toast.complete_onboarding':'请先完成新手引导',
        'toast.import_fail':'导入失败',
        'toast.imported':'已导入 {n} 个文件到「{dir}」',
        'toast.network_retry':'网络错误，请重试',
        'toast.no_workspace':'请先选择 workspace',
        'toast.request_timeout':'请求超时',
        'workspace.add':'添加公司',
        'workspace.select':'— 选择公司 —',
    },
    en: {
        'btn.cancel':'Cancel',
        'btn.close':'Close',
        'btn.save':'Save',
        'chat.clr':'🗑️ Clear',
        'guide.progress':'Today\'s Progress',
        'guide.rest':'No task scheduled now',
        'hist.confirm_delete':'Delete this conversation? This cannot be undone.',
        'hist.delete_fail':'Delete failed',
        'hist.delete_title':'Delete',
        'hist.deleted':'Conversation deleted',
        'history.no_records':'No chat history',
        'history.title':'Chat History',
        'import.confirm':'Confirm Upload',
        'import.importing':'Importing...',
        'license.activate_btn':'🔑 Enter Activation Code',
        'license.active':'Active',
        'license.days_left':'{n} days left',
        'license.expired':'Expired',
        'license.expiring':'Expiring Soon',
        'license.req_code':'Request Code',
        'license.trial':'Trial',
        'misc.thinking':'Thinking...',
        'modal.co.add_title':'Add Workspace',
        'modal.co.contact':'Contact',
        'modal.co.contact_ph':'Name',
        'modal.co.create':'Create Workspace',
        'modal.co.email':'Email',
        'modal.co.identity_label':'Agent Identity (Markdown)',
        'modal.co.identity_ph':'Paste agent-identity.md content...',
        'modal.co.name':'Workspace Name *',
        'modal.co.name_ph':'e.g. My Trading Co.',
        'modal.co.slug_ph':'Auto-generated',
        'modal.co.slug_tt':'Auto-generated from workspace name',
        'modal.co.tab_identity':'Agent Identity',
        'modal.co.tab_list':'Workspaces',
        'modal.co.title':'🏢 Workspace Settings',
        'modal.co.website':'Website',
        'nav.history':'History',
        'nav.tasks':'Tasks',
        'quality.avg':'Avg',
        'quality.rated':'Ratings (30d)',
        'quality.worst':'Needs work',
        'sys.restart_fail':'❌ Restart failed: ',
        'sys.restart_ok':'✅ Restart command sent, page will refresh soon',
        'sys.restart_timeout':'⚠️ Restart timeout, please refresh manually',
        'sys.restart_toast':'🔄 Restarting service...',
        'sys.restart_wait':'🔄 Service restarting, page will refresh...',
        'sys.update_done':'✅ Update complete. Click "🔄 Restart" to apply.',
        'sys.update_done_restart':'✅ Update complete! Restarting...',
        'sys.update_fail':'❌ Update failed: ',
        'sys.update_network':'⚠️ Update request failed, check network',
        'sys.update_unknown':'⚠️ Update result unknown, check network',
        'toast.activate_fail':'Activation failed',
        'toast.complete_onboarding':'Please complete the tutorial first',
        'toast.import_fail':'Import failed',
        'toast.imported':'Imported {n} files to "{dir}"',
        'toast.network_retry':'Network error, please retry',
        'toast.no_workspace':'Please select a workspace first',
        'toast.request_timeout':'Request timeout',
        'workspace.add':'Add',
        'workspace.select':'— Select Workspace —',
    }
};

function t(key, params) {
    var s = (I18N[currentLang] && I18N[currentLang][key]) || (I18N.zh && I18N.zh[key]) || key;
    if (params) { for (var k in params) s = s.replace('{'+k+'}', params[k]); }
    return s;
}

function switchLang(lang) {
    if (lang === currentLang) return;
    currentLang = lang;
    try { localStorage.setItem('agentbase_lang', lang); } catch(_) {}
    // 完整刷新 UI
    _applyLanguage();
}

function initLang() {
    try { currentLang = localStorage.getItem('agentbase_lang') || 'zh'; } catch(_) { currentLang = 'zh'; }
    var sel = document.getElementById('lang-select');
    if (sel) sel.value = currentLang;
    _applyLanguage();
}

function _applyLanguage() {
    // 1. 侧边栏
    _updateSidebarLabels();
    // 2. 公司选择器
    var cs = document.getElementById('workspace-select');
    if (cs && cs.options[0]) cs.options[0].text = t('workspace.select');
    var addBtn = document.querySelector('.csel-row button');
    if (addBtn) { addBtn.title = t('workspace.add'); addBtn.textContent = '+'; }
    // 3. Footer 按钮 —— 图标（textContent）写在 HTML 里，这里只填悬停提示。
    //    早期把图标和文字一起塞进 i18n（'⬆️ 系统更新'），改图标要同步改两份翻译；
    //    现在翻译只管文字。
    var map = {
        'system-update-btn': 'footer.update', 'system-restart-btn': 'footer.restart',
'skills-update-btn': 'footer.skills_update',
        'onboarding-btn': 'footer.onboarding',
    };
    for (var id in map) {
        var b = document.getElementById(id);
        if (b) b.setAttribute('data-tip', t(map[id]));
    }
    // 4. 静态 modal 文本更新
    _updateStaticModals();
    // 5. 重新渲染当前视图
    if (currentView === 'chat') {
        navToView('chat', currentChatContext, t('nav.' + currentChatContext));
    } else {
        navToView(currentView);
    }
    // 6. 更新页面标题
}

function _updateSidebarLabels() {
    var sectionKeys = ['nav.workbench', 'nav.outreach', 'nav.sales', 'nav.tools', 'nav.hist'];
    document.querySelectorAll('.nav-section-title').forEach(function(el, i) {
        if (i < sectionKeys.length) el.textContent = t(sectionKeys[i]);
    });
    var ctxMap = {
        'daily':'nav.daily','lead':'nav.lead','platform':'nav.platform',
        'docs':'nav.docs','docgen':'nav.docgen','osint':'nav.osint',
    };
    var viewMap = {'customers':'nav.customers','tasks':'nav.tasks','history':'nav.history'};
    document.querySelectorAll('.nav-item').forEach(function(el) {
        var ctx = el.getAttribute('data-chat-context');
        var view = el.getAttribute('data-view');
        var key = (ctx && ctxMap[ctx]) || (view && viewMap[view]);
        if (key) {
            var label = el.querySelector('.nav-label');
            if (label) label.textContent = t(key);
            if (ctx && view === 'chat') {
                el.setAttribute('onclick', "navToView('chat','"+ctx+"','"+t(key)+"')");
            }
        }
    });
    if (currentView === 'chat') currentChatName = t('nav.' + currentChatContext);
}

function _updateStaticModals() {
    // Workspace modal
    var cm = document.getElementById('workspace-modal');
    if (cm) {
        var h3 = cm.querySelector('h3'); if (h3) h3.textContent = t('modal.co.title');
        var tb1 = document.getElementById('tab-btn-workspaces'); if (tb1) tb1.textContent = t('modal.co.tab_list');
        var tb2 = document.getElementById('tab-btn-identity'); if (tb2) tb2.textContent = t('modal.co.tab_identity');
        var h4 = cm.querySelector('#tab-workspaces h4'); if (h4) h4.textContent = t('modal.co.add_title');
        var lbls = cm.querySelectorAll('label');
        lbls.forEach(function(l) {
            var f = l.getAttribute('for');
            if (f === 'co-name') l.textContent = t('modal.co.name');
            else if (f === 'co-contact-name') l.textContent = t('modal.co.contact');
            else if (f === 'co-contact-email') l.textContent = t('modal.co.email');
            else if (f === 'co-website') l.textContent = t('modal.co.website');
            else if (f === 'identity-editor') l.textContent = t('modal.co.identity_label');
        });
        var inps = cm.querySelectorAll('input');
        inps.forEach(function(inp) {
            if (inp.id === 'co-name') inp.placeholder = t('modal.co.name_ph');
            else if (inp.id === 'co-slug') { inp.placeholder = t('modal.co.slug_ph'); inp.title = t('modal.co.slug_tt'); }
            else if (inp.id === 'co-contact-name') inp.placeholder = t('modal.co.contact_ph');
        });
        var ta = cm.querySelector('#identity-editor'); if (ta) ta.placeholder = t('modal.co.identity_ph');
        var btns = cm.querySelectorAll('.form-actions button');
        btns.forEach(function(b) {
            if (b.textContent.includes('创建') || b.textContent.includes('Create')) b.textContent = t('modal.co.create');
            else if (b.textContent.includes('保存') || b.textContent.includes('Save')) b.textContent = t('btn.save');
            else if (b.textContent.includes('关闭') || b.textContent.includes('Close')) b.textContent = t('btn.close');
        });
    }
}

let _onboardingOsinResponse = ''; // accumulated AI response text
let _onboardingStreamCtl = null;  // AbortController for SSE stream

// ═════════════════════ 通用 onboarding 向导 ═════════════════════
// 字段来自 business.yaml 的 onboarding_fields（由 /api/branding 下发），框架不写死业务字段。
let _wizardIndex = 0;
let _wizardAnswers = {};
let _wizardFields = [];
let _onboardingFields = [];

function isOnboardingCompleted() {
    try { return localStorage.getItem('_onboarding_completed') === '1'; } catch(_) { return false; }
}

function showWizardInLeadView() {
    var msgs = document.getElementById('chat-messages');
    var empty = document.getElementById('chat-empty');
    if (!msgs || !empty) return;
    _wizardFields = _onboardingFields.slice();
    if (!_wizardFields.length) return;
    empty.style.display = 'none';
    var old = document.getElementById('wizard-card');
    if (old) old.remove();
    _wizardIndex = 0;
    var card = document.createElement('div');
    card.id = 'wizard-card';
    card.innerHTML = wizardRenderStep();
    msgs.appendChild(card);
    setTimeout(function() { var el = document.getElementById('wizard-input'); if (el) el.focus(); }, 200);
}

function wizardRenderStep() {
    var field = _wizardFields[_wizardIndex] || {};
    var total = _wizardFields.length;
    var pct = Math.round((( _wizardIndex) / total) * 100);
    return `<div class="onboarding-card" style="margin:0 auto;max-width:580px;">
        <div style="height:4px;background:var(--border-light);border-radius:2px;overflow:hidden;margin-bottom:16px;">
            <div style="width:${pct}%;height:100%;background:var(--primary);"></div>
        </div>
        <h2 class="onboarding-title" style="font-size:20px;">${esc(field.label || field.key || '')}</h2>
        <p style="text-align:center;color:var(--text-secondary);font-size:14px;margin-bottom:16px;">
            第 ${_wizardIndex + 1} / ${total} 项 · 随时可以跳过</p>
        <div class="onboarding-input-row">
            <input type="text" id="wizard-input" class="onboarding-text-input"
                placeholder="${esc(field.example || '')}"
                value="${esc(_wizardAnswers[field.key] || '')}"
                onkeydown="if(event.key==='Enter')wizardNext()" autofocus />
        </div>
        <button class="btn btn-primary btn-lg" onclick="wizardNext()">${_wizardIndex + 1 === total ? '完成' : '下一步 →'}</button>
        <div class="onboarding-skip" style="display:flex;justify-content:space-between;">
            ${_wizardIndex > 0 ? '<a onclick="wizardBack()">← 返回</a>' : '<span></span>'}
            <a onclick="wizardClose()">跳过</a>
        </div>
    </div>`;
}

function wizardNext() {
    var field = _wizardFields[_wizardIndex];
    var el = document.getElementById('wizard-input');
    if (field) _wizardAnswers[field.key] = (el?.value || '').trim();
    if (_wizardIndex + 1 < _wizardFields.length) {
        _wizardIndex += 1;
        updateWizardCard(wizardRenderStep());
        setTimeout(function() { var i = document.getElementById('wizard-input'); if (i) i.focus(); }, 150);
    } else {
        wizardSubmit();
    }
}

function wizardBack() {
    if (_wizardIndex > 0) {
        _wizardIndex -= 1;
        updateWizardCard(wizardRenderStep());
        setTimeout(function() { var i = document.getElementById('wizard-input'); if (i) i.focus(); }, 150);
    }
}

function updateWizardCard(html) {
    var card = document.getElementById('wizard-card');
    if (card) card.innerHTML = html;
}

function wizardClose() {
    _wizardIndex = 0; _wizardAnswers = {};
    var card = document.getElementById('wizard-card'); if (card) card.remove();
    var empty = document.getElementById('chat-empty'); if (empty) empty.style.display = '';
}

function wizardSubmit() {
    var lines = _wizardFields.map(function(f) {
        return '- ' + (f.label || f.key) + '：' + (_wizardAnswers[f.key] || '（未填写）');
    });
    var text = '请记住以下业务信息：\n' + lines.join('\n');
    var textarea = document.getElementById('msg-input');
    if (!textarea) return;
    textarea.value = text;
    try { localStorage.setItem('_onboarding_completed', '1'); } catch(_) {}
    setTimeout(function() { wizardClose(); }, 300);
    setTimeout(function() { sendMsg(); }, 400);
}

function saveState() {
    if (currentCompanyId) sessionStorage.setItem('agentbase_cid', currentCompanyId);
    else sessionStorage.removeItem('agentbase_cid');
    sessionStorage.setItem('agentbase_view', currentView);
    if (currentChatContext) sessionStorage.setItem('agentbase_ctx', currentChatContext);
}
function loadSavedCid() { return parseInt(sessionStorage.getItem('agentbase_cid') || '0') || null; }

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

// 401 自动恢复：token 失效（服务重启）→ 重取新 token；公司缺失 → 重载公司列表
async function recoverAuth(method, path, body) {
    if (_authRecovering) return null;
    _authRecovering = true;
    try {
        // 服务重启后旧页面 token 失效：重新拉取 /agentbase 提取新 token
        var fresh = await fetch('/agentbase?_=' + Date.now(), { cache: 'no-store' });
        if (fresh.ok) {
            var html = await fresh.text();
            var m = html.match(/(?:const|let|var)\s+TOKEN\s*=\s*"([^"]+)"/);
            if (m && m[1] && m[1] !== TOKEN) {
                TOKEN = m[1];
                var retry = await api(method, path, body);
                if (retry !== null) return retry;
            }
        }
        // token 没变 → 可能是 X-Workspace-ID 缺失/失效 → 重载公司
        var prevCid = currentCompanyId;
        currentCompanyId = null;
        await loadCompanies();
        if (prevCid && !workspaces.find(function(c) { return c.id === prevCid; })) {
            toast(t('toast.no_workspace'));
            return null;
        }
        if (currentCompanyId) {
            var retry2 = await api(method, path, body);
            if (retry2 !== null) return retry2;
        }
        return null;
    } catch (e) {
        return null;
    } finally {
        _authRecovering = false;
    }
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
    const tid = setTimeout(() => ctrl.abort(), 120000);
    opts.signal = ctrl.signal;
    try {
        const r = await fetch(path, opts);
        clearTimeout(tid);
        if (!r.ok) {
            const err = await r.json().catch(() => ({}));
            const msg = err.detail || `请求失败 (${r.status})`;
            if (r.status === 401) {
                // 自动恢复一次：重取 token / 重载公司
                const recovered = await recoverAuth(method, path, body);
                if (recovered !== null) return recovered;
                toast(t('toast.no_workspace'));
            }
            else if (r.status === 402) showLicenseExpired(msg);
            else if (r.status === 404) toast(msg);
            else if (r.status === 409) toast(msg);
            else toast(msg);
            return null;
        }
        return r.json();
    } catch(e) {
        clearTimeout(tid);
        if (e.name === 'AbortError') { toast(t('toast.request_timeout')); return null; }
        throw e;
    }
}

// ── 许可证 ──

async function loadLicenseStatus() {
    try {
        const r = await fetch('/api/agentbase/license/status');
        const data = await r.json();
        const bar = document.getElementById('license-bar');
        if (!bar) return;

        var _daysLeft = (typeof data.days_remaining === 'number') ? data.days_remaining : 999;
        var _bgColor = _daysLeft <= 7 ? '#FEF3C7' : '#DBEAFE';
        if (data.status === 'expired' || data.status === 'tampered') _bgColor = '#FEE2E2';
        var reqCodeHtml = data.request_code
            ? ' · ' + t('license.req_code') + ': <code style="background:' + _bgColor + ';padding:1px 6px;border-radius:3px;font-size:11px;user-select:all;cursor:text;" onclick="navigator.clipboard.writeText(this.textContent);toast(t(\'toast.copied\'))">' + esc(data.request_code) + '</code>'
            : '';

        if (data.status === 'expired') {
            bar.style.display = 'block'; bar.style.background = '#FEF2F2'; bar.style.color = '#991B1B';
            bar.innerHTML = '⚠️ ' + t('license.expired') + ' · <a href="#" onclick="showActivateModal()" style="color:#DC2626;text-decoration:underline;">' + t('license.activate_btn') + '</a>' + reqCodeHtml;
        } else if (data.status === 'active' && data.days_remaining <= 7) {
            bar.style.display = 'block';
            bar.style.background = data.days_remaining === 0 ? '#FEF2F2' : '#FFFBEB';
            bar.style.color = data.days_remaining === 0 ? '#991B1B' : '#92400E';
            bar.innerHTML = '✅ ' + t('license.active') + ' · ' + t('license.expiring') + (data.expires_at ? ' ' + data.expires_at.slice(0, 10) : '') + ' · <a href="#" onclick="showActivateModal()" style="color:' + (data.days_remaining===0?'#DC2626':'#D97706') + ';text-decoration:underline;font-weight:600;">' + t('license.activate_btn') + '</a>' + reqCodeHtml;
        } else if (data.status === 'active') {
            bar.style.display = 'block'; bar.style.background = '#F0FDF4'; bar.style.color = '#166534';
            bar.innerHTML = '✅ ' + t('license.active') + (data.expires_at ? ' · ' + t('license.expiring') + ' ' + data.expires_at.substring(0, 10) : '');
        } else if (data.status === 'trial') {
            bar.style.display = 'block';
            bar.style.background = data.days_remaining <= 7 ? '#FFFBEB' : '#EFF6FF';
            bar.style.color = data.days_remaining <= 7 ? '#92400E' : '#1E40AF';
            bar.innerHTML = '⏳ ' + t('license.trial') + ' ' + t('license.days_left', {n: data.days_remaining}) + ' · <a href="#" onclick="showActivateModal()" style="color:' + (data.days_remaining <= 7 ? '#D97706' : '#2563EB') + ';text-decoration:underline;">' + t('license.activate_btn') + '</a>' + reqCodeHtml;
        } else if (data.status === 'tampered') {
            bar.style.display = 'block'; bar.style.background = '#FEF2F2'; bar.style.color = '#991B1B';
            bar.innerHTML = '⚠️ License Error · <a href="#" onclick="showActivateModal()" style="color:#DC2626;text-decoration:underline;font-weight:600;">Reactivate</a>' + reqCodeHtml;
        }
    } catch(e) {}
}

function showLicenseExpired(msg) {
    const div = document.createElement('div');
    div.className = 'modal-backdrop';
    div.innerHTML = '<div class="modal" style="text-align:center;max-width:420px;">' +
        '<h3>⏰ ' + esc(msg || t('license.expired')) + '</h3>' +
        '<p style="margin:8px 0;color:var(--text-secondary);">' + (currentLang==='en'?'Contact Roger Lococo for activation':'请联系 Roger Lococo 获取激活码继续使用') + '</p>' +
        '<img src="/static/wechat-contact.jpeg" alt="WeChat QR" style="width:200px;border-radius:8px;margin:8px 0;">' +
        '<p style="font-size:11px;color:var(--text-muted);">' + (currentLang==='en'?'Contact support':'联系技术支持') + '</p>' +
        '<p style="font-size:11px;color:var(--text-muted);">📧 lauroge@gmail.com</p>' +
        '<button class="btn btn-primary" onclick="showActivateModal()">' + t('license.activate_btn') + '</button>' +
        '<button class="btn" onclick="this.closest(\'.modal-backdrop\').remove()" style="margin-top:8px;">' + t('btn.close') + '</button>' +
    '</div>';
    document.body.appendChild(div);
}

async function showActivateModal() {
    _removeDynamicModals();
    var reqCode = '';
    try {
        var s = await fetch('/api/agentbase/license/status');
        var sd = await s.json();
        reqCode = sd.request_code || '';
    } catch(e) {}
    const div = document.createElement('div');
    div.className = 'modal-backdrop';
    div.innerHTML = '<div class="modal" style="text-align:center;">' +
        '<h3>🔑 ' + (currentLang==='en'?'Activate agentbase':'激活 agentbase') + '</h3>' +
        '<p style="margin:8px 0;color:var(--text-secondary);">' + (currentLang==='en'?'Send the code below to the author to get an activation code':'请将下方申请码发送给作者获取激活码') + '</p>' +
        (reqCode ? '<div style="background:var(--bg-secondary);padding:10px 14px;border-radius:var(--radius-sm);font-family:monospace;font-size:16px;letter-spacing:2px;margin:8px 0;cursor:pointer;user-select:all;" onclick="navigator.clipboard.writeText(this.textContent);toast(t(\'toast.copied\'))" title="' + (currentLang==='en'?'Click to copy':'点击复制') + '">' + reqCode + '</div>' : '') +
        '<input type="text" id="activate-code-input" aria-label="Activation code" placeholder="' + (currentLang==='en'?'Paste activation code':'粘贴作者提供的激活码') + '" style="width:100%;padding:10px;border:1px solid var(--border);border-radius:var(--radius-sm);font-family:monospace;font-size:14px;text-align:center;text-transform:uppercase;margin:12px 0;">' +
        '<button class="btn btn-primary" onclick="doActivate()" style="margin-top:8px;">✅ ' + (currentLang==='en'?'Activate':'激活') + '</button>' +
        '<button class="btn" onclick="this.closest(\'.modal-backdrop\').remove()">' + t('btn.cancel') + '</button>' +
        '<p id="activate-msg" style="margin-top:10px;font-size:12px;"></p>' +
    '</div>';
    document.body.appendChild(div);
    setTimeout(() => document.getElementById('activate-code-input')?.focus(), 100);
}

async function doActivate() {
    const input = document.getElementById('activate-code-input');
    const msg = document.getElementById('activate-msg');
    const code = input.value.trim();
    if (!code) { msg.textContent = currentLang === 'en' ? 'Please enter the activation code' : '请输入激活码'; msg.style.color = 'var(--accent-red)'; return; }
    try {
        // 走统一 api 包装：激活是写操作，必须带 session token
        const data = await api('POST', '/license/activate', {code});
        if (!data) {
            msg.textContent = t('toast.activate_fail');
            msg.style.color = 'var(--accent-red)';
            return;
        }
        if (data.ok) {
            msg.textContent = data.message;
            msg.style.color = 'var(--accent-green)';
            setTimeout(() => {
                _removeDynamicModals();
                loadLicenseStatus();
            }, 1500);
        } else {
            msg.textContent = data.error || t('toast.activate_fail');
            msg.style.color = 'var(--accent-red)';
        }
    } catch(e) {
        msg.textContent = t('toast.network_retry');
        msg.style.color = 'var(--accent-red)';
    }
}

// ── 重启协调 ──
// 清理前端运行时缓存，但保留用户上下文（agentbase_cid 让重启后不必重新选公司）
function _clearRuntimeCaches() {
    try {
        // 清理视图缓存（DOM 引用 + 渲染状态），强制重启后重新拉取
        if (typeof viewCache === 'object') {
            for (const k of Object.keys(viewCache)) delete viewCache[k];
        }
        // 仅清理与服务端 schema 强耦合的会话状态，保留 agentbase_cid（公司选择）
        const preserveKeys = new Set(['agentbase_cid', '_agentbase_reload_state']);
        const ssKeys = [];
        for (let i = 0; i < sessionStorage.length; i++) ssKeys.push(sessionStorage.key(i));
        ssKeys.forEach(k => { if (!preserveKeys.has(k)) sessionStorage.removeItem(k); });
    } catch(_) { /* sessionStorage 在隐私模式下可能抛错，忽略 */ }
}

// ── 重启前状态保存 / 恢复（避免 hard reload 丢失阅读位置）──────────

function _saveReloadState() {
    try {
        const state = {
            view: currentView || 'chat',
            scrollY: window.scrollY || document.documentElement.scrollTop || 0,
            chatCtx: currentView === 'chat' ? (currentChatContext || '') : '',
            chatName: currentView === 'chat' ? (currentChatName || '') : '',
            ts: Date.now(),
        };
        sessionStorage.setItem('_agentbase_reload_state', JSON.stringify(state));
    } catch(_) {}
}

function _restoreReloadState() {
    try {
        const raw = sessionStorage.getItem('_agentbase_reload_state');
        if (!raw) return null;
        sessionStorage.removeItem('_agentbase_reload_state');
        const state = JSON.parse(raw);
        // 超过 5 分钟的旧状态丢弃（可能是残留）
        if (Date.now() - state.ts > 300000) return null;
        return state;
    } catch(_) { return null; }
}

// 通过 /api/status 的 started_at 时间戳检测进程是否已重启，然后 hard-reload
// 不依赖 DOWN→UP 序列：新进程启动快时 DOWN 瞬间无法捕捉
//
// maxSeconds：兜底等待秒数，默认 120（重启场景足够）。
// **重建运行环境必须传更大的值** —— 那一步要建 venv + 装全部依赖，5~10 分钟是常态，
// 用默认的 2 分钟会在真正成功之前就报「超时」，把用户吓去手动折腾。
async function _waitForRestartAndReload(onTimeout, maxSeconds) {
    let attempts = 0;
    const maxAttempts = maxSeconds || 120;   // 每 1 秒一次轮询
    // 保存当前 started_at，重启后新进程的时间戳会不同
    let oldStartedAt = -1;  // -1 = 无法获取（旧服务无此字段 / 请求失败）
    try {
        const r0 = await fetch('/api/status?_=' + Date.now(), { cache: 'no-store' });
        if (r0.ok) {
            const d0 = await r0.json();
            // 旧服务可能无此字段 → 存 -1，只要能获取到新值就视为重启成功
            oldStartedAt = (typeof d0.started_at === 'number') ? d0.started_at : -1;
        }
    } catch(_) {}

    console.log('[重启] 开始轮询 /api/status (old started_at=' + oldStartedAt + ') ...');
    const tick = async () => {
        attempts++;
        try {
            const r = await fetch('/api/status?_=' + Date.now(), { cache: 'no-store' });
            if (r.ok) {
                const d = await r.json();
                const cur = (typeof d.started_at === 'number') ? d.started_at : -1;
                // 检测到重启：started_at 从旧值变为新值（-1→数值也算）
                if (cur > 0 && cur !== oldStartedAt) {
                    console.log('[重启] 第 ' + attempts + ' 次 — 检测到新进程 (started_at=' + cur + ')，刷新页面');
                    _saveReloadState();  // 保存当前浏览位置，reload 后恢复
                    _clearRuntimeCaches();
                    try { sessionStorage.removeItem('_upgrade_in_progress'); } catch(_) {}
                    location.href = '/agentbase?_=' + Date.now();
                    return;
                }
            }
        } catch(_) { /* 旧进程已下线但新进程未就绪，继续等 */ }
        if (attempts >= maxAttempts) {
            console.error('[重启] 超时 (' + maxAttempts + ' 次轮询)，请手动刷新');
            toast(t('sys.restart_timeout'));
            if (typeof onTimeout === 'function') onTimeout();
            return;
        }
        setTimeout(tick, 1000);
    };
    setTimeout(tick, 500);
}

/**
 * 切换侧边栏按钮的「忙」态：忙时图标换成沙漏并禁用，闲时恢复原图标。
 *
 * 图标化之后不能再沿用旧写法（把 textContent 设成「更新中…」这样的文字）——
 * 那会把按钮上的图标直接抹掉，恢复时还得重新知道原图标长什么样。
 * 原图标记在 dataset 里，连续多次 busy 也不会把沙漏本身记成原图标。
 */
function _setBtnBusy(btn, busy) {
    if (!btn) return;
    if (busy) {
        if (btn.dataset.idleIcon === undefined) btn.dataset.idleIcon = btn.textContent;
        btn.disabled = true;
        btn.textContent = '⏳';
    } else {
        btn.disabled = false;
        if (btn.dataset.idleIcon !== undefined) btn.textContent = btn.dataset.idleIcon;
    }
}

// ── 系统更新 ──
async function doSystemUpdate(e) {
    // 用 currentTarget 或回退到事件对象，再不行直接查 DOM
    const btn = (e && (e.currentTarget || e.target)) || document.querySelector('#system-update-btn');
    if (!btn) return;
    _setBtnBusy(btn, true);
    toast(t('sys.restart_toast').replace('Restarting','Updating'));
    var updateFailed = false;
    var restartScheduled = false;
    try {
        const resp = await api('POST', '/api/agentbase/system/update');
        if (!resp) {
            updateFailed = true;
        } else if (resp.ok) {
            restartScheduled = !!resp.restart_scheduled;
            if (restartScheduled) {
                toast(t('sys.update_done_restart'));
            } else {
                toast(t('sys.update_done'));
            }
            // 非致命步骤（skills 同步等）失败只算警告，不阻止升级，但必须让用户看见
            if (resp.warnings && resp.warnings.length) {
                toast('⚠️ 升级完成，但有 ' + resp.warnings.length + ' 项警告：' + resp.warnings.join('; '));
            }
        } else if (resp.error || (resp.errors && resp.errors.length)) {
            const errMsg = resp.error || resp.errors.join('; ');
            toast(t('sys.update_fail') + errMsg);
            updateFailed = true;
        } else {
            toast(t('sys.update_unknown'));
            updateFailed = true;
        }
    } catch(e) {
        toast(t('sys.update_network'));
        updateFailed = true;
    }
    if (updateFailed || !restartScheduled) {
        _setBtnBusy(btn, false);
        return;
    }
    // 存入标记，页面 reload 后检测并显示 toast
    try { sessionStorage.setItem('_agentbase_upgrade_done', '1'); } catch(_) {}
    _waitForRestartAndReload(() => {
        _setBtnBusy(btn, false);
    });
}

// ── 数据备份 ──
async function doSystemRestart(e) {
    const btn = (e && (e.currentTarget || e.target)) || document.querySelector('#system-restart-btn');
    if (!btn) return;
    _setBtnBusy(btn, true);
    toast(t('sys.restart_toast'));
    try {
        const resp = await api('POST', '/api/agentbase/system/restart');
        if (resp && resp.ok) {
            toast(t('sys.restart_ok'));
        } else {
            toast(t('sys.restart_fail') + (resp?.error || ''));
        }
    } catch(e) {
        toast(t('sys.restart_wait'));
    }
    _waitForRestartAndReload(() => {
        _setBtnBusy(btn, false);
    });
}


function $(id) { return document.getElementById(id); }
function showModal(id) { $(id).classList.remove('hidden'); }
function hideModal(id) { $(id).classList.add('hidden'); }
function toast(msg) {
    const c = $('toast-container');
    const t = document.createElement('div'); t.className = 'toast'; t.textContent = msg;
    c.appendChild(t); setTimeout(() => t.remove(), 3000);
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
// 聊天流的归属记账：记录「当前这条流属于哪个公司」。
// 存在的理由：sendMsg 里的 AbortController 是局部变量，切换公司时无人能中止它，
// 旧流跑完后又会走 addMsg()，而 addMsg 读全局 currentChatContainer（已指向新公司），
// 于是 A 公司的回复被写进 B 公司的会话窗口。归属记账让切公司能统一作废旧流。
let _chatStream = null;  // { cid, ctl }

// 开始一条属于 cid 的聊天流，返回它的 AbortController
function _beginChatStream(cid) {
    const ctl = new AbortController();
    _chatStream = { cid: cid, ctl: ctl };
    return ctl;
}

// 作废当前聊天流（切换公司时调用），保证旧流不再往页面写内容
function _abortChatStream() {
    if (_chatStream) {
        _chatStream.ctl.abort();
        _chatStream = null;
    }
}

// 流收尾时清理自己那条（仅当它仍是当前流，避免误清用户切公司后新建的流）
function _endChatStream(ctl) {
    if (_chatStream && _chatStream.ctl === ctl) _chatStream = null;
}

// 该公司的流是否仍是当前活跃流（旧流据此丢弃输出）
function _chatStreamBelongsTo(cid) {
    return !!_chatStream && _chatStream.cid === cid;
}
// #endregion stream-guard

// ═════════════════════ NAVIGATION ═════════════════════
// 视图缓存：{ viewKey: { element, rendered, context } }
const viewCache = {};
// 当前活跃的 chat 容器（用于解决多视图 DOM 中相同 ID 元素的查找问题）
let currentChatContainer = null;

function navToView(view, chatCtx, chatName) {
    // 新手引导进行中时阻止导航
    if (!isOnboardingCompleted() && document.getElementById('onboarding-panel')) {
        toast(t('toast.complete_onboarding'));
        return;
    }
    // 未选择公司时，所有菜单点击都显示固定提示页
    if (!currentCompanyId) {
        renderNoCompanyPage();
        return;
    }

    currentView = view;
    if (chatCtx) { currentChatContext = chatCtx; currentChatName = chatName || ''; }
    saveState();

    // Update sidebar active
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
    const activeItem = document.querySelector(`.nav-item[data-view="${view}"][data-chat-context="${chatCtx||''}"]`) ||
                       document.querySelector(`.nav-item[data-view="${view}"]`);
    if (activeItem) activeItem.classList.add('active');

    // 隐藏所有视图，并清除非缓存内容（如 empty state）
    const main = $('main-content');
    for (const key in viewCache) {
        viewCache[key].element.style.display = 'none';
    }
    // 移除 main 中不属于视图缓存的子元素（首次从 empty state 切换时）
    const cachedIds = new Set(Object.keys(viewCache).map(k => 'view-' + k));
    for (const child of Array.from(main.children)) {
        if (child.id === 'guidance-bar') continue;  // 不删除全局横幅
        if (!cachedIds.has(child.id)) {
            child.remove();
        }
    }

    // 构建缓存 key
    const cacheKey = view + (chatCtx ? '-' + chatCtx : '');

    if (!viewCache[cacheKey]) {
        // 首次渲染此视图：创建容器 div 并挂到 main
        const container = document.createElement('div');
        container.className = view === 'chat' ? 'chat-view' : 'panel-view';
        container.id = 'view-' + cacheKey;
        main.appendChild(container);
        viewCache[cacheKey] = { element: container, rendered: false };

        switch (view) {
            case 'chat':
                currentChatContainer = container;
                renderChatViewInto(container, chatCtx, chatName);
                break;
            case 'tasks':
                renderTasksViewInto(container);
                break;
            case 'history':
                renderHistoryViewInto(container);
                break;
            case 'settings':
                renderSettingsViewInto(container);
                break;
        }
        viewCache[cacheKey].rendered = true;
    }

    viewCache[cacheKey].element.style.display = 'flex';
    // 记录当前活跃的 chat 容器
    if (view === 'chat') {
        currentChatContainer = viewCache[cacheKey].element;
        // 切换到聊天视图时直接滚动到底部（最新消息）
        requestAnimationFrame(() => {
            const msg = currentChatContainer?.querySelector('#chat-messages');
            if (msg) msg.scrollTop = msg.scrollHeight;
        });
        // 绑定滚动监听——每次激活聊天视图都重新挂载浮标
        setTimeout(() => {
            const msg = currentChatContainer?.querySelector('#chat-messages');
            if (msg) _ensureScrollHint(msg);
        }, 300);
    }
}

// ═════════════════════ CHAT VIEW ═════════════════════
function renderChatViewInto(container, ctx, name) {
    const coName = currentCompanyId ? (workspaces.find(c => c.id === currentCompanyId)?.name || '') : '';

    container.innerHTML = `
        <div class="chat-topbar">
            <div style="display:flex;align-items:center;gap:8px;">
                <h2>${esc(name)}</h2>
                ${coName ? `<span class="workspace-badge" style="display:inline-flex;align-items:center;gap:4px;padding:3px 10px;background:rgba(59,130,246,0.08);color:var(--primary);border-radius:999px;font-size:12px;font-weight:500;">🏢 ${esc(coName)}</span>` : ''}
                <span class="chat-context-tag" id="chat-context-tag"></span>
            </div>
            <div class="chat-topbar-actions">
                <input type="file" id="chat-file-input" multiple hidden onchange="uploadChatFiles(this.files)">
                <button onclick="document.getElementById('chat-file-input').click()" title="${t('chat.upload')}">📎</button>
                <button onclick="clearChat()">${t('chat.clr')}</button>
            </div>
        </div>
        <div class="chat-messages" id="chat-messages">
            <div class="empty-state" id="chat-empty">
                <div class="empty-icon">💬</div>
                <h2>${esc(name)}</h2>
                <p>${t('chat.ph.' + ctx)}</p>
            </div>
        </div>
        <div class="chat-input-area">
            <div class="chat-input-inner">
                <textarea id="msg-input" aria-label="输入消息" placeholder="${t('chat.ph.' + ctx)}" rows="1"
                    onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();sendMsg();}"
                    oninput="this.style.height='24px';this.style.height=(this.scrollHeight>80?80:this.scrollHeight)+'px';"></textarea>
                <button onclick="sendMsg()" id="send-btn" title="发送">↑</button>
                <button id="stop-btn" class="hidden" title="停止">■</button>
            </div>
        </div>
        <div class="drop-overlay" id="drop-overlay"><div class="drop-overlay-inner">&#128193; ${currentLang==='en'?'Drop files to add':'释放以添加文件'}</div></div>`;

    loadChatHistory();
    // 首次使用且未完成 onboarding 时显示引导
    if (ctx === 'general' && !isOnboardingCompleted()) {
        setTimeout(function() { showWizardInLeadView(); }, 300);
    }
    // 每日简报视图：额外拉取一次 cron 状态（全局轮询已覆盖）
    if (ctx === 'daily') {
        _shownCronOutputs = new Set();
        loadCronStatus(false);
    }
}

// ═════════════════════ 全局 cron 轮询与工作台横幅 ═════════════════════
let _cronPollTimer = null;
let _shownCronOutputs = new Set();  // 已展示过的 cron 输出任务名

// 框架不含固定的业务任务表：任务全部来自 Hermes cron。

function _renderGuidanceBar(currentTimeStr, completed, pending) {
    const guidance = _getCurrentTaskGuidance(currentTimeStr);
    const doneCount = completed.length, totalPending = pending.length;

    let barHtml = `<div id="guidance-bar" style="flex-shrink:0;max-height:20vh;overflow-y:auto;background:var(--bg-card);border-bottom:1px solid var(--border);padding:6px 12px;line-height:1.4;font-size:12px;">`;

    // 当前任务行
    if (guidance) {
        barHtml += `<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">`;
        barHtml += `<span style="font-size:15px;">⏰</span>`;
        barHtml += `<span style="font-weight:600;font-size:13px;color:var(--primary);">${esc(guidance.name)}</span>`;
        barHtml += `<span style="font-size:13px;color:var(--text-secondary);">${guidance.desc}</span>`;
        barHtml += `</div>`;
    } else {
        barHtml += `<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">`;
        barHtml += `<span style="font-size:15px;">☕</span>`;
        barHtml += '<span style="font-size:13px;color:var(--text-secondary);">'+t('guide.rest')+' · '+esc(currentTimeStr)+'</span>';
        barHtml += `</div>`;
    }

    // 进度条
    const total = doneCount + totalPending;
    const pct = total > 0 ? Math.round(doneCount/total*100) : 0;
    barHtml += '<div style="display:flex;justify-content:space-between;font-size:11px;color:var(--text-muted);margin-bottom:1px;"><span>'+t('guide.progress')+'</span><span>'+doneCount+'/'+total+'</span></div>';
    barHtml += `<div style="height:3px;background:var(--bg-main);border-radius:2px;overflow:hidden;margin-bottom:4px;"><div style="height:100%;width:${pct}%;background:var(--accent-green);border-radius:2px;transition:width 0.3s;"></div></div>`;

    // 今日所有定时任务列表（从 completed + pending 合并，按时间排序）
    const _stripEmoji = s => s.replace(/[\u{1F600}-\u{1F9FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}\u{1F300}-\u{1F5FF}\u{1F680}-\u{1F6FF}\u{1F900}-\u{1F9FF}\u{200D}\u{FE0F}]/gu, '').trim();
    const all = [...completed, ...pending].sort((a, b) => {
        const ta = (a.time || '').split('-')[0], tb = (b.time || '').split('-')[0];
        return ta.localeCompare(tb);
    });
    const items = all.map(t => `<div style="font-size:11px;color:var(--text-muted);line-height:1.6;">${esc(t.time)} ${esc(_stripEmoji(t.name))}</div>`);
    barHtml += `<div>${items.join('')}</div>`;

    barHtml += `</div>`;
    return barHtml;
}

function startCronPolling() {
    stopCronPolling();
    _cronPollTimer = setInterval(() => {
        if (currentCompanyId) loadCronStatus(true);
    }, 30000);
}

function stopCronPolling() {
    if (_cronPollTimer) { clearInterval(_cronPollTimer); _cronPollTimer = null; }
}

// ── 版本更新检查 ──
let _versionPollTimer = null;

async function checkVersion() {
    // 关闭版本升级提醒：用户手上版本稳定就不强制升级
    try {
        const r = await fetch('/api/status?_=' + Date.now(), { cache: 'no-store' });
        if (!r.ok) return;
        const data = await r.json();
        console.log('Version check: current=' + data.version + ' latest=' + (data.latest_version || ''));
    } catch(e) { /* 静默 */ }
}

function startVersionCheck() {
    stopVersionCheck();
    checkVersion();
    _versionPollTimer = setInterval(checkVersion, 10 * 60 * 1000); // 每 10 分钟
}

function stopVersionCheck() {
    if (_versionPollTimer) { clearInterval(_versionPollTimer); _versionPollTimer = null; }
}

async function doUpdateSystem() {
    const btn = document.getElementById('update-banner');
    if (btn) btn.textContent = '更新中...';
    var restartScheduled = false;
    try {
        const resp = await api('POST', '/api/agentbase/system/update');
        if (resp?.ok) {
            restartScheduled = !!resp.restart_scheduled;
            toast(restartScheduled ? '✅ 系统更新完成！正在重启...' : '✅ 更新完成。请点击"🔄 重启"以应用新版本。');
            // 非致命步骤失败只算警告，不阻止升级，但必须让用户看见
            if (resp.warnings && resp.warnings.length) {
                toast('⚠️ 升级完成，但有 ' + resp.warnings.length + ' 项警告：' + resp.warnings.join('; '));
            }
        } else if (resp?.error || (resp?.errors && resp.errors.length)) {
            toast('⚠️ 更新失败');
        }
        // resp 为 null 时 api() 已 toast，不重复提示
    } catch(e) {
        // 升级请求路径上服务器有可能抢先重启，吞异常并继续走重启等待流程
        toast('🔄 服务正在重启，页面即将刷新...');
        restartScheduled = true;
    }
    if (!restartScheduled) {
        // 升级未触发重启（可能已是最新版本或更新失败），立即重新检查版本状态
        if (btn) { btn.remove(); }
        checkVersion();
        return;
    }
    // 后端 BackgroundTasks 已调度重启——等待 DOWN→UP 后强制刷新（清 cache + cache-bust）
    _waitForRestartAndReload(() => {
        if (btn) btn.textContent = '⬆️ 升级';
    });
}

async function loadCronStatus(isPoll = false) {
    if (!currentCompanyId) return;
    const data = await api('GET', '/api/agentbase/cron/today');
    if (!data) return;
    const {completed, pending, current_time} = data;

    // 更新全局顶部横幅
    const main = $('main-content');
    let bar = document.getElementById('guidance-bar');
    const barHtml = _renderGuidanceBar(current_time, completed, pending);
    if (bar) {
        bar.outerHTML = barHtml;
    } else {
        main.insertAdjacentHTML('afterbegin', barHtml);
    }

    // 在今日简报视图更新 cron 面板；在任意聊天视图追加 cron 输出
    const ct = currentChatContainer;
    if (!ct || currentView !== 'chat') return;
    const container = ct.querySelector('#chat-messages');
    if (!container) return;

    const isDailyView = currentChatContext === 'daily';

    // 只在今日简报视图更新 cron 面板
    if (isDailyView) {
        let panel = container.querySelector('.cron-panel');
        let panelHtml = `<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;">`;
        panelHtml += `<div style="font-weight:600;font-size:14px;">📋 今日任务清单 <span style="font-weight:400;color:var(--text-muted);font-size:12px;">${current_time}</span></div>`;
        panelHtml += `<div style="font-size:12px;color:${pending.length === 0 ? 'var(--accent-green)' : 'var(--accent)'};">${pending.length === 0 ? '✅ 全部完成' : '⏳ ' + pending.length + ' 项待处理'}</div>`;
        panelHtml += `</div>`;
        if (completed.length) {
            panelHtml += `<div style="font-size:12px;color:var(--accent-green);margin-bottom:6px;">已完成 (${completed.length})</div>`;
            for (const t of completed) {
                panelHtml += `<div style="display:flex;align-items:center;gap:8px;padding:3px 0;font-size:13px;"><span style="color:var(--accent-green);">✓</span><span style="font-weight:500;">${esc(t.name)}</span><span style="color:var(--text-muted);font-size:11px;">${t.time}</span></div>`;
            }
        }
        if (pending.length) {
            panelHtml += `<div style="font-size:12px;color:var(--text-secondary);margin:6px 0;">待处理 (${pending.length})</div>`;
            for (const t of pending) {
                panelHtml += _cronTaskLine(t);
            }
        }
        if (panel) {
            panel.innerHTML = panelHtml;
        } else {
            panel = document.createElement('div');
            panel.className = 'cron-panel';
            panel.style.cssText = 'background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius);padding:14px 16px;margin-bottom:12px;box-shadow:var(--shadow-sm);';
            panel.innerHTML = panelHtml;
            const emptyEl = container.querySelector('.empty-state');
            if (emptyEl) emptyEl.insertAdjacentElement('afterend', panel);
            else container.insertAdjacentElement('afterbegin', panel);
        }
    }

    // 增量追加已完成任务的 AI 输出（仅今日简报视图，避免干扰其他对话）
    if (isDailyView) {
        for (const t of completed) {
            if (!t.output || _shownCronOutputs.has(t.name)) continue;
            const msgDiv = document.createElement('div');
            msgDiv.className = 'message assistant msg-cron-output';
            // 截断 cron 输出中的冗余管理指令
            let cleanOutput = t.output || '';
            const truncIdx = cleanOutput.search(/管理命令参考|##?\s*管理命令|crontab\s*命令参考/i);
            if (truncIdx >= 0) cleanOutput = cleanOutput.substring(0, truncIdx).trimEnd();
            msgDiv.innerHTML = `<div class="bubble"><div class="bubble-meta"><span class="cron-badge" style="display:inline-block;padding:2px 8px;background:var(--primary);color:#fff;border-radius:999px;font-size:10px;margin-bottom:6px;">⏰ ${esc(t.name)} · ${esc(t.time)}</span></div><div class="cron-output-content">${DOMPurify.sanitize(marked.parse(cleanOutput))}</div></div>`;
            container.appendChild(msgDiv);
            _shownCronOutputs.add(t.name);
        }
        if (completed.length) {
            const nearBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 120;
            if (nearBottom) container.scrollTop = container.scrollHeight;
        }
    }
}

// ── 滚动到底部浮标（用户不在底部时始终显示）─────────

let _lastHintContainer = null;

function _ensureScrollHint(container) {
    // 同一个容器不重复绑定 scroll 监听
    if (container === _lastHintContainer) return;
    _lastHintContainer = container;
    container.style.position = 'relative';

    // 创建浮标（全局唯一，跟随活跃容器）
    const _getHint = () => {
        let h = document.getElementById('scroll-hint');
        if (!h) {
            h = document.createElement('div');
            h.id = 'scroll-hint';
            h.title = '回到底部';
            h.innerHTML = '▼';
            h.style.cssText = 'position:absolute;right:16px;bottom:80px;width:36px;height:36px;'
                + 'background:var(--primary);color:#fff;border-radius:50%;display:none;align-items:center;justify-content:center;'
                + 'cursor:pointer;font-size:16px;box-shadow:0 2px 8px rgba(0,0,0,0.2);z-index:10;transition:transform 0.15s;animation:pulseHint 2s infinite;';
            h.onmouseenter = () => h.style.transform = 'scale(1.1)';
            h.onmouseleave = () => h.style.transform = 'scale(1)';
            h.onclick = () => {
                const ct = currentChatContainer;
                const msg = ct?.querySelector('#chat-messages');
                if (msg) msg.scrollTop = msg.scrollHeight;
                h.style.display = 'none';
            };
        }
        return h;
    };

    const _update = () => {
        const nearBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 120;
        const hint = _getHint();
        if (nearBottom) {
            hint.style.display = 'none';
        } else {
            if (hint.parentElement !== container) {
                // 切换视图时把浮标移到新容器
                if (hint.parentElement) hint.remove();
                container.appendChild(hint);
            }
            hint.style.display = 'flex';
        }
    };

    container.addEventListener('scroll', _update, { passive: true });
    _update();
}

function _formatBytes(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1048576).toFixed(1) + ' MB';
}

const _IMAGE_EXTENSIONS = new Set(['png','jpg','jpeg','gif','bmp','webp','svg','ico']);

function _isImageFile(name) {
    const dot = name.lastIndexOf('.');
    return dot > -1 && _IMAGE_EXTENSIONS.has(name.slice(dot + 1).toLowerCase());
}

let _pendingDropFiles = [];

async function _collectFilesFromDataTransfer(dt) {
    const files = [];
    const entries = [];
    // 先尝试 webkitGetAsEntry（支持递归目录）
    if (dt.items && dt.items.length) {
        for (const item of dt.items) {
            if (item.kind === 'file') {
                const entry = item.webkitGetAsEntry ? item.webkitGetAsEntry() : null;
                if (entry) { entries.push(entry); } else { files.push(item.getAsFile()); }
            }
        }
    }
    // 回退到直接取 files
    if (!entries.length && dt.files && dt.files.length) {
        for (const f of dt.files) files.push(f);
    }

    // 递归读取目录
    async function _readEntry(entry, prefix) {
        if (entry.isFile) {
            const f = await new Promise(r => entry.file(r));
            Object.defineProperty(f, '_relPath', { value: prefix + entry.name, writable: true });
            files.push(f);
        } else if (entry.isDirectory) {
            const reader = entry.createReader();
            // readEntries 每次最多返回 ~100 条，需循环读取直到空
            const allEntries = [];
            while (true) {
                const batch = await new Promise(r => reader.readEntries(r));
                if (!batch.length) break;
                allEntries.push(...batch);
            }
            for (const e of allEntries) await _readEntry(e, prefix + entry.name + '/');
        }
    }
    for (const e of entries) await _readEntry(e, '');
    return files;
}

// 公司工作目录下的 9 个子目录名 — 与 agentbase/workspace.py _WORK_DIR_CATEGORIES 同步
let _WORK_SUBDIRS = ['documents'];

// 品牌与工作目录配置来自后端的 business.yaml（/api/branding）
async function loadBranding() {
    try {
        const resp = await fetch('/api/agentbase/branding');
        const data = await resp.json();
        if (data.title) {
            // 稳定标记 "AgentBase" 永远留在标题里：桌面端靠它匹配已打开的窗口
            document.title = data.title === 'AgentBase' ? 'AgentBase' : data.title + ' · AgentBase';
            const logo = document.getElementById('brand-logo');
            if (logo) logo.textContent = data.title;
        }
        if (Array.isArray(data.work_dirs) && data.work_dirs.length) {
            _WORK_SUBDIRS = data.work_dirs;
        }
        if (Array.isArray(data.onboarding_fields)) {
            _onboardingFields = data.onboarding_fields;
        }
    } catch (e) {
        console.warn('branding load failed', e);
    }
}

// 顶栏上传按钮：单个配置目录时直接传；多个目录时弹选择框
async function uploadChatFiles(fileList) {
    const files = Array.from(fileList || []);
    if (!files.length) return;
    try {
        if (_WORK_SUBDIRS.length === 1) {
            const result = await _uploadToWorkDir(files, _WORK_SUBDIRS[0]);
            toast(t('toast.imported', {n: result.uploaded, dir: _WORK_SUBDIRS[0]}));
        } else {
            _showDropModal(files);
        }
    } catch (e) {
        toast('上传失败：' + (e && e.message ? e.message : e));
    } finally {
        const input = document.getElementById('chat-file-input');
        if (input) input.value = '';
    }
}

// 上传文件到后端指定子目录
async function _uploadToWorkDir(files, subdir) {
    const form = new FormData();
    form.append('subdir', subdir);
    for (const f of files) {
        form.append('files', f, f._relPath || f.name);
    }
    // 走 api() 统一封装：拿到 120s 超时与 401 自愈。
    // 历史上这里裸 fetch 且无超时，上传卡死时确认按钮会永久 disabled。
    const resp = await api('POST', '/api/agentbase/upload-files', form);
    if (!resp) throw new Error(t('toast.import_fail'));
    return resp;
}

function _showDropModal(files) {
    _removeDynamicModals();
    _pendingDropFiles = files;

    const totalSize = files.reduce((s, f) => s + f.size, 0);
    const fileListHtml = files.slice(0, 20).map(f =>
        `<div class="file-item">${esc(f._relPath || f.name)} <span style="color:var(--text-muted)">${_formatBytes(f.size)}</span></div>`
    ).join('') + (files.length > 20 ? `<div class="file-item" style="color:var(--text-muted)">... 还有 ${files.length - 20} 个文件</div>` : '');

    const subdirOpts = _WORK_SUBDIRS.map(d => `<option value="${d}">${d}</option>`).join('');

    const backdrop = document.createElement('div');
    backdrop.className = 'modal-backdrop';
    backdrop.id = 'drop-file-modal';
    backdrop.onclick = function(e) { if (e.target === backdrop) backdrop.remove(); };
    backdrop.innerHTML = `
    <div class="modal" style="max-width:440px;width:95%;" onclick="event.stopPropagation()">
        <h3 style="margin:0 0 4px;">拖入 ${files.length} 个文件 (${_formatBytes(totalSize)})</h3>
        <div class="drop-file-list">${fileListHtml}</div>
        <div style="margin:10px 0;">
            <label style="font-size:13px;color:var(--text-muted);">存入工作目录：</label>
            <select id="drop-subdir-select" style="width:100%;padding:8px;border-radius:6px;border:1px solid var(--border);font-size:14px;margin-top:4px;">${subdirOpts}</select>
        </div>
        <div style="display:flex;gap:8px;">
            <button class="btn btn-primary" id="drop-confirm-btn" style="flex:1;">确认导入</button>
            <button class="btn" onclick="this.closest('.modal-backdrop').remove()">取消</button>
        </div>
    </div>`;
    document.body.appendChild(backdrop);

    backdrop.querySelector('#drop-confirm-btn').onclick = async function() {
        const subdir = backdrop.querySelector('#drop-subdir-select').value;
        const btn = backdrop.querySelector('#drop-confirm-btn');
        btn.disabled = true; btn.textContent = t('import.importing');
        try {
            const result = await _uploadToWorkDir(_pendingDropFiles, subdir);
            toast(t('toast.imported', {n: result.uploaded, dir: subdir}));
            const input = document.getElementById('msg-input');
            if (input) {
                // 检查是否有图片文件，提示 Agent 使用 vision 识别
                const hasImages = _pendingDropFiles.some(f => _isImageFile(f._relPath || f.name));
                let hint = `[已导入 ${result.uploaded} 个文件到「${result.target_path}」，请递归读取该目录下的所有文件并分析`;
                if (hasImages) {
                    hint += `。图片文件请使用 vision 工具识别文字内容`;
                }
                hint += ']\n\n';
                input.value = hint + input.value;
                input.focus();
            }
            backdrop.remove();
        } catch (e) {
            toast(t('toast.import_fail') + ': ' + e.message);
            btn.disabled = false; btn.textContent = t('import.confirm');
        }
    };
}

function setupDropZone() {
    const overlay = document.getElementById('drop-overlay');
    let _dragCounter = 0;

    function handleDragOver(e) {
        e.preventDefault(); e.stopPropagation();
    }

    function handleDragEnter(e) {
        e.preventDefault(); e.stopPropagation();
        _dragCounter++;
        if (overlay) overlay.classList.add('show');
    }

    function handleDragLeave(e) {
        e.preventDefault(); e.stopPropagation();
        _dragCounter--;
        if (_dragCounter <= 0) { _dragCounter = 0; if (overlay) overlay.classList.remove('show'); }
    }

    async function handleDrop(e) {
        e.preventDefault(); e.stopPropagation();
        _dragCounter = 0;
        if (overlay) overlay.classList.remove('show');
        // 不拦截拖到已有弹窗上的文件（如用户在库弹窗上误拖）
        if (e.target.closest('.modal-backdrop')) return;
        const dt = e.dataTransfer;
        if (!dt || !dt.files.length) return;
        const files = await _collectFilesFromDataTransfer(dt);
        if (!files.length) return;
        _showDropModal(files);
    }

    document.body.addEventListener('dragover', handleDragOver, false);
    document.body.addEventListener('dragenter', handleDragEnter, false);
    document.body.addEventListener('dragleave', handleDragLeave, false);
    document.body.addEventListener('drop', handleDrop, false);

    document.addEventListener('paste', async function(e) {
        if (!e.clipboardData || !e.clipboardData.files.length) return;
        if (e.target.tagName === 'TEXTAREA' && e.target.id === 'msg-input') {
            e.preventDefault();
            const files = await _collectFilesFromDataTransfer(e.clipboardData);
            if (!files.length) return;
            _showDropModal(files);
        }
    });
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setupDropZone);
} else {
    setupDropZone();
}

async function clearChat() {
    const ct = currentChatContainer;
    if (!ct) return;
    ct.querySelector('#chat-messages').innerHTML = `<div class="empty-state"><div class="empty-icon">💬</div><h2>${esc(currentChatName)}</h2></div>`;
}

// ═════════════════════ CHAT MESSAGES ═════════════════════
function addMsg(role, content, files, save, convId) {
    const ct = currentChatContainer;
    if (!ct) return;
    const container = ct.querySelector('#chat-messages');
    // Remove empty state
    const emptyEl = container.querySelector('.empty-state');
    if (emptyEl) emptyEl.remove();

    const div = document.createElement('div');
    div.className = `message ${role}`;
    const avatar = document.createElement('div');
    avatar.className = 'msg-avatar';
    avatar.textContent = role === 'user' ? '👤' : '🤖';
    const body = document.createElement('div');
    body.className = 'msg-body';
    const raw = marked.parse(content || '');
    body.innerHTML = DOMPurify.sanitize(raw, {
        ALLOWED_TAGS: ['p','br','strong','em','b','i','ul','ol','li','h1','h2','h3','h4','h5','h6',
            'blockquote','code','pre','a','table','thead','tbody','tr','th','td','hr','span','div','img'],
        ALLOWED_ATTR: ['href','target','class','id','style','src','alt','width','height'],
    });
    if (files && files.length) {
        const s = document.createElement('div'); s.className = 'sources';
        s.innerHTML = '<div class="sources-title">📄 '+(currentLang==='en'?'References':'参考文件')+'</div>' + files.map(f => '<div>📎 '+esc(f.file||f)+'</div>').join('');
        body.appendChild(s);
    }
    div.appendChild(avatar); div.appendChild(body);

    // AI 回复右侧加「📋 复制」按钮，点击写入剪贴板
    if (role === 'assistant' && content) {
        const copyBtn = document.createElement('button');
        copyBtn.textContent = '📋';
        copyBtn.title = currentLang==='en'?'Copy to clipboard':'复制到剪贴板';
        copyBtn.style.cssText = 'position:absolute;top:6px;right:8px;background:none;border:1px solid #D1D5DB;border-radius:4px;padding:2px 6px;font-size:12px;cursor:pointer;color:#9CA3AF;opacity:0.5;transition:opacity 0.15s;';
        copyBtn.onmouseenter = function() { this.style.opacity = '1'; };
        copyBtn.onmouseleave = function() { this.style.opacity = '0.5'; };
        copyBtn.onclick = function(e) {
            e.stopPropagation();
            navigator.clipboard.writeText(content).then(function() {
                copyBtn.textContent = '✅'; setTimeout(function() { copyBtn.textContent = '📋'; }, 1500);
            }).catch(function() {
                copyBtn.textContent = '❌'; setTimeout(function() { copyBtn.textContent = '📋'; }, 1500);
            });
        };
        div.style.position = 'relative';
        div.appendChild(copyBtn);

        // 评分按钮 — 仅传入 convId 时显示（避免全局变量竞态）
        const convIdForRating = convId;
        if (convIdForRating) {
            const ratingDiv = document.createElement('div');
            ratingDiv.className = 'msg-rating';
            ratingDiv.style.cssText = 'display:flex;align-items:center;gap:6px;margin-top:8px;padding-top:8px;border-top:1px solid var(--border-light);';
            ratingDiv.innerHTML = '<span style="font-size:11px;color:var(--text-muted);">'+(currentLang==='en'?'Rate this reply: ':'评价此回复：')+'</span>'
                + '<button class="rating-btn" data-r="👍" style="border:1px solid #D1D5DB;border-radius:4px;padding:2px 8px;font-size:13px;cursor:pointer;background:#fff;">👍</button>'
                + '<button class="rating-btn" data-r="👎" style="border:1px solid #D1D5DB;border-radius:4px;padding:2px 8px;font-size:13px;cursor:pointer;background:#fff;">👎</button>';
            body.appendChild(ratingDiv);

            ratingDiv.querySelectorAll('.rating-btn').forEach(function(btn) {
                btn.addEventListener('click', async function(e) {
                    e.stopPropagation();
                    var rVal = this.dataset.r === '👍' ? 4 : 2;
                    await api('POST', '/api/agentbase/conversations/' + convIdForRating + '/rate', { rating: rVal, feedback: '' });
                    ratingDiv.innerHTML = '<span style="font-size:11px;color:var(--accent-green);">✅ '+(currentLang==='en'?'Thanks for feedback':'感谢反馈')+'</span>';
                });
            });
        }
    }

    container.appendChild(div);
    // 只在用户发消息或新 AI 回复流式到达时自动滚到底部
    // 历史加载和手动浏览不强制滚动
}

async function loadChatHistory() {
    if (!currentCompanyId) return;
    const ct = currentChatContainer;
    if (!ct) return;
    // 按 context 过滤，避免不同主题的对话混在一起
    const ctx = encodeURIComponent(currentChatContext || '');
    const params = currentLibraryId
        ? `?library_id=${currentLibraryId}&limit=30`
        : `?context=${ctx}&limit=30`;
    const data = await api('GET', `/api/agentbase/conversations${params}`);
    if (!data || !data.length) return;
    const container = ct.querySelector('#chat-messages');
    if (!container) return;
    // Remove empty state
    const emptyEl = container.querySelector('.empty-state');
    if (emptyEl) emptyEl.remove();

    container.innerHTML = '';
    data.reverse().forEach(c => {
        let filesRead = [];
        try { filesRead = c.files_read ? JSON.parse(c.files_read) : []; } catch(e) { filesRead = []; }
        if (c.query) addMsg('user', c.query, filesRead, false);
        if (c.response) addMsg('assistant', c.response, null, false);
    });
    // 加载历史后直接滚动到底部（最新消息）
    container.scrollTop = container.scrollHeight;
}

// ═════════════════════ SSE STREAMING ═════════════════════
const TOOL_NAMES = {
    read_file:'📄 读取文件',list_files:'📂 列出文件',file_extract:'📋 提取文档',
    web_search:'🌐 搜索',web_fetch:'📥 抓取',memory_recall:'🧠 回忆',
    memory_retain:'💾 保存',execute_code:'💻 代码',terminal:'🖥️ 终端',
    delegate_task:'🤖 委派',vision:'👁️ 图像',skill_load:'📦 技能',
};
function fmtTool(name) { return TOOL_NAMES[name] || `🔧 ${name.replace(/_/g,' ')}`; }
function fmtArg(v) { return typeof v==='string' ? (v.length>80?v.slice(0,77)+'...':v) : JSON.stringify(v).slice(0,80); }

async function sendMsg() {
    if (!currentCompanyId) { toast('请先选择 workspace'); return; }
    const ct = currentChatContainer;
    if (!ct) { toast('请先点击一个聊天入口'); return; }
    const input = ct.querySelector('#msg-input');
    const query = input.value.trim();
    if (!query) return;

    // 本地触发：显示工作清单 → 拉取 cron 状态，不调 Agent
    if (query === '显示工作清单' || query === '工作清单' || query === '今日任务') {
        addMsg('user', query, null);
        input.value = '';
        input.style.height = '24px';  // 复位输入框高度
        await loadCronStatus();
        return;
    }

    addMsg('user', query, null);
    input.value = '';
    input.style.height = '24px';  // 复位输入框高度
    const sendBtn = ct.querySelector('#send-btn');
    if (sendBtn) sendBtn.disabled = true;

    // 用户可主动取消 SSE 流（替代原硬性 10 分钟超时）
    // 网站诊断等复杂 skill 可能需要 >10 分钟，依赖 SSE 心跳保活即可
    // 归属记账：让切换公司时能统一作废这条流（否则旧流会写进新公司的窗口）
    const ownerCid = currentCompanyId;
    const streamCtl = _beginChatStream(ownerCid);
    // 切公司后旧流的输出必须丢弃：addMsg 写的是全局 currentChatContainer
    function deliver(role, text, save, convId) {
        if (!_chatStreamBelongsTo(ownerCid)) return;
        addMsg(role, text, null, save, convId);
    }
    const stopBtn = ct.querySelector('#stop-btn');
    if (stopBtn) {
        stopBtn.classList.remove('hidden');
        stopBtn.onclick = () => streamCtl.abort();
    }
    // 计时器：显示已用时，让用户知道仍在工作
    const elapsedTimer = setInterval(() => {
        const sec = Math.floor((Date.now() - startMs) / 1000);
        const m = Math.floor(sec / 60), s = sec % 60;
        const tEl = progDiv.querySelector('.elapsed');
        if (tEl) tEl.textContent = `⏱ ${m}:${s.toString().padStart(2,'0')}`;
    }, 1000);
    const startMs = Date.now();

    const container = ct.querySelector('#chat-messages');
    const progDiv = document.createElement('div');
    progDiv.className = 'message assistant';
    const pid = 'prog-' + Date.now();
    progDiv.id = pid;
    progDiv.innerHTML = '<div class="msg-avatar">🤖</div><div class="msg-body"><div class="thinking-msg">💭 '+t('misc.thinking')+'</div><div class="elapsed" style="font-size:11px;color:var(--text-muted);margin-top:4px;"></div></div>';
    container.appendChild(progDiv);
    container.scrollTop = container.scrollHeight;

    const toolEls = {};
    let progressDiv = null;
    let responseText = '';
    let responseConvId = null;
    let sawDone = false;  // 服务端是否发过 done（区分「服务端没内容」与「连接断了」）
    _currentConvId = null;

    function ensureProgress() {
        if (!progressDiv) { progressDiv = document.createElement('div'); progressDiv.className = 'tool-progress'; progDiv.appendChild(progressDiv); }
        return progressDiv;
    }
    function addToolItem(tcId, name, status, detail) {
        const div = ensureProgress();
        const el = document.createElement('div');
        el.className = `tool-item ${status}`; el.id = `tool-${tcId}`;
        // 安全构建 DOM：textContent 防止工具参数中的 HTML 注入
        const icon = document.createElement('span');
        icon.className = 'tool-icon';
        icon.textContent = status === 'running' ? '◌' : status === 'done' ? '✓' : '✗';
        const body = document.createElement('div');
        body.className = 'tool-body';
        const nameEl = document.createElement('div');
        nameEl.className = 'tool-name';
        nameEl.textContent = fmtTool(name);
        const detailEl = document.createElement('div');
        detailEl.className = 'tool-detail';
        detailEl.textContent = detail || '';
        body.appendChild(nameEl);
        body.appendChild(detailEl);
        el.appendChild(icon);
        el.appendChild(body);
        div.appendChild(el); container.scrollTop = container.scrollHeight;
        toolEls[tcId] = el;
    }
    function updateTool(tcId, status, detail) {
        const el = toolEls[tcId]; if (!el) return;
        el.className = `tool-item ${status}`;
        el.querySelector('.tool-icon').textContent = status==='running'?'◌':status==='done'?'✓':'✗';
        if (detail) el.querySelector('.tool-detail').textContent = detail;
        container.scrollTop = container.scrollHeight;
    }

    try {
        const r = await fetch('/api/agentbase/chat/stream', {
            method:'POST',
            headers:{'Content-Type':'application/json','X-Hermes-Session-Token':TOKEN,'X-Workspace-ID':String(currentCompanyId)},
            body:JSON.stringify({library_id:currentLibraryId,customer_id:currentCustomerId,query,context:currentChatContext,language:currentLang}),
            signal:streamCtl.signal,
        });
        if (!r.ok) { progDiv.remove(); deliver('assistant', `⚠️ 请求失败 (${r.status})`); sendBtn.disabled = false; return; }

        const reader = r.body.getReader(); const decoder = new TextDecoder();
        let buffer = '';
        while (true) {
            const {done,value} = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, {stream:true});
            const lines = buffer.split('\n'); buffer = lines.pop()||'';
            let eventType='',dataStr='';
            for (const raw of lines) {
                const line = raw.replace(/\r$/,'');
                if (line.startsWith('event: ')) { eventType=line.slice(7).trim(); continue; }
                if (line.startsWith('data: ')) { dataStr=line.slice(6).trimStart(); continue; }
                if (line===''&&eventType&&dataStr) {
                    let data;
                    try { data = JSON.parse(dataStr); } catch(e) { eventType='';dataStr='';continue; }
                    switch(eventType) {
                    case 'tool_start': addToolItem(data.tool_call_id,data.name,'running',data.args?Object.entries(data.args).map(([k,v])=>`${k}=${fmtArg(v)}`).join(', '):''); break;
                    case 'tool_complete': updateTool(data.tool_call_id,'done',data.result_preview||'完成'); break;
                    case 'thinking':
                        if (!progDiv.querySelector('.thinking-msg')) { const t=document.createElement('div'); t.className='thinking-msg'; t.style.cssText='font-size:12px;color:var(--text-muted);padding:4px 0;'; t.textContent='💭 '+(data.message||'思考中...'); progDiv.appendChild(t); }
                        break;
                    case 'analysis_gate': {
                        // 不通过时正文会给出完整原因，这里只做一行进度提示。
                        const files = (data.files||[]).length;
                        const skipped = (data.skipped||[]);
                        const note = document.createElement('div'); note.className='thinking-msg';
                        const ok = data.status === 'complete';
                        note.style.cssText = 'font-size:12px;color:'+(ok?'var(--text-muted)':'var(--accent-red)')+';padding:4px 0;';
                        note.textContent = (ok ? '✓ 已完整读取 ' : '⚠ 完整读取未通过，已完整读取 ') + files + ' 个文件'
                            + (skipped.length ? '；未纳入：' + skipped.map(function(s){return s.file;}).join(', ') : '');
                        // 能力边界如实披露：本机无法逐 Sheet/逐页核验时必须说出来
                        if (data.coverage_note) {
                            const cap = document.createElement('div');
                            cap.className = 'thinking-msg';
                            cap.style.cssText = 'font-size:12px;color:var(--text-muted);padding:2px 0 4px;';
                            cap.textContent = 'ℹ️ ' + data.coverage_note;
                            progDiv.appendChild(note);
                            progDiv.appendChild(cap);
                            break;
                        }
                        progDiv.appendChild(note);
                        break;
                    }
                    case 'response': responseText = data.text||''; responseConvId = data.conversation_id || null; _currentConvId = data.conversation_id || null; break;
                    case 'done': sawDone = true; break;  // 服务端正常收尾的标记（用于区分「服务端没内容」与「连接断了」）
                    case 'error': progDiv.innerHTML=`<div class="msg-avatar" style="background:var(--accent-red);color:#fff;">⚠</div><div class="msg-body" style="color:var(--accent-red);">${esc(data.message)}</div>`; sendBtn.disabled = false; return;
                    }
                    eventType='';dataStr='';
                }
            }
        }
        progDiv.remove();
        const outcome = _sseStreamOutcome(!!responseText, sawDone);
        if (outcome.kind === 'response') deliver('assistant', responseText, true, responseConvId);
        else deliver('assistant', outcome.message, true, null);
    } catch(e) {
        progDiv.remove();
        _currentConvId = null;
        // AbortError 分两种：用户主动停止（应提示）与切公司导致的作废（不该再往页面写）
        if (e.name==='AbortError') deliver('assistant','🛑 已停止生成。');
        else deliver('assistant',`网络错误：${e.message}`);
    } finally {
        clearInterval(elapsedTimer);
        _currentConvId = null;
        _endChatStream(streamCtl);
        if (stopBtn) { stopBtn.classList.add('hidden'); stopBtn.onclick = null; }
    }
    sendBtn.disabled = false;
}

// ═════════════════════ CUSTOMERS VIEW ═════════════════════
let allCustomers = [];
// ── Customer Detail Slide Panel ────────────────────────────────
// ── Order List / Modal ─────────────────────────────────────

// ── Customer CRUD Modal ──────────────────────────────────────
// ── 批量导入 ───────────────────────────────────────────
// ── 下载管理表格 Excel ──────────────────────────────
// ── 下载 CSV 模板（需携带 auth header） ─────────────

async function renderTasksViewInto(container) {
    container.innerHTML = `
    <div class="panel-view" style="display:flex;flex-direction:column;height:100%;">
        <div class="panel-topbar">
            <h2>⏰ 定时任务</h2>
            <div class="panel-topbar-actions">
                <button class="btn" onclick="loadActiveCronJobs()">刷新</button>
            </div>
        </div>
        <div class="panel-body" style="overflow-y:auto;padding:16px 20px;">
            <div id="tasks-body" style="color:var(--text-muted);font-size:12px;">加载中...</div>
        </div>
    </div>`;
    await loadActiveCronJobs();
}

function runSingleTask(taskName, prompt) {
    if (!currentCompanyId) { toast('请先选择 workspace'); return; }
    navToView('chat', 'general', taskName);
    setTimeout(() => {
        const ct = currentChatContainer;
        const input = ct ? ct.querySelector('#msg-input') : null;
        if (input) {
            input.value = prompt;
            sendMsg();
        }
    }, 300);
}

async function loadActiveCronJobs() {
    if (!currentCompanyId) return;
    const data = await api('GET', '/api/agentbase/cron/jobs');
    const grid = document.getElementById('tasks-body');
    if (!grid) return;
    if (!data || !data.length) {
        grid.innerHTML = '<div style="color:var(--text-muted);font-size:12px;padding:12px;">暂无定时任务。可通过 Hermes cron 创建。</div>';
        return;
    }
    grid.innerHTML = data.map(j => `
        <div class="task-card">
            <div class="task-card-header">
                <span class="task-card-name">${esc(j.name)}</span>
                <span style="font-size:10px;color:${j.enabled ? 'var(--accent-green)' : 'var(--text-muted)'};">${j.enabled ? '● 运行中' : '○ 已暂停'}</span>
            </div>
            <div class="task-card-schedule">🕐 ${esc(j.schedule)}</div>
            ${j.next_run ? `<div style="font-size:11px;color:var(--accent-green);margin-bottom:6px;">▶ 下次执行：${esc(j.next_run)}</div>` : ''}
            <div class="task-card-actions">
                <button onclick="runActiveJob(${escJs(j.id)})">▶ 立即执行</button>
            </div>
        </div>
    `).join('');
}

function runActiveJob(jobId) {
    if (!currentCompanyId) return;
    navToView('chat', 'general', '立即执行任务');
    setTimeout(() => {
        const ct = currentChatContainer;
        const input = ct ? ct.querySelector('#msg-input') : null;
        if (input) {
            input.value = `请使用 cronjob 工具手动触发一次任务 ID ${jobId}，将结果输出到当前对话。`;
            sendMsg();
        }
    }, 300);
}

function renderDirectoryViewInto(container) {
    const coName = currentCompanyId ? (workspaces.find(c => c.id === currentCompanyId)?.name || '') : '';
    container.innerHTML = `
        <div class="panel-topbar">
            <h2>📂 数据目录${coName ? `<span style="margin-left:10px;padding:3px 10px;background:rgba(59,130,246,0.08);color:var(--primary);border-radius:999px;font-size:12px;font-weight:500;">🏢 ${esc(coName)}</span>` : ''}</h2>
            <div class="panel-topbar-actions">
                <button class="btn" onclick="toast('功能开发中：将在文件管理器中打开')">📂 打开目录</button>
            </div>
        </div>
        <div class="panel-body" style="display:flex;gap:16px;">
            <div style="width:320px;flex-shrink:0;">
                <div class="dir-tree" id="dir-tree">
                    <div class="loading-row"><div class="spinner"></div>加载目录结构...</div>
                </div>
            </div>
            <div style="flex:1;">
                <div class="file-preview" id="file-preview">
                    <div style="color:var(--text-muted);text-align:center;padding:40px;">👈 点击左侧文件查看内容</div>
                </div>
            </div>
        </div>`;
    loadDirectoryTree();
}

async function loadDirectoryTree() {
    // Build tree from known structure since we can't browse server filesystem via API
    // Show the standard ~/.agentbase/ layout
    const co = workspaces.find(c => c.id === currentCompanyId);
    const slug = co?.slug || 'default';

    const tree = [
        {name:'workspace-profile.md',icon:'📄',type:'file'},
        {name:'products.md',icon:'📄',type:'file'},
        {name:'agent-identity.md',icon:'📄',type:'file'},
        {name:'business-scope.md',icon:'📄',type:'file'},
        {name:'competitors.md',icon:'📄',type:'file'},
        {name:'certifications.md',icon:'📄',type:'file'},
        {name:'marketing-strategy.md',icon:'📄',type:'file'},
        {name:'sales-playbook.md',icon:'📄',type:'file'},
        {name:'libraries/',icon:'📂',type:'dir',children:[
            {name:'{lib-slug}/',icon:'📂',type:'dir',children:[
                {name:'index.md',icon:'📄',type:'file'},
                {name:'changelog.md',icon:'📄',type:'file'},
                {name:'metadata.md',icon:'📄',type:'file'},
            ]}
        ]},
        {name:'clients/',icon:'📂',type:'dir',children:[
            {name:'{client-slug}/',icon:'📂',type:'dir',children:[
                {name:'profile.md',icon:'📄',type:'file'},
                {name:'contacts.md',icon:'📄',type:'file'},
                {name:'interactions.md',icon:'📄',type:'file'},
                {name:'requirements.md',icon:'📄',type:'file'},
                {name:'quotes.md',icon:'📄',type:'file'},
                {name:'orders.md',icon:'📄',type:'file'},
                {name:'notes.md',icon:'📄',type:'file'},
            ]}
        ]},
    ];

    $('dir-tree').innerHTML = `<div style="font-weight:600;margin-bottom:8px;color:var(--text-secondary);">~/.agentbase/${esc(slug)}/</div>` +
        renderTreeItems(tree, 0);

    // 委托事件：文件树点击（避免 onclick 中直接拼接文件名导致 XSS）
    $('dir-tree').onclick = function(e) {
        var el = e.target.closest && e.target.closest('[data-file-click]');
        if (el && el.getAttribute('data-file-click') === 'preview') {
            previewFile(el.getAttribute('data-file-name'));
        }
    };

    // Also load agent identity preview if available
    const identity = await api('GET', `/api/agentbase/workspaces/${currentCompanyId}/agent-identity`);
    if (identity?.agent_identity_md) {
        $('file-preview').innerHTML = `<div class="file-preview-header"><h3>📄 agent-identity.md</h3></div>
            <div>${DOMPurify.sanitize(marked.parse(identity.agent_identity_md), {ALLOWED_TAGS:['p','br','strong','em','ul','ol','li','h1','h2','h3','blockquote','code','pre','a','table','thead','tbody','tr','th','td','hr','span'],ALLOWED_ATTR:['href','target','class']})}</div>`;
    }
}

function renderTreeItems(items, depth) {
    return items.map(item => {
        const indent = depth * 20;
        const attrs = item.type === 'file'
            ? `data-file-name="${esc(item.name)}" data-file-click="preview"`
            : '';
        return `<div class="dir-tree-item ${item.type}" style="padding-left:${indent}px;" ${attrs}>
            <span class="tree-icon">${item.icon}</span> ${esc(item.name)}
        </div>` + (item.children ? renderTreeItems(item.children, depth+1) : '');
    }).join('');
}

function previewFile(name) {
    $('file-preview').innerHTML = `<div class="file-preview-header"><h3>📄 ${esc(name)}</h3></div>
        <p style="color:var(--text-muted);">文件内容通过 Agent 对话中的 read_file 工具访问。在侧边栏中选择对应功能入口后，Agent 会自动读取相关文件。</p>`;
}

// ═════════════════════ HISTORY VIEW ═════════════════════
async function renderHistoryViewInto(container) {
    const coName = currentCompanyId ? (workspaces.find(c => c.id === currentCompanyId)?.name || '') : '';
    container.innerHTML = `
        <div class="panel-topbar">
            <h2>💬 ${t('history.title')}${coName ? '<span style="margin-left:10px;padding:3px 10px;background:rgba(59,130,246,0.08);color:var(--primary);border-radius:999px;font-size:12px;font-weight:500;">🏢 '+esc(coName)+'</span>' : ''}</h2>
            <div class="panel-topbar-actions">
                <input class="panel-search" id="conv-search" aria-label="搜索对话" placeholder="${currentLang==='en'?'Search conversations...':'搜索对话...'}" oninput="filterConversations()">
            </div>
        </div>
        <div class="panel-body">
            <div class="quality-bar" id="quality-bar" style="display:none;"></div>
            <div class="conv-list" id="conv-list">
                <div class="loading-row"><div class="spinner"></div>加载对话记录...</div>
            </div>
        </div>`;
    await loadConversations();
    loadQualityStats();
}

// 质量概览（rating 闭环）：近 30 天评分总数 / 均分 / 低分最多的技能
async function loadQualityStats() {
    const bar = $('quality-bar');
    if (!bar || !currentCompanyId) return;
    const s = await api('GET', '/api/agentbase/conversations/quality-stats?days=30');
    // 无评分数据时不占位（新用户/未评分公司）
    if (!s || !s.total_rated) { bar.style.display = 'none'; return; }
    // by_skill 已按「低分优先」排序，取第一个有低分的技能作为待改进项
    const worst = (s.by_skill || []).find(x => x.low_count > 0);
    let txt = `📊 ${t('quality.rated')} ${s.total_rated} · ${t('quality.avg')} ${s.avg_rating}`;
    if (worst) txt += ` · ${t('quality.worst')} ${worst.skill} (👎×${worst.low_count})`;
    // 用 textContent 赋值，避免技能名/上下文注入 HTML
    bar.textContent = txt;
    bar.style.display = 'block';
}

let allConversations = [];
async function loadConversations() {
    if (!currentCompanyId) return;
    allConversations = await api('GET', '/api/agentbase/conversations?limit=100') || [];
    renderConversationsList(allConversations);
}

function renderConversationsList(data) {
    const container = $('conv-list');
    if (!data.length) {
        container.innerHTML = '<div class="empty-state"><div class="empty-icon">💬</div><h2>'+t('history.no_records')+'</h2></div>';
        return;
    }
    container.innerHTML = data.map(c => `
        <div class="conv-list-item" style="display:flex;align-items:flex-start;gap:8px;">
            <div style="flex:1;min-width:0;" onclick="showConversationDetail(${c.id})">
                <div class="conv-meta">
                    <span>${esc((c.created_at||'').slice(0,16))}</span>
                    ${c.library_id ? '<span style="background:#EFF6FF;color:var(--primary);padding:2px 6px;border-radius:4px;">📁 '+t('nav.docs')+'</span>' : ''}
                </div>
                <div class="conv-q">${esc(c.query||'').slice(0,100)}</div>
                <div class="conv-a">${esc(c.response||'').slice(0,150)}</div>
            </div>
            <button class="btn-xs" style="color:var(--accent-red);border-color:var(--accent-red);flex-shrink:0;margin-top:2px;"
                onclick="event.stopPropagation();deleteConversation(${c.id})" title="${t('hist.delete_title')}">🗑</button>
        </div>
    `).join('');
}

async function deleteConversation(cid) {
    if (!confirm(t('hist.confirm_delete'))) return;
    const r = await api('DELETE', `/api/agentbase/conversations/${cid}`);
    if (r && r.ok) {
        toast(t('hist.deleted'));
        allConversations = allConversations.filter(c => c.id !== cid);
        renderConversationsList(allConversations);
    } else {
        toast(r?.detail || t('hist.delete_fail'));
    }
}

function filterConversations() {
    const search = ($('conv-search')?.value||'').toLowerCase();
    if (!search) { renderConversationsList(allConversations); return; }
    const filtered = allConversations.filter(c =>
        (c.query||'').toLowerCase().includes(search) || (c.response||'').toLowerCase().includes(search)
    );
    renderConversationsList(filtered);
}

function showConversationDetail(cid) {
    const c = allConversations.find(x => x.id === cid);
    if (!c) return;

    // 从对话记录读取真实的 context；旧数据无 context 则回退到旧逻辑
    if (c.context) {
        currentChatContext = c.context;
    } else if (c.library_id) {
        currentChatContext = 'docs';
    } else {
        currentChatContext = 'daily';
    }
    currentLibraryId = c.library_id || null;
    currentChatName = '对话详情';
    currentCustomerId = null;

    // 强制重建目标视图
    const cacheKey = 'chat-' + currentChatContext;
    if (viewCache[cacheKey]) {
        viewCache[cacheKey].element.remove();
        delete viewCache[cacheKey];
    }

    navToView('chat', currentChatContext, currentChatName);

    // 用 MutationObserver 等 DOM 渲染完成后再拉取数据
    const tryLoad = () => {
        const ct = currentChatContainer;
        if (!ct || !ct.querySelector('#chat-messages')) {
            // DOM 还没到位，再等一轮
            requestAnimationFrame(tryLoad);
            return;
        }
        loadChatHistory();
    };
    requestAnimationFrame(tryLoad);
}

// ═════════════════════ ONBOARDING GUIDE ═════════════════════

function showOnboardingGuide() {
    // 通用引导：打开对话视图并显示由 business.yaml 驱动的字段向导
    navToView('chat', 'general', '对话');
    setTimeout(function() { showWizardInLeadView(); }, 300);
}

function restartOnboarding() {
    try { localStorage.removeItem('_onboarding_completed'); } catch(_) {}
    showOnboardingGuide();
}

// ═════════════════════ WORKSPACE MANAGEMENT ═════════════════════
function showAddCompanyModal() {
    switchModalTab('tab-workspaces');
    showModal('workspace-modal');
    loadCompanyListUI();
}

function switchModalTab(tab) {
    $('tab-workspaces').classList.toggle('hidden', tab !== 'tab-workspaces');
    $('tab-identity').classList.toggle('hidden', tab !== 'tab-identity');
    $('tab-btn-workspaces').classList.toggle('active', tab === 'tab-workspaces');
    $('tab-btn-identity').classList.toggle('active', tab === 'tab-identity');
    if (tab === 'tab-identity') loadIdentityForCurrentCompany();
}

async function loadCompanies() {
    const prev = currentCompanyId;
    workspaces = await api('GET', '/api/agentbase/workspaces') || [];
    const sel = $('workspace-select');
    sel.innerHTML = '<option value="">— 选择公司 —</option>' +
        workspaces.map(c => `<option value="${c.id}" ${c.id===prev?'selected':''}>${esc(c.name)}</option>`).join('');
    if (prev && !workspaces.find(c=>c.id===prev)) {
        // Previously selected workspace was deleted
        currentCompanyId = null;
        saveState();
    }
}

function loadCompanyListUI() {
    const container = $('workspace-list-ui');
    if (!workspaces.length) {
        container.innerHTML = '<p style="color:var(--text-muted);font-size:13px;">暂无公司，请下方创建。</p>';
        return;
    }
    container.innerHTML = workspaces.map(c => `
        <div style="display:flex;align-items:center;gap:8px;padding:8px 0;border-bottom:1px solid var(--border-light);">
            <div style="flex:1;"><div style="font-weight:600;font-size:13px;">${esc(c.name)}</div>
            <div style="font-size:11px;color:var(--text-muted);">${esc(c.slug)} · ${c.contact_email ? ' · ' + esc(c.contact_email) : ''}</div></div>
            <button class="btn btn-danger btn-xs" onclick="deleteCompany(${c.id})">删除</button>
        </div>`).join('');
}

function autoSlug() {
    const name = $('co-name').value.trim();
    const slugEl = $('co-slug');
    if (!name) {
        slugEl.value = '';
        slugEl.placeholder = '自动生成';
        slugEl.style.color = 'var(--text-muted)';
        return;
    }
    // 前端实时生成 slug 预览（与后端的 _slugify 逻辑一致）
    let s = name.toLowerCase()
        .replace(/[^\w\s-]/g, '')
        .replace(/[\s_]+/g, '-')
        .replace(/--+/g, '-')
        .replace(/^-|-$/g, '') || 'workspace';
    slugEl.value = s;
    slugEl.style.color = '';
}

async function createCompany() {
    const name = $('co-name').value.trim();
    if (!name) { toast('请填写公司名称'); return; }
    const slug = $('co-slug').value.trim();
    const body = {name};
    if (slug) body.slug = slug;
    ['contact_name','contact_email','website'].forEach(f => {
        const elId = 'co-' + f.replace(/_/g, '-');
        const v = (document.getElementById(elId)?.value || '').trim();
        if (v) body[f] = v;
    });
    const r = await api('POST', '/api/agentbase/workspaces', body);
    if (r?.id) {
        if (r.work_dir_is_new === false) {
            toast(`桌面目录已存在，已创建为：${r.work_dir.split('/').pop()}`);
        } else {
            toast('公司创建成功，桌面工作目录已就绪');
        }
        ['co-name','co-slug','co-contact-name','co-contact-email','co-website'].forEach(id=>$(id).value='');
        await loadCompanies();
        onCompanyChange(r.id);
    } else toast(r?.detail||'创建失败');
}

async function deleteCompany(id) {
    if (!confirm('确定停用该公司？数据将保留 30 天后自动清理。')) return;
    const r = await api('DELETE', `/api/agentbase/workspaces/${id}`);
    if (r?.ok) { toast('已删除'); if (currentCompanyId===id) onCompanyChange(''); await loadCompanies(); loadCompanyListUI(); }
    else toast(r?.detail||'删除失败');
}

async function onCompanyChange(cid) {
    // 清空视图缓存
    for (const key in viewCache) {
        viewCache[key].element.remove();
        delete viewCache[key];
    }
    // 中止进行中的新手引导流，防止 reader 泄漏
    if (_onboardingStreamCtl) { _onboardingStreamCtl.abort(); _onboardingStreamCtl = null; }
    // 中止进行中的聊天流：否则它会继续消耗 token，且结束后把回复写进新公司的会话窗口
    _abortChatStream();
    // 清空 cron 输出记录，防止跨公司污染
    _shownCronOutputs = new Set();
    if (cid) {
        const newCid = parseInt(cid);
        // 先更新前端状态（让后续 API 调用带上正确的 X-Workspace-ID header）
        currentCompanyId = newCid;
        // 通知后端切换 session 绑定（旧 cid 会触发 403，因此 _enforce_workspace_binding 需放行 /switch 端点）
        try { await api('POST', '/api/agentbase/workspaces/' + newCid + '/switch'); } catch(_) {}
        saveState();
        // 首个公司 + 引导未完成 → 显示新手引导
        if (workspaces.length === 1 && !isOnboardingCompleted()) {
            showOnboardingGuide();
            return;
        }
        navToView('chat', 'daily', '今日简报');
    } else {
        currentCompanyId = null;
        saveState();
        renderNoCompanyPage();
    }
}

async function loadIdentityForCurrentCompany() {
    if (!currentCompanyId) return;
    const r = await api('GET', `/api/agentbase/workspaces/${currentCompanyId}/agent-identity`);
    if (r) $('identity-editor').value = r.agent_identity_md || '';
}

async function saveCompanyIdentity() {
    if (!currentCompanyId) return;
    const identity = $('identity-editor').value;
    const r = await api('PUT', `/api/agentbase/workspaces/${currentCompanyId}/agent-identity`, {agent_identity_md:identity});
    if (r?.workspace_id) { toast('身份配置已保存'); hideModal('workspace-modal'); }
    else toast(r?.detail||'保存失败');
}

// ═════════════════════ SETTINGS ═════════════════════
async function renderSettingsViewInto(container) {
    container.innerHTML = `<div class="panel-view" style="display:flex;flex-direction:column;height:100%;">
        <div class="panel-topbar"><h2>⚙️ 设置</h2></div>
        <div class="panel-body" id="settings-body" style="overflow-y:auto;padding:16px 20px;color:var(--text-muted);font-size:13px;">加载中...</div>
    </div>`;
    await loadSettings();
}

async function loadSettings() {
    const body = document.getElementById('settings-body');
    if (!body) return;
    const data = await api('GET', '/api/agentbase/settings');
    if (!data) { body.textContent = '加载失败'; return; }

    const providers = (data.providers || []).filter(p => (p.key_env_vars || []).length);
    const providerRows = providers.map(p => `
        <div class="task-card" style="margin-bottom:10px;">
            <div class="task-card-header"><span class="task-card-name">${esc(p.name || p.id)}</span>
                <span style="font-size:11px;color:${p.has_key ? 'var(--accent-green)' : 'var(--text-muted)'};">${p.has_key ? '● 已配置' : '○ 未配置'}</span>
            </div>
            ${(p.key_env_vars || []).map(env => `
                <div style="display:flex;gap:8px;margin-top:8px;">
                    <input type="password" id="key-${esc(p.id)}-${esc(env)}" placeholder="${esc(env)}" style="flex:1;padding:6px 8px;border:1px solid var(--border);border-radius:6px;">
                    <button class="btn" onclick="saveProviderKey('${escJs(p.id)}','${escJs(env)}')">保存</button>
                </div>`).join('')}
        </div>`).join('') || '<p>暂无需要填写 Key 的 provider。</p>';

    const modelOptions = (data.providers || []).map(p => `<option value="${esc(p.id)}" ${p.id === data.active?.provider ? 'selected' : ''}>${esc(p.name || p.id)}</option>`).join('');

    body.innerHTML = `
        <h3 style="font-size:15px;margin:0 0 10px;">模型与 API Key</h3>
        <p style="font-size:12px;color:var(--text-secondary);margin-bottom:12px;">Key 只保存在本机 <code>~/.agentbase/.env</code>，不会上传。</p>
        ${providerRows}
        <h3 style="font-size:15px;margin:18px 0 10px;">默认模型</h3>
        <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
            <select id="default-provider" style="padding:6px 8px;border:1px solid var(--border);border-radius:6px;">${modelOptions}</select>
            <input id="default-model" value="${esc(data.active?.model || '')}" placeholder="模型名，如 deepseek-chat" style="padding:6px 8px;border:1px solid var(--border);border-radius:6px;min-width:220px;">
            <button class="btn btn-primary" onclick="saveDefaultModel()">保存</button>
            <span style="font-size:12px;color:var(--text-muted);">当前：${esc(data.active?.provider || '未设置')} / ${esc(data.active?.model || '未设置')}</span>
        </div>
        <h3 style="font-size:15px;margin:18px 0 10px;">MoA（多模型协作）</h3>
        <p style="font-size:12px;color:var(--text-secondary);">${data.moa_available ? '已配置 ' + data.configured_provider_count + ' 个 provider，可开启 MoA。' : '至少配置 2 个 provider 的 Key 才能开启 MoA。'}<br>${esc(data.moa_hint || '')}</p>
        <label style="display:flex;align-items:center;gap:8px;font-size:13px;margin-top:8px;${data.moa_available ? '' : 'opacity:.5;'}">
            <input type="checkbox" id="moa-toggle" ${data.moa?.enabled ? 'checked' : ''} ${data.moa_available ? '' : 'disabled'} onchange="setMoa(this.checked)">
            启用 MoA
        </label>
        ${data.moa?.presets?.length ? `<p style="font-size:12px;color:var(--text-muted);margin-top:4px;">预设：${esc((data.moa.presets || []).join(', '))}</p>` : ''}
        <h3 style="font-size:15px;margin:18px 0 10px;">业务技能包</h3>
        <div id="packs-body" style="font-size:13px;">加载中...</div>
    `;
    loadPacks();
}

async function saveProviderKey(providerId, envVar) {
    const el = document.getElementById('key-' + providerId + '-' + envVar);
    const value = (el?.value || '').trim();
    if (!value) { toast('请输入 Key'); return; }
    const resp = await api('POST', '/api/agentbase/settings/keys', { keys: { [envVar]: value } });
    if (resp?.ok) { el.value = ''; toast('已保存'); loadSettings(); }
}

async function setMoa(enabled) {
    const resp = await api('POST', '/api/agentbase/settings/moa', { enabled });
    if (resp?.ok) { toast(enabled ? '已开启 MoA，重启后生效' : '已关闭 MoA，重启后生效'); }
    else { const el = document.getElementById('moa-toggle'); if (el) el.checked = !enabled; }
    loadSettings();
}

async function saveDefaultModel() {
    const provider = document.getElementById('default-provider')?.value || '';
    const model = (document.getElementById('default-model')?.value || '').trim();
    if (!provider || !model) { toast('请填写 provider 和模型名'); return; }
    const resp = await api('POST', '/api/agentbase/settings/model', { provider, model });
    if (resp?.ok) toast('已保存，重启服务后生效');
}

async function loadPacks() {
    const body = document.getElementById('packs-body');
    if (!body) return;
    const data = await api('GET', '/api/agentbase/skill-packs');
    if (!data) { body.textContent = '加载失败'; return; }
    const rows = (data.packs || []).map(p => `
        <div class="task-card" style="margin-bottom:8px;">
            <div class="task-card-header"><span class="task-card-name">${esc(p.name)}</span>
                ${data.active === p.path ? '<span style="font-size:11px;color:var(--accent-green);">● 已启用</span>' : ''}
            </div>
            <div class="task-card-actions">
                <button onclick="activatePack('${escJs(p.name)}')">启用</button>
                <button onclick="removePack('${escJs(p.name)}')">卸载</button>
            </div>
        </div>`).join('') || '<p style="color:var(--text-muted);">尚未安装业务技能包。框架仍可正常聊天。</p>';
    body.innerHTML = rows + `
        <div style="display:flex;gap:8px;margin-top:10px;">
            <input id="pack-install-path" placeholder="本地 pack 目录（含 pack.yaml）" style="flex:1;padding:6px 8px;border:1px solid var(--border);border-radius:6px;">
            <button class="btn" onclick="installPack()">安装</button>
        </div>`;
}

async function installPack() {
    const path = (document.getElementById('pack-install-path')?.value || '').trim();
    if (!path) { toast('请填写目录路径'); return; }
    const resp = await api('POST', '/api/agentbase/skill-packs/install', { path });
    if (resp?.ok) { toast('已安装：' + resp.name); loadPacks(); }
}

async function activatePack(name) {
    const resp = await api('POST', '/api/agentbase/skill-packs/activate', { name });
    if (resp?.ok) { toast('已启用，加载 ' + resp.skills + ' 个技能'); loadPacks(); }
}

async function removePack(name) {
    if (!confirm('确定卸载该技能包？')) return;
    const resp = await api('DELETE', '/api/agentbase/skill-packs/' + encodeURIComponent(name));
    if (resp?.ok) { toast('已卸载'); loadPacks(); }
}

// ═════════════════════ INIT ═════════════════════
document.addEventListener('DOMContentLoaded', async () => {
    // 初始化语言 + 业务品牌/目录配置
    initLang();
    await loadBranding();

    // 检测是否刚完成系统升级（页面 reload 后显示 toast）
    try {
        if (sessionStorage.getItem('_agentbase_upgrade_done')) {
            sessionStorage.removeItem('_agentbase_upgrade_done');
            setTimeout(() => toast('✅ 系统更新完成！'), 500);
        }
    } catch(_) {}

    // 许可证状态检查
    loadLicenseStatus();

    try {
        await loadCompanies();
    } catch(e) {
        console.error('Init loadCompanies failed:', e);
    }
    const savedCid = loadSavedCid();
    if (savedCid && workspaces.find(c => c.id === savedCid)) {
        currentCompanyId = savedCid;
    } else if (workspaces.length === 1) {
        currentCompanyId = workspaces[0].id;
    }

    // 检测重启前保存的浏览状态（避免 hard reload 丢失阅读位置）
    const reloadState = _restoreReloadState();

    if (currentCompanyId) {
        saveState();
        const sel = $('workspace-select');
        if (sel) sel.value = currentCompanyId;
        // 首个公司 + 引导未完成 → 显示新手引导
        if (workspaces.length === 1 && !isOnboardingCompleted()) {
            showOnboardingGuide();
            startCronPolling();
            startVersionCheck();
            return;
        }
        // 恢复之前的视图或默认打开今日简报
        const restoreView = reloadState?.view || 'chat';
        const restoreCtx = reloadState?.chatCtx || 'general';
        const restoreName = reloadState?.chatName || '对话';
        navToView(restoreView, restoreCtx, restoreName);
        // 恢复滚动位置（等 DOM 渲染完成后）
        if (reloadState?.scrollY > 0) {
            setTimeout(() => { window.scrollTo({ top: reloadState.scrollY, behavior: 'instant' }); }, 200);
        }
        startCronPolling();
        startVersionCheck();
    } else {
        renderNoCompanyPage();
    }
});

// 页面关闭时清理轮询
window.addEventListener('beforeunload', () => { stopCronPolling(); stopVersionCheck(); });

function renderNoCompanyPage() {
    // 清除视图缓存
    for (const key in viewCache) {
        viewCache[key].element.remove();
        delete viewCache[key];
    }
    $('main-content').innerHTML = `<div class="empty-state"><div class="empty-icon">🏢</div><h2>请先选择或创建 workspace</h2><p>AgentBase 支持多 workspace 隔离</p><button onclick="showAddCompanyModal()">➕ 创建公司</button></div>`;
}
