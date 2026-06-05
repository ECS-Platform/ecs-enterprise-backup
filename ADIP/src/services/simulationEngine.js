/**
 * Enterprise banking simulation engine.
 *
 * Drives a SimulationState through a single, correlated tick every 30 seconds.
 * Instead of perturbing each metric with an independent Math.random(), this
 * engine maintains a small set of latent "driver" variables that model the
 * operational reality of an enterprise bank:
 *
 *   - simulated hour-of-day (advances ~30 simulated minutes per tick)
 *   - per-channel load factors for UPI / IMPS / NEFT / RTGS / Merchant Payments
 *   - architectural service health (Fraud Engine, UPI Switch, Payment Gateway, …)
 *   - active incidents, active governance findings, at-risk releases, escaped defects
 *
 * Every visible KPI is then derived from those drivers via deterministic
 * business rules so that:
 *
 *   - More incidents       -> lower operational / production / domain health
 *   - Failed releases      -> lower release confidence & readiness
 *   - More findings        -> higher governance risk (lower score)
 *   - More escaped defects -> lower delivery score & test effectiveness
 *
 * A seeded RNG (mulberry32) is used only to add small bounded jitter; the
 * underlying movement is causal, not noise.
 */

import {
  PAYMENT_CHANNELS,
  INCIDENT_CATALOG_FULL,
  GOVERNANCE_CATALOG_FULL,
  createInitialState,
  clamp,
} from './mockDataEngine.js';

const REFRESH_MS = 30_000;
const SIM_MINUTES_PER_TICK = 30;

let intervalId = null;

export function getRefreshInterval() {
  return REFRESH_MS;
}

/* ------------------------------------------------------------------ */
/* Deterministic seeded RNG (mulberry32)                              */
/* ------------------------------------------------------------------ */

function makeRng(seed) {
  let a = seed >>> 0;
  return function rng() {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4_294_967_296;
  };
}

const round = (n, d = 0) => {
  const f = 10 ** d;
  return Math.round(n * f) / f;
};

/* ------------------------------------------------------------------ */
/* Driver bootstrap & advancement                                     */
/* ------------------------------------------------------------------ */

function bootstrapDrivers(state) {
  const seed = 0x9e3779b1; // golden-ratio constant
  const drivers = {
    rngSeed: seed,
    simHour: 9,          // start at 09:00 — peak ramping
    simDayIndex: 0,
    incidentMomentum: 0.35,
    releasePressure: 0.40,
    governancePressure: 0.45,
    testingBacklog: 0.30,
    fraudEngineHealth: 90,
    upiSwitchHealth: 94,
    paymentGatewayHealth: 96,
    coreBankingHealth: 98,
    activeIncidents: INCIDENT_CATALOG_FULL.slice(0, 4).map((i, idx) => ({
      ...i,
      ageTicks: idx + 1,
      status: idx === 0 ? 'Investigating' : 'Mitigating',
    })),
    activeFindings: GOVERNANCE_CATALOG_FULL.slice(0, 5).map((f) => ({ ...f })),
    atRiskReleaseIds: ['R-UPI-24.6', 'R-PAY-12.2'],
    escapedDefects: 2,
    foundDefects: 19,
    technicalDebt: 34,
    historicalKpis: {
      'Delivery Health': sevenDayBuffer(94),
      'Production Health': sevenDayBuffer(92),
      'Governance Health': sevenDayBuffer(96),
      'Engineering Health': sevenDayBuffer(89),
    },
    incidentTrendBuffer: [2, 1, 3, 2, 4, 1, 0],
    defectTrendBuffer: [
      { found: 24, escaped: 2 },
      { found: 19, escaped: 1 },
      { found: 22, escaped: 3 },
      { found: 17, escaped: 1 },
    ],
    confidenceTrendBuffer: [
      { net: 88, mobile: 90, payments: 84 },
      { net: 89, mobile: 91, payments: 85 },
      { net: 90, mobile: 90, payments: 86 },
      { net: 91, mobile: 92, payments: 85 },
      { net: 92, mobile: 91, payments: 87 },
      { net: 93, mobile: 91, payments: 86 },
    ],
  };
  return { ...state, _drivers: drivers };
}

function sevenDayBuffer(base) {
  return Array.from({ length: 7 }, (_, i) => ({
    day: `D${i + 1}`,
    value: clamp(base + Math.round(Math.sin(i * 0.8) * 3), 80, 99),
  }));
}

/**
 * Advance the latent driver state. This is the "physics" of the simulation:
 * load profiles, incident generation, recovery, dependency degradation.
 */
