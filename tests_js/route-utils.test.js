const { test } = require('node:test');
const assert = require('node:assert');
const { loadRegion } = require('./_extract');

const { parseHashRoute, routeHash, SETTINGS_PAGES } = loadRegion(
    'route-utils',
    '{ parseHashRoute: parseHashRoute, routeHash: routeHash, SETTINGS_PAGES: SETTINGS_PAGES }'
);

test('空 hash 回落设置首页', () => {
    assert.deepEqual(parseHashRoute(''), { view: 'settings', page: 'home' });
    assert.deepEqual(parseHashRoute('#'), { view: 'settings', page: 'home' });
});

test('#/settings 与 #/settings/xxx', () => {
    assert.deepEqual(parseHashRoute('#/settings'), { view: 'settings', page: 'home' });
    assert.deepEqual(parseHashRoute('#/settings/models'), { view: 'settings', page: 'models' });
    assert.deepEqual(parseHashRoute('#/settings/agent-behavior'), { view: 'settings', page: 'agent-behavior' });
});

test('非法设置页回落到 home', () => {
    assert.deepEqual(parseHashRoute('#/settings/nope'), { view: 'settings', page: 'home' });
});

test('#/dev 是调试页', () => {
    assert.deepEqual(parseHashRoute('#/dev'), { view: 'debug', page: 'dev' });
});

test('routeHash 与 parseHashRoute 往返一致', () => {
    for (const page of SETTINGS_PAGES) {
        const route = { view: 'settings', page };
        assert.deepEqual(parseHashRoute(routeHash(route)), route);
    }
    assert.deepEqual(parseHashRoute(routeHash({ view: 'debug', page: 'dev' })), { view: 'debug', page: 'dev' });
});
