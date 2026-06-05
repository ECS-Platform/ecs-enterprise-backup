/**
 * Executive summary generator.
 *
 * Produces a structured narrative purely from the current `SimulationState`
 * (no hard-coded text bodies). Every sentence and bullet is derived from
 * live values produced by `simulationEngine.js`. The same module exposes a
 * `formatSummaryAsText` helper used by the drawer's Copy and Export-to-Text
 * actions.
 *
 * @typedef {import('../types/executiveSummary').ExecutiveSummary} ExecutiveSummary
 * @typedef {import('../types/simulation').SimulationState} SimulationState
 */

/** @param {number} v */
function healthBand(v) {
  if (v >= 90) return 'Healthy';
  if (v >= 80) return 'Watch';
  return 'Attention';
}

function pluralise(n, singular, plural) {
  return `${n} ${n === 1 ? singular : plural ?? `${singular}s`}`;
}

function pct(v, d = 0) {
  return `${Number(v).toFixed(d)}%`;
}

function simTimeFromState(state) {
  const d = state._drivers;
  if (!d || typeof d.simHour !== 'number') return '';
  const h = Math.floor(d.simHour);
  const m = Math.round((d.simHour - h) * 60);
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
}

/**
 * Produce an ExecutiveSummary snapshot from the supplied simulation state.
 * @param {SimulationState} state
 * @returns {ExecutiveSummary}
 */
