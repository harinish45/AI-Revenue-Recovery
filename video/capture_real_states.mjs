import { chromium } from 'playwright';
import fs from 'node:fs/promises';
const root = 'C:/Documents/Projects/RAZOR PAY/AI-Revenue-Recovery';
const out = `${root}/video/real-website-capture`;
const chrome = 'C:/Users/HARINISH S V/.cache/hyperframes/chrome/chrome-headless-shell/win64-152.0.7977.30/chrome-headless-shell-win64/chrome-headless-shell.exe';
await fs.mkdir(out,{recursive:true});
const browser = await chromium.launch({headless:true,executablePath:chrome});
const page = await browser.newPage({viewport:{width:1600,height:900}});
const wait = ms => page.waitForTimeout(ms);
async function reset(){await page.goto('http://localhost:8001/');await page.waitForLoadState('domcontentloaded');await wait(1000);await page.evaluate(async()=>{await fetch('/api/demo/reset',{method:'POST'});await fetch('/api/demo/seed',{method:'POST'});});await page.reload();await wait(900);}
async function shot(name){await page.screenshot({path:`${out}/${name}.png`});}
async function highlight(selector){await page.locator(selector).first().click();await wait(250);}
await reset();
await page.getByRole('button',{name:'◎ Focus',exact:true}).click();
await page.getByRole('button',{name:'Seed Data',exact:true}).click(); await wait(900); await shot('01-overview');
await page.getByRole('button',{name:/^Cases/}).first().click(); await wait(700);
await page.locator('#caseRiskFilter').selectOption('high'); await wait(700); await shot('02-cases-high-risk');
await page.getByRole('button',{name:'Batch Run',exact:true}).click(); await wait(700);
await page.getByRole('button',{name:/Run Batch Recovery|Start Batch/}).click(); await wait(10000); await shot('03-batch-economics');
await highlight('.bm'); await shot('03-batch-economics-focus');
await reset(); await page.getByRole('switch',{name:/Arm Failure Sim/}).click(); await page.getByRole('button',{name:/^Cases/}).first().click(); await wait(700);
await page.getByRole('row',{name:/RC-IL_001/}).getByRole('button',{name:'Execute',exact:true}).click(); await wait(4300); await shot('04-human-review-result');
const close=page.getByRole('button',{name:'Close',exact:true}); if(await close.count()) await close.click(); await wait(700);
await page.getByRole('button',{name:'Voice Agent',exact:true}).click(); await wait(800);
await page.getByRole('button',{name:'English',exact:true}).click(); await page.locator('button[data-act="sel-voice"]').first().click(); await wait(700);
await page.getByRole('checkbox',{name:/Operator consent gate/}).check(); await wait(700); await shot('05-voice-consent');
await highlight('.voice-compliance'); await shot('05-voice-consent-focus');
await page.getByRole('button',{name:'Audit Trail',exact:true}).click(); await wait(900); await shot('06-audit-trail');
await browser.close(); console.log('states-captured');