function advanceDrivers(prev, rng) {
  const d = { ...prev };
  d.rngSeed = (prev.rngSeed + 0x9e3779b1) >>> 0;

  // Time of day advances ~30 simulated minutes per real tick.
  d.simHour = (prev.simHour + SIM_MINUTES_PER_TICK / 60) % 24;
  if (d.simHour < prev.simHour) d.simDayIndex = prev.simDayIndex + 1;

  // --- architectural service health: slow random walk biased to high values
  // Each tick it pulls a little toward 95–98 with occasional dips when
  // incidents are active in their dependency chain.
  const upiPressureFromIncidents = countActive(prev.activeIncidents, 'upi') * 4;
  const merchantPressureFromIncidents = countActive(prev.activeIncidents, 'merchant') * 3;
  d.fraudEngineHealth = clamp(
    pullToward(prev.fraudEngineHealth, 94, 0.25) - upiPressureFromIncidents * 0.4 + jitter(rng, 1.2),
    74, 99,
  );
  d.upiSwitchHealth = clamp(
    pullToward(prev.upiSwitchHealth, 96, 0.25) - upiPressureFromIncidents * 0.2 + jitter(rng, 1),
    80, 99,
  );
  d.paymentGatewayHealth = clamp(
    pullToward(prev.paymentGatewayHealth, 97, 0.25) - merchantPressureFromIncidents * 0.3 + jitter(rng, 0.8),
    82, 99,
  );
  d.coreBankingHealth = clamp(
    pullToward(prev.coreBankingHealth, 98, 0.2) + jitter(rng, 0.5),
    88, 99,
  );

  // --- pressure cycles: slow oscillation so dashboards trend rather than noise
  d.incidentMomentum = clamp(
    prev.incidentMomentum + (incidentForcing(d.simHour, d) - prev.incidentMomentum) * 0.25 + jitter(rng, 0.05),
    0.1, 0.95,
  );
  d.releasePressure = clamp(
    prev.releasePressure + (d.atRiskReleaseIds.length / 4 - 0.4) * 0.15 + jitter(rng, 0.04),
    0.15, 0.9,
  );
  d.governancePressure = clamp(
    prev.governancePressure + (criticalCount(prev.activeFindings) / 3 - 0.3) * 0.1 + jitter(rng, 0.03),
    0.15, 0.9,
  );
  d.testingBacklog = clamp(
    prev.testingBacklog + (prev.escapedDefects / 6 - 0.3) * 0.1 + jitter(rng, 0.03),
    0.1, 0.9,
  );

  // --- incident lifecycle: age existing incidents, retire some, possibly open new
  d.activeIncidents = ageAndRetireIncidents(prev.activeIncidents, rng, d);
  const opened = maybeOpenIncidents(d, rng);
  d.activeIncidents = dedupe([...d.activeIncidents, ...opened], 'id').slice(0, 7);

  // --- governance findings lifecycle
  d.activeFindings = updateFindings(prev.activeFindings, d, rng);

  // --- release pipeline: shift at-risk set occasionally
  d.atRiskReleaseIds = updateAtRiskReleases(prev.atRiskReleaseIds, d, rng);

  // --- testing/delivery drivers
  const escapeDelta = (d.testingBacklog - 0.4) * 1.6 + jitter(rng, 0.4);
  d.escapedDefects = clamp(round(prev.escapedDefects + escapeDelta * 0.4, 0), 0, 8);
  d.foundDefects = clamp(
    round(prev.foundDefects + (peakLoad(d.simHour) - 0.5) * 6 + jitter(rng, 2), 0),
    8, 32,
  );
  d.technicalDebt = clamp(
    round(prev.technicalDebt + (d.releasePressure - 0.4) * 0.6 + jitter(rng, 0.4), 0),
    20, 55,
  );

  // --- rolling buffers
  d.incidentTrendBuffer = shiftIn(prev.incidentTrendBuffer, criticalIncidentToday(d));
  d.defectTrendBuffer = shiftIn(prev.defectTrendBuffer, { found: d.foundDefects, escaped: d.escapedDefects });

  return d;
}

function incidentForcing(hour, d) {
  // higher load -> more incidents; weighted by current channel load profile
  const load = peakLoad(hour);
  const dependencyStrain =
    (99 - d.fraudEngineHealth) / 30 + (99 - d.upiSwitchHealth) / 40 + (99 - d.paymentGatewayHealth) / 50;
  return clamp(0.25 + load * 0.5 + dependencyStrain * 0.4, 0.15, 0.95);
}

function peakLoad(hour) {
  const h = Math.floor(hour) % 24;
  let sum = 0;
  let wsum = 0;
  for (const c of PAYMENT_CHANNELS) {
    sum += c.timeProfile[h] * c.weight * (c.basePeakTps / 1000);
    wsum += c.weight * (c.basePeakTps / 1000);
  }
  return wsum > 0 ? sum / wsum : 0.5;
}

function pullToward(value, target, k) {
  return value + (target - value) * k;
}

function jitter(rng, amp) {
  return (rng() - 0.5) * 2 * amp;
}

function countActive(incidents, channel) {
  return incidents.filter((i) => i.channel === channel).length;
}

function criticalCount(items) {
  return items.filter((i) => i.severity === 'critical').length;
}

function criticalIncidentToday(d) {
  return clamp(d.activeIncidents.filter((i) => i.severity === 'critical').length + Math.floor(peakLoad(d.simHour) * 2), 0, 6);
}

function shiftIn(arr, next) {
  return [...arr.slice(1), next];
}

function dedupe(arr, key) {
  const seen = new Set();
  const out = [];
  for (const item of arr) {
    if (!seen.has(item[key])) {
      seen.add(item[key]);
      out.push(item);
    }
  }
  return out;
}

function ageAndRetireIncidents(active, rng, d) {
  const next = [];
  for (const inc of active) {
    const aged = { ...inc, ageTicks: (inc.ageTicks ?? 0) + 1 };
    // recovery probability climbs with age & lowers with critical severity
    const recoverChance =
      0.08 + aged.ageTicks * 0.06 - (aged.severity === 'critical' ? 0.05 : 0);
    if (rng() < recoverChance) continue; // retired
    aged.status = aged.ageTicks > 4 ? 'Mitigating' : 'Investigating';
    next.push(aged);
  }
  // momentum: if very few incidents and momentum high, ensure at least 1 active payments incident
  if (next.length === 0 && d.incidentMomentum > 0.6) {
    const seed = INCIDENT_CATALOG_FULL.find((i) => i.domain === 'Payments');
    if (seed) next.push({ ...seed, ageTicks: 1, status: 'Investigating' });
  }
  return next;
}

function maybeOpenIncidents(d, rng) {
  const opened = [];
  for (const channel of PAYMENT_CHANNELS) {
    const hour = Math.floor(d.simHour) % 24;
    const load = channel.timeProfile[hour];
    if (load < 0.05) continue; // closed window (NEFT/RTGS at night)
    const dependencyDrag =
      channel.dependsOn.reduce((acc, dep) => acc + (99 - dependencyHealth(d, dep)) / 40, 0);
    const prob = clamp(
      load * 0.12 * channel.incidentBias + dependencyDrag * 0.18 + d.incidentMomentum * 0.05,
      0,
      0.55,
    );
    if (rng() < prob) {
      const seed =
        INCIDENT_CATALOG_FULL.find((i) => i.channel === channel.id) ||
        INCIDENT_CATALOG_FULL.find((i) => i.domain === 'Payments');
      if (seed) opened.push({ ...seed, ageTicks: 1, status: 'Investigating' });
    }
  }
  // non-payments domains: very low rate
  if (rng() < 0.12) {
    const seed = INCIDENT_CATALOG_FULL.find((i) => i.domain === 'Mobile Banking');
    if (seed) opened.push({ ...seed, ageTicks: 1, status: 'Investigating' });
  }
  if (rng() < 0.08) {
    const seed = INCIDENT_CATALOG_FULL.find((i) => i.domain === 'Net Banking');
    if (seed) opened.push({ ...seed, ageTicks: 1, status: 'Investigating' });
  }
  return opened;
}

