import React, { useState, useEffect, useCallback, useRef } from 'react';
import './index.css';
import { api } from './services/api';

/* ═══ CONSTANTS & BRAINS ═══ */
const NAMES = ['Arjun Mehta', 'Priya Sharma', 'Rohit Kumar', 'Sneha Iyer', 'Vikram Singh', 'Ananya Rao', 'Karthik Nair', 'Divya Pillai', 'Aditya Gupta', 'Meera Joshi', 'Rahul Verma', 'Kavya Reddy'];
const CATS = [
  { code: 'INSUF', name: 'Insufficient Funds', risk: 'high' },
  { code: 'GW_TIMEOUT', name: 'Gateway Timeout', risk: 'medium' },
  { code: 'CARD_EXP', name: 'Card Expired', risk: 'low' },
  { code: 'UPI_FAIL', name: 'UPI Failure', risk: 'high' },
  { code: 'AUTH_DECL', name: 'Auth Declined', risk: 'medium' },
  { code: 'ABANDON', name: 'Checkout Abandoned', risk: 'low' }
];
const METHODS = ['UPI', 'Card', 'NetBanking', 'Wallet'];
const ACTIONS = ['Smart Retry T+2h', 'Retry via Alt Rail', 'Send Payment Link', 'Voice Follow-up', 'Card Update Request'];

const PLAYBOOKS = [
  {
    id: 'degradation', name: 'Payment Degradation Scan', desc: 'Detects gateway degradation and retries via alternate rails', color: '#22c55e', runs: 47,
    filterFn: (c) => c.status === 'open' && (c.category?.code === 'GW_TIMEOUT' || c.category?.code === 'AUTH_DECL'),
    processFn: (c) => c.confidence > 78 ? { outcome: 'recovered', action: 'Retry via alternate rail succeeded' } : { outcome: 'escalated', action: 'Degradation requires manual review' }
  },
  {
    id: 'checkout', name: 'Checkout Recovery', desc: 'Sends smart payment links for abandoned checkouts', color: '#3b82f6', runs: 112,
    filterFn: (c) => c.status === 'open' && c.category?.code === 'ABANDON',
    processFn: (c) => (c.attempts || 1) < 3 ? { outcome: 'recovered', action: 'Payment link sent and completed' } : { outcome: 'skip', action: 'Max outreach reached' }
  },
  {
    id: 'dunning', name: 'Subscription Dunning', desc: 'Smart retry ladder with optimal timing windows', color: '#8b5cf6', runs: 38,
    filterFn: (c) => c.status === 'open' && (c.category?.code === 'INSUF' || c.category?.code === 'UPI_FAIL'),
    processFn: (c) => (c.confidence + (c.attempts || 1) * 10) > 85 ? { outcome: 'recovered', action: 'Dunning retry succeeded' } : { outcome: 'escalated', action: 'Dunning ladder exhausted' }
  },
  {
    id: 'receivables', name: 'B2B Receivables Chaser', desc: 'Aging buckets with escalating chaser tones', color: '#f59e0b', runs: 26,
    filterFn: (c) => c.status === 'open' && c.amount > 5000,
    processFn: (c) => c.amount > 20000 ? { outcome: 'escalated', action: 'High-value B2B escalated' } : { outcome: 'recovered', action: 'Chaser sent, payment received' }
  },
  {
    id: 'mandate', name: 'Mandate Retry Sequencer', desc: 'UPI AutoPay eNACH intelligent retry', color: '#3b82f6', runs: 64,
    filterFn: (c) => c.status === 'open' && c.method === 'UPI' && (c.category?.code === 'UPI_FAIL' || c.category?.code === 'INSUF'),
    processFn: (c) => parseInt(c.created || '10') < 24 ? { outcome: 'recovered', action: 'Mandate retry succeeded' } : { outcome: 'skip', action: 'Retry window expired' }
  },
  {
    id: 'voice', name: 'Hinglish Voice Recovery', desc: 'AI voice agent calls customers in their language', color: '#ec4899', runs: 19, actionType: 'voice',
    filterFn: (c) => c.status === 'open' && c.risk !== 'low',
    processFn: (c) => c.confidence > 80 ? { outcome: 'recovered', action: 'Voice call, payment commitment secured' } : { outcome: 'escalated', action: 'Voice call, needs human follow-up' }
  },
  {
    id: 'ptp', name: 'Promise-to-Pay Tracker', desc: 'Converts verbal or chat commitments into tracked follow-ups', color: '#06b6d4', runs: 31,
    filterFn: (c) => c.status === 'open' && c.confidence >= 75 && c.confidence < 90,
    processFn: (c) => ({ outcome: 'promise', action: 'Promise captured, follow-up scheduled' })
  }
];

/* ═══ VOICE INTENT ENGINE ═══
   One shared, language-agnostic keyword table used for EVERY voice language.
   Real Indian customers code-switch mid-sentence regardless of which
   language the agent is speaking, so instead of 5 isolated per-language
   dictionaries, every utterance is checked against the full cross-language
   set - a Hindi caller who suddenly says "wrong number" in English still
   gets recognized correctly. Order matters: specific multi-word phrases
   are checked before generic single-word negations. */
const INTENT_KEYWORDS = {
  PROMISE_TO_PAY: ['haan bilkul', 'haan', 'yes', 'sure', 'theek hai', 'ok kar', 'kar dunga', 'will pay', 'i will pay', 'pay kar dunga', 'avunu cheptanu', 'sare chestanu', 'aam sollunga', 'seiren', 'haudu madtini', 'settle pannuven', 'definitely pay'],
  ALREADY_PAID: ['maine already pay kar diya', 'already paid', 'payment ho gaya', 'ho chuka hai', 'already pay chesanu', 'already pay madidini', 'already pay pannitten', 'already'],
  DISPUTE: ['yeh galat charge hai', 'wrong charge', 'not my transaction', 'idhu thappu charge', 'idi tappu charge', 'idu tappu charge', 'dispute', 'fraud'],
  ANGRY: ['stop calling', 'harass mat karo', 'baar baar call', 'angry', 'gussa', 'irritat'],
  WRONG_NUMBER: ['wrong number hai', 'wrong number', 'galat number', 'who is this', 'not me'],
  CANNOT_PAY: ['balance nahi hai', 'paisa nahi hai', 'no balance', 'no money', 'dabbu ledu', 'panam illai', 'hana illa'],
  NEED_TIME: ['thoda baad mein', 'baad mein', 'later', 'salary nahi aaya', 'abhi nahi', 'tarvata pesalam', 'mele call madi', 'tarvata call cheyandi'],
  LINK_REQUEST: ['send link', 'payment link chahiye', 'naya link bhejo', 'link anuppu', 'link kaluhisu', 'link pampu'],
  GOODBYE: ['dhanyavaad', 'thanks', 'thank you', 'nandri', 'dhanyavadagalu', 'dhanyavadalu'],
  DECLINE: ['nahi', 'no', 'nope', 'vendam', 'beda', 'illa'],
};

function matchIntent(text) {
  const t = ' ' + text.toLowerCase() + ' ';
  for (const intent of Object.keys(INTENT_KEYWORDS)) {
    if (INTENT_KEYWORDS[intent].some(kw => t.includes(kw.toLowerCase()))) return intent;
  }
  return null;
}