export function generateExecutiveSummary(state) {
  const { executive, release, production, operations, governance, testing, delivery, payments } = state;
  const sev = governance.findingSeverity.reduce((acc, f) => ({ ...acc, [f.name.toLowerCase()]: f.value }), {
    critical: 0, high: 0, medium: 0, low: 0,
  });

  const criticalIncidents = production.openIncidents.filter((i) => i.severity === 'critical');
  const highIncidents = production.openIncidents.filter((i) => i.severity === 'high');
  const atRiskReleases = release.releases.filter((r) => r.risk === 'high' || r.confidence < 88);
  const blockingChecklist = release.checklist.filter((c) => c.status !== 'completed');

  const paymentsDomain = executive.domainHealth.find((d) => d.name === 'Payments');
  const netDomain = executive.domainHealth.find((d) => d.name === 'Net Banking');
  const mobileDomain = executive.domainHealth.find((d) => d.name === 'Mobile Banking');

  /* -------------------------------------------------------------- */
  /* Headline                                                       */
  /* -------------------------------------------------------------- */
  const headline = buildHeadline({
    portfolioHealth: executive.portfolioHealth,
    band: healthBand(executive.portfolioHealth),
    openIncidents: executive.openIncidents,
    criticalCount: criticalIncidents.length,
    atRiskCount: atRiskReleases.length,
    goNoGo: release.goNoGo,
  });

  /* -------------------------------------------------------------- */
  /* Overall Health Score                                           */
  /* -------------------------------------------------------------- */
  const overallHealthScore = {
    score: Math.round(executive.portfolioHealth),
    label: healthBand(executive.portfolioHealth),
    narrative: [
      `Enterprise portfolio health stands at ${pct(executive.portfolioHealth)} (${healthBand(executive.portfolioHealth)}).`,
      `Payments domain at ${pct(paymentsDomain?.score ?? 0)}, Net Banking at ${pct(netDomain?.score ?? 0)}, Mobile Banking at ${pct(mobileDomain?.score ?? 0)}.`,
      payments?.aggregateHealth != null
        ? `Aggregate Payments channel health (UPI, IMPS, NEFT, RTGS, Merchant) is ${pct(payments.aggregateHealth)} across ${pluralise(payments.channels.length, 'channel')} processing ~${payments.totalTps.toLocaleString()} TPS.`
        : '',
      `${pluralise(executive.openIncidents, 'open incident')} and ${pluralise(executive.openRisks, 'open risk')} currently tracked.`,
    ].filter(Boolean).join(' '),
    breakdown: [
      { name: 'Portfolio Health', value: round(executive.portfolioHealth), status: healthBand(executive.portfolioHealth) },
      { name: 'Production Health', value: round(production.health), status: healthBand(production.health) },
      { name: 'Operational Health', value: round(operations.operationalHealth), status: healthBand(operations.operationalHealth) },
      ...executive.domainHealth.map((d) => ({ name: d.name, value: round(d.score), status: healthBand(d.score) })),
    ],
  };

  /* -------------------------------------------------------------- */
  /* Key Risks                                                       */
  /* -------------------------------------------------------------- */
  /** @type {import('../types/executiveSummary').RiskItem[]} */
  const riskItems = [];
  for (const r of atRiskReleases.slice(0, 3)) {
    riskItems.push({
      title: `${r.name} confidence at ${pct(r.confidence)}`,
      severity: r.risk === 'high' ? 'high' : 'medium',
      impact: r.domain === 'Payments'
        ? 'Payments revenue / settlement SLA exposure'
        : `${r.domain} customer experience exposure`,
      source: 'Release Center',
    });
  }
  if (sev.critical > 0) {
    riskItems.push({
      title: `${pluralise(sev.critical, 'critical governance finding')} open`,
      severity: 'critical',
      impact: 'Regulatory and audit exposure',
      source: 'Governance Center',
    });
  }
  if (criticalIncidents.length > 0) {
    riskItems.push({
      title: `${pluralise(criticalIncidents.length, 'critical incident')} active in production`,
      severity: 'critical',
      impact: `Availability ${pct(production.availability, 2)} · MTTR ${production.mttrMinutes}m`,
      source: 'Production Center',
    });
  }
  if (operations.capacityUtilization >= 80) {
    riskItems.push({
      title: `Capacity utilisation at ${pct(operations.capacityUtilization)}`,
      severity: operations.capacityUtilization >= 88 ? 'high' : 'medium',
      impact: `Headroom under peak Payments load (CPU ${pct(operations.cpuUtilization)})`,
      source: 'Operations Center',
    });
  }
  if (delivery && delivery.changeFailureRate >= 6) {
    riskItems.push({
      title: `Change failure rate at ${pct(delivery.changeFailureRate, 1)}`,
      severity: delivery.changeFailureRate >= 9 ? 'high' : 'medium',
      impact: 'Delivery throughput and release confidence',
      source: 'Delivery Hub',
    });
  }

  const keyRisks = {
    narrative: riskItems.length === 0
      ? `${pluralise(executive.openRisks, 'risk')} tracked across the portfolio with no top-quartile risk currently elevated.`
      : `${pluralise(riskItems.length, 'top risk')} elevated this cycle — ${riskItems.filter((r) => r.severity === 'critical').length} critical, ${riskItems.filter((r) => r.severity === 'high').length} high.`,
    items: riskItems.slice(0, 6),
  };

  /* -------------------------------------------------------------- */
  /* Key Achievements                                                */
  /* -------------------------------------------------------------- */
  const achievements = [];
  if (production.availability >= 99.9) {
    achievements.push(`Production availability sustained at ${pct(production.availability, 2)} (>= 99.90% SLA).`);
  }
  if (production.mttrMinutes <= 20) {
    achievements.push(`MTTR within target at ${production.mttrMinutes} minutes.`);
  }
  for (const kpi of executive.kpis) {
    if (kpi.value >= 95) {
      achievements.push(`${kpi.label} performing at ${pct(kpi.value)} (top quartile).`);
    }
  }
  const completedChecklist = release.checklist.filter((c) => c.status === 'completed');
  if (completedChecklist.length > 0) {
    achievements.push(
      `Release readiness: ${completedChecklist.length} of ${release.checklist.length} gate items completed (${completedChecklist.map((c) => c.item).join('; ')}).`,
    );
  }
  if (payments?.channels?.length) {
    const healthyChannels = payments.channels.filter((c) => c.health >= 92);
    if (healthyChannels.length > 0) {
      achievements.push(
        `${pluralise(healthyChannels.length, 'Payments channel')} operating at ${pct(healthyChannels[0].health)}+ health: ${healthyChannels.map((c) => c.name).join(', ')}.`,
      );
    }
  }
  if (testing.coverage >= 95) {
    achievements.push(`Test coverage at ${pct(testing.coverage, 1)} with ${pct(testing.automation, 1)} automation.`);
  }
  if (governance.governanceScore >= 95) {
    achievements.push(`Governance score at ${pct(governance.governanceScore)} — compliance posture strong.`);
  }
  if (achievements.length === 0) {
    achievements.push('No top-quartile achievements logged this cycle — operations holding steady at baseline.');
  }

  const keyAchievements = {
    narrative: `${pluralise(achievements.length, 'achievement')} recognised this cycle, anchored by sustained availability and active release-gate progress.`,
    items: achievements.slice(0, 6),
  };

  /* -------------------------------------------------------------- */
  /* Critical Incidents                                              */
  /* -------------------------------------------------------------- */
  const incidentItems = [...criticalIncidents, ...highIncidents].slice(0, 5).map((i) => ({
    id: i.id,
    title: i.title,
    domain: i.domain,
    severity: i.severity,
    duration: i.duration ?? '—',
    status: i.status ?? 'Investigating',
  }));
  const paymentsCriticalCount = criticalIncidents.filter((i) => i.domain === 'Payments').length;
  const criticalNarrative = criticalIncidents.length === 0
    ? `No critical incidents active. ${pluralise(highIncidents.length, 'high-severity incident')} under monitoring.`
    : `${pluralise(criticalIncidents.length, 'critical incident')} active, ${paymentsCriticalCount} in Payments. Current MTTR ${production.mttrMinutes} minutes, ${pluralise(production.slaBreaches ?? 0, 'SLA breach', 'SLA breaches')} in window.`;
  const criticalIncidentsSection = {
    narrative: criticalNarrative,
    items: incidentItems,
  };

  /* -------------------------------------------------------------- */
  /* Release Status                                                  */
  /* -------------------------------------------------------------- */
  const releaseItems = release.releases.map((r) => ({
    id: r.id,
    name: r.name,
    domain: r.domain,
    confidence: r.confidence,
    risk: r.risk,
  }));
  const releaseNarrative = [
    `Enterprise release confidence at ${pct(release.confidence)} — current call: ${release.goNoGo}.`,
    `Deployment readiness ${pct(release.deploymentReadiness)}, rollback readiness ${pct(release.rollbackReadiness)}.`,
    atRiskReleases.length > 0
      ? `${pluralise(atRiskReleases.length, 'release')} flagged at risk: ${atRiskReleases.map((r) => r.name).join(', ')}.`
      : 'All in-flight releases tracking above the 88% confidence floor.',
    blockingChecklist.length > 0
      ? `Outstanding gate items: ${blockingChecklist.map((c) => c.item).join('; ')}.`
      : 'All release-readiness gate items completed.',
  ].join(' ');

  const releaseStatusSection = {
    narrative: releaseNarrative,
    goNoGo: release.goNoGo,
    confidence: Math.round(release.confidence),
    items: releaseItems,
  };

  /* -------------------------------------------------------------- */
  /* Governance Status                                               */
  /* -------------------------------------------------------------- */
  const governanceBullets = [
    `Governance score: ${pct(governance.governanceScore)} · baseline compliance ${pct(governance.baselineCompliance)} · policy compliance ${pct(governance.policyCompliance)}.`,
    `Findings open — Critical ${sev.critical}, High ${sev.high}, Medium ${sev.medium}, Low ${sev.low}.`,
    `VAPT findings: ${governance.vaptFindings}; audit observations: ${governance.auditObservations}; policy violations: ${governance.policyViolations}.`,
    ...governance.complianceStandards.map((s) => `${s.name}: ${pct(s.score)}`),
  ];
  const governanceNarrative = sev.critical > 0
    ? `Governance posture under pressure with ${pluralise(sev.critical, 'critical finding')} open; score reduced to ${pct(governance.governanceScore)}.`
    : `Governance posture stable at ${pct(governance.governanceScore)} with no critical findings open.`;
  const governanceStatusSection = {
    narrative: governanceNarrative,
    score: Math.round(governance.governanceScore),
    bullets: governanceBullets.slice(0, 8),
  };

  /* -------------------------------------------------------------- */
  /* Recommended Actions                                             */
  /* -------------------------------------------------------------- */
  /** @type {import('../types/executiveSummary').ActionItem[]} */
  const actions = [];
  for (const inc of criticalIncidents) {
    actions.push({
      priority: 'P0',
      action: `Resolve ${inc.id} (${inc.title}) — engage ${inc.domain} war-room.`,
      owner: ownerFor(inc.domain),
    });
  }
  for (const r of atRiskReleases) {
    actions.push({
      priority: r.domain === 'Payments' ? 'P1' : 'P2',
      action: `Run readiness re-assessment for ${r.name} (currently ${pct(r.confidence)} confidence, ${r.risk} risk).`,
      owner: ownerFor(r.domain),
    });
  }
  if (sev.critical > 0) {
    actions.push({
      priority: 'P1',
      action: `Remediate ${pluralise(sev.critical, 'critical governance finding')} before next governance review.`,
      owner: 'CISO Office',
    });
  }
  if (operations.capacityUtilization >= 85) {
    actions.push({
      priority: 'P1',
      action: `Scale Payments processing cluster — capacity at ${pct(operations.capacityUtilization)} ahead of EOD settlement window.`,
      owner: 'SRE / Capacity',
    });
  }
  for (const item of blockingChecklist) {
    actions.push({
      priority: 'P2',
      action: `Close release gate item: ${item.item}.`,
      owner: 'Release Manager',
    });
  }
  if (delivery && delivery.changeFailureRate >= 6) {
    actions.push({
      priority: 'P2',
      action: `Address change failure rate (${pct(delivery.changeFailureRate, 1)}) — root-cause last two failed deployments.`,
      owner: 'Engineering Lead',
    });
  }
  if (actions.length === 0) {
    actions.push({
      priority: 'P2',
      action: 'Maintain monitoring cadence — no urgent actions required this cycle.',
      owner: 'Operations Manager',
    });
  }

  const recommendedActions = {
    narrative: `${pluralise(actions.length, 'action')} recommended — ${actions.filter((a) => a.priority === 'P0').length} P0, ${actions.filter((a) => a.priority === 'P1').length} P1, ${actions.filter((a) => a.priority === 'P2').length} P2.`,
    items: actions.slice(0, 8),
  };

  return {
    generatedAt: new Date().toISOString(),
    simulationTick: state.tick,
    simulatedTime: simTimeFromState(state),
    headline,
    overallHealthScore,
    keyRisks,
    keyAchievements,
    criticalIncidents: criticalIncidentsSection,
    releaseStatus: releaseStatusSection,
    governanceStatus: governanceStatusSection,
    recommendedActions,
  };
}

