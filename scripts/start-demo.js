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
const fs = require('fs');
const http = require('http');

const ROOT = path.resolve(__dirname, '..');
const BACKEND_DIR = path.join(ROOT, 'backend');
const FRONTEND_DIR = path.join(ROOT, 'frontend');
const isWin = process.platform === 'win32';

const COLORS = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  red: '\x1b[31m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m',
  magenta: '\x1b[35m',
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
  } catch {
    try {
      const v = execSync('python3 --version 2>&1').toString().trim();
      log(COLORS.green, '✓', `Python: ${v}`);
      return 'python3';
    } catch {
      log(COLORS.red, '✗', 'Python not found. Please install Python 3.9+');
      process.exit(1);
    }
  }
}

function checkNode() {
  try {
    const v = execSync('node --version').toString().trim();
    log(COLORS.green, '✓', `Node.js: ${v}`);
  } catch {
    log(COLORS.red, '✗', 'Node.js not found. Please install Node.js 18+');
    process.exit(1);
  }
}

function installFrontendDeps() {
  const nodeModules = path.join(FRONTEND_DIR, 'node_modules');
  if (!fs.existsSync(nodeModules)) {
    log(COLORS.yellow, '⟳', 'Installing frontend dependencies...');
    execSync('npm install', { cwd: FRONTEND_DIR, stdio: 'inherit' });
    log(COLORS.green, '✓', 'Frontend dependencies installed');
  } else {
    log(COLORS.green, '✓', 'Frontend dependencies ready');
  }
}

function installBackendDeps(python) {
  const reqFile = path.join(BACKEND_DIR, 'requirements.txt');
  log(COLORS.yellow, '⟳', 'Checking backend dependencies...');
  try {
    execSync(`${python} -m pip install -r "${reqFile}" -q`, { stdio: 'pipe' });
    log(COLORS.green, '✓', 'Backend dependencies ready');
  } catch (err) {
    log(COLORS.yellow, '!', 'pip install had warnings (continuing)');
  }
}

function startBackend(python) {
  log(COLORS.yellow, '⟳', 'Starting FastAPI backend on port 8000...');
  const cmd = python;
  const args = ['-m', 'uvicorn', 'app.main:app', '--host', '0.0.0.0', '--port', '8000'];
  const proc = spawn(cmd, args, {
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

function startFrontend() {
  log(COLORS.yellow, '⟳', 'Starting Vite frontend on port 5173...');
  const npmCmd = isWin ? 'npm.cmd' : 'npm';
  const proc = spawn(npmCmd, ['run', 'dev'], {
    cwd: FRONTEND_DIR,
    stdio: ['ignore', 'pipe', 'pipe'],
    detached: false,
  });
  proc.stdout.on('data', d => {
    const line = d.toString().trim();
    if (line) log(COLORS.magenta, '[frontend]', line);
  });
  proc.stderr.on('data', d => {
    const line = d.toString().trim();
    if (line) log(COLORS.magenta, '[frontend]', line);
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
    try { p.kill(); } catch {}
  });
  process.exit(0);
}

async function main() {
  banner();

  // Checks
  const python = checkPython();
  checkNode();
  console.log('');

  // Setup
  installBackendDeps(python);
  installFrontendDeps();
  console.log('');

  // Start processes
  const backend = startBackend(python);
  const frontend = startFrontend();
  const procs = [backend, frontend];

  // Ctrl+C cleanup
  process.on('SIGINT', () => cleanup(procs));
  process.on('SIGTERM', () => cleanup(procs));

  console.log('');
  log(COLORS.yellow, '⟳', 'Waiting for servers to start...');

  try {
    await Promise.all([
      waitForHealth('http://localhost:8000/health'),
      waitForHealth('http://localhost:5173'),
    ]);
  } catch (err) {
    log(COLORS.red, '✗', `Health check failed: ${err.message}`);
    cleanup(procs);
  }

  console.log('\n' + COLORS.bright + COLORS.green);
  console.log('╔═════════════════════════════════════════╗');
  console.log('║          RecoverAI Started ✓            ║');
  console.log('╠═════════════════════════════════════════╣');
  console.log('║  Frontend:  http://localhost:5173       ║');
  console.log('║  Backend:   http://localhost:8000       ║');
  console.log('║  API Docs:  http://localhost:8000/docs  ║');
  console.log('║  Health:    OK ✓                        ║');
  console.log('╚═════════════════════════════════════════╝');
  console.log(COLORS.reset);
  log(COLORS.cyan, 'ℹ', 'Press Ctrl+C to stop both servers');
}

main().catch(err => {
  log(COLORS.red, '✗', err.message);
  process.exit(1);
});