function dependencyHealth(d, service) {
  switch (service) {
    case 'Fraud Engine': return d.fraudEngineHealth;
    case 'UPI Switch': return d.upiSwitchHealth;
    case 'Payment Gateway': return d.paymentGatewayHealth;
    case 'Core Banking': return d.coreBankingHealth;
    default: return 95;
  }
}

function updateFindings(prev, d, rng) {
  const next = prev.filter(() => rng() > 0.08); // mild resolution rate
  const room = Math.max(0, 6 - next.length);
  const wantNew = Math.round(d.governancePressure * 4) - next.length;
  const candidates = GOVERNANCE_CATALOG_FULL.filter((f) => !next.some((n) => n.title === f.title));
  for (let i = 0; i < Math.min(room, Math.max(0, wantNew)); i += 1) {
    if (candidates[i]) next.push({ ...candidates[i] });
  }
  // ensure at least one critical when pressure is high
  if (d.governancePressure > 0.7 && !next.some((f) => f.severity === 'critical')) {
    const crit = GOVERNANCE_CATALOG_FULL.find((f) => f.severity === 'critical');
    if (crit) next.push({ ...crit });
  }
  return next.slice(0, 7);
}

function updateAtRiskReleases(prev, d, rng) {
  const candidates = ['R-UPI-24.6', 'R-MOB-5.9', 'R-PAY-12.2', 'R-NB-8.4'];
  let next = prev.slice();

  // releases tied to Payments domain inherit risk if Payments incidents are heavy
  const paymentsIncidents = d.activeIncidents.filter((i) => i.domain === 'Payments').length;
  if (paymentsIncidents >= 3 && !next.includes('R-UPI-24.6')) next.push('R-UPI-24.6');
  if (paymentsIncidents >= 4 && !next.includes('R-PAY-12.2')) next.push('R-PAY-12.2');

  // probabilistic flips driven by release pressure
  for (const r of candidates) {
    if (next.includes(r)) {
      if (rng() < 0.08 - d.releasePressure * 0.06) {
        next = next.filter((x) => x !== r);
      }
    } else if (rng() < 0.03 + d.releasePressure * 0.06) {
      next.push(r);
    }
  }
  return Array.from(new Set(next)).slice(0, 4);
}

/* ------------------------------------------------------------------ */
/* Derivation of visible state from drivers                           */
/* ------------------------------------------------------------------ */

function derivePaymentsChannels(d) {
  const hour = Math.floor(d.simHour) % 24;
  return PAYMENT_CHANNELS.map((c) => {
    const load = c.timeProfile[hour];
    const tps = round(c.basePeakTps * load, 0);
    const channelIncidents = d.activeIncidents.filter((i) => i.channel === c.id);
    const dependencyPenalty =
      c.dependsOn.reduce((acc, dep) => acc + (99 - dependencyHealth(d, dep)) / c.dependsOn.length, 0);
    const incidentPenalty = channelIncidents.length * 3 +
      channelIncidents.filter((i) => i.severity === 'critical').length * 5;
    const health = clamp(99 - dependencyPenalty * 0.8 - incidentPenalty - load * 2, 60, 99);
    const successRate = round(clamp(99.95 - incidentPenalty * 0.12 - dependencyPenalty * 0.04, 96, 99.99), 2);
    const latencyMs = round(
      clamp(120 + load * 220 + incidentPenalty * 40 + dependencyPenalty * 4, 80, 1800),
      0,
    );
    return {
      id: c.id,
      name: c.name,
      weight: c.weight,
      health: round(health, 0),
      tps,
      successRate,
      latencyMs,
      openIncidents: channelIncidents.length,
      load: round(load, 2),
    };
  });
}

