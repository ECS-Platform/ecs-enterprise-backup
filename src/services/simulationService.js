import { drift, driftTrend, clamp, createInitialState } from './mockDataEngine.js';

const REFRESH_MS = 15000;

let intervalId = null;

export function getRefreshInterval() {
  return REFRESH_MS;
}

export function tickSimulation(state) {
  const prev = {
    paymentsHealth: state.executive.domainHealth.find((d) => d.name === 'Payments')?.score ?? 86,
    releaseConfidence: state.release.confidence,
    openIncidents: state.executive.openIncidents,
    criticalVapt: state.governance.findingSeverity.find((f) => f.name === 'Critical')?.value ?? 2,
    testCoverage: state.testing.coverage,
  };

  const executive = { ...state.executive };
  executive.kpis = executive.kpis.map((kpi) => {
    const value = drift(kpi.value, 85, 99, 1);
    const trend = clamp(Number((value - kpi.value + kpi.trend * 0.3).toFixed(1)), -5, 5);
    return {
      ...kpi,
      value,
      trend,
      data: driftTrend(kpi.data, 85, 99),
    };
  });

  executive.openRisks = clamp(drift(executive.openRisks, 8, 22, 1), 8, 22);
  executive.openIncidents = clamp(drift(executive.openIncidents, 2, 10, 1), 2, 10);
  executive.businessImpactScore = drift(executive.businessImpactScore, 72, 95, 1);
  executive.portfolioHealth = drift(executive.portfolioHealth, 85, 98, 1);

  executive.domainHealth = executive.domainHealth.map((d) => {
    const score = d.name === 'Payments'
      ? drift(d.score, 82, 92, 1)
      : drift(d.score, 88, 97, 1);
    return {
      ...d,
      score,
      changes: clamp(drift(d.changes, 25, 55, 2), 25, 55),
      risks: clamp(drift(d.risks, 2, 12, 1), 2, 12),
      incidents: d.name === 'Payments'
        ? clamp(drift(d.incidents, 3, 8, 1), 3, 8)
        : clamp(drift(d.incidents, 0, 4, 1), 0, 4),
      trend: driftTrend(d.trend, 82, 98),
    };
  });

  executive.portfolioMetrics = [
    { label: 'Active Changes', value: clamp(drift(executive.portfolioMetrics[0].value, 100, 160, 3), 100, 160), trend: executive.portfolioMetrics[0].trend },
    { label: 'In-Flight Releases', value: clamp(drift(executive.portfolioMetrics[1].value, 2, 6, 1), 2, 6), trend: 0 },
    { label: 'Open Incidents', value: executive.openIncidents, trend: executive.openIncidents < prev.openIncidents ? -12 : 4 },
    { label: 'Open Risks', value: executive.openRisks, trend: executive.openRisks < 14 ? -3 : 2 },
  ];

  executive.businessImpactAreas = executive.businessImpactAreas.map((a) => ({
    ...a,
    value: drift(a.value, 70, 96, 1),
  }));

  const release = { ...state.release };
  release.confidence = drift(release.confidence, 80, 96, 1);
  release.rollbackReadiness = drift(release.rollbackReadiness, 85, 98, 1);
  release.deploymentReadiness = drift(release.deploymentReadiness, 80, 95, 1);
  release.readiness = release.readiness.map((r) => {
    const score = drift(r.score, 78, 98, 1);
    return { ...r, score, status: score < 86 ? 'At Risk' : 'Ready' };
  });
  release.releases = release.releases.map((r) => ({
    ...r,
    confidence: r.name.includes('UPI')
      ? drift(r.confidence, 78, 90, 1)
      : drift(r.confidence, 85, 96, 1),
  }));
  release.goNoGo = release.confidence >= 85 ? 'GO' : 'NO-GO';

  const production = { ...state.production };
  production.availability = Number(drift(production.availability, 99.9, 99.99, 0.01).toFixed(2));
  production.mttrMinutes = clamp(drift(production.mttrMinutes, 15, 35, 2), 15, 35);
  production.health = drift(production.health, 85, 96, 1);
  production.activeIncidents = executive.openIncidents;
  production.incidentTrend = production.incidentTrend.map((d, i) => ({
    ...d,
    count: clamp(drift(d.count, 0, 5, 1), 0, 5),
  }));

  const operations = { ...state.operations };
  operations.capacityUtilization = drift(operations.capacityUtilization, 58, 88, 2);
  operations.cpuUtilization = drift(operations.cpuUtilization, 55, 90, 2);
  operations.storageUtilization = drift(operations.storageUtilization, 65, 85, 1);
  operations.batchHealth = drift(operations.batchHealth, 88, 99, 1);
  operations.operationalHealth = drift(operations.operationalHealth, 82, 94, 1);
  operations.capacityTrend = operations.capacityTrend.map((p) => ({
    hour: p.hour,
    cpu: drift(p.cpu, 35, 90, 3),
    memory: drift(p.memory, 40, 85, 3),
    storage: drift(p.storage, 70, 82, 1),
  }));

  const governance = { ...state.governance };
  governance.governanceScore = drift(governance.governanceScore, 90, 99, 1);
  governance.vaptFindings = clamp(drift(governance.vaptFindings, 12, 24, 1), 12, 24);
  governance.baselineCompliance = drift(governance.baselineCompliance, 88, 98, 1);
  governance.policyCompliance = drift(governance.policyCompliance, 90, 99, 1);

  const testing = { ...state.testing };
  testing.coverage = Number(drift(testing.coverage, 94, 99, 0.2).toFixed(1));
  testing.automation = Number(drift(testing.automation, 65, 78, 0.3).toFixed(1));
  testing.optimizationProgress = clamp(drift(testing.optimizationProgress, 45, 75, 2), 45, 75);

  const delivery = { ...state.delivery };
  delivery.requirementsAnalysed = clamp(drift(delivery.requirementsAnalysed, 260, 320, 2), 260, 320);
  delivery.testCoverageAvg = Number(drift(delivery.testCoverageAvg, 92, 98, 0.2).toFixed(1));
  delivery.codeQualityAvg = drift(delivery.codeQualityAvg, 84, 92, 1);

  const requirements = { ...state.requirements };
  requirements.qualityScore = drift(requirements.qualityScore, 82, 92, 1);

  const dynamicInsights = generateExecutiveInsights(prev, {
    paymentsHealth: executive.domainHealth.find((d) => d.name === 'Payments')?.score,
    releaseConfidence: release.confidence,
    openIncidents: executive.openIncidents,
    criticalVapt: governance.findingSeverity.find((f) => f.name === 'Critical')?.value,
    testCoverage: testing.coverage,
  });

  return {
    ...state,
    tick: state.tick + 1,
    lastUpdated: new Date().toISOString(),
    executive,
    release,
    production,
    operations,
    governance,
    testing,
    delivery,
    requirements,
    dynamicInsights,
    previous: {
      paymentsHealth: prev.paymentsHealth,
      releaseConfidence: prev.releaseConfidence,
      openIncidents: prev.openIncidents,
      criticalVapt: prev.criticalVapt,
      testCoverage: prev.testCoverage,
    },
  };
}

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
    insights.push('UPI Release 24.6 remains highest risk due to Fraud Engine dependency.');
    insights.push(`Payments incidents: ${current.openIncidents >= 5 ? 'elevated' : 'within threshold'} for operations review.`);
  }

  return insights.slice(0, 5);
}

export function startSimulation(onTick) {
  stopSimulation();
  let state = createInitialState();
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