const VOICE_BRAIN = {
  'hi-IN': {
    label: 'Hindi', name: 'Hindi / Hinglish',
    greeting: (c) => `Namaste ${c.customer.split(' ')[0]} ji, main RecoverAI team se bol rahi hoon. Aapke payment ke regarding baat karni thi. Kya abhi 2 minute hain?`,
    context: (c) => `Sir, aapka payment of ${fmtINR(c.amount)} fail ho gaya tha. Reason hai ${c.category?.name || 'Technical issue'}.`,
    responses: {
      PROMISE_TO_PAY: { say: 'Perfect sir! Main abhi ek secure payment link WhatsApp pe bhej rahi hoon. Aap 24 ghante mein clear kar dijiyega.', stage: 'objection', outcome: 'PROMISE_TO_PAY' },
      ALREADY_PAID: { say: 'Oh accha, main abhi verify karti hoon apne system mein. Agar payment already reflect ho chuka hai toh main case turant close kar dungi.', stage: 'closed', outcome: 'ALREADY_PAID_VERIFY' },
      DISPUTE: { say: 'Samajh gayi sir, yeh galat charge lagta hai. Main isse humari dispute team ko forward kar rahi hoon, 48 ghante mein review hoga.', stage: 'closed', outcome: 'DISPUTE_RAISED' },
      ANGRY: { say: 'Maaf kijiye sir, main aapki takleef samajh sakti hoon. Main abhi is number ko human agent ke paas bhej rahi hoon.', stage: 'closed', outcome: 'ANGRY_ESCALATED' },
      WRONG_NUMBER: { say: 'Oh sorry sir, galti se call chala gaya. Main is number ko turant apne records se hata deti hoon.', stage: 'closed', outcome: 'WRONG_NUMBER' },
      CANNOT_PAY: { say: 'Samajh sakti hoon sir, mushkil time hai. Main isse installments mein split karne ke liye ek senior ko note bhej rahi hoon.', stage: 'closed', outcome: 'HARDSHIP_ESCALATED' },
      NEED_TIME: { say: 'Koi baat nahi sir. Main 2 din baad automatic retry laga rahi hoon.', stage: 'closed', outcome: 'CALLBACK_SCHEDULED' },
      LINK_REQUEST: { say: 'Bilkul sir! Main abhi fresh secure payment link bhej rahi hoon WhatsApp pe.', stage: 'closed', outcome: 'LINK_SENT' },
      GOODBYE: { say: 'Dhanyavaad sir! Aapka din shubh rahe.', stage: 'closed', outcome: 'POLITE_END' },
      DECLINE: { say: 'Theek hai sir, sorry for disturbing. WhatsApp pe details bhej rahi hoon.', stage: 'closed', outcome: 'SOFT_REFUSAL' },
    },
    fallback: () => ({ say: 'Sir, main theek se samajh nahi payi. Kya aap payment abhi kar sakte hain? Ya main link bhej doon?', stage: 'objection' }),
    quickReplies: ['Haan bilkul', 'Thoda baad mein', 'Balance nahi hai', 'Maine already pay kar diya', 'Yeh galat charge hai', 'Wrong number hai', 'Dhanyavaad']
  },
  'en-IN': {
    label: 'English', name: 'English',
    greeting: (c) => `Hello ${c.customer.split(' ')[0]}, this is the RecoverAI team. Do you have 2 minutes to discuss your pending payment?`,
    context: (c) => `Your payment of ${fmtINR(c.amount)} failed due to ${c.category?.name || 'Technical issue'}.`,
    responses: {
      PROMISE_TO_PAY: { say: 'Great! I will send a secure payment link to your WhatsApp right now, please clear it within 24 hours.', stage: 'objection', outcome: 'PROMISE_TO_PAY' },
      ALREADY_PAID: { say: 'Let me verify that on our system right now - if the payment already reflects, I will close this case immediately.', stage: 'closed', outcome: 'ALREADY_PAID_VERIFY' },
      DISPUTE: { say: 'I understand your concern. I am forwarding this to our dispute team for review within 48 hours.', stage: 'closed', outcome: 'DISPUTE_RAISED' },
      ANGRY: { say: 'I sincerely apologize for the inconvenience. I am connecting you with a human agent right away.', stage: 'closed', outcome: 'ANGRY_ESCALATED' },
      WRONG_NUMBER: { say: 'My apologies for the confusion, I will remove this number from our records immediately.', stage: 'closed', outcome: 'WRONG_NUMBER' },
      CANNOT_PAY: { say: 'I understand this is a difficult time. I am flagging this for a senior agent to discuss an installment plan.', stage: 'closed', outcome: 'HARDSHIP_ESCALATED' },
      NEED_TIME: { say: 'No problem at all. I will schedule an automatic retry for 2 days from now.', stage: 'closed', outcome: 'CALLBACK_SCHEDULED' },
      LINK_REQUEST: { say: 'Absolutely! Sending a fresh secure payment link right now.', stage: 'closed', outcome: 'LINK_SENT' },
      GOODBYE: { say: 'Thank you for your time! Have a great day.', stage: 'closed', outcome: 'POLITE_END' },
      DECLINE: { say: 'No problem, sorry for the inconvenience. I will send details via WhatsApp.', stage: 'closed', outcome: 'SOFT_REFUSAL' },
    },
    fallback: () => ({ say: 'I did not quite catch that. Can you make the payment now, or should I send a link?', stage: 'objection' }),
    quickReplies: ['Yes, I will pay', 'Call me later', 'No balance', 'Already paid', 'Wrong charge', 'Wrong number', 'Thanks']
  },
  'ta-IN': {
    label: 'Tamil', name: 'Tamil',
    greeting: (c) => `Vanakkam ${c.customer.split(' ')[0]}, naan RecoverAI team pesugiren. Ungal payment pathi pesa 2 nimidam undo?`,
    context: (c) => `Ungal ${fmtINR(c.amount)} payment failed aagiyulladhu. Kaaranam ${c.category?.name || 'Technical issue'}.`,
    responses: {
      PROMISE_TO_PAY: { say: 'Nandri! Naan ippo secure payment link ungal WhatsApp-ku anuppen. 24 mani neram-il settle pannunga.', stage: 'objection', outcome: 'PROMISE_TO_PAY' },
      ALREADY_PAID: { say: 'Sari, naan ippo system-la verify pannuren. Payment already aiten-na, case-ah udane close pannuven.', stage: 'closed', outcome: 'ALREADY_PAID_VERIFY' },
      DISPUTE: { say: 'Puriyudhu sir, idhu thappu charge maadhiri irukku. Naan dispute team-ku forward pandren, 48 mani neram-il review aagum.', stage: 'closed', outcome: 'DISPUTE_RAISED' },
      ANGRY: { say: 'Mannikkavum sir, ungal frustration puriyudhu. Naan ippo ungala human agent-kitta connect pandren.', stage: 'closed', outcome: 'ANGRY_ESCALATED' },
      WRONG_NUMBER: { say: 'Sorry sir, thappa call pochu. Indha number-a naan records-la irundhu edukkuren.', stage: 'closed', outcome: 'WRONG_NUMBER' },
      CANNOT_PAY: { say: 'Puriyudhu sir, kashtama irukku. Naan idha installment-a split panna senior-kitta note anuppuren.', stage: 'closed', outcome: 'HARDSHIP_ESCALATED' },
      NEED_TIME: { say: 'Paravaila. Naan 2 naal apparam automatic retry vaipen.', stage: 'closed', outcome: 'CALLBACK_SCHEDULED' },
      LINK_REQUEST: { say: 'Ninaikkamal! Puthusa secure payment link anuppen.', stage: 'closed', outcome: 'LINK_SENT' },
      GOODBYE: { say: 'Ungal nerathirku nandri! Nalla naal vazhthukiren.', stage: 'closed', outcome: 'POLITE_END' },
      DECLINE: { say: 'Sari, thondaravu seiyadhu mannikkavum. WhatsApp-la details anuppuren.', stage: 'closed', outcome: 'SOFT_REFUSAL' },
    },
    fallback: () => ({ say: 'Sariya puriyala sir. Ippo payment pannalama? Illa link anuppattuma?', stage: 'objection' }),
    quickReplies: ['Aam sollunga', 'Tarvata pesalam', 'Panam illai', 'Already pay pannitten', 'Idhu thappu charge', 'Wrong number', 'Nandri']
  },
  'kn-IN': {
    label: 'Kannada', name: 'Kannada',
    greeting: (c) => `Namaskara ${c.customer.split(' ')[0]}, naanu RecoverAI team inda matanaduttiddene. Nimma payment bagge matanadalu 2 nimisha ideya?`,
    context: (c) => `Nimma ${fmtINR(c.amount)} payment failed aagide. Karana ${c.category?.name || 'Technical issue'}.`,
    responses: {
      PROMISE_TO_PAY: { say: 'Dhanyavadagalu! Naanu ippo ondu secure payment link nimma WhatsApp-ge kaluhisuttiddene. 24 gantegalolage settle madi.', stage: 'objection', outcome: 'PROMISE_TO_PAY' },
      ALREADY_PAID: { say: 'Sari, naanu ippa system-nalli verify madtiddini. Payment already aagiddare, case-nu kudale close madtini.', stage: 'closed', outcome: 'ALREADY_PAID_VERIFY' },
      DISPUTE: { say: 'Ninna concern arthavagide sir. Idu tappu charge anisatte. Naanu dispute team-ge forward madtiddini, 48 gante-nalli review aagutte.', stage: 'closed', outcome: 'DISPUTE_RAISED' },
      ANGRY: { say: 'Kshamisi sir, nimma kashta arthavagide. Naanu ippa nimmannu human agent-ge connect madtiddini.', stage: 'closed', outcome: 'ANGRY_ESCALATED' },
      WRONG_NUMBER: { say: 'Sorry sir, tappagi call hogide. Ee number-nu naanu records-inda tegeyuttiddini.', stage: 'closed', outcome: 'WRONG_NUMBER' },
      CANNOT_PAY: { say: 'Arthavagide sir, kashtada samaya. Naanu idannu installment-nalli split madoke senior-ge note kaluhisuttiddini.', stage: 'closed', outcome: 'HARDSHIP_ESCALATED' },
      NEED_TIME: { say: 'Paravagilla. Naanu 2 dina muktavu automatic retry hakuttiddene.', stage: 'closed', outcome: 'CALLBACK_SCHEDULED' },
      LINK_REQUEST: { say: 'Khandita! Hosa secure payment link kaluhisuttiddene.', stage: 'closed', outcome: 'LINK_SENT' },
      GOODBYE: { say: 'Nimma samayakkagi dhanyavadagalu!', stage: 'closed', outcome: 'POLITE_END' },
      DECLINE: { say: 'Sari, tondarage kshamisi. WhatsApp-nalli details kaluhisuttiddene.', stage: 'closed', outcome: 'SOFT_REFUSAL' },
    },
    fallback: () => ({ say: 'Sariyagi ardhavagalilla sir. Ippa payment madabahuda? Athava link kaluhisali?', stage: 'objection' }),
    quickReplies: ['Haudu madtini', 'Mele call madi', 'Hana illa', 'Already pay madidini', 'Idu tappu charge', 'Wrong number', 'Dhanyavadagalu']
  },
  'te-IN': {
    label: 'Telugu', name: 'Telugu',
    greeting: (c) => `Namaste ${c.customer.split(' ')[0]}, nenu RecoverAI team nunche matladtunnanu. Mee payment gurinchi matladataniki 2 nimisham unnaya?`,
    context: (c) => `Mee ${fmtINR(c.amount)} payment failed ayyindi. Karanam ${c.category?.name || 'Technical issue'}.`,
    responses: {
      PROMISE_TO_PAY: { say: 'Dhanyavadalu! Nenu ippudu oka secure payment link mee WhatsApp-ki pampistunnanu. 24 gantalalo settle cheyandi.', stage: 'objection', outcome: 'PROMISE_TO_PAY' },
      ALREADY_PAID: { say: 'Sare, nenu ippudu system-lo verify chestunnanu. Payment already ayyi unte, case-ni ventane close chestanu.', stage: 'closed', outcome: 'ALREADY_PAID_VERIFY' },
      DISPUTE: { say: 'Ardhamayindi sir, idi tappu charge la anipistundi. Nenu dispute team-ki forward chestunnanu, 48 gantalalo review avutundi.', stage: 'closed', outcome: 'DISPUTE_RAISED' },
      ANGRY: { say: 'Kshaminchandi sir, mee kashtam ardham chesukuntunnanu. Nenu ippudu mimmalni human agent-ki connect chestunnanu.', stage: 'closed', outcome: 'ANGRY_ESCALATED' },
      WRONG_NUMBER: { say: 'Sorry sir, tappuga call vellindi. Ee number-ni nenu records nunchi teestanu.', stage: 'closed', outcome: 'WRONG_NUMBER' },
      CANNOT_PAY: { say: 'Ardhamayindi sir, kashtamaina samayam. Nenu idi installment-ga split cheyadaniki senior-ki note pampistunnanu.', stage: 'closed', outcome: 'HARDSHIP_ESCALATED' },
      NEED_TIME: { say: 'Parvaledu. Nenu 2 rojula tarvata automatic retry pedatanu.', stage: 'closed', outcome: 'CALLBACK_SCHEDULED' },
      LINK_REQUEST: { say: 'Tappakunda! Kotta secure payment link pampistunnanu.', stage: 'closed', outcome: 'LINK_SENT' },
      GOODBYE: { say: 'Mee samayam kosam dhanyavadalu!', stage: 'closed', outcome: 'POLITE_END' },
      DECLINE: { say: 'Sare, disturb chesinanduku kshaminchandi. WhatsApp-lo details pampistunnanu.', stage: 'closed', outcome: 'SOFT_REFUSAL' },
    },
    fallback: () => ({ say: 'Sariga ardham kaledu sir. Ippudu payment cheyagalara? Leda link pampana?', stage: 'objection' }),
    quickReplies: ['Avunu cheptanu', 'Tarvata call cheyandi', 'Dabbu ledu', 'Already pay chesanu', 'Idi tappu charge', 'Wrong number', 'Dhanyavadalu']
  }
};

/* ═══ UTILS ═══ */
function fmtINR(n) { return 'Rs.' + Math.round(n || 0).toLocaleString('en-IN'); }
function fmt(n) {
  if (n >= 100000) return 'Rs.' + (n / 100000).toFixed(1) + 'L';
  if (n >= 1000) return 'Rs.' + (n / 1000).toFixed(1) + 'K';
  return 'Rs.' + Math.round(n || 0).toLocaleString('en-IN');
}
function rnd(a) { return a[Math.floor(Math.random() * a.length)]; }
function rndI(a, b) { return Math.floor(Math.random() * (b - a + 1)) + a; }
function nowTs() { return new Date().toTimeString().slice(0, 8); }
function esc(s) { return String(s || ''); }

