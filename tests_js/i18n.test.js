const { test } = require('node:test');
const assert = require('node:assert');
const { SRC, loadRegion } = require('./_extract');

const { I18N } = loadRegion('i18n', '{ I18N: I18N }');

test('所有字面量 t() key 都同时有 zh 与 en', () => {
    const keys = new Set();
    const re = /\bt\('([^']+)'/g;
    let m;
    while ((m = re.exec(SRC)) !== null) keys.add(m[1]);

    const missing = [...keys].filter((k) => !(k in I18N.zh) || !(k in I18N.en));
    assert.deepEqual(missing, [], `缺少 zh/en 文案：${missing.join(', ')}`);
});

test('zh 与 en 的 key 集合一致', () => {
    const zh = Object.keys(I18N.zh).sort();
    const en = Object.keys(I18N.en).sort();
    assert.deepEqual(en, zh, 'zh/en key 必须一一对应');
});

test('设置分类 key 完整', () => {
    const required = [
        'settings.group.models', 'settings.group.agent_behavior', 'settings.group.workspaces',
        'settings.group.agent', 'settings.group.business', 'settings.group.skills',
        'settings.group.files', 'settings.group.system', 'settings.group.developer',
    ];
    for (const key of required) {
        assert.ok(I18N.zh[key], `缺少 ${key}`);
        assert.ok(I18N.en[key], `缺少 ${key} (en)`);
    }
});
