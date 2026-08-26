/**
 * health-check.js
 * ────────────────
 * Checks that the RecoverAI backend (which also serves the app UI) is up.
 *
 * Usage:  npm run health
 */

const http = require('http');

const COLORS = { reset: '\x1b[0m', green: '\x1b[32m', red: '\x1b[31m' };
const log = (ok, label, detail) =>
  console.log(`${ok ? COLORS.green + '✓' : COLORS.red + '✗'}${COLORS.reset} ${label} ${detail}`);

function check(url, label, timeoutMs = 3000) {
  return new Promise(resolve => {
    const req = http.get(url, res => {
      const ok = res.statusCode >= 200 && res.statusCode < 400;
      log(ok, label, `(${url}) → HTTP ${res.statusCode}`);
      res.resume();
      resolve(ok);
    });
    req.setTimeout(timeoutMs, () => {
      req.destroy();
      log(false, label, `(${url}) → timed out after ${timeoutMs}ms`);
      resolve(false);
    });
    req.on('error', err => {
      log(false, label, `(${url}) → ${err.message}`);
      resolve(false);
    });
  });
}

async function main() {
  const appOk = await check('http://localhost:8000/api/health', 'RecoverAI');
  process.exit(appOk ? 0 : 1);
}

main();