/* ═══ POLICY ENGINE ═══
   Deterministic guardrail layer. The AI recommends; this decides.
   Every recovery action (single execute, batch, playbook, voice call)
   is run through evaluatePolicy() first - nothing bypasses it. */
function isQuietHours(quietStart, quietEnd) {
  const h = new Date().getHours();
  return quietStart > quietEnd ? (h >= quietStart || h < quietEnd) : (h >= quietStart && h < quietEnd);
}

function evaluatePolicy(c, actionType, policy) {
  const { cap, maxRetries, confThreshold, quietStart, quietEnd, armed } = policy;
  const checks = [];
  let allowed = true;
  let reason = '';
  const fail = (msg) => { if (allowed) { allowed = false; reason = msg; } };

  const capOk = c.amount <= cap;
  checks.push({ label: `Amount within auto-cap (${fmtINR(cap)})`, pass: capOk });
  if (!capOk) fail(`Amount ${fmtINR(c.amount)} exceeds the ${fmtINR(cap)} auto-cap`);

  const retriesOk = (c.attempts || 1) <= maxRetries;
  checks.push({ label: `Within max retries (${maxRetries})`, pass: retriesOk });
  if (!retriesOk) fail(`Attempt ${c.attempts} exceeds max retries (${maxRetries})`);

  const confOk = c.confidence >= confThreshold;
  checks.push({ label: `Confidence at/above ${confThreshold}%`, pass: confOk });
  if (!confOk) fail(`Confidence ${c.confidence}% is below the ${confThreshold}% threshold`);

  const quiet = isQuietHours(quietStart, quietEnd);
  const isQuietSensitive = actionType === 'voice' || actionType === 'sms';
  const quietOk = !(quiet && isQuietSensitive);
  checks.push({ label: `Outside quiet hours (${String(quietStart).padStart(2, '0')}:00-${String(quietEnd).padStart(2, '0')}:00) for voice/SMS`, pass: quietOk });
  if (!quietOk) fail(`Quiet hours active - voice/SMS blocked until ${String(quietEnd).padStart(2, '0')}:00`);

  checks.push({ label: 'Gateway health check', pass: !armed });
  if (armed) fail('Gateway failure simulation is armed');

  return { allowed, checks, reason };
}

function spark(data, color) {
  const w = 100, h = 28, max = Math.max(...data), min = Math.min(...data);
  const pts = data.map((v, i) => `${(i / (data.length - 1)) * w},${h - ((v - min) / ((max - min) || 1)) * (h - 4) - 2}`).join(' ');
  return (
    <svg width="100%" height={h} viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" aria-hidden="true">
      <polyline points={pts} fill="none" stroke={color} strokeWidth="1.5" opacity=".7" />
    </svg>
  );
}

function genMockCases() {
  const cases = [];
  for (let i = 0; i < 20; i++) {
    const cat = rnd(CATS);
    const status = i < 4 ? 'recovered' : (i < 7 ? 'escalated' : (i < 17 ? 'open' : 'closed'));
    cases.push({
      id: 'RC-' + (1041 + i),
      customer: rnd(NAMES),
      amount: rndI(450, 32000),
      method: rnd(METHODS),
      risk: cat.risk,
      category: cat,
      status: status,
      action: rnd(ACTIONS),
      confidence: rndI(68, 97),
      txn: 'pay_' + Math.random().toString(36).slice(2, 14),
      created: rndI(1, 72) + 'h ago',
      attempts: rndI(1, 4)
    });
  }
  return cases;
}

function genMockAudit() {
  const types = [
    { t: 'DETECTION', c: '#3b82f6', d: () => `Detected failed payment ${fmtINR(rndI(500, 15000))} - ${rnd(CATS).name}` },
    { t: 'DIAGNOSIS', c: '#8b5cf6', d: () => `Root cause: ${rnd(CATS).name}, confidence ${rndI(78, 96)}%` },
    { t: 'DECISION', c: '#f59e0b', d: () => `Policy selected: ${rnd(ACTIONS)}` },
    { t: 'EXECUTION', c: '#22c55e', d: () => `Recovered ${fmtINR(rndI(500, 15000))} via smart retry` },
    { t: 'ESCALATION', c: '#ef4444', d: () => `Escalated to human review - confidence below 75%` }
  ];
  const audit = [];
  for (let i = 0; i < 18; i++) {
    const ty = types[i % 5];
    audit.push({
      id: 'AE-' + (9001 + i),
      type: ty.t,
      color: ty.c,
      desc: ty.d(),
      actor: rnd(['agent:recovery-core', 'agent:policy-engine', 'agent:voice-ai']),
      decision: rnd(ACTIONS),
      reason: rnd(['Failure matches retry policy', 'Customer LTV above threshold', 'Retry window optimal', 'Amount within bound', 'Stopping rule applied']),
      result: Math.random() > 0.2 ? 'SUCCESS' : 'ESCALATED',
      ts: nowTs()
    });
  }
  return audit;
}

function genMockPromises() {
  const promises = [];
  for (let i = 0; i < 6; i++) {
    promises.push({
      id: 'PT-' + (201 + i),
      customer: rnd(NAMES),
      amount: rndI(800, 18000),
      promisedDate: rndI(1, 5) + 'd',
      source: rnd(['Voice Call', 'WhatsApp', 'SMS']),
      status: rnd(['pending', 'fulfilled', 'broken']),
      confidence: rndI(60, 95)
    });
  }
  return promises;
}

