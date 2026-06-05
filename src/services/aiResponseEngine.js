/**
 * Contextual AI responses for Operations Manager query console.
 * @param {string} question
 * @param {import('./mockDataEngine.js').createInitialState extends () => infer S ? S : never} state
 */
export function generateAIResponse(question, state) {
  const q = question.toLowerCase().trim();
  const pay = state.executive.domainHealth.find((d) => d.name === 'Payments');
  const highestRiskRelease = [...state.release.releases].sort((a, b) => a.confidence - b.confidence)[0];
  const criticalCount = state.production.openIncidents.filter(
    (i) => i.severity === 'critical',
  ).length;
  const failedBatch = state.operations.batchJobs.find((j) => j.status === 'Failed');

  if (q.includes('payments') && (q.includes('health') || q.includes('lower') || q.includes('why'))) {
    return formatAnswer([
      `Payments domain health is ${pay?.score}% (below Net Banking and Mobile Banking).`,
      `Because:`,
      `• ${pay?.incidents ?? 0} open incidents in Payments`,
      `• ${pay?.risks ?? 0} open operational/architecture risks`,
      `• Fraud Engine dependency issues affecting UPI path`,
      `• Release readiness below target (UPI Release 24.6 at ${state.release.releases.find((r) => r.name.includes('UPI'))?.confidence ?? 84}%)`,
      `• Active critical incidents: ${state.production.openIncidents.filter((i) => i.domain === 'Payments' && i.severity === 'critical').length}`,
    ]);
  }

  if (q.includes('release') && (q.includes('risk') || q.includes('highest'))) {
    const r = highestRiskRelease;
    const defects = r.risk === 'high' ? 2 : 1;
    return formatAnswer([
      `${r.name}`,
      `Reason:`,
      `• ${defects} critical defects pending closure`,
      `• Fraud Engine dependency on UPI settlement path`,
      `• Governance review pending for merchant auto-settlement changes`,
      `• Current confidence: ${r.confidence}% (${r.risk} risk)`,
      `• Rollback readiness: ${state.release.rollbackReadiness}%`,
    ]);
  }

  if (q.includes('upi') && (q.includes('block') || q.includes('24.6'))) {
    return formatAnswer([
      `UPI Release 24.6 blockers:`,
      `• Fraud rules validation in progress (${state.release.checklist.find((c) => c.item.includes('Fraud'))?.status})`,
      `• Fraud Engine timeout incidents (${criticalCount} critical production issues)`,
      `• CAB approval pending`,
      `• Architecture readiness: ${state.release.readiness.find((r) => r.dimension === 'Architecture')?.score}%`,
      `Recommended: complete fraud validation before deployment window.`,
    ]);
  }

  if (q.includes('incident') && (q.includes('critical') || q.includes('how many') || q.includes('open'))) {
    return formatAnswer([
      `${state.executive.openIncidents} open incidents enterprise-wide.`,
      `${criticalCount} classified as critical.`,
      `Active critical:`,
      ...state.production.openIncidents
        .filter((i) => i.severity === 'critical')
        .map((i) => `• ${i.id} — ${i.title} (${i.domain})`),
      `MTTR current average: ${state.production.mttrMinutes} minutes.`,
    ]);
  }

  if (q.includes('mttr')) {
    return formatAnswer([
      `Current MTTR: ${state.production.mttrMinutes} minutes.`,
      `Production health: ${state.production.health}%.`,
      `Availability: ${state.production.availability}%.`,
      `Trend: ${state.production.mttrMinutes <= 20 ? 'within SLA target' : 'above target — review Fraud Engine and UPI settlement runbooks'}.`,
    ]);
  }

  if (q.includes('batch') && q.includes('fail')) {
    return formatAnswer([
      failedBatch
        ? `Failed batch: ${failedBatch.name} (${failedBatch.progress}% complete before failure).`
        : 'No failed batch jobs in the current monitoring window.',
      `Batch health: ${state.operations.batchHealth}%.`,
      `Active jobs: ${state.operations.activeJobs}.`,
      `Failed jobs: ${state.operations.failedJobs}.`,
      failedBatch ? 'Action: restart Mandate Reconciliation after settlement DB pool review.' : '',
    ].filter(Boolean));
  }

  if (q.includes('governance') || q.includes('vapt') || q.includes('compliance')) {
    return formatAnswer([
      `Governance score: ${state.governance.governanceScore}%.`,
      `VAPT findings: ${state.governance.vaptFindings}.`,
      `Policy violations: ${state.governance.policyViolations}.`,
      `Top finding: ${state.governance.topFindings[0]?.title ?? 'None'}.`,
      `PCI-DSS compliance: ${state.governance.complianceStandards.find((c) => c.name.includes('PCI'))?.score}%.`,
    ]);
  }

  if (q.includes('capacity') || q.includes('utilization')) {
    return formatAnswer([
      `Capacity utilization: ${state.operations.capacityUtilization}%.`,
      `CPU: ${state.operations.cpuUtilization}% · Storage: ${state.operations.storageUtilization}%.`,
      `Forecast D+3: ${state.operations.capacityForecast[2]?.predicted}% predicted load.`,
      state.operations.capacityUtilization > 75
        ? 'Recommendation: scale Payments API cluster before EOD settlement.'
        : 'Capacity within operational thresholds.',
    ]);
  }

  return formatAnswer([
    `Operations snapshot (${new Date(state.lastUpdated).toLocaleTimeString()}):`,
    `• Portfolio health: ${state.executive.portfolioHealth}%`,
    `• Open incidents: ${state.executive.openIncidents} · Open risks: ${state.executive.openRisks}`,
    `• Payments health: ${pay?.score}%`,
    `• Release confidence: ${state.release.confidence}%`,
    `• Highest risk release: ${highestRiskRelease.name}`,
    `Ask a specific question about Payments health, releases, incidents, MTTR, or batch jobs.`,
  ]);
}

function formatAnswer(lines) {
  return lines.join('\n');
}