function deriveExecutive(prev, d, channels, derived) {
  const exec = { ...prev };

  // KPI sparkline buffers: shift in new values each tick
  const kpiValues = {
    'Delivery Health': derived.deliveryHealth,
    'Production Health': derived.productionHealth,
    'Governance Health': derived.governanceScore,
    'Engineering Health': derived.engineeringHealth,
  };
  for (const k of Object.keys(d.historicalKpis)) {
    const buf = d.historicalKpis[k];
    d.historicalKpis[k] = buf
      .slice(1)
      .concat({ day: `D${buf.length}`, value: round(kpiValues[k], 0) })
      .map((p, i) => ({ day: `D${i + 1}`, value: p.value }));
  }

  exec.kpis = exec.kpis.map((kpi) => {
    const value = round(kpiValues[kpi.label] ?? kpi.value, 0);
    const buf = d.historicalKpis[kpi.label] ?? kpi.data;
    const trend = round(value - (buf[buf.length - 2]?.value ?? value), 1);
    return { ...kpi, value, trend, data: buf };
  });

  exec.openRisks = derived.openRisks;
  exec.openIncidents = derived.openIncidents;
  exec.businessImpactScore = derived.businessImpactScore;
  exec.portfolioHealth = derived.portfolioHealth;

  exec.domainHealth = exec.domainHealth.map((dom) => {
    const score =
      dom.name === 'Payments'
        ? round(derived.paymentsHealth, 0)
        : dom.name === 'Net Banking'
        ? round(derived.netBankingHealth, 0)
        : round(derived.mobileBankingHealth, 0);
    const incidents = d.activeIncidents.filter((i) => i.domain === dom.name).length;
    const risks = dom.name === 'Payments'
      ? clamp(round(2 + d.atRiskReleaseIds.length * 2 + criticalCount(d.activeFindings), 0), 1, 14)
      : clamp(round(2 + d.atRiskReleaseIds.length, 0), 1, 8);
    const changes = round(dom.changes + (jitter(rngFromSeed(d.rngSeed + dom.name.length), 1.2)), 0);
    const trend = shiftIn(dom.trend, { day: `D${dom.trend.length}`, value: score })
      .map((p, i) => ({ day: `D${i + 1}`, value: p.value }));
    return { ...dom, score, incidents, risks, changes: clamp(changes, 25, 60), trend };
  });

  exec.portfolioMetrics = [
    {
      label: 'Active Changes',
      value: clamp(round(120 + d.releasePressure * 40 + jitter(rngFromSeed(d.rngSeed + 7), 4), 0), 100, 170),
      trend: derived.openRisks > prev.openRisks ? 5 : -2,
    },
    {
      label: 'In-Flight Releases',
      value: 4,
      trend: d.atRiskReleaseIds.length > 2 ? -1 : 1,
    },
    {
      label: 'Open Incidents',
      value: derived.openIncidents,
      trend: derived.openIncidents < prev.openIncidents ? -12 : 6,
    },
    {
      label: 'Open Risks',
      value: derived.openRisks,
      trend: derived.openRisks > prev.openRisks ? 4 : -3,
    },
  ];

  exec.riskByPhase = [
    { name: 'Requirements', value: clamp(round(3 + d.testingBacklog * 4, 0), 1, 9), color: '#EF4444' },
    { name: 'Architecture', value: clamp(round(2 + d.releasePressure * 4, 0), 1, 8), color: '#F97316' },
    { name: 'Development', value: clamp(round(2 + d.technicalDebt / 18, 0), 1, 8), color: '#F59E0B' },
    { name: 'Testing', value: clamp(round(1 + d.escapedDefects * 0.6, 0), 1, 6), color: '#3B82F6' },
  ];

  exec.businessImpactAreas = [
    { name: 'Customer Experience', value: round(clamp(98 - derived.openIncidents * 1.5, 70, 98), 0) },
    { name: 'Revenue / UPI Volume', value: round(clamp(channels.find((c) => c.id === 'upi').health, 70, 98), 0) },
    { name: 'Regulatory Compliance', value: round(clamp(derived.governanceScore - 6, 70, 98), 0) },
    { name: 'Settlement SLA', value: round(clamp(channels.find((c) => c.id === 'merchant').successRate * 0.95, 70, 98), 0) },
  ];

  // confidenceTrend rolling 6 months — shift in latest values per tick
  d.confidenceTrendBuffer = shiftIn(d.confidenceTrendBuffer, {
    net: round(derived.netBankingHealth, 0),
    mobile: round(derived.mobileBankingHealth, 0),
    payments: round(derived.paymentsHealth, 0),
  });
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  exec.confidenceTrend = d.confidenceTrendBuffer.map((p, i) => ({
    month: months[(d.simDayIndex + i) % 12],
    ...p,
  }));

  exec.criticalIncidents = d.activeIncidents.slice(0, 3).map((i) => ({
    id: i.id,
    title: i.title,
    domain: i.domain,
    severity: i.severity,
    duration: durationLabel(i.ageTicks),
    status: i.status,
  }));

  exec.scorecard = [
    { label: 'Portfolio Health', value: round(derived.portfolioHealth, 0) },
    { label: 'AI Impact Score', value: round(clamp(60 + (1 - d.testingBacklog) * 30, 50, 95), 0) },
    { label: 'Release Confidence', value: round(derived.releaseConfidence, 0) },
    { label: 'Compliance Posture', value: round(clamp(derived.governanceScore - 2, 70, 98), 0) },
  ];

  exec.activeScans = [
    {
      name: 'Payments Ops Scan',
      progress: round(clamp(60 + d.incidentMomentum * 35, 0, 100), 0),
      status: 'In Progress',
    },
    {
      name: 'UPI Release 24.6 Readiness',
      progress: round(clamp(50 + (1 - d.releasePressure) * 45, 0, 100), 0),
      status: d.atRiskReleaseIds.includes('R-UPI-24.6') ? 'At Risk' : 'In Progress',
    },
    {
      name: 'Governance Compliance',
      progress: 100,
      status: 'Completed',
    },
  ];

  return exec;
}

function rngFromSeed(seed) {
  return makeRng(seed);
}

function durationLabel(ticks) {
  const mins = Math.max(1, ticks) * SIM_MINUTES_PER_TICK;
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}

function deriveProduction(prev, d, derived) {
  const next = { ...prev };
  next.activeIncidents = derived.openIncidents;
  next.health = round(derived.productionHealth, 0);
  next.availability = round(
    clamp(99.99 - derived.openIncidents * 0.015 - derived.criticalIncidents * 0.06, 99.50, 99.99),
    2,
  );
  next.mttrMinutes = round(
    clamp(15 + derived.openIncidents * 1.4 + derived.criticalIncidents * 3.2, 12, 60),
    0,
  );
  next.slaBreaches = derived.criticalIncidents;
  next.incidentTrend = d.incidentTrendBuffer.map((count, i) => ({
    day: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][i],
    count,
  }));
  next.serviceHealth = [
    { name: 'UPI Switch', status: statusFromHealth(d.upiSwitchHealth), uptime: round(d.upiSwitchHealth, 2) },
    { name: 'Payment Gateway', status: statusFromHealth(d.paymentGatewayHealth), uptime: round(d.paymentGatewayHealth, 2) },
    { name: 'Fraud Engine', status: statusFromHealth(d.fraudEngineHealth), uptime: round(d.fraudEngineHealth, 2) },
    { name: 'Notification Hub', status: 'healthy', uptime: 99.95 },
    { name: 'Net Banking Portal', status: statusFromHealth(derived.netBankingHealth), uptime: round(clamp(derived.netBankingHealth + 5, 99, 99.99), 2) },
  ];
  next.openIncidents = d.activeIncidents.slice(0, 5).map((i) => ({
    id: i.id,
    title: i.title,
    domain: i.domain,
    severity: i.severity,
    duration: durationLabel(i.ageTicks),
    status: i.status,
  }));
  next.topIssues = [
    {
      issue: 'Fraud Engine Timeout',
      rca: `Thread pool exhaustion under peak UPI load. Fraud Engine health at ${round(d.fraudEngineHealth, 0)}% — circuit breaker still pending on UPI verify path.`,
    },
    {
      issue: 'Payment Gateway Latency',
      rca: `p99 latency elevated on auth path (${round(120 + (99 - d.paymentGatewayHealth) * 10, 0)}ms). TLS renegotiation on legacy endpoint suspected.`,
    },
  ];
  return next;
}

function statusFromHealth(h) {
  if (h >= 99) return 'healthy';
  if (h >= 96) return 'degraded';
  return 'critical';
}

