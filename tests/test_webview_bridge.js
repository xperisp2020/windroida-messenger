'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const read = (p) => fs.readFileSync(p, 'utf8');
function bootstrap(source, marker) {
  const markerAt = source.indexOf(marker);
  assert.notEqual(markerAt, -1, `missing bootstrap marker: ${marker}`);
  const start = source.indexOf('(()=>{', markerAt);
  const end = source.indexOf('})();', start);
  assert.ok(start >= 0 && end > start, 'bootstrap IIFE boundaries not found');
  return source.slice(start, end + 5);
}
function run(code, hash, storedNonce = '') {
  const calls = [];
  const raw = new Proxy({}, { get: (_, name) => (...args) => { calls.push([String(name), ...args]); return name === 'only' ? true : 'ok'; } });
  const store = new Map();
  if (storedNonce) store.set('__wd_main_bridge_nonce', storedNonce);
  const sessionStorage = {
    getItem: (key) => store.get(key) ?? null,
    setItem: (key, value) => store.set(key, String(value))
  };
  const location = { hash, pathname: '/', search: '?test=1' };
  let replaced = null;
  const context = {
    window: { WD: raw },
    location,
    sessionStorage,
    history: { replaceState: (_state, _title, url) => { replaced = url; } }
  };
  vm.runInNewContext(code, context);
  return { bridge: context.window.WD, calls, store, replaced };
}
const nonce = 'a'.repeat(43);
const web = read('web/app.js');
assert.equal((web.match(/const noncePart=parts\.find/g) || []).length, 1, 'main WebView nonce bootstrap must exist exactly once');
assert.match(read('web/index.html'), /frame-src 'none'/, 'messenger WebView must not load frames');
assert.match(read('ghab/web/index.html'), /frame-src 'none'/, 'Ghab WebView must not load frames');
assert.match(read('android/app/src/main/res/xml/backup_rules.xml'), /wd_internal_launch\.xml/, 'internal launch capabilities must not be backed up');
assert.match(read('android/app/src/main/res/xml/data_extraction_rules.xml'), /<device-transfer>[\s\S]*?wd_internal_launch\.xml/, 'internal launch capabilities must not be transferred to another device');
const mainCode = bootstrap(web, 'The Android Java bridge is callable from every WebView frame');
const first = run(mainCode, `#room=42&wdnonce=${nonce}`);
assert.equal(first.replaced, '/?test=1#room=42');
first.bridge.setServicePort('drive', 9123);
assert.deepEqual(JSON.parse(JSON.stringify(first.calls[0])), ['setServicePort', nonce, 'drive', 9123]);
first.bridge.setToken('session-token');
assert.deepEqual(JSON.parse(JSON.stringify(first.calls[1])), ['setToken', nonce, 'session-token']);
assert.equal(first.bridge.only(), true);
assert.deepEqual(JSON.parse(JSON.stringify(first.calls[2])), ['only', nonce]);
const reload = run(mainCode, '#room=42', nonce);
reload.bridge.setToken('after-reload');
assert.deepEqual(JSON.parse(JSON.stringify(reload.calls[0])), ['setToken', nonce, 'after-reload']);
const noNonce = run(mainCode, '#room=42');
assert.equal(noNonce.bridge, null, 'bridge must be disabled when no valid nonce exists');

const ghab = read('ghab/web/static/app.js');
const ghabCode = bootstrap(ghab, 'SiteActivity injects WD into every frame');
const ghabRun = run(ghabCode, `#wdnonce=${nonce}`);
ghabRun.bridge.playVideo('/media/1', 'video');
assert.deepEqual(JSON.parse(JSON.stringify(ghabRun.calls[0])), ['playVideo', nonce, '/media/1', 'video']);

const drive = read('cloud-drive/app/static/js/common.js');
const driveCode = bootstrap(drive, 'SiteActivity injects WD into every frame');
const driveRun = run(driveCode, `#wdnonce=${nonce}`);
driveRun.bridge.saveFile('/download/1', 'file.pdf');
driveRun.bridge.saveFileId('d1', '/download/2', 'file2.pdf');
assert.deepEqual(JSON.parse(JSON.stringify(driveRun.calls[0])), ['saveFile', nonce, '/download/1', 'file.pdf']);
assert.deepEqual(JSON.parse(JSON.stringify(driveRun.calls[1])), ['saveFileId', nonce, 'd1', '/download/2', 'file2.pdf']);

console.log('WebView bridge nonce tests passed');
