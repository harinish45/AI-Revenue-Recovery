/**
 * start-demo.js
 * ─────────────
 * One-command RecoverAI demo launcher.
 * Works on Windows, macOS, and Linux.
 *
 * Usage:  npm run demo
 */

const { spawn, execSync } = require('child_process');
const path = require('path');
const http = require('http');

const ROOT = path.resolve(__dirname, '..');
const BACKEND_DIR = path.join(ROOT, 'backend');

const COLORS = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  red: '\x1b[31m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m',
};

const log = (color, prefix, msg) =>
  console.log(`${color}${prefix}${COLORS.reset} ${msg}`);

function banner() {
  console.log('\n' + COLORS.bright + COLORS.blue + '╔═════════════════════════════════════════╗');
  console.log('║       RecoverAI — Demo Launcher         ║');
  console.log('║  Razorpay Hackathon · Track 03          ║');
  console.log('╚═════════════════════════════════════════╝' + COLORS.reset + '\n');
}

function checkPython() {
  try {
    const v = execSync('python --version 2>&1').toString().trim();
    log(COLORS.green, '✓', `Python: ${v}`);
    return 'python';
  } catch (pythonError) {
    try {
      const v = execSync('python3 --version 2>&1').toString().trim();
      log(COLORS.green, '✓', `Python: ${v}`);
      return 'python3';
    } catch (python3Error) {
      log(COLORS.red, '✗', 'Python not found. Please install Python 3.9+');
      process.exit(1);
    }
  }
}

function installBackendDeps(python) {
  const reqFile = path.join(BACKEND_DIR, 'requirements.txt');
  log(COLORS.yellow, '⟳', 'Checking backend dependencies...');
  try {
    execSync(`${python} -m pip install -r "${reqFile}" -q`, { stdio: 'pipe' });
    log(COLORS.green, '✓', 'Backend dependencies ready');
  } catch (installError) {
    log(COLORS.yellow, '!', `pip install failed (${installError.message}); using installed packages`);
  }
}

function startBackend(python) {
  log(COLORS.yellow, '⟳', 'Starting RecoverAI on port 8000...');
  const proc = spawn(python, ['-m', 'uvicorn', 'app.main:app', '--host', '0.0.0.0', '--port', '8000'], {
    cwd: BACKEND_DIR,
    stdio: ['ignore', 'pipe', 'pipe'],
    detached: false,
  });
  proc.stdout.on('data', d => {
    const line = d.toString().trim();
    if (line) log(COLORS.cyan, '[backend]', line);
  });
  proc.stderr.on('data', d => {
    const line = d.toString().trim();
    if (line && !line.includes('INFO')) log(COLORS.cyan, '[backend]', line);
  });
  proc.on('exit', code => {
    if (code !== null) log(COLORS.red, '[backend]', `exited with code ${code}`);
  });
  return proc;
}

function waitForHealth(url, timeoutMs = 30000) {
  return new Promise((resolve, reject) => {
    const start = Date.now();
    const check = () => {
      http.get(url, res => {
        if (res.statusCode === 200) return resolve();
        setTimeout(check, 1000);
      }).on('error', () => {
        if (Date.now() - start > timeoutMs) return reject(new Error(`Timeout waiting for ${url}`));
        setTimeout(check, 1000);
      });
    };
    check();
  });
}

function cleanup(procs) {
  procs.forEach(p => {
    try { p.kill(); } catch (killError) { log(COLORS.yellow, '!', `Process already stopped: ${killError.message}`); }
  });
  process.exit(0);
}

async function main() {
  banner();

  const python = checkPython();
  console.log('');

  installBackendDeps(python);
  console.log('');

  const backend = startBackend(python);
  const procs = [backend];

  process.on('SIGINT', () => cleanup(procs));
  process.on('SIGTERM', () => cleanup(procs));

  console.log('');
  log(COLORS.yellow, '⟳', 'Waiting for server to start...');

  try {
    await waitForHealth('http://localhost:8000/');
  } catch (err) {
    log(COLORS.red, '✗', `Health check failed: ${err.message}`);
    cleanup(procs);
  }

  console.log('\n' + COLORS.bright + COLORS.green);
  console.log('╔═════════════════════════════════════════╗');
  console.log('║          RecoverAI Started ✓            ║');
  console.log('╠═════════════════════════════════════════╣');
  console.log('║  App:       http://localhost:8000       ║');
  console.log('║  API Docs:  http://localhost:8000/docs  ║');
  console.log('╚═════════════════════════════════════════╝');
  console.log(COLORS.reset);
  log(COLORS.cyan, 'ℹ', 'Press Ctrl+C to stop the server');
}

main().catch(err => {
  log(COLORS.red, '✗', err.message);
  process.exit(1);
});