function deriveOperations(prev, d, channels, derived) {
  const next = { ...prev };
  const load = peakLoad(d.simHour);
  const upi = channels.find((c) => c.id === 'upi');
  const merchant = channels.find((c) => c.id === 'merchant');
  next.capacityUtilization = round(
    clamp(45 + load * 35 + (upi.tps / upi.weight / 30000) * 10, 50, 92),
    0,
  );
  next.cpuUtilization = round(
    clamp(40 + load * 38 + derived.openIncidents * 1.5, 40, 95),
    0,
  );
  next.storageUtilization = round(
    clamp(68 + merchant.load * 10 + jitter(rngFromSeed(d.rngSeed + 11), 2), 60, 88),
    0,
  );
  next.batchHealth = round(
    clamp(99 - derived.openIncidents * 0.6 - countActive(d.activeIncidents, 'neft') * 4, 80, 99),
    0,
  );
  next.operationalHealth = round(
    clamp(96 - derived.openIncidents * 1.4 - derived.criticalIncidents * 2 - (next.cpuUtilization - 70) * 0.2, 60, 96),
    0,
  );
  next.activeJobs = clamp(round(110 + load * 30, 0), 90, 160);
  next.failedJobs = clamp(round(d.activeIncidents.filter((i) => i.channel === 'neft' || i.channel === 'merchant').length, 0), 0, 5);

  // capacity trend tied to upi load profile shifted across 24h
  next.capacityTrend = [0, 4, 8, 12, 16, 20].map((h) => {
    const hour = (Math.floor(d.simHour) + h) % 24;
    const upiAtH = PAYMENT_CHANNELS[0].timeProfile[hour];
    const merchantAtH = PAYMENT_CHANNELS[4].timeProfile[hour];
    return {
      hour: String(hour).padStart(2, '0'),
      cpu: round(clamp(38 + upiAtH * 45 + jitter(rngFromSeed(d.rngSeed + h), 2), 30, 95), 0),
      memory: round(clamp(42 + upiAtH * 40 + jitter(rngFromSeed(d.rngSeed + h + 1), 2), 35, 92), 0),
      storage: round(clamp(70 + merchantAtH * 14, 65, 90), 0),
    };
  });

  next.capacityForecast = [1, 2, 3, 4, 5].map((day) => ({
    day: `D+${day}`,
    predicted: round(
      clamp(next.capacityUtilization + day * 1.2 - (day > 3 ? 4 : 0) + jitter(rngFromSeed(d.rngSeed + day * 17), 2), 60, 92),
      0,
    ),
  }));

  // batch jobs: state reflects active channel pressure
  const neftIncident = d.activeIncidents.find((i) => i.channel === 'neft');
  const merchantIncident = d.activeIncidents.find((i) => i.channel === 'merchant');
  next.batchJobs = [
    { name: 'UPI Settlement EOD', status: 'Running', progress: round(clamp(60 + load * 35, 0, 99), 0) },
    {
      name: 'Merchant Auto Settlement',
      status: merchantIncident ? 'Failed' : 'Completed',
      progress: merchantIncident ? round(clamp(20 + jitter(rngFromSeed(d.rngSeed + 33), 10), 5, 80), 0) : 100,
    },
    { name: 'Mandate Reconciliation', status: 'Running', progress: round(clamp(40 + load * 40, 0, 99), 0) },
    {
      name: 'Fraud Report Export',
      status: d.fraudEngineHealth < 88 ? 'Failed' : 'Completed',
      progress: d.fraudEngineHealth < 88 ? round(clamp(30 + jitter(rngFromSeed(d.rngSeed + 41), 8), 10, 80), 0) : 100,
    },
    {
      name: 'NEFT Hourly Batch',
      status: neftIncident ? 'Failed' : (PAYMENT_CHANNELS[2].timeProfile[Math.floor(d.simHour) % 24] > 0.5 ? 'Running' : 'Completed'),
      progress: neftIncident ? round(clamp(25 + jitter(rngFromSeed(d.rngSeed + 47), 10), 5, 80), 0) : 100,
    },
  ];

  next.operationalRisks = [
    {
      title: `Settlement DB connection pool at ${next.cpuUtilization > 80 ? '88%' : '74%'}`,
      severity: next.cpuUtilization > 82 ? 'high' : 'medium',
    },
    { title: 'Batch window overlap: EOD + Mandate', severity: 'medium' },
    {
      title: d.fraudEngineHealth < 88 ? 'Fraud Engine degraded — UPI exposure' : 'DR failover test overdue',
      severity: d.fraudEngineHealth < 88 ? 'high' : 'low',
    },
  ];
  return next;
}

function deriveGovernance(prev, d, derived) {
  const next = { ...prev };
  const sev = countBySeverity(d.activeFindings);
  next.findingSeverity = [
    { name: 'Critical', value: sev.critical, color: '#EF4444' },
    { name: 'High', value: sev.high, color: '#F97316' },
    { name: 'Medium', value: sev.medium, color: '#F59E0B' },
    { name: 'Low', value: clamp(round(8 + d.governancePressure * 8, 0), 5, 18), color: '#3B82F6' },
  ];
  const totalSev = sev.critical + sev.high + sev.medium;
  next.vaptFindings = clamp(round(10 + totalSev * 1.3, 0), 8, 28);
  next.auditObservations = clamp(round(3 + sev.critical * 1.5 + sev.high * 0.5, 0), 2, 12);
  next.policyViolations = clamp(round(4 + sev.medium * 0.6 + sev.high * 0.4, 0), 2, 14);
  next.securityFindings = clamp(round(6 + sev.critical * 2 + sev.high * 1, 0), 4, 20);
  next.governanceScore = round(derived.governanceScore, 0);
  next.baselineCompliance = round(clamp(98 - sev.critical * 4 - sev.high * 1.5, 75, 98), 0);
  next.policyCompliance = round(clamp(99 - sev.critical * 3 - sev.high * 1, 78, 99), 0);
  next.topFindings = d.activeFindings.slice(0, 6).map((f) => ({ ...f }));
  next.complianceStandards = [
    { name: 'NPCI UPI Guidelines', score: round(clamp(95 - countActive(d.activeIncidents, 'upi') * 2 - sev.critical * 2, 75, 98), 0) },
    { name: 'PCI-DSS', score: round(clamp(94 - sev.high * 1.5, 78, 98), 0) },
    { name: 'RBI IT Framework', score: round(clamp(96 - sev.critical * 2, 80, 99), 0) },
    { name: 'ISO 27001', score: round(clamp(97 - sev.medium * 0.5, 88, 99), 0) },
  ];
  // refresh latest audit-trail entry to reflect current condition
  next.auditTrail = [
    {
      event: sev.critical > 0
        ? `Critical finding flagged – ${d.activeFindings.find((f) => f.severity === 'critical')?.title ?? 'Security control'}`
        : 'TLS cert expiry flagged – Payment Gateway',
      time: 'just now',
    },
    { event: 'VAPT scan completed – UPI Switch', time: '2h ago' },
  ];
  return next;
}

