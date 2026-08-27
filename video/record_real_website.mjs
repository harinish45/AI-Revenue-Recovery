import { chromium } from 'playwright';
import fs from 'node:fs/promises';

const root = 'C:/Documents/Projects/RAZOR PAY/AI-Revenue-Recovery';
const videoDir = `${root}/video/real-website-capture`;
const chrome = 'C:/Users/Harinish S V/.cache/hyperframes/chrome/chrome-headless-shell/win64-152.0.7977.30/chrome-headless-shell-win64/chrome-headless-shell.exe';
await fs.mkdir(videoDir, { recursive: true });
const browser = await chromium.launch({ headless: true, executablePath: chrome });
const context = await browser.newContext({ viewport: { width: 1600, height: 900 }, recordVideo: { dir: videoDir, size: { width: 1600, height: 900 } } });
const page = await context.newPage();
const wait = ms => page.waitForTimeout(ms);
let t0;
async function until(seconds) { const remaining = seconds * 1000 - (Date.now() - t0); if (remaining > 0) await wait(remaining); }
async function focus(selector) { await page.locator(selector).first().click(); await wait(1800); }
async function resetDemo() {
  await page.evaluate(async () => { await fetch('/api/demo/reset', { method: 'POST' }); await fetch('/api/demo/seed', { method: 'POST' }); });
  await page.reload(); await page.waitForLoadState('domcontentloaded'); await wait(900);
}

await page.goto('http://localhost:8001/');
await page.waitForLoadState('domcontentloaded');
await wait(2500);
await resetDemo();
t0 = Date.now();

// 0:00–0:45 — overview and detection
await until(4);
await page.getByRole('button', { name: '◎ Focus', exact: true }).click();
await focus('.kpi');
await focus('#seedBtn');
await until(45);

// 0:45–1:35 — cases, filters, and inspection
await page.getByRole('button', { name: /^Cases/ }).first().click(); await wait(700);
await until(52);
await focus('select[aria-label="Filter by risk"]');
await page.locator('select[aria-label="Filter by risk"]').selectOption('high'); await wait(2500);
await until(65);
await focus('select[aria-label="Filter by status"]');
await page.locator('select[aria-label="Filter by status"]').selectOption('open'); await wait(2500);
const inspect = page.getByRole('button', { name: 'Inspect', exact: true }).first();
if (await inspect.count()) { await inspect.click(); await wait(4500); }
await until(95);

// 1:35–2:25 — batch recovery and economics
await page.getByRole('button', { name: 'Batch Run', exact: true }).click(); await wait(700);
await focus('button[data-act="run-batch"]');
await until(150);

// 2:25–3:15 — controlled failure and reflected terminal state
await resetDemo();
await page.getByRole('switch', { name: /Arm Failure Sim/ }).click(); await wait(700);
await page.getByRole('button', { name: /^Cases/ }).first().click(); await wait(700);
await until(170);
const firstRow = page.getByRole('row', { name: /RC-IL_001/ });
await firstRow.getByRole('button', { name: 'Execute', exact: true }).click(); await wait(5200);
const close = page.getByRole('button', { name: 'Close', exact: true });
if (await close.count()) { await close.click(); await wait(2400); }
await until(185);
await focus('select[aria-label="Filter by status"]');
await page.locator('select[aria-label="Filter by status"]').selectOption('escalated'); await wait(3000);
await until(200);

// 3:15–4:20 — voice agent and consent boundary
await page.getByRole('button', { name: 'Voice Agent', exact: true }).click(); await wait(900);
await until(208);
await focus('button[data-act="set-vlang"][data-lang="en-IN"]');
const caseButton = page.getByRole('button', { name: /Vikram Singh RC-IL_002/ }).first();
if (await caseButton.count()) { await caseButton.click(); await wait(1800); }
await focus('input[type="checkbox"]');
await page.getByRole('checkbox', { name: /Operator consent gate/ }).check(); await wait(3000);
await until(250);

// 4:20–5:00 — audit trail and closing proof
await page.getByRole('button', { name: 'Audit Trail', exact: true }).click(); await wait(900);
await until(258);
await focus('button[data-act="verify-audit"]');
await wait(3500);
await focus('button[data-act="export-audit"]');
await wait(3000);
await until(285);
await page.getByRole('button', { name: 'Overview', exact: true }).click();
await until(300);

await context.close();
await browser.close();
console.log('recording-complete');