function ownerFor(domain) {
  switch (domain) {
    case 'Payments': return 'Payments Domain Lead';
    case 'Net Banking': return 'Net Banking Lead';
    case 'Mobile Banking': return 'Mobile Banking Lead';
    default: return 'Operations Manager';
  }
}

function buildHeadline({ portfolioHealth, band, openIncidents, criticalCount, atRiskCount, goNoGo }) {
  const parts = [];
  parts.push(`Portfolio at ${pct(portfolioHealth)} (${band})`);
  if (criticalCount > 0) parts.push(`${pluralise(criticalCount, 'critical incident')} active`);
  if (atRiskCount > 0) parts.push(`${pluralise(atRiskCount, 'release')} at risk`);
  parts.push(`release call: ${goNoGo}`);
  return `${parts.join(' · ')} · ${pluralise(openIncidents, 'open incident')} in flight.`;
}

function round(n) {
  return Math.round(n);
}

/**
 * Render an ExecutiveSummary as plain text suitable for clipboard or .txt
 * download. The output is human-readable and uses simple ASCII separators.
 * @param {ExecutiveSummary} s
 * @returns {string}
 */
export function formatSummaryAsText(s) {
  const line = '='.repeat(72);
  const sub = '-'.repeat(72);
  const out = [];
  out.push(line);
  out.push('ENTERPRISE EXECUTIVE SUMMARY');
  out.push(`Generated ${new Date(s.generatedAt).toLocaleString()} · Tick #${s.simulationTick}${s.simulatedTime ? ` · Sim ${s.simulatedTime}` : ''}`);
  out.push(line);
  out.push('');
  out.push(s.headline);
  out.push('');

  // 1. Overall Health Score
  out.push(sub);
  out.push(`1. OVERALL HEALTH SCORE — ${s.overallHealthScore.score}% (${s.overallHealthScore.label})`);
  out.push(sub);
  out.push(s.overallHealthScore.narrative);
  out.push('');
  for (const b of s.overallHealthScore.breakdown) {
    out.push(`  • ${b.name.padEnd(22)} ${String(b.value).padStart(3)}%  ${b.status}`);
  }
  out.push('');

  // 2. Key Risks
  out.push(sub);
  out.push('2. KEY RISKS');
  out.push(sub);
  out.push(s.keyRisks.narrative);
  out.push('');
  for (const r of s.keyRisks.items) {
    out.push(`  • [${r.severity.toUpperCase()}] ${r.title}`);
    out.push(`      Impact: ${r.impact}`);
    out.push(`      Source: ${r.source}`);
  }
  if (s.keyRisks.items.length === 0) out.push('  (no elevated risks this cycle)');
  out.push('');

  // 3. Key Achievements
  out.push(sub);
  out.push('3. KEY ACHIEVEMENTS');
  out.push(sub);
  out.push(s.keyAchievements.narrative);
  out.push('');
  for (const a of s.keyAchievements.items) {
    out.push(`  • ${a}`);
  }
  out.push('');

  // 4. Critical Incidents
  out.push(sub);
  out.push('4. CRITICAL INCIDENTS');
  out.push(sub);
  out.push(s.criticalIncidents.narrative);
  out.push('');
  if (s.criticalIncidents.items.length === 0) {
    out.push('  (no incidents in scope)');
  }
  for (const i of s.criticalIncidents.items) {
    out.push(`  • ${i.id}  [${i.severity.toUpperCase()}]  ${i.title}`);
    out.push(`      Domain: ${i.domain} · Duration: ${i.duration} · Status: ${i.status}`);
  }
  out.push('');

  // 5. Release Status
  out.push(sub);
  out.push(`5. RELEASE STATUS — ${s.releaseStatus.goNoGo} (${s.releaseStatus.confidence}%)`);
  out.push(sub);
  out.push(s.releaseStatus.narrative);
  out.push('');
  for (const r of s.releaseStatus.items) {
    out.push(`  • ${r.id.padEnd(12)} ${r.name.padEnd(28)} ${String(r.confidence).padStart(3)}%  ${r.risk}  (${r.domain})`);
  }
  out.push('');

  // 6. Governance Status
  out.push(sub);
  out.push(`6. GOVERNANCE STATUS — Score ${s.governanceStatus.score}%`);
  out.push(sub);
  out.push(s.governanceStatus.narrative);
  out.push('');
  for (const b of s.governanceStatus.bullets) {
    out.push(`  • ${b}`);
  }
  out.push('');

  // 7. Recommended Actions
  out.push(sub);
  out.push('7. RECOMMENDED ACTIONS');
  out.push(sub);
  out.push(s.recommendedActions.narrative);
  out.push('');
  for (const a of s.recommendedActions.items) {
    out.push(`  [${a.priority}] ${a.action}`);
    out.push(`        Owner: ${a.owner}`);
  }
  out.push('');
  out.push(line);
  out.push('End of summary.');
  out.push(line);
  return out.join('\n');
}