function countBySeverity(items) {
  return items.reduce(
    (acc, i) => {
      if (i.severity === 'critical') acc.critical += 1;
      else if (i.severity === 'high') acc.high += 1;
      else if (i.severity === 'medium') acc.medium += 1;
      return acc;
    },
    { critical: 0, high: 0, medium: 0 },
  );
}

function deriveTesting(prev, d) {
  const next = { ...prev };
  const latest = d.defectTrendBuffer[d.defectTrendBuffer.length - 1];
  next.coverage = round(clamp(98 - latest.escaped * 0.4 - d.testingBacklog * 4, 88, 99), 1);
  next.automation = round(clamp(74 - d.testingBacklog * 6, 60, 82), 1);
  next.effectiveness = round(clamp(95 - latest.escaped * 0.8 - d.testingBacklog * 4, 78, 98), 1);
  next.defectLeakage = latest.escaped <= 1 ? 'Low Risk' : latest.escaped <= 3 ? 'Medium Risk' : 'High Risk';
  next.optimizationProgress = round(clamp(45 + (1 - d.testingBacklog) * 40, 35, 85), 0);
  next.recommended = clamp(round(240 + d.testingBacklog * 90, 0), 200, 360);
  next.defectTrend = d.defectTrendBuffer.map((p, i) => ({ week: `W${i + 1}`, found: p.found, escaped: p.escaped }));

  // heatmap: coverage depresses where channel under stress
  const upiHealth = clamp(96 - countActive(d.activeIncidents, 'upi') * 4, 70, 96);
  const merchantHealth = clamp(94 - countActive(d.activeIncidents, 'merchant') * 4, 70, 95);
  next.coverageHeatmap = [
    ['Net Banking', round(next.coverage, 0), 92, 94, 81],
    ['Mobile Banking', 94, 88, 92, 78],
    ['Payments', round(upiHealth, 0), round(merchantHealth - 4, 0), round(upiHealth - 5, 0), round(merchantHealth - 12, 0)],
  ];
  return next;
}

function deriveDelivery(prev, d, derived) {
  const next = { ...prev };
  next.changeFailureRate = round(clamp(2 + d.escapedDefects * 0.4 + d.atRiskReleaseIds.length * 0.6, 1, 12), 1);
  next.deploymentFrequency = clamp(round(14 - d.releasePressure * 4, 0), 8, 16);
  next.leadTimeHours = clamp(round(30 + d.releasePressure * 18 + d.escapedDefects * 1.5, 0), 24, 72);
  next.requirementsAnalysed = clamp(round(260 + (1 - d.testingBacklog) * 60, 0), 240, 340);
  next.businessImpactIndex = round(clamp(85 - d.releasePressure * 14, 65, 92), 0);
  next.complianceImpactCount = clamp(round(15 + d.governancePressure * 10, 0), 12, 28);
  next.requirementRisks = clamp(round(8 + d.testingBacklog * 6, 0), 6, 18);
  next.architectureRisks = clamp(round(4 + d.releasePressure * 6, 0), 3, 12);
  next.technicalDebtItems = d.technicalDebt;
  next.testCoverageAvg = round(clamp(95 - d.escapedDefects * 0.4, 88, 98), 1);
  next.codeQualityAvg = round(clamp(92 - d.technicalDebt * 0.18 - d.escapedDefects * 0.6, 75, 95), 0);
  next.defectDensity = round(clamp(0.5 + d.escapedDefects * 0.12, 0.3, 1.6), 2);
  return next;
}

function deriveRelease(prev, d, derived) {
  const next = { ...prev };
  next.confidence = round(derived.releaseConfidence, 0);
  next.rollbackReadiness = round(clamp(96 - d.atRiskReleaseIds.length * 2, 80, 98), 0);
  next.deploymentReadiness = round(clamp(94 - d.atRiskReleaseIds.length * 4 - derived.criticalIncidents * 2, 70, 96), 0);
  next.readiness = [
    {
      dimension: 'Architecture',
      score: round(clamp(94 - d.atRiskReleaseIds.length * 1.5, 75, 96), 0),
    },
    {
      dimension: 'Development',
      score: round(clamp(92 - d.technicalDebt * 0.15 - d.escapedDefects * 0.8, 70, 95), 0),
    },
    {
      dimension: 'Testing',
      score: round(clamp(95 - d.escapedDefects * 1.2 - d.testingBacklog * 4, 70, 98), 0),
    },
    {
      dimension: 'Operations',
      score: round(clamp(95 - derived.openIncidents * 1.6 - derived.criticalIncidents * 2.5, 65, 98), 0),
    },
    {
      dimension: 'Governance',
      score: round(clamp(99 - criticalCount(d.activeFindings) * 3 - countBySeverity(d.activeFindings).high * 1.2, 75, 99), 0),
    },
  ].map((r) => ({ ...r, status: r.score < 86 ? 'At Risk' : 'Ready' }));

  next.releases = prev.releases.map((r) => {
    const atRisk = d.atRiskReleaseIds.includes(r.id);
    const channelIncidents = r.domain === 'Payments'
      ? d.activeIncidents.filter((i) => i.domain === 'Payments').length
      : d.activeIncidents.filter((i) => i.domain === r.domain).length;
    const conf = clamp(
      96 - (atRisk ? 8 : 0) - channelIncidents * 2 - (r.id === 'R-UPI-24.6' ? (99 - d.fraudEngineHealth) * 0.4 : 0),
      72, 97,
    );
    return { ...r, confidence: round(conf, 0), risk: atRisk ? 'high' : (conf < 88 ? 'medium' : 'low') };
  });

  next.checklist = [
    { item: 'UPI regression sign-off', status: d.escapedDefects <= 1 ? 'completed' : 'in progress' },
    { item: 'Fraud rules validation', status: d.fraudEngineHealth >= 92 ? 'completed' : 'in progress' },
    { item: 'Settlement dry-run', status: countActive(d.activeIncidents, 'merchant') === 0 ? 'completed' : 'in progress' },
    { item: 'CAB approval', status: d.atRiskReleaseIds.length <= 2 ? 'completed' : 'in progress' },
    { item: 'Governance sign-off', status: criticalCount(d.activeFindings) === 0 ? 'completed' : 'in progress' },
  ];

  next.riskMatrix = [
    { title: 'Fraud Engine dependency on UPI 24.6', severity: d.fraudEngineHealth < 88 ? 'high' : 'medium', domain: 'Payments' },
    { title: 'Merchant settlement cutover window', severity: countActive(d.activeIncidents, 'merchant') > 0 ? 'high' : 'medium', domain: 'Payments' },
    { title: 'NEFT batch window overrun', severity: countActive(d.activeIncidents, 'neft') > 0 ? 'high' : 'low', domain: 'Payments' },
    { title: 'Biometric cert rotation', severity: 'low', domain: 'Mobile Banking' },
  ];
  next.goNoGo = next.confidence >= 85 ? 'GO' : 'NO-GO';
  return next;
}

