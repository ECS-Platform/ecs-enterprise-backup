/**
 * Evidence-based AI responses for Operations Manager query console.
 * @param {string} question
 * @param {import('./mockDataEngine.js').createInitialState extends () => infer S ? S : never} state
 */
export function generateAIResponse(question, state) {
  const q = question.toLowerCase().trim();
  const pay = state.executive.domainHealth.find((d) => d.name === 'Payments');
  const highestRiskRelease = [...state.release.releases].sort((a, b) => a.confidence - b.confidence)[0];
  const atRiskReleases = state.release.releases.filter((r) => r.risk === 'high' || r.confidence < 88);
  const paymentsIncidents = state.production.openIncidents.filter((i) => i.domain === 'Payments');
  const criticalCount = state.production.openIncidents.filter((i) => i.severity === 'critical').length;
  const failedBatch = state.operations.batchJobs.find((j) => j.status === 'Failed');
  const unresolvedFindings = state.governance.topFindings.filter(
    (f) => f.severity === 'critical' || f.severity === 'high',
  );
  const pendingChecklist = state.release.checklist.filter((c) => c.status !== 'completed');
  const latestDefects = state.testing.defectTrend[state.testing.defectTrend.length - 1];

  if (q.includes('payments') && (q.includes('health') || q.includes('lower') || q.includes('why'))) {
    const prev = state.previous.paymentsHealth ?? (pay?.score ?? 86) + Math.abs((pay?.score ?? 86) - 91);
    const current = pay?.score ?? 86;
    const sev2Count = paymentsIncidents.filter((i) => i.severity === 'high').length;
    const sev1Count = paymentsIncidents.filter((i) => i.severity === 'critical').length;
    const failedReleases = atRiskReleases.filter((r) => r.domain === 'Payments').length;
    const govFindings = unresolvedFindings.length;

    return formatAnswer([
      `Payments Health reduced from ${prev} to ${current} due to:`,
      '',
      `• ${sev2Count + sev1Count} Sev2 incidents${sev1Count ? ` (${sev1Count} critical)` : ''}`,
      `• ${failedReleases || 1} failed release${failedReleases === 1 ? '' : 's'}`,
      `• ${govFindings} open governance finding${govFindings === 1 ? '' : 's'}`,
      '',
      'Contributing signals:',
      ...paymentsIncidents.slice(0, 3).map((i) => `• ${i.id} — ${i.title} (${i.severity})`),
      `• Production health: ${state.production.health}% · Fraud Engine uptime ${state.production.serviceHealth.find((s) => s.name === 'Fraud Engine')?.uptime ?? 98.6}%`,
      `• UPI Release 24.6 confidence: ${state.release.releases.find((r) => r.name.includes('UPI'))?.confidence ?? 84}%`,
    ]);
  }

  if (
    q.includes('release') && (q.includes('risk') || q.includes('at risk') || q.includes('highest'))
  ) {
    if (q.includes('releases') || q.includes('which') || q.includes('what')) {
      if (atRiskReleases.length === 0) {
        return formatAnswer([
          'No releases currently flagged as high risk.',
          `Enterprise release confidence: ${state.release.confidence}%.`,
          `Deployment readiness: ${state.release.deploymentReadiness}%.`,
        ]);
      }
      return formatAnswer([
        `${atRiskReleases.length} release${atRiskReleases.length === 1 ? '' : 's'} at risk:`,
        '',
        ...atRiskReleases.flatMap((r) => releaseRiskLines(r, state, pendingChecklist, latestDefects, unresolvedFindings)),
      ]);
    }

    const r = highestRiskRelease;
    return formatAnswer([
      `${r.name} is at risk because:`,
      '',
      ...releaseRiskBullets(r, state, pendingChecklist, latestDefects, unresolvedFindings),
    ]);
  }

  if (q.includes('upi') && (q.includes('block') || q.includes('24.6'))) {
    const upi = state.release.releases.find((r) => r.name.includes('UPI')) ?? highestRiskRelease;
    return formatAnswer([
      `UPI Release 24.6 blockers:`,
      '',
      ...releaseRiskBullets(upi, state, pendingChecklist, latestDefects, unresolvedFindings),
      `• Fraud rules validation: ${state.release.checklist.find((c) => c.item.includes('Fraud'))?.status ?? 'in progress'}`,
      `• Architecture readiness: ${state.release.readiness.find((r) => r.dimension === 'Architecture')?.score}%`,
    ]);
  }

  if (q.includes('incident') && (q.includes('critical') || q.includes('how many') || q.includes('open'))) {
    return formatAnswer([
      `${state.executive.openIncidents} open incidents enterprise-wide.`,
      `${criticalCount} classified as critical.`,
      '',
      'Active critical:',
      ...state.production.openIncidents
        .filter((i) => i.severity === 'critical')
        .map((i) => `• ${i.id} — ${i.title} (${i.domain})`),
      '',
      `MTTR: ${state.production.mttrMinutes} minutes · Availability: ${state.production.availability}%`,
      ...state.production.topIssues.slice(0, 2).map((i) => `• RCA: ${i.issue}`),
    ]);
  }

  if (q.includes('mttr')) {
    return formatAnswer([
      `Current MTTR: ${state.production.mttrMinutes} minutes.`,
      `Production health: ${state.production.health}%.`,
      `Availability: ${state.production.availability}%.`,
      '',
      'Driving incidents:',
      ...state.production.openIncidents.slice(0, 3).map((i) => `• ${i.id} — ${i.title} (${i.duration ?? 'active'})`),
      state.production.mttrMinutes <= 20
        ? 'Trend: within SLA target.'
        : 'Trend: above target — review Fraud Engine and UPI settlement runbooks.',
    ]);
  }

  if (q.includes('batch') && q.includes('fail')) {
    return formatAnswer([
      failedBatch
        ? `Failed batch: ${failedBatch.name} (${failedBatch.progress}% complete before failure).`
        : 'No failed batch jobs in the current monitoring window.',
      `Batch health: ${state.operations.batchHealth}%.`,
      `Active jobs: ${state.operations.activeJobs} · Failed jobs: ${state.operations.failedJobs}.`,
      '',
      ...state.operations.operationalRisks.slice(0, 2).map((r) => `• ${r.title} (${r.severity})`),
      failedBatch ? 'Action: restart Mandate Reconciliation after settlement DB pool review.' : '',
    ].filter(Boolean));
  }

  if (q.includes('governance') || q.includes('vapt') || q.includes('compliance')) {
    return formatAnswer([
      `Governance score: ${state.governance.governanceScore}%.`,
      `VAPT findings: ${state.governance.vaptFindings} · Policy violations: ${state.governance.policyViolations}.`,
      '',
      'Open findings:',
      ...unresolvedFindings.map((f) => `• ${f.title} (${f.severity})`),
      '',
      `PCI-DSS compliance: ${state.governance.complianceStandards.find((c) => c.name.includes('PCI'))?.score}%.`,
      ...state.governance.auditTrail.slice(0, 2).map((a) => `• ${a.event} (${a.time})`),
    ]);
  }

  if (q.includes('test') || q.includes('coverage')) {
    return formatAnswer([
      `Test coverage: ${state.testing.coverage}% · Automation: ${state.testing.automation}%.`,
      `Effectiveness: ${state.testing.effectiveness}% · Defect leakage: ${state.testing.defectLeakage}.`,
      '',
      'Latest defect cycle:',
      `• Found: ${latestDefects?.found ?? 0} · Escaped: ${latestDefects?.escaped ?? 0}`,
      '',
      'AI recommendations:',
      ...state.testing.aiRecommendations.map((r) => `• ${r}`),
    ]);
  }

  if (q.includes('capacity') || q.includes('utilization')) {
    return formatAnswer([
      `Capacity utilization: ${state.operations.capacityUtilization}%.`,
      `CPU: ${state.operations.cpuUtilization}% · Storage: ${state.operations.storageUtilization}%.`,
      `Forecast D+3: ${state.operations.capacityForecast[2]?.predicted}% predicted load.`,
      '',
      ...state.operations.operationalRisks.map((r) => `• ${r.title} (${r.severity})`),
      state.operations.capacityUtilization > 75
        ? 'Recommendation: scale Payments API cluster before EOD settlement.'
        : 'Capacity within operational thresholds.',
    ]);
  }

  return formatAnswer([
    `Operations snapshot (${new Date(state.lastUpdated).toLocaleTimeString()}):`,
    '',
    `• Portfolio health: ${state.executive.portfolioHealth}%`,
    `• Open incidents: ${state.executive.openIncidents} · Open risks: ${state.executive.openRisks}`,
    `• Payments health: ${pay?.score}%`,
    `• Release confidence: ${state.release.confidence}%`,
    `• Highest risk release: ${highestRiskRelease.name} (${highestRiskRelease.confidence}%)`,
    '',
    'Ask about Payments health, releases at risk, incidents, MTTR, governance, testing, or batch jobs.',
  ]);
}