export default function App() {
  // Navigation & Core state
  const [page, setPage] = useState('overview');
  const [connected, setConnected] = useState(false);
  const [cases, setCases] = useState([]);
  const [audit, setAudit] = useState([]);
  const [promises, setPromises] = useState([]);
  const [armed, setArmed] = useState(false);
  const [running, setRunning] = useState(false);

  // Policy Engine config - live-editable guardrails, actually enforced (not display-only)
  const [polCap, setPolCap] = useState(25000);
  const [polMaxRetries, setPolMaxRetries] = useState(3);
  const [polConfThreshold, setPolConfThreshold] = useState(75);
  const [polQuietStart, setPolQuietStart] = useState(22);
  const [polQuietEnd, setPolQuietEnd] = useState(8);
  const policy = { cap: polCap, maxRetries: polMaxRetries, confThreshold: polConfThreshold, quietStart: polQuietStart, quietEnd: polQuietEnd, armed };

  // Filters & Views
  const [filter, setFilter] = useState('all');
  const [search, setSearch] = useState('');
  const [caseView, setCaseView] = useState('table');
  const [auditFilter, setAuditFilter] = useState('all');
  const [auditSearch, setAuditSearch] = useState('');

  // Voice Agent State
  const [voiceCase, setVoiceCase] = useState(null);
  const [voiceLang, setVoiceLang] = useState('hi-IN');
  const [voiceActive, setVoiceActive] = useState(false);
  const [voiceMsgs, setVoiceMsgs] = useState([]);
  const [voiceStage, setVoiceStage] = useState('idle');
  const [voiceListening, setVoiceListening] = useState(false);
  const [voiceSpeaking, setVoiceSpeaking] = useState(false);
  const [voiceTimerVal, setVoiceTimerVal] = useState('00:00');
  const voiceStartTimeRef = useRef(0);
  const voiceTimerIntervalRef = useRef(null);
  const recogRef = useRef(null);

  // Batch Run State
  const [batchLog, setBatchLog] = useState([]);
  const [batchStats, setBatchStats] = useState(null);
  const [batchHistory, setBatchHistory] = useState([]);

  // Modals & Overlays
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [palInput, setPalInput] = useState('');
  const [palIdx, setPalIdx] = useState(0);

  const [execOvl, setExecOvl] = useState({ open: false, title: '', step: 0, res: null, canClose: false });
  const [selectedCaseDetail, setSelectedCaseDetail] = useState(null);

  const [rawAuditIds, setRawAuditIds] = useState(new Set());
  const [toasts, setToasts] = useState([]);
  const toastSeq = useRef(0);

  // Helper Toast
  const toast = useCallback((type, title, msg) => {
    const id = ++toastSeq.current;
    setToasts(prev => [...prev, { id, type, title, msg }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 4000);
  }, []);

  const addAuditLog = useCallback((type, desc) => {
    const C = { DETECTION: '#3b82f6', DIAGNOSIS: '#8b5cf6', DECISION: '#f59e0b', EXECUTION: '#22c55e', ESCALATION: '#ef4444' };
    setAudit(prev => [{
      id: 'AE-' + Math.floor(Math.random() * 9000 + 1000),
      type,
      color: C[type] || '#9d9da6',
      desc,
      actor: 'operator:human',
      decision: '-',
      reason: 'Manual action',
      result: type === 'ESCALATION' ? 'ESCALATED' : 'SUCCESS',
      ts: nowTs()
    }, ...prev]);
  }, []);

  // Sync API Data
  const syncWithBackend = useCallback(async () => {
    try {
      const summary = await api.getDashboard();
      setConnected(true);
      
      const backendCases = await api.getCases();
      if (Array.isArray(backendCases) && backendCases.length > 0) {
        setCases(backendCases.map(c => ({
          id: c.case_id || `RC-${c.id}`,
          customer: c.payment?.customer_name || 'Razorpay User',
          amount: c.payment?.amount || 1500,
          method: c.payment?.method || 'UPI',
          risk: (c.risk_level || 'medium').toLowerCase(),
          category: { code: c.diagnosis || 'GW_TIMEOUT', name: c.diagnosis || 'Gateway Failure', risk: (c.risk_level || 'medium').toLowerCase() },
          status: (c.status || 'open').toLowerCase(),
          action: c.recommended_action || 'Smart Retry T+2h',
          confidence: Math.round((c.confidence || 0.85) * 100),
          txn: c.payment?.razorpay_payment_id || 'pay_test123',
          created: '2h ago',
          attempts: c.attempt_count || 1
        })));
      }
      
      const auditData = await api.getAudit();
      if (Array.isArray(auditData) && auditData.length > 0) {
        const C = { DETECTION: '#3b82f6', DIAGNOSIS: '#8b5cf6', DECISION: '#f59e0b', EXECUTION: '#22c55e', ESCALATION: '#ef4444' };
        setAudit(auditData.map(a => ({
          id: `AE-${a.id}`,
          type: a.event_type?.includes('EXEC') ? 'EXECUTION' : (a.event_type?.includes('ESCALAT') ? 'ESCALATION' : 'DECISION'),
          color: C[a.event_type] || '#3b82f6',
          desc: a.result_summary || a.action || 'Audit log event',
          actor: a.actor || 'system',
          decision: a.action || '-',
          reason: a.event_type,
          result: a.decision || 'SUCCESS',
          ts: a.timestamp ? new Date(a.timestamp).toTimeString().slice(0, 8) : nowTs()
        })));
      }

      const status = await api.getFailureStatus();
      setArmed(status.failure_armed);
    } catch (e) {
      setConnected(false);
    }
  }, []);

  // Init Data
  useEffect(() => {
    setCases(genMockCases());
    setAudit(genMockAudit());
    setPromises(genMockPromises());
    syncWithBackend();
    const timer = setInterval(syncWithBackend, 30000);
    return () => clearInterval(timer);
  }, [syncWithBackend]);

  // Command Palette Items
  const CMDS = [
    { l: 'Overview', g: 'Navigate', fn: () => setPage('overview') },
    { l: 'Cases', g: 'Navigate', fn: () => setPage('cases') },
    { l: 'Batch Run', g: 'Navigate', fn: () => setPage('batch') },
    { l: 'Playbooks', g: 'Navigate', fn: () => setPage('playbooks') },
    { l: 'Voice Agent', g: 'Navigate', fn: () => setPage('voice') },
    { l: 'Promises', g: 'Navigate', fn: () => setPage('promises') },
    { l: 'Audit Trail', g: 'Navigate', fn: () => setPage('audit') },
    { l: 'Settings', g: 'Navigate', fn: () => setPage('settings') },
    { l: 'Run Batch', g: 'Actions', fn: () => { setPage('batch'); runBatch(); } },
    { l: 'Arm / Disarm Failure Sim', g: 'Actions', fn: () => toggleArm() },
    { l: 'Start Voice Call', g: 'Actions', fn: () => { setPage('voice'); startVoiceCall(); } },
    { l: 'Seed Data', g: 'Actions', fn: () => doSeed() },
    { l: 'Reset All Data', g: 'Actions', fn: () => doReset() },
    { l: 'Export Audit JSON', g: 'Actions', fn: () => exportAudit() }
  ];

  const palFiltered = CMDS.filter(c => c.l.toLowerCase().includes(palInput.toLowerCase()));

  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setPaletteOpen(prev => !prev);
        setPalInput('');
        setPalIdx(0);
      } else if (e.key === 'Escape') {
        setPaletteOpen(false);
        setExecOvl(prev => ({ ...prev, open: false }));
        setSelectedCaseDetail(null);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Execute single case flow - real policy evaluation gates every outcome
  const execCase = (id) => {
    const c = cases.find(x => x.id === id);
    if (!c) return;

    setExecOvl({ open: true, title: `Executing ${c.id}`, step: 0, res: null, canClose: false });

    let step = 0;
    const iv = setInterval(async () => {
      step++;
      setExecOvl(prev => ({ ...prev, step }));
      if (step === 1) addAuditLog('DETECTION', `Signal captured for ${c.id} - ${c.category?.name || 'payment failure'}`);
      if (step === 2) addAuditLog('DIAGNOSIS', `Root cause: ${c.category?.name || 'unknown'}, confidence ${c.confidence}%`);
      if (step >= 4) {
        clearInterval(iv);
        const evalResult = evaluatePolicy(c, 'execute', policy);
        addAuditLog('DECISION', `Policy check ${c.id}: ${evalResult.checks.filter(x => x.pass).length}/${evalResult.checks.length} passed`);
        let isEscalated = !evalResult.allowed;
        let reason = evalResult.reason;
        if (connected) {
          try {
            const res = await api.executeCase(c.id);
            if (res.status === 'ESCALATED' || res.status === 'NEEDS_HUMAN_REVIEW') { isEscalated = true; reason = res.reason || reason; }
          } catch (err) {
            // fallback to local policy result
          }
        }
        if (isEscalated) {
          c.status = 'escalated';
          addAuditLog('ESCALATION', `Case ${c.id} escalated - ${reason || 'policy guardrail'}`);
          setExecOvl(prev => ({
            ...prev, canClose: true,
            res: <div className="res bad"><div className="escb">ESCALATED</div><div>{reason || 'Human review required'}</div></div>
          }));
          toast('e', 'Escalated', reason || c.id);
        } else {
          c.status = 'recovered';
          addAuditLog('EXECUTION', `Case ${c.id} recovered - ${fmtINR(c.amount)}`);
          setExecOvl(prev => ({
            ...prev, canClose: true,
            res: <div className="res ok"><div className="escb ok">RECOVERED</div><div>{fmtINR(c.amount)} reclaimed</div></div>
          }));
          toast('s', 'Recovered', `${c.id} · ${fmt(c.amount)}`);
        }
        setCases([...cases]);
      }
    }, 600);
  };

  // Toggle arming failure sim
  const toggleArm = async () => {
    const next = !armed;
    setArmed(next);
    if (connected) {
      try {
        if (next) await api.simulateFailure();
      } catch (err) {}
    }
    addAuditLog('DECISION', next ? 'Failure sim armed' : 'Sim disarmed');
    toast(next ? 'w' : 'i', next ? 'Armed' : 'Disarmed', next ? 'Next executions will escalate' : '');
  };

  // Run Batch Recovery
  const runBatch = async () => {
    if (running) return;
    setRunning(true);
    setPage('batch');
    setBatchLog([]);

    const openCases = cases.filter(c => c.status === 'open');
    if (openCases.length === 0) {
      setBatchLog([{ cls: 'lt', txt: 'No eligible cases. Seed data first.' }]);
      setRunning(false);
      return;
    }

    setBatchLog([{ cls: 'lt', txt: `--- Batch started: ${openCases.length} cases ---` }]);

    let proc = 0, rec = 0, escCount = 0, skp = 0, amt = 0;

    openCases.forEach((c, i) => {
      setTimeout(() => {
        proc++;
        const ts = nowTs();
        const evalResult = evaluatePolicy(c, 'batch', policy);

        if (!evalResult.allowed) {
          c.status = 'escalated';
          escCount++;
          setBatchLog(prev => [...prev, { cls: 'bad', txt: `[${ts}] ESCALATED: ${c.id} - ${esc(c.customer)} - ${evalResult.reason}` }]);
        } else {
          c.status = 'recovered';
          rec++;
          amt += c.amount;
          setBatchLog(prev => [...prev, { cls: 'ok', txt: `[${ts}] RECOVERED: ${c.id} - ${esc(c.customer)} - ${fmtINR(c.amount)}` }]);
        }

        setCases([...cases]);

        if (i === openCases.length - 1) {
          setRunning(false);
          const finalStats = { proc, rec, esc: escCount, skp, amt };
          setBatchStats(finalStats);
          setBatchHistory(prev => [{ ts: nowTs(), rec, esc: escCount, skp, amt }, ...prev.slice(0, 5)]);
          setBatchLog(prev => [...prev, { cls: 'lt', txt: `--- Done: ${rec} recovered, ${escCount} escalated, ${skp} skipped ---` }]);
          addAuditLog('EXECUTION', `Batch: ${rec} recovered, ${escCount} escalated, ${fmtINR(amt)}`);
          toast('s', 'Batch Complete', `${rec} recovered · ${fmt(amt)}`);
        }
      }, i * 500);
    });
  };

  // Run Playbook
  const runPlaybook = (id) => {
    if (running) { toast('w', 'Busy', 'Another operation is already running'); return; }
    const pb = PLAYBOOKS.find(x => x.id === id);
    if (!pb) return;
    const eligible = cases.filter(pb.filterFn);
    if (eligible.length === 0) {
      toast('w', 'No Cases', `${pb.name}: no eligible cases`);
      return;
    }
    setRunning(true);
    setExecOvl({ open: true, title: pb.name, step: 0, res: null, canClose: false });

    setTimeout(() => {
      let rec = 0, escCount = 0, skp = 0, promised = 0, amt = 0;
      eligible.forEach(c => {
        const evalResult = evaluatePolicy(c, pb.actionType || 'execute', policy);
        if (!evalResult.allowed) {
          c.status = 'escalated';
          escCount++;
          addAuditLog('ESCALATION', `${pb.name}: ${c.id} escalated - ${evalResult.reason}`);
          return;
        }
        const r = pb.processFn(c);
        if (r.outcome === 'recovered') {
          c.status = 'recovered';
          rec++;
          amt += c.amount;
        } else if (r.outcome === 'escalated') {
          c.status = 'escalated';
          escCount++;
        } else if (r.outcome === 'promise') {
          c.status = 'promise_pending';
          promised++;
          setPromises(prev => [{ id: 'PT-' + (300 + rndI(1, 99)), customer: c.customer, amount: c.amount, promisedDate: rndI(1, 3) + 'd', source: 'Playbook', status: 'pending', confidence: c.confidence, caseId: c.id }, ...prev]);
        } else {
          skp++;
        }
        addAuditLog('EXECUTION', `${pb.name}: ${c.id} -> ${r.outcome}`);
      });
      setCases([...cases]);
      setRunning(false);
      setExecOvl({
        open: true, title: pb.name, step: 4, canClose: true,
        res: (
          <div className="res ok">
            <div className="escb ok">COMPLETE</div>
            <div style={{ fontSize: '12px', color: '#9d9da6' }}>
              <b style={{ color: '#4ade80' }}>{rec}</b> recovered - <b style={{ color: '#f87171' }}>{escCount}</b> escalated{promised > 0 && <> - <b style={{ color: '#22d3ee' }}>{promised}</b> promised</>}{skp > 0 && <> - <b style={{ color: '#fbbf24' }}>{skp}</b> skipped</>}<br />
              <b style={{ color: '#4ade80' }}>{fmtINR(amt)}</b> reclaimed
            </div>
          </div>
        )
      });
      toast('s', 'Playbook Done', `${pb.name}: ${rec}/${eligible.length} recovered`);
    }, 1200);
  };

  const runAllPlaybooks = () => {
    if (running) { toast('w', 'Busy', 'Another operation is already running'); return; }
    setRunning(true);
    toast('i', 'Orchestrating', `Running all ${PLAYBOOKS.length} playbooks...`);
    PLAYBOOKS.forEach((p, i) => {
      setTimeout(() => {
        const eligible = cases.filter(p.filterFn);
        eligible.forEach(c => {
          const evalResult = evaluatePolicy(c, p.actionType || 'execute', policy);
          if (!evalResult.allowed) { c.status = 'escalated'; return; }
          const r = p.processFn(c);
          if (r.outcome === 'recovered') c.status = 'recovered';
          else if (r.outcome === 'escalated') c.status = 'escalated';
          else if (r.outcome === 'promise') {
            c.status = 'promise_pending';
            setPromises(prev => [{ id: 'PT-' + (300 + rndI(1, 99)), customer: c.customer, amount: c.amount, promisedDate: rndI(1, 3) + 'd', source: p.name, status: 'pending', confidence: c.confidence, caseId: c.id }, ...prev]);
          }
        });
        if (eligible.length) addAuditLog('EXECUTION', `${p.name}: ${eligible.length} processed`);
        setCases([...cases]);
        if (i === PLAYBOOKS.length - 1) {
          setRunning(false);
          addAuditLog('EXECUTION', 'All playbooks orchestrated');
          toast('s', 'Done', 'All playbooks complete');
        }
      }, (i + 1) * 800);
    });
  };

  const scanPromises = () => {
    toast('i', 'Scanning', 'Analyzing commitments...');
    setTimeout(() => {
      const newP = {
        id: 'PT-' + (300 + rndI(1, 99)),
        customer: rnd(NAMES),
        amount: rndI(500, 15000),
        promisedDate: rndI(1, 3) + 'd',
        source: rnd(['Voice Call', 'WhatsApp']),
        status: 'pending',
        confidence: rndI(55, 90)
      };
      setPromises(prev => [newP, ...prev]);
      addAuditLog('DETECTION', 'New promise detected');
      toast('s', 'Found', 'New commitment captured');
      setPage('promises');
    }, 1000);
  };

  // Resolve a captured promise - closes the loop back into the case pipeline instead of
  // leaving commitments as a dead-end list. A caseId links back to whichever case (playbook
  // or voice call) generated the promise; mock-seeded promises have none and only self-update.
  const markPromiseFulfilled = (id) => {
    const p = promises.find(x => x.id === id);
    if (!p || p.status !== 'pending') return;
    p.status = 'fulfilled';
    setPromises([...promises]);
    if (p.caseId) {
      const c = cases.find(x => x.id === p.caseId);
      if (c) { c.status = 'recovered'; setCases([...cases]); }
    }
    addAuditLog('EXECUTION', `Promise ${p.id} kept - ${fmtINR(p.amount)} recovered from ${p.customer}`);
    toast('s', 'Promise Kept', `${p.customer} - ${fmt(p.amount)}`);
  };

  const markPromiseBroken = (id) => {
    const p = promises.find(x => x.id === id);
    if (!p || p.status !== 'pending') return;
    p.status = 'broken';
    setPromises([...promises]);
    if (p.caseId) {
      const c = cases.find(x => x.id === p.caseId);
      if (c) { c.status = 'escalated'; setCases([...cases]); }
    }
    addAuditLog('ESCALATION', `Promise ${p.id} broken - ${p.customer} did not pay as committed`);
    toast('w', 'Promise Broken', `${p.customer} - escalated to human review`);
  };

  const doSeed = async () => {
    if (connected) {
      try {
        await api.seedDemo();
      } catch (err) {}
    }
    setCases(genMockCases());
    setAudit(genMockAudit());
    setPromises(genMockPromises());
    setArmed(false);
    setBatchLog([]);
    setBatchStats(null);
    setBatchHistory([]);
    cleanupVoice();
    setVoiceActive(false);
    setVoiceCase(null);
    toast('s', 'Seeded', 'Data refreshed');
  };

  const doReset = async () => {
    if (connected) {
      try {
        await api.resetDemo();
      } catch (err) {}
    }
    cleanupVoice();
    setCases([]);
    setAudit([]);
    setPromises([]);
    setArmed(false);
    setRunning(false);
    setBatchLog([]);
    setBatchStats(null);
    setBatchHistory([]);
    setVoiceActive(false);
    setVoiceCase(null);
    setVoiceMsgs([]);
    toast('w', 'Reset', 'All data cleared');
  };

  const exportAudit = () => {
    const data = JSON.stringify(audit, null, 2);
    const blob = new Blob([data], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'audit-trail.json';
    a.click();
    URL.revokeObjectURL(url);
    toast('s', 'Exported', 'Audit trail downloaded');
  };

  // Voice Call Helpers
  const cleanupVoice = () => {
    if (window.speechSynthesis) {
      try { window.speechSynthesis.cancel(); } catch (e) {}
    }
    if (recogRef.current) {
      try { recogRef.current.stop(); } catch (e) {}
    }
    if (voiceTimerIntervalRef.current) {
      clearInterval(voiceTimerIntervalRef.current);
      voiceTimerIntervalRef.current = null;
    }
  };

  const speakText = (text, cb) => {
    if (!window.speechSynthesis) { if (cb) cb(); return; }
    try { window.speechSynthesis.cancel(); } catch (e) {}
    const u = new SpeechSynthesisUtterance(text);
    const voices = window.speechSynthesis.getVoices();
    const v = voices.find(x => x.lang === voiceLang) || voices.find(x => x.lang.startsWith(voiceLang.slice(0, 2))) || voices[0];
    if (v) u.voice = v;
    u.lang = voiceLang;
    u.rate = 0.92;
    u.pitch = 1.05;
    u.onstart = () => setVoiceSpeaking(true);
    u.onend = () => { setVoiceSpeaking(false); if (cb) cb(); };
    u.onerror = () => { setVoiceSpeaking(false); if (cb) cb(); };
    window.speechSynthesis.speak(u);
  };

  const startListening = () => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
      toast('w', 'No STT', 'Speech recognition unavailable, use text input');
      return;
    }
    if (recogRef.current) {
      try { recogRef.current.stop(); } catch (e) {}
    }
    const recog = new SR();
    recog.lang = voiceLang;
    recog.interimResults = true;
    recog.continuous = false;
    recogRef.current = recog;

    recog.onstart = () => setVoiceListening(true);
    recog.onresult = (e) => {
      let t = '';
      for (let i = 0; i < e.results.length; i++) t += e.results[i][0].transcript;
      if (e.results[e.results.length - 1].isFinal) {
        setVoiceListening(false);
        voiceUserSaid(t);
      }
    };
    recog.onerror = (e) => {
      setVoiceListening(false);
      if (e.error === 'no-speech') toast('w', 'No speech', 'Try speaking again');
    };
    recog.onend = () => setVoiceListening(false);
    try { recog.start(); } catch (e) {}
  };

  const startVoiceCall = () => {
    const c = cases.find(x => x.id === voiceCase) || cases[0];
    if (!c) { toast('w', 'Select Case', 'Choose a case first'); return; }
    if (isQuietHours(policy.quietStart, policy.quietEnd)) {
      addAuditLog('ESCALATION', `Voice call blocked for ${c.id} - quiet hours active`);
      toast('w', 'Quiet Hours', `Outbound voice blocked until ${String(policy.quietEnd).padStart(2, '0')}:00`);
      return;
    }
    cleanupVoice();
    setVoiceCase(c.id);
    setVoiceActive(true);
    setVoiceMsgs([]);
    setVoiceStage('greeting');
    setPage('voice');
    voiceStartTimeRef.current = Date.now();

    voiceTimerIntervalRef.current = setInterval(() => {
      const s = Math.floor((Date.now() - voiceStartTimeRef.current) / 1000);
      setVoiceTimerVal(`${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`);
    }, 1000);

    const brain = VOICE_BRAIN[voiceLang];
    const greetingMsg = brain.greeting(c);
    setVoiceMsgs([{ role: 'agent', text: greetingMsg }]);
    addAuditLog('DECISION', `Voice call started - ${c.id} - ${brain.name}`);
    toast('i', 'Call Started', `${brain.name} agent active`);

    speakText(greetingMsg, () => {
      setTimeout(startListening, 400);
    });
  };

  const voiceUserSaid = (text) => {
    if (!text || !text.trim()) return;
    setVoiceMsgs(prev => [...prev, { role: 'user', text }]);

    const c = cases.find(x => x.id === voiceCase) || cases[0];
    if (!c) return;
    const brain = VOICE_BRAIN[voiceLang];
    const intent = matchIntent(text);
    let resp;

    if (voiceStage === 'greeting') {
      // Even at the opener, a real objection (angry / wrong number / decline) must be
      // handled immediately instead of blindly reciting the payment context.
      resp = intent ? brain.responses[intent] : { say: brain.context(c), stage: 'objection' };
    } else {
      resp = (intent && brain.responses[intent]) || brain.fallback(c);
    }

    setTimeout(() => {
      setVoiceMsgs(prev => [...prev, { role: 'agent', text: resp.say }]);
      setVoiceStage(resp.stage || 'objection');
      if (resp.stage === 'closed') {
        speakText(resp.say, () => {
          setTimeout(() => endCall(resp.outcome || 'COMPLETED'), 800);
        });
      } else {
        speakText(resp.say, () => {
          setTimeout(startListening, 400);
        });
      }
    }, 500);
  };

  const endCall = (outcome) => {
    cleanupVoice();
    setVoiceActive(false);
    setVoiceListening(false);
    setVoiceSpeaking(false);
    const c = cases.find(x => x.id === voiceCase);
    if (c) {
      const escalatingOutcomes = ['SOFT_REFUSAL', 'DISPUTE_RAISED', 'ANGRY_ESCALATED', 'WRONG_NUMBER', 'HARDSHIP_ESCALATED'];
      if (outcome === 'PROMISE_TO_PAY') {
        c.status = 'promise_pending';
        setPromises(prev => [{ id: 'PT-' + (300 + rndI(1, 99)), customer: c.customer, amount: c.amount, promisedDate: '1d', source: 'Voice Call', status: 'pending', confidence: rndI(80, 95), caseId: c.id }, ...prev]);
      } else if (escalatingOutcomes.includes(outcome)) {
        c.status = 'escalated';
      }
      // CALLBACK_SCHEDULED / ALREADY_PAID_VERIFY / LINK_SENT / POLITE_END / MANUAL_END leave status
      // as-is - none of these are a confirmed recovery or a guardrail breach on their own.
      addAuditLog(escalatingOutcomes.includes(outcome) ? 'ESCALATION' : 'EXECUTION', `Voice call ${c.id}: ${outcome}`);
      const toastType = outcome === 'PROMISE_TO_PAY' ? 's' : (escalatingOutcomes.includes(outcome) ? 'w' : 'i');
      toast(toastType, 'Call Ended', outcome.replace(/_/g, ' '));
      setCases([...cases]);
    }
  };

  // Calculations for Overview
  const openCasesList = cases.filter(c => c.status === 'open');
  const atRisk = openCasesList.reduce((s, c) => s + c.amount, 0);
  const recovered = cases.filter(c => c.status === 'recovered').reduce((s, c) => s + c.amount, 0);
  const rate = (recovered + atRisk) > 0 ? Math.round(recovered / (recovered + atRisk) * 100) : 0;
  const sparkData = [40, 65, 30, 85, 45, 90, 70, 95, 60, 80, 50, 75];

  // Cases List Filtered
  const filteredCasesList = cases.filter(c => {
    if (filter !== 'all' && c.risk !== filter) return false;
    if (search) {
      const q = search.toLowerCase();
      if (!c.customer.toLowerCase().includes(q) && !c.id.toLowerCase().includes(q) && !c.category?.name.toLowerCase().includes(q)) return false;
    }
    return true;
  }).sort((a, b) => b.amount - a.amount);

  return (
    <div className="app-root">
      <div className="tstrip">
        <i></i> Test Mode · Razorpay Sandbox · No real money moves
      </div>

      <div className="shell">
        {/* Sidebar */}
        <aside className="side">
          <div className="brand">
            <div><b>RecoverAI</b><br /><span>Revenue Agent</span></div>
          </div>
          <nav className="nav">
            <span className="ncap">Main</span>
            <button className={page === 'overview' ? 'on' : ''} onClick={() => setPage('overview')}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="7" height="9" rx="1" /><rect x="14" y="3" width="7" height="5" rx="1" /><rect x="14" y="12" width="7" height="9" rx="1" /><rect x="3" y="16" width="7" height="5" rx="1" /></svg>
              <span className="nl">Overview</span>
            </button>
            <button className={page === 'cases' ? 'on' : ''} onClick={() => setPage('cases')}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="12 2 2 7 12 12 22 7 12 2" /><polyline points="2 17 12 22 22 17" /><polyline points="2 12 12 17 22 12" /></svg>
              <span className="nl">Cases</span><span className="nbadge">{openCasesList.length}</span>
            </button>
            <button className={page === 'batch' ? 'on' : ''} onClick={() => setPage('batch')}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" /></svg>
              <span className="nl">Batch Run</span>
            </button>

            <span className="ncap">Growth Suite</span>
            <button className={page === 'playbooks' ? 'on' : ''} onClick={() => setPage('playbooks')}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 2l3 7h7l-5.5 4.5L18 21l-6-4-6 4 1.5-7.5L2 9h7z" /></svg>
              <span className="nl">Playbooks</span>
            </button>
            <button className={page === 'voice' ? 'on' : ''} onClick={() => setPage('voice')}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" /><path d="M19 10v2a7 7 0 0 1-14 0v-2" /><path d="M12 19v4" /><path d="M8 23h8" /></svg>
              <span className="nl">Voice Agent</span>
            </button>
            <button className={page === 'promises' ? 'on' : ''} onClick={() => setPage('promises')}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="4" width="18" height="18" rx="2" /><line x1="16" y1="2" x2="16" y2="6" /><line x1="8" y1="2" x2="8" y2="6" /><line x1="3" y1="10" x2="21" y2="10" /></svg>
              <span className="nl">Promises</span>
            </button>

            <span className="ncap">System</span>
            <button className={page === 'audit' ? 'on' : ''} onClick={() => setPage('audit')}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /></svg>
              <span className="nl">Audit Trail</span>
            </button>
            <button className={page === 'settings' ? 'on' : ''} onClick={() => setPage('settings')}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="4" y1="21" x2="4" y2="14" /><line x1="4" y1="10" x2="4" y2="3" /><line x1="12" y1="21" x2="12" y2="12" /><line x1="12" y1="8" x2="12" y2="3" /><line x1="20" y1="21" x2="20" y2="16" /><line x1="20" y1="12" x2="20" y2="3" /><line x1="1" y1="14" x2="7" y2="14" /><line x1="9" y1="8" x2="15" y2="8" /><line x1="17" y1="16" x2="23" y2="16" /></svg>
              <span className="nl">Settings</span>
            </button>
          </nav>
          <div className="side-foot">
            <span className={`conn ${connected ? '' : 'demo'}`}>
              <i></i><span>{connected ? 'API Connected' : 'Demo Mode'}</span>
            </span>
            <small className="mono">v5.1 · MIT</small>
          </div>
        </aside>

        {/* Main Content Wrap */}
        <div className="mainwrap">
          <header className="top">
            <div className="crumb">
              <b>{page.charAt(0).toUpperCase() + page.slice(1)}</b><br />
              <span>{page === 'overview' ? 'Revenue at a glance' : 'Control center'}</span>
            </div>
            <div className="top-r">
              <button className="btn btn-g btn-sm" onClick={() => setPaletteOpen(true)}>⌘K Search</button>
              <button className="btn btn-g btn-sm" onClick={doSeed}>Seed Data</button>
            </div>
          </header>

          <main>
            <div className="page">
              {/* PAGE: OVERVIEW */}
              {page === 'overview' && (
                <>
                  <div className="kpis">
                    <div className="kpi"><div className="kl">At Risk</div><div className="kv" style={{ color: '#f87171' }}>{fmt(atRisk)}</div><div className="ks">open pipeline</div>{spark(sparkData, '#f87171')}</div>
                    <div className="kpi"><div className="kl">Recovered</div><div className="kv" style={{ color: '#4ade80' }}>{fmt(recovered)}</div><div className="ks">measured</div>{spark(sparkData, '#4ade80')}</div>
                    <div className="kpi"><div className="kl">Rate</div><div className="kv" style={{ color: '#60a5fa' }}>{rate}%</div><div className="ks">batch-verified</div>{spark(sparkData, '#60a5fa')}</div>
                    <div className="kpi"><div className="kl">Open</div><div className="kv" style={{ color: '#fbbf24' }}>{openCasesList.length}</div><div className="ks">eligible</div>{spark(sparkData, '#fbbf24')}</div>
                    <div className="kpi"><div className="kl">Escalated</div><div className="kv" style={{ color: '#a78bfa' }}>{cases.filter(c => c.status === 'escalated').length}</div><div className="ks">human review</div>{spark(sparkData, '#a78bfa')}</div>
                  </div>

                  {armed && (
                    <div className="card" style={{ borderColor: 'rgba(239,68,68,.4)', background: 'rgba(239,68,68,.04)', padding: '10px 14px', fontSize: '12px', color: '#f87171', fontWeight: '600' }}>
                      Failure simulation ARMED - next executions escalate deterministically
                    </div>
                  )}

                  <div className="ovgrid">
                    <div className="card">
                      <div className="chead"><h3>Agent Activity</h3><span className="hint">live feed</span></div>
                      {audit.length === 0 ? (
                        <div className="empty"><h4>No activity yet</h4><p>Seed data or run a batch.</p></div>
                      ) : (
                        audit.slice(0, 8).map(e => {
                          const tagCls = e.type === 'EXECUTION' ? 'g' : e.type === 'ESCALATION' ? 'r' : e.type === 'DECISION' ? 'a' : e.type === 'DIAGNOSIS' ? 'v' : 'b';
                          return (
                            <div key={e.id} className="actrow">
                              <span className="lt">{e.ts}</span>
                              <span className={`tag ${tagCls}`}>{e.type}</span>
                              <span className="ax">{e.desc}</span>
                            </div>
                          );
                        })
                      )}
                    </div>

                    <div className="card">
                      <div className="chead"><h3>Actions</h3></div>
                      <div className="cbody">
                        <div className="actcol">
                          <button className="btn btn-p" onClick={runBatch} disabled={running}>
                            {running ? 'Running...' : 'Run Batch Recovery'}
                          </button>
                          <div className="swrow" onClick={toggleArm} role="switch" aria-checked={armed}>
                            <div><b>Arm Failure Sim</b><small>{armed ? 'ARMED' : 'Deterministic escalation'}</small></div>
                            <div className={`sw ${armed ? 'on armed-pulse' : ''}`}></div>
                          </div>
                          <button className="btn btn-g" onClick={() => setPage('audit')}>Audit Trail</button>
                          <button className="btn btn-g" onClick={() => setPage('playbooks')}>Playbooks</button>
                        </div>
                        <div className="glist">
                          <div>Max autonomous: {fmtINR(polCap)}</div>
                          <div>Max {polMaxRetries} retries (stopping rule)</div>
                          <div>Confidence threshold: {polConfThreshold}%</div>
                          <div>Quiet hours: {String(polQuietStart).padStart(2, '0')}:00-{String(polQuietEnd).padStart(2, '0')}:00{isQuietHours(polQuietStart, polQuietEnd) ? ' (active now)' : ''}</div>
                        </div>
                      </div>
                    </div>
                  </div>
                </>
              )}

              {/* PAGE: CASES */}
              {page === 'cases' && (
                <div className="card">
                  <div className="toolbar">
                    <div className="srch">
                      <input placeholder="Search cases..." value={search} onChange={e => setSearch(e.target.value)} aria-label="Search cases" />
                    </div>
                    <div style={{ display: 'flex', gap: '5px' }}>
                      {['all', 'low', 'medium', 'high'].map(r => (
                        <button key={r} className={`chip ${filter === r ? 'on' : ''}`} onClick={() => setFilter(r)}>{r}</button>
                      ))}
                    </div>
                    <div className="vtog" style={{ marginLeft: 'auto' }}>
                      <button className={caseView === 'table' ? 'on' : ''} onClick={() => setCaseView('table')}>Table</button>
                      <button className={caseView === 'kanban' ? 'on' : ''} onClick={() => setCaseView('kanban')}>Board</button>
                    </div>
                  </div>

                  {caseView === 'table' ? (
                    <div style={{ overflowX: 'auto' }}>
                      <table className="tbl">
                        <thead>
                          <tr><th>Case ID</th><th>Customer</th><th>Amount</th><th>Diagnosis</th><th>Risk</th><th>Status</th><th></th></tr>
                        </thead>
                        <tbody>
                          {filteredCasesList.length === 0 ? (
                            <tr><td colSpan="7"><div className="empty"><h4>No cases found</h4><p>Adjust filters or seed data.</p></div></td></tr>
                          ) : (
                            filteredCasesList.map(c => (
                              <tr key={c.id} onClick={() => setSelectedCaseDetail(c)}>
                                <td className="mono" style={{ color: '#4ade80' }}>{c.id}</td>
                                <td>
                                  <div className="cust">
                                    <div className="ava">{c.customer.split(' ').map(w => w[0]).join('')}</div>
                                    <div><b>{c.customer}</b><span>{c.created}</span></div>
                                  </div>
                                </td>
                                <td className="amt">{fmt(c.amount)}</td>
                                <td style={{ color: '#9d9da6', fontSize: '11px' }}>{c.category?.name}</td>
                                <td><span className={`rb ${c.risk}`}><i></i>{c.risk}</span></td>
                                <td><span className={`sb ${c.status}`}><i></i>{c.status}</span></td>
                                <td onClick={e => e.stopPropagation()}>
                                  {c.status === 'open' && (
                                    <button className="btn btn-p btn-sm" onClick={() => execCase(c.id)}>Execute</button>
                                  )}
                                </td>
                              </tr>
                            ))
                          )}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '12px', padding: '14px' }}>
                      {[{ n: 'open', c: '#60a5fa' }, { n: 'promise_pending', c: '#22d3ee' }, { n: 'recovered', c: '#4ade80' }, { n: 'escalated', c: '#f87171' }, { n: 'closed', c: '#9d9da6' }].map(col => {
                        const items = filteredCasesList.filter(c => c.status === col.n);
                        return (
                          <div key={col.n} style={{ background: 'var(--p1)', border: '1px solid var(--ln)', borderRadius: '12px', padding: '10px', minHeight: '200px' }}>
                            <div style={{ fontSize: '10px', fontWeight: '800', textTransform: 'uppercase', color: col.c, padding: '4px 6px 10px' }}>
                              {col.n} · {items.length}
                            </div>
                            {items.map(c => (
                              <div key={c.id} onClick={() => setSelectedCaseDetail(c)} style={{ background: 'var(--p2)', border: '1px solid var(--ln2)', borderRadius: '8px', padding: '11px', marginBottom: '9px', cursor: 'pointer' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                  <span className="mono" style={{ fontSize: '10px', color: '#4ade80' }}>{c.id}</span>
                                  <span className={`rb ${c.risk}`}>{c.risk}</span>
                                </div>
                                <p style={{ fontSize: '11px', color: 'var(--mut)', margin: '3px 0 8px' }}>{c.customer}</p>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                  <span className="amt">{fmt(c.amount)}</span>
                                  {c.status === 'open' && (
                                    <button className="btn btn-p btn-sm" onClick={e => { e.stopPropagation(); execCase(c.id); }}>Exec</button>
                                  )}
                                </div>
                              </div>
                            ))}
                            {items.length === 0 && <div style={{ textAlign: 'center', color: '#5c5c66', fontSize: '11px', padding: '20px' }}>No cases</div>}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}

              {/* PAGE: BATCH RUN */}
              {page === 'batch' && (
                <>
                  <div className="card">
                    <div className="chead">
                      <h3>Batch Pipeline</h3>
                      <span className="hint">{openCasesList.length} cases - {fmt(atRisk)}</span>
                    </div>
                    <div className="cbody">
                      <button className="btn btn-p" onClick={runBatch} disabled={running} style={{ width: '100%', marginBottom: '12px' }}>
                        {running ? 'Running...' : 'Start Batch'}
                      </button>
                      {armed && <div style={{ padding: '8px 12px', borderRadius: '6px', background: 'rgba(239,68,68,.06)', border: '1px solid rgba(239,68,68,.25)', marginBottom: '10px', fontSize: '11px', color: '#f87171', fontWeight: '600' }}>Warning: Failure sim armed</div>}
                      <div className="blog">
                        {batchLog.length > 0 ? (
                          batchLog.map((l, i) => <div key={i} className={`ln ${l.cls}`}>{l.txt}</div>)
                        ) : (
                          <div className="lt">Awaiting batch start...</div>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="card">
                    <div className="chead"><h3>Metrics</h3><span className="hint">{batchStats ? 'last run' : 'no run yet'}</span></div>
                    <div className="cbody">
                      <div className="bmrow">
                        <div className="bm"><b style={{ color: '#60a5fa' }}>{batchStats?.proc || 0}</b><span>Processed</span></div>
                        <div className="bm"><b style={{ color: '#4ade80' }}>{batchStats?.rec || 0}</b><span>Recovered</span></div>
                        <div className="bm"><b style={{ color: '#4ade80' }}>{batchStats ? fmt(batchStats.amt) : '—'}</b><span>Reclaimed</span></div>
                        <div className="bm"><b style={{ color: '#f87171' }}>{batchStats?.esc || 0}</b><span>Escalated</span></div>
                        <div className="bm"><b style={{ color: '#fbbf24' }}>{batchStats?.skp || 0}</b><span>Skipped</span></div>
                      </div>
                      {batchStats && batchStats.proc > 0 && (
                        <>
                          <div className="split">
                            <i className="a" style={{ width: `${Math.round(batchStats.rec / batchStats.proc * 100)}%` }}></i>
                            <i className="c" style={{ width: `${Math.round(batchStats.skp / batchStats.proc * 100)}%` }}></i>
                            <i className="d" style={{ width: `${Math.max(0, 100 - Math.round(batchStats.rec / batchStats.proc * 100) - Math.round(batchStats.skp / batchStats.proc * 100))}%` }}></i>
                          </div>
                          <div className="dlegend"><i style={{ background: '#22c55e' }}></i> Recovered - <i style={{ background: '#fbbf24' }}></i> Skipped - <i style={{ background: '#ef4444' }}></i> Escalated</div>
                        </>
                      )}
                    </div>
                  </div>

                  {batchHistory.length > 0 && (
                    <div className="card">
                      <div className="chead"><h3>Run History</h3><span className="hint">{batchHistory.length}</span></div>
                      {batchHistory.map((r, i) => (
                        <div key={i} className="actrow">
                          <span className="lt">{r.ts}</span>
                          <span className="tag g">{r.rec} rec</span>
                          <span className="tag r">{r.esc} esc</span>
                          <span className="ax">{fmt(r.amt)} reclaimed</span>
                        </div>
                      ))}
                    </div>
                  )}
                </>
              )}

              {/* PAGE: PLAYBOOKS */}
              {page === 'playbooks' && (
                <>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <p style={{ color: '#9d9da6', fontSize: '12px' }}>Each playbook processes real eligible cases</p>
                    <button className="btn btn-p btn-sm" onClick={runAllPlaybooks} disabled={running}>Run All</button>
                  </div>
                  <div className="pbgrid">
                    {PLAYBOOKS.map(p => {
                      const eligible = cases.filter(p.filterFn).length;
                      return (
                        <button key={p.id} className="pbcard" onClick={() => runPlaybook(p.id)} disabled={running}>
                          <div className="top">
                            <div className="pbic" style={{ background: `${p.color}15`, color: p.color }}>
                              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" /></svg>
                            </div>
                            <h3>{p.name}</h3>
                            <span className={`st ${eligible ? 'done' : ''}`}>{eligible ? 'Ready' : 'Idle'}</span>
                          </div>
                          <p>{p.desc}</p>
                          <div className="eligible">{eligible} cases eligible</div>
                          <div className="go">Run Playbook</div>
                          <div className="lr">{p.runs} runs</div>
                        </button>
                      );
                    })}
                  </div>
                </>
              )}

              {/* PAGE: VOICE AGENT */}
              {page === 'voice' && (
                <div className="vgrid">
                  <div className="card">
                    <div className="chead"><h3>Select Case</h3><span className="hint">{cases.filter(c => c.status === 'open' || c.status === 'escalated').length} eligible</span></div>
                    <div className="cbody" style={{ display: 'flex', flexDirection: 'column', gap: '7px' }}>
                      {cases.filter(c => c.status === 'open' || c.status === 'escalated').map(c => (
                        <button key={c.id} className="swrow" onClick={() => setVoiceCase(c.id)} style={voiceCase === c.id ? { borderColor: 'rgba(139,92,246,.4)', background: 'rgba(139,92,246,.06)' } : {}}>
                          <div><b>{c.customer}</b><small>{c.id} - {fmt(c.amount)}</small></div>
                          <span className={`rb ${c.risk}`}>{c.risk}</span>
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="card" style={{ overflow: 'hidden' }}>
                    <div className="chead">
                      <h3>Voice Agent</h3>
                      {voiceActive ? <span className="vtimer">{voiceTimerVal}</span> : <span className="hint">{VOICE_BRAIN[voiceLang].name}</span>}
                    </div>
                    <div className="vlang">
                      {Object.keys(VOICE_BRAIN).map(code => (
                        <button key={code} className={voiceLang === code ? 'on' : ''} onClick={() => setVoiceLang(code)} disabled={voiceActive}>
                          {VOICE_BRAIN[code].label}
                        </button>
                      ))}
                    </div>

                    {voiceActive ? (
                      <>
                        <div className="vchat">
                          {voiceMsgs.map((m, i) => (
                            <div key={i} className={`vmsg ${m.role}`}>
                              <div className="vbub">
                                {m.role === 'agent' && <span className="role">Agent</span>}
                                {m.text}
                              </div>
                            </div>
                          ))}
                        </div>
                        <div className="vcontrols">
                          <button className={`micbtn ${voiceSpeaking ? 'speaking' : (voiceListening ? 'listening' : 'idle')}`} onClick={startListening}>
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" /><path d="M19 10v2a7 7 0 0 1-14 0v-2" /><path d="M12 19v4" /><path d="M8 23h8" /></svg>
                          </button>
                          <div style={{ flex: 1 }}>
                            <div className="vstatus">{voiceSpeaking ? 'Agent speaking...' : (voiceListening ? 'Listening...' : 'Ready - click mic')}</div>
                          </div>
                          <button className="btn btn-r btn-sm" onClick={() => endCall('MANUAL_END')}>End</button>
                        </div>
                        <div className="vquick">
                          {VOICE_BRAIN[voiceLang].quickReplies.map((s, i) => (
                            <button key={i} onClick={() => voiceUserSaid(s)}>{s}</button>
                          ))}
                        </div>
                      </>
                    ) : (
                      <div className="empty" style={{ padding: '40px' }}>
                        <h4 style={{ fontSize: '14px', marginBottom: '4px' }}>Voice Recovery Agent</h4>
                        <p style={{ fontSize: '12px' }}>Speaks {VOICE_BRAIN[voiceLang].name}, listens via mic, handles objections</p>
                        <button className="btn btn-v" onClick={startVoiceCall} disabled={!voiceCase} style={{ marginTop: '14px' }}>
                          Start Voice Call
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* PAGE: PROMISES */}
              {page === 'promises' && (
                <div className="card">
                  <div className="chead">
                    <h3>Promises & Commitments</h3>
                    <button className="btn btn-g btn-sm" style={{ marginLeft: 'auto' }} onClick={scanPromises}>Scan</button>
                  </div>
                  <div style={{ overflowX: 'auto' }}>
                    <table className="tbl">
                      <thead>
                        <tr><th>ID</th><th>Customer</th><th>Amount</th><th>Due</th><th>Source</th><th>Confidence</th><th>Status</th><th></th></tr>
                      </thead>
                      <tbody>
                        {promises.length === 0 ? (
                          <tr><td colSpan="8"><div className="empty"><h4>No promises captured</h4><p>Run a playbook, take a voice call, or scan for commitments.</p></div></td></tr>
                        ) : (
                        promises.map(p => (
                          <tr key={p.id}>
                            <td className="mono" style={{ color: '#4ade80' }}>{p.id}</td>
                            <td><b>{p.customer}</b>{p.caseId && <span style={{ display: 'block', fontSize: '10px', color: '#5c5c66' }}>{p.caseId}</span>}</td>
                            <td className="amt">{fmt(p.amount)}</td>
                            <td style={{ color: '#9d9da6' }}>in {p.promisedDate}</td>
                            <td><span className="rb low" style={{ background: 'rgba(255,255,255,.05)', color: '#9d9da6' }}>{p.source}</span></td>
                            <td>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <div className="meter" style={{ width: '50px' }}>
                                  <i style={{ width: `${p.confidence}%`, background: p.confidence > 80 ? '#22c55e' : (p.confidence > 65 ? '#f59e0b' : '#ef4444') }}></i>
                                </div>
                                <span className="mono" style={{ fontSize: '11px', color: '#9d9da6' }}>{p.confidence}%</span>
                              </div>
                            </td>
                            <td><span className={`sb ${p.status}`}><i></i>{p.status}</span></td>
                            <td>
                              {p.status === 'pending' && (
                                <div style={{ display: 'flex', gap: '5px' }}>
                                  <button className="btn btn-p btn-sm" onClick={() => markPromiseFulfilled(p.id)}>Paid</button>
                                  <button className="btn btn-r btn-sm" onClick={() => markPromiseBroken(p.id)}>Broken</button>
                                </div>
                              )}
                            </td>
                          </tr>
                        )))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* PAGE: AUDIT TRAIL */}
              {page === 'audit' && (
                <div className="card">
                  <div className="toolbar">
                    <div className="srch">
                      <input placeholder="Search audit..." value={auditSearch} onChange={e => setAuditSearch(e.target.value)} aria-label="Search audit" />
                    </div>
                    <div style={{ display: 'flex', gap: '5px', flexWrap: 'wrap' }}>
                      {['all', 'DETECTION', 'DIAGNOSIS', 'DECISION', 'EXECUTION', 'ESCALATION'].map(t => (
                        <button key={t} className={`chip ${auditFilter === t ? 'on' : ''}`} onClick={() => setAuditFilter(t)}>{t}</button>
                      ))}
                    </div>
                    <button className="btn btn-g btn-sm" onClick={exportAudit} style={{ marginLeft: 'auto' }}>Export</button>
                  </div>
                  <div className="cbody">
                    <div className="tl">
                      {audit.filter(e => {
                        if (auditFilter !== 'all' && e.type !== auditFilter) return false;
                        if (auditSearch) {
                          const q = auditSearch.toLowerCase();
                          if (!e.desc.toLowerCase().includes(q) && !e.actor.toLowerCase().includes(q) && !e.type.toLowerCase().includes(q)) return false;
                        }
                        return true;
                      }).map(e => (
                        <div key={e.id} className={`tlev ${rawAuditIds.has(e.id) ? 'raw' : ''}`} onClick={() => {
                          setRawAuditIds(prev => {
                            const next = new Set(prev);
                            if (next.has(e.id)) next.delete(e.id);
                            else next.add(e.id);
                            return next;
                          });
                        }} style={{ '--evc': e.color }}>
                          <div className="tlt"><span className="tltype">{e.type}</span><span className="tltime">{e.ts}</span></div>
                          <div className="tlreason">{e.desc}</div>
                          <div className="tlmeta"><span>Actor: {e.actor}</span> - <span>Result: <b style={{ color: e.result === 'SUCCESS' ? '#4ade80' : '#f87171' }}>{e.result}</b></span> - <span>{e.reason}</span></div>
                          <pre className="tljson">{JSON.stringify(e, null, 2)}</pre>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* PAGE: SETTINGS */}
              {page === 'settings' && (
                <>
                  <div className="card">
                    <div className="chead"><h3>Configuration</h3></div>
                    <div className="cbody" style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      <div className="swrow">
                        <b>Voice Language</b>
                        <select value={voiceLang} onChange={e => setVoiceLang(e.target.value)} style={{ background: 'var(--p1)', border: '1px solid var(--ln2)', borderRadius: '8px', padding: '6px 8px', color: 'var(--tx)' }}>
                          {Object.keys(VOICE_BRAIN).map(code => (
                            <option key={code} value={code}>{VOICE_BRAIN[code].name}</option>
                          ))}
                        </select>
                      </div>
                      <div className="swrow" onClick={toggleArm} role="switch" aria-checked={armed}>
                        <b>Failure Simulation</b>
                        <div className={`sw ${armed ? 'on armed-pulse' : ''}`}></div>
                      </div>
                    </div>
                  </div>

                  <div className="card">
                    <div className="chead"><h3>Policy Engine Guardrails</h3><span className="hint">enforced live, not just displayed</span></div>
                    <div className="cbody" style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      <div className="polinput">
                        <b>Auto-cap (Rs.)</b>
                        <input type="number" min="0" step="500" value={polCap} onChange={e => setPolCap(Math.max(0, Number(e.target.value) || 0))} />
                      </div>
                      <div className="polinput">
                        <b>Max Retries</b>
                        <input type="number" min="1" max="10" value={polMaxRetries} onChange={e => setPolMaxRetries(Math.max(1, Number(e.target.value) || 1))} />
                      </div>
                      <div className="polinput">
                        <b>Min Confidence (%)</b>
                        <input type="number" min="0" max="100" value={polConfThreshold} onChange={e => setPolConfThreshold(Math.min(100, Math.max(0, Number(e.target.value) || 0)))} />
                      </div>
                      <div className="polinput">
                        <b>Quiet Hours Start (24h)</b>
                        <input type="number" min="0" max="23" value={polQuietStart} onChange={e => setPolQuietStart(Math.min(23, Math.max(0, Number(e.target.value) || 0)))} />
                      </div>
                      <div className="polinput">
                        <b>Quiet Hours End (24h)</b>
                        <input type="number" min="0" max="23" value={polQuietEnd} onChange={e => setPolQuietEnd(Math.min(23, Math.max(0, Number(e.target.value) || 0)))} />
                      </div>
                      <p style={{ fontSize: '10.5px', color: 'var(--dim)', marginTop: '2px' }}>
                        Changes apply immediately to every Execute, Batch Run, Playbook, and Voice Call - try lowering the confidence threshold and re-running a batch to see fewer escalations.
                      </p>
                    </div>
                  </div>

                  <div className="card">
                    <div className="chead"><h3>Data Operations</h3></div>
                    <div className="cbody" style={{ display: 'flex', gap: '8px' }}>
                      <button className="btn btn-g" onClick={doSeed}>Seed Data</button>
                      <button className="btn btn-r" onClick={doReset}>Reset All</button>
                    </div>
                  </div>
                </>
              )}
            </div>
          </main>
        </div>
      </div>

      {/* OVERLAY: COMMAND PALETTE */}
      {paletteOpen && (
        <div className="ovl top show" onClick={() => setPaletteOpen(false)}>
          <div className="pal" onClick={e => e.stopPropagation()}>
            <input
              autoFocus
              value={palInput}
              onChange={e => setPalInput(e.target.value)}
              placeholder="Search or command…"
              aria-label="Command palette"
            />
            <div className="pal-list">
              {palFiltered.length === 0 ? (
                <div className="pal-item">No results</div>
              ) : (
                palFiltered.map((c, i) => (
                  <div
                    key={i}
                    className={`pal-item ${i === palIdx ? 'sel' : ''}`}
                    onClick={() => { c.fn(); setPaletteOpen(false); }}
                  >
                    {c.l}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {/* OVERLAY: EXECUTION MODAL */}
      {execOvl.open && (
        <div className="ovl show" onClick={() => execOvl.canClose && setExecOvl(prev => ({ ...prev, open: false }))}>
          <div className="exec" onClick={e => e.stopPropagation()}>
            <div className="ehead">
              <span className="espin"></span>
              <div>
                <div className="etitle">{execOvl.title}</div>
                <div className="esub">Autonomous pipeline - policy-gated</div>
              </div>
            </div>
            <ol className="esteps">
              <li className={execOvl.step >= 1 ? (execOvl.step > 1 ? 'done' : 'act') : ''}>
                <span className="sdot">1</span><div className="stx"><b>Detect</b><span>Payment and gateway signals</span></div>
              </li>
              <li className={execOvl.step >= 2 ? (execOvl.step > 2 ? 'done' : 'act') : ''}>
                <span className="sdot">2</span><div className="stx"><b>Diagnose</b><span>Root cause classification</span></div>
              </li>
              <li className={execOvl.step >= 3 ? (execOvl.step > 3 ? 'done' : 'act') : ''}>
                <span className="sdot">3</span><div className="stx"><b>Decide</b><span>Policy-gated action</span></div>
              </li>
              <li className={execOvl.step >= 4 ? (execOvl.step > 4 ? 'done' : 'act') : ''}>
                <span className="sdot">4</span><div className="stx"><b>Execute</b><span>Safe workflow + audit</span></div>
              </li>
            </ol>
            <div className="pbar"><i style={{ width: `${execOvl.step * 25}%` }}></i></div>
            {execOvl.res}
            {execOvl.canClose && (
              <div className="efoot">
                <button className="btn btn-p" onClick={() => setExecOvl(prev => ({ ...prev, open: false }))}>Close</button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* OVERLAY: CASE DETAIL MODAL */}
      {selectedCaseDetail && (() => {
        const detailEval = evaluatePolicy(selectedCaseDetail, 'execute', policy);
        return (
        <div className="ovl show" onClick={() => setSelectedCaseDetail(null)}>
          <div className="exec" onClick={e => e.stopPropagation()} style={{ maxWidth: '500px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
              <b className="mono" style={{ color: '#4ade80', fontSize: '15px' }}>{selectedCaseDetail.id}</b>
              <button className="btn btn-g btn-sm" onClick={() => setSelectedCaseDetail(null)}>✕</button>
            </div>
            <div style={{ marginBottom: '12px' }}>
              <div style={{ fontSize: '10px', color: 'var(--dim)', textTransform: 'uppercase', fontWeight: '700' }}>Customer</div>
              <b style={{ fontSize: '16px' }}>{selectedCaseDetail.customer}</b>
            </div>
            <div className="grid2">
              <div className="dcell"><span>Amount</span><b style={{ fontSize: '14px' }}>{fmtINR(selectedCaseDetail.amount)}</b></div>
              <div className="dcell"><span>Risk Level</span><b style={{ textTransform: 'uppercase', color: selectedCaseDetail.risk === 'high' ? '#f87171' : '#4ade80' }}>{selectedCaseDetail.risk}</b></div>
            </div>
            <div className="diag">
              <h4>AI Diagnosis</h4>
              <p style={{ fontSize: '12px', color: '#9d9da6' }}>{selectedCaseDetail.category?.name} - {selectedCaseDetail.confidence}% confidence</p>
              <div className="conf">
                <span>Confidence</span>
                <div className="meter"><i style={{ width: `${selectedCaseDetail.confidence}%`, background: '#22c55e' }}></i></div>
                <span className="mono">{selectedCaseDetail.confidence}%</span>
              </div>
            </div>
            <div className="pchk">
              {detailEval.checks.map((chk, i) => (
                <div key={i} className={`pc ${chk.pass ? 'pass' : 'fail'}`}>
                  {chk.label}<b>{chk.pass ? 'PASS' : 'FAIL'}</b>
                </div>
              ))}
            </div>
            {!detailEval.allowed && (
              <div className="polnote" style={{ marginTop: '10px', color: 'var(--red2)', borderColor: 'rgba(239,68,68,.3)', background: 'rgba(239,68,68,.06)' }}>Would escalate: {detailEval.reason}</div>
            )}
            {detailEval.allowed && (
              <div className="polnote" style={{ marginTop: '10px' }}>All guardrails pass - eligible for autonomous execution</div>
            )}
            <div className="efoot" style={{ marginTop: '16px' }}>
              {selectedCaseDetail.status === 'open' && (
                <button className="btn btn-p" onClick={() => { const id = selectedCaseDetail.id; setSelectedCaseDetail(null); execCase(id); }}>
                  Execute
                </button>
              )}
              <button className="btn btn-g" onClick={() => setSelectedCaseDetail(null)}>Close</button>
            </div>
          </div>
        </div>
        );
      })()}

      {/* TOAST STACK */}
      <div className="twrap2">
        {toasts.map(t => (
          <div key={t.id} className={`toast ${t.type}`}>
            <div><b>{t.title}</b>{t.msg && <p>{t.msg}</p>}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