function deriveRequirements(prev, d) {
  const next = { ...prev };
  next.analysed = clamp(round(260 + (1 - d.testingBacklog) * 60, 0), 240, 340);
  next.highRisk = clamp(round(10 + d.testingBacklog * 8, 0), 8, 22);
  next.ambiguous = clamp(round(7 + d.testingBacklog * 4, 0), 5, 14);
  next.missingCriteria = clamp(round(4 + d.testingBacklog * 4, 0), 3, 10);
  next.qualityScore = round(clamp(92 - d.testingBacklog * 10 - d.escapedDefects * 0.5, 70, 95), 0);
  next.complianceImpact = clamp(round(15 + d.governancePressure * 10, 0), 12, 28);
  next.riskDistribution = [
    { name: 'High', value: next.highRisk, color: '#EF4444' },
    { name: 'Medium', value: clamp(round(28 + d.testingBacklog * 8, 0), 22, 42), color: '#F59E0B' },
    { name: 'Low', value: clamp(round(64 - d.testingBacklog * 6, 0), 50, 72), color: '#3B82F6' },
  ];
  return next;
}

function deriveDevelopment(prev, d) {
  const next = { ...prev };
  next.codeQuality = round(clamp(92 - d.technicalDebt * 0.18 - d.escapedDefects * 0.6, 75, 95), 0);
  next.techDebt = d.technicalDebt;
  next.securityFindings = clamp(round(3 + criticalCount(d.activeFindings) + countBySeverity(d.activeFindings).high * 0.5, 0), 2, 12);
  next.health = round(clamp(94 - d.technicalDebt * 0.18 - countBySeverity(d.activeFindings).high * 0.6, 70, 96), 0);
  return next;
}

/* ------------------------------------------------------------------ */
/* Insights                                                            */
/* ------------------------------------------------------------------ */

function buildInsights(prev, d, derived, channels) {
  const insights = [];
  const upi = channels.find((c) => c.id === 'upi');
  const neft = channels.find((c) => c.id === 'neft');
  const merchant = channels.find((c) => c.id === 'merchant');

  if (derived.paymentsHealth !== prev.paymentsHealth) {
    const dir = derived.paymentsHealth > prev.paymentsHealth ? 'improved' : 'reduced';
    insights.push(
      `Payments domain health ${dir} to ${round(derived.paymentsHealth, 0)}% — UPI ${upi.health}%, Merchant ${merchant.health}%, ${derived.openIncidents} open incidents.`,
    );
  }
  if (d.activeIncidents.some((i) => i.channel === 'upi' && i.severity === 'critical')) {
    insights.push(`Critical UPI incident active — Fraud Engine at ${round(d.fraudEngineHealth, 0)}%, response in progress.`);
  }
  if (d.atRiskReleaseIds.length > 0) {
    insights.push(
      `${d.atRiskReleaseIds.length} release${d.atRiskReleaseIds.length === 1 ? '' : 's'} flagged at-risk → release confidence at ${round(derived.releaseConfidence, 0)}%.`,
    );
  }
  if (countActive(d.activeIncidents, 'neft') > 0) {
    insights.push(`NEFT batch window stressed — ${neft.openIncidents} incident active, batch health depressed.`);
  }
  if (criticalCount(d.activeFindings) > 0) {
    insights.push(
      `Governance pressure rising — ${criticalCount(d.activeFindings)} critical finding(s), score at ${round(derived.governanceScore, 0)}%.`,
    );
  }
  if (d.escapedDefects >= 3) {
    insights.push(`Escaped defects climbing (${d.escapedDefects}) — delivery score at ${round(derived.deliveryHealth, 0)}%, change failure rate elevated.`);
  }
  if (insights.length === 0) {
    insights.push(`Operations telemetry stable at simulated ${formatSimTime(d.simHour)} — no material cascades this cycle.`);
    insights.push(`Payments running at ${round(peakLoad(d.simHour) * 100, 0)}% of peak load.`);
  }
  return insights.slice(0, 5);
}

function formatSimTime(hour) {
  const h = Math.floor(hour);
  const m = Math.round((hour - h) * 60);
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
}

/* ------------------------------------------------------------------ */
/* Top-level tick                                                      */
/* ------------------------------------------------------------------ */