/**
 * @param {import('./mockDataEngine.js').createInitialState extends () => infer S ? S : never} state
 */
function releaseRiskBullets(release, state, pendingChecklist, latestDefects, unresolvedFindings) {
  const failedSuites = pendingChecklist.length + (latestDefects?.escaped ?? 0);
  const findings = unresolvedFindings.filter(
    (f) => release.domain === 'Payments' || f.title.toLowerCase().includes('api'),
  ).length || Math.min(unresolvedFindings.length, 2);

  return [
    `• ${failedSuites} failed test suite${failedSuites === 1 ? '' : 's'}`,
    `• ${findings} unresolved finding${findings === 1 ? '' : 's'}`,
    `• deployment confidence reduced to ${release.confidence}%`,
    `• Rollback readiness: ${state.release.rollbackReadiness}% · Deployment readiness: ${state.release.deploymentReadiness}%`,
    ...state.release.riskMatrix
      .filter((r) => r.domain === release.domain)
      .slice(0, 2)
      .map((r) => `• Risk: ${r.title} (${r.severity})`),
  ];
}

function releaseRiskLines(release, state, pendingChecklist, latestDefects, unresolvedFindings) {
  return [
    release.name,
    ...releaseRiskBullets(release, state, pendingChecklist, latestDefects, unresolvedFindings),
    '',
  ];
}

function formatAnswer(lines) {
  return lines.join('\n');
}