export function tickSimulation(state) {
  const withDrivers = state._drivers ? state : bootstrapDrivers(state);
  const prevDrivers = withDrivers._drivers;
  const rng = makeRng(prevDrivers.rngSeed);
  const d = advanceDrivers(prevDrivers, rng);

  const channels = derivePaymentsChannels(d);

  // --- aggregate Payments domain health from channels (weighted)
  const paymentsHealth = channels.reduce((acc, c) => acc + c.health * c.weight, 0);
  // Net Banking & Mobile Banking: a few targeted drivers + small jitter, but
  // still influenced by incident & governance pressure (enterprise context).
  const netBankingHealth = clamp(
    96 - d.activeIncidents.filter((i) => i.domain === 'Net Banking').length * 3 - criticalCount(d.activeFindings) * 0.5 + jitter(rngFromSeed(d.rngSeed + 101), 0.8),
    78, 98,
  );
  const mobileBankingHealth = clamp(
    95 - d.activeIncidents.filter((i) => i.domain === 'Mobile Banking').length * 3 - criticalCount(d.activeFindings) * 0.4 + jitter(rngFromSeed(d.rngSeed + 103), 0.8),
    78, 98,
  );

  // --- derived rollups
  const openIncidents = d.activeIncidents.length;
  const criticalIncidents = d.activeIncidents.filter((i) => i.severity === 'critical').length;
  const sev = countBySeverity(d.activeFindings);

  const productionHealth = clamp(
    96 - openIncidents * 1.4 - criticalIncidents * 2.5 + jitter(rngFromSeed(d.rngSeed + 201), 0.6),
    65, 96,
  );
  const operationalHealth = clamp(
    96 - openIncidents * 1.4 - criticalIncidents * 2 + jitter(rngFromSeed(d.rngSeed + 211), 0.6),
    60, 96,
  );
  const governanceScore = clamp(
    99 - sev.critical * 5 - sev.high * 2 - sev.medium * 0.6,
    72, 99,
  );
  const deliveryHealth = clamp(
    95 - d.escapedDefects * 1.4 - d.technicalDebt * 0.12 - d.atRiskReleaseIds.length * 1.2,
    72, 96,
  );
  const engineeringHealth = clamp(
    94 - d.technicalDebt * 0.18 - sev.high * 0.5 - d.escapedDefects * 0.6,
    72, 95,
  );
  const releaseConfidence = clamp(
    96 - d.atRiskReleaseIds.length * 4 - criticalIncidents * 3 - d.escapedDefects * 0.8 - sev.critical * 1.5,
    70, 97,
  );

  const openRisks = clamp(
    8 + d.atRiskReleaseIds.length * 2 + sev.high + sev.critical * 2 + Math.round(d.testingBacklog * 4),
    8, 24,
  );
  const businessImpactScore = clamp(
    90 - openIncidents * 1.2 - sev.critical * 3 - d.atRiskReleaseIds.length * 1.5,
    65, 95,
  );
  const portfolioHealth = clamp(
    (paymentsHealth * 0.45 + netBankingHealth * 0.30 + mobileBankingHealth * 0.25) -
      criticalIncidents * 1.5,
    72, 96,
  );

  const derived = {
    paymentsHealth, netBankingHealth, mobileBankingHealth,
    openIncidents, criticalIncidents,
    productionHealth, operationalHealth, governanceScore,
    deliveryHealth, engineeringHealth,
    releaseConfidence, openRisks, businessImpactScore, portfolioHealth,
  };

  // previous (for delta-driven insights/UI)
  const previousSnapshot = {
    paymentsHealth: withDrivers.executive?.domainHealth?.find((x) => x.name === 'Payments')?.score ?? 86,
    releaseConfidence: withDrivers.release?.confidence ?? 88,
    openIncidents: withDrivers.executive?.openIncidents ?? 6,
    criticalVapt: withDrivers.governance?.findingSeverity?.find((f) => f.name === 'Critical')?.value ?? 2,
    testCoverage: withDrivers.testing?.coverage ?? 96.5,
  };

  // build visible state
  const executive = deriveExecutive(withDrivers.executive, d, channels, derived);
  const production = deriveProduction(withDrivers.production, d, derived);
  const operations = deriveOperations(withDrivers.operations, d, channels, derived);
  const governance = deriveGovernance(withDrivers.governance, d, derived);
  const testing = deriveTesting(withDrivers.testing, d);
  const delivery = deriveDelivery(withDrivers.delivery, d, derived);
  const release = deriveRelease(withDrivers.release, d, derived);
  const requirements = deriveRequirements(withDrivers.requirements, d);
  const development = deriveDevelopment(withDrivers.development, d);

  const payments = {
    channels,
    aggregateHealth: round(paymentsHealth, 0),
    totalTps: channels.reduce((acc, c) => acc + c.tps, 0),
    criticalChannels: channels.filter((c) => c.health < 80).length,
  };

  const dynamicInsights = buildInsights(previousSnapshot, d, derived, channels);

  return {
    ...withDrivers,
    tick: withDrivers.tick + 1,
    lastUpdated: new Date().toISOString(),
    _drivers: d,
    executive,
    release,
    production,
    operations,
    governance,
    testing,
    delivery,
    requirements,
    development,
    payments,
    dynamicInsights,
    previous: previousSnapshot,
  };
}

export function startSimulation(onTick) {
  stopSimulation();
  let state = bootstrapDrivers(createInitialState());
  // emit once immediately with the initial state so UI is populated, then tick.
  onTick(state);
  intervalId = setInterval(() => {
    state = tickSimulation(state);
    onTick(state);
  }, REFRESH_MS);
  return () => stopSimulation();
}

export function stopSimulation() {
  if (intervalId) {
    clearInterval(intervalId);
    intervalId = null;
  }
}

export function forceTick(state) {
  return tickSimulation(state);
}

/**
 * Re-export for callers that historically imported from simulationService.
 * Same name & signature, so the AI insights & drilldown engines keep working.
 */
export function generateExecutiveInsights(prev, current) {
  const insights = [];
  const payDelta = current.paymentsHealth - prev.paymentsHealth;
  if (payDelta !== 0) {
    insights.push(
      `Payments domain health ${payDelta > 0 ? 'improved' : 'reduced'} by ${Math.abs(payDelta)}% (now ${current.paymentsHealth}%).`,
    );
  }
  const relDelta = Number((current.releaseConfidence - prev.releaseConfidence).toFixed(0));
  if (relDelta !== 0) {
    insights.push(`Release confidence ${relDelta > 0 ? 'improved' : 'declined'} by ${Math.abs(relDelta)}%.`);
  }
  if (current.openIncidents !== prev.openIncidents) {
    insights.push(
      `Open incidents ${current.openIncidents < prev.openIncidents ? 'reduced' : 'increased'} from ${prev.openIncidents} to ${current.openIncidents}.`,
    );
  }
  if (current.criticalVapt !== prev.criticalVapt) {
    insights.push(
      `Critical VAPT findings ${current.criticalVapt < prev.criticalVapt ? 'reduced' : 'increased'} from ${prev.criticalVapt} to ${current.criticalVapt}.`,
    );
  }
  const covDelta = Number((current.testCoverage - prev.testCoverage).toFixed(1));
  if (Math.abs(covDelta) >= 0.1) {
    insights.push(`Test coverage ${covDelta > 0 ? 'increased' : 'decreased'} by ${Math.abs(covDelta)}%.`);
  }
  if (insights.length === 0) {
    insights.push('Operations telemetry stable — no material shifts in the last cycle.');
  }
  return insights.slice(0, 5);
}
