import { sparkline7d } from './mockDataEngine.js';

/** @typedef {import('../types/kpiDrilldown').KpiDrilldownPayload} KpiDrilldownPayload */
/** @typedef {import('../types/kpiDrilldown').KpiDrilldownContext} KpiDrilldownContext */
/** @typedef {import('../types/simulation').SimulationState} SimulationState */

/**
 * @param {SimulationState} state
 * @returns {{ name: string; status?: string }[]}
 */
function appsFromArchitecture(state) {
  return state.architecture.services.map((s) => ({
    name: s.label,
    status: s.risk,
  }));
}

/**
 * @param {SimulationState} state
 * @returns {{ id: string; title: string; severity: string; domain?: string }[]}
 */
function incidentsFromState(state) {
  return state.production.openIncidents.map((i) => ({
    id: i.id,
    title: i.title,
    severity: i.severity,
    domain: i.domain,
  }));
}

/**
 * @param {SimulationState} state
 * @returns {{ id: string; name: string; confidence: number; risk: string }[]}
 */
function releasesFromState(state) {
  return state.release.releases.map((r) => ({
    id: r.id,
    name: r.name,
    confidence: r.confidence,
    risk: r.risk,
  }));
}

/**
 * @param {KpiDrilldownContext} ctx
 * @param {Partial<KpiDrilldownPayload>} overrides
 * @returns {KpiDrilldownPayload}
 */
function buildPayload(ctx, overrides = {}) {
  return {
    label: ctx.label,
    value: ctx.value,
    suffix: ctx.suffix,
    sourceRecords: [],
    supportingEvidence: [],
    relatedApplications: [],
    relatedIncidents: [],
    relatedReleases: [],
    historicalTrend: ctx.data?.length ? ctx.data : sparkline7d(90),
    ...overrides,
  };
}

/** @type {Record<string, (state: SimulationState, ctx: KpiDrilldownContext) => KpiDrilldownPayload>} */
const resolvers = {
  'Delivery Health': (state, ctx) =>
    buildPayload(ctx, {
      sourceRecords: state.delivery.topRequirements.map((r) => ({
        id: r.id,
        title: r.title,
        detail: r.domain,
        meta: `${r.risk} risk · ${r.impact}`,
      })),
      supportingEvidence: [
        `Pipeline velocity: ${state.delivery.pipelineVelocity.map((p) => `${p.stage} (${p.count})`).join(', ')}`,
        `Change failure rate: ${state.delivery.changeFailureRate}%`,
        `Lead time: ${state.delivery.leadTimeHours} hours`,
      ],
      relatedApplications: appsFromArchitecture(state).slice(0, 4),
      relatedIncidents: incidentsFromState(state).slice(0, 2),
      relatedReleases: releasesFromState(state),
      historicalTrend: ctx.data ?? sparkline7d(Number(ctx.value) || 94),
    }),

  'Production Health': (state, ctx) =>
    buildPayload(ctx, {
      sourceRecords: state.production.serviceHealth.map((s) => ({
        id: s.name,
        title: s.name,
        detail: `Uptime ${s.uptime}%`,
        meta: s.status,
      })),
      supportingEvidence: state.production.topIssues.map((i) => `${i.issue}: ${i.rca}`),
      relatedApplications: appsFromArchitecture(state).filter((a) => a.status === 'critical' || a.status === 'high'),
      relatedIncidents: incidentsFromState(state),
      relatedReleases: releasesFromState(state).filter((r) => r.risk !== 'low'),
      historicalTrend: state.production.incidentTrend.map((p) => ({ day: p.day, value: p.count * 10 })),
    }),

  'Governance Health': (state, ctx) =>
    buildPayload(ctx, {
      sourceRecords: state.governance.topFindings.map((f, i) => ({
        id: `GOV-${i + 1}`,
        title: f.title,
        meta: f.severity,
      })),
      supportingEvidence: [
        ...state.governance.auditTrail.map((a) => `${a.event} (${a.time})`),
        `Policy compliance: ${state.governance.policyCompliance}%`,
      ],
      relatedApplications: appsFromArchitecture(state).filter((a) => a.status === 'critical'),
      relatedIncidents: incidentsFromState(state).filter((i) => i.severity === 'critical'),
      relatedReleases: releasesFromState(state),
      historicalTrend: ctx.data ?? sparkline7d(state.governance.governanceScore),
    }),

  'Engineering Health': (state, ctx) =>
    buildPayload(ctx, {
      sourceRecords: state.development.securityItems.map((s, i) => ({
        id: `SEC-${i + 1}`,
        title: s.title,
        meta: s.severity,
      })),
      supportingEvidence: [
        `PR aging: ${state.development.prAging.map((p) => `${p.range}: ${p.count}`).join(' · ')}`,
        `Tech debt items: ${state.development.techDebt}`,
      ],
      relatedApplications: appsFromArchitecture(state),
      relatedIncidents: incidentsFromState(state).slice(0, 2),
      relatedReleases: releasesFromState(state),
      historicalTrend: state.development.qualityTrend.map((p) => ({ day: p.month, value: p.quality })),
    }),

  'Open Risks': (state, ctx) =>
    buildPayload(ctx, {
      sourceRecords: state.executive.riskByPhase.map((p) => ({
        id: p.name,
        title: p.name,
        detail: 'SDLC phase',
        meta: `${p.value} risks`,
      })),
      supportingEvidence: state.requirements.topRiskRequirements.map(
        (r) => `${r.id} — ${r.title} (${r.risk})`,
      ),
      relatedApplications: appsFromArchitecture(state).filter((a) => a.status !== 'low'),
      relatedIncidents: incidentsFromState(state),
      relatedReleases: releasesFromState(state).filter((r) => r.risk === 'high'),
      historicalTrend: sparkline7d(state.executive.openRisks * 4),
    }),

  'Open Incidents': (state, ctx) =>
    buildPayload(ctx, {
      sourceRecords: state.production.openIncidents.map((i) => ({
        id: i.id,
        title: i.title,
        detail: i.domain,
        meta: `${i.severity} · ${i.status}`,
      })),
      supportingEvidence: state.production.topIssues.map((i) => i.rca),
      relatedApplications: state.production.serviceHealth
        .filter((s) => s.status !== 'healthy')
        .map((s) => ({ name: s.name, status: s.status })),
      relatedIncidents: incidentsFromState(state),
      relatedReleases: releasesFromState(state).filter((r) => r.domain === 'Payments'),
      historicalTrend: state.production.incidentTrend.map((p) => ({ day: p.day, value: p.count })),
    }),

  'Business Impact': (state, ctx) =>
    buildPayload(ctx, {
      sourceRecords: state.executive.businessImpactAreas.map((a) => ({
        id: a.name,
        title: a.name,
        meta: `${a.value}% impact score`,
      })),
      supportingEvidence: state.dynamicInsights.slice(0, 3),
      relatedApplications: appsFromArchitecture(state).slice(0, 3),
      relatedIncidents: incidentsFromState(state).filter((i) => i.severity !== 'low'),
      relatedReleases: releasesFromState(state),
      historicalTrend: sparkline7d(state.executive.businessImpactScore),
    }),

  'Portfolio Health': (state, ctx) =>
    buildPayload(ctx, {
      sourceRecords: state.executive.scorecard.map((s) => ({
        id: s.label,
        title: s.label,
        meta: `${s.value}%`,
      })),
      supportingEvidence: state.dynamicInsights,
      relatedApplications: appsFromArchitecture(state),
      relatedIncidents: incidentsFromState(state),
      relatedReleases: releasesFromState(state),
      historicalTrend: ctx.data ?? sparkline7d(state.executive.portfolioHealth),
    }),

  'Active Changes': (state, ctx) =>
    buildPayload(ctx, {
      sourceRecords: state.delivery.pipelineVelocity.map((p) => ({
        id: p.stage,
        title: p.stage,
        detail: `${p.count} items`,
        meta: `Avg ${p.avgDays}d`,
      })),
      supportingEvidence: [
        `Sprint burndown on track: ${state.delivery.sprintBurndown[state.delivery.sprintBurndown.length - 1]?.actual}% complete`,
      ],
      relatedApplications: appsFromArchitecture(state),
      relatedIncidents: incidentsFromState(state).slice(0, 2),
      relatedReleases: releasesFromState(state),
      historicalTrend: sparkline7d(120),
    }),

  'In-Flight Releases': (state, ctx) =>
    buildPayload(ctx, {
      sourceRecords: state.release.releases.map((r) => ({
        id: r.id,
        title: r.name,
        detail: r.domain,
        meta: `${r.confidence}% · ${r.risk} risk`,
      })),
      supportingEvidence: state.release.checklist.map((c) => `${c.item}: ${c.status}`),
      relatedApplications: appsFromArchitecture(state).filter((a) => a.status === 'critical'),
      relatedIncidents: incidentsFromState(state),
      relatedReleases: releasesFromState(state),
      historicalTrend: sparkline7d(state.release.confidence),
    }),

  'Requirements Analysed': (state, ctx) =>
    buildPayload(ctx, {
      sourceRecords: state.requirements.topRiskRequirements.map((r) => ({
        id: r.id,
        title: r.title,
        detail: r.domain,
        meta: `${r.risk} · ${r.impact}`,
      })),
      supportingEvidence: state.requirements.complianceBreakdown.map(
        (c) => `${c.name}: ${c.count} requirements`,
      ),
      relatedApplications: appsFromArchitecture(state).slice(0, 4),
      relatedIncidents: incidentsFromState(state).slice(0, 2),
      relatedReleases: releasesFromState(state),
      historicalTrend: sparkline7d(85),
    }),

  'Business Impact Index': (state, ctx) =>
    buildPayload(ctx, {
      sourceRecords: state.executive.businessImpactAreas.map((a) => ({
        id: a.name,
        title: a.name,
        meta: `${a.value}%`,
      })),
      supportingEvidence: state.delivery.topRequirements.map((r) => `${r.title} — ${r.impact} impact`),
      relatedApplications: appsFromArchitecture(state),
      relatedIncidents: incidentsFromState(state),
      relatedReleases: releasesFromState(state),
      historicalTrend: sparkline7d(state.delivery.businessImpactIndex),
    }),

  'Compliance Impact': (state, ctx) =>
    buildPayload(ctx, {
      sourceRecords: state.requirements.complianceBreakdown.map((c) => ({
        id: c.name,
        title: c.name,
        meta: `${c.count} reqs`,
      })),
      supportingEvidence: state.governance.complianceStandards.map((s) => `${s.name}: ${s.score}%`),
      relatedApplications: [{ name: 'Payment Gateway', status: 'high' }, { name: 'UPI Switch', status: 'critical' }],
      relatedIncidents: incidentsFromState(state).slice(0, 2),
      relatedReleases: releasesFromState(state).filter((r) => r.domain === 'Payments'),
      historicalTrend: sparkline7d(state.requirements.complianceImpact * 3),
    }),

  'Requirement Risks': (state, ctx) =>
    buildPayload(ctx, {
      sourceRecords: state.requirements.topRiskRequirements.map((r) => ({
        id: r.id,
        title: r.title,
        meta: r.risk,
      })),
      supportingEvidence: state.requirements.riskDistribution.map((d) => `${d.name}: ${d.value}`),
      relatedApplications: appsFromArchitecture(state),
      relatedIncidents: incidentsFromState(state),
      relatedReleases: releasesFromState(state),
      historicalTrend: sparkline7d(state.delivery.requirementRisks * 5),
    }),

  'Architecture Risks': (state, ctx) =>
    buildPayload(ctx, {
      sourceRecords: state.architecture.techRisks.map((r, i) => ({
        id: `AR-${i + 1}`,
        title: r.title,
        meta: r.severity,
      })),
      supportingEvidence: state.architecture.recommendations,
      relatedApplications: appsFromArchitecture(state),
      relatedIncidents: incidentsFromState(state).filter((i) => i.domain === 'Payments'),
      relatedReleases: releasesFromState(state),
      historicalTrend: sparkline7d(state.architecture.readiness),
    }),

  'Technical Debt': (state, ctx) =>
    buildPayload(ctx, {
      sourceRecords: state.development.securityItems.map((s, i) => ({
        id: `TD-${i + 1}`,
        title: s.title,
        meta: s.severity,
      })),
      supportingEvidence: [
        `Tech debt score: ${state.development.techDebt} items`,
        ...state.architecture.recommendations,
      ],
      relatedApplications: appsFromArchitecture(state).filter((a) => a.status !== 'low'),
      relatedIncidents: incidentsFromState(state).slice(0, 1),
      relatedReleases: releasesFromState(state),
      historicalTrend: state.development.qualityTrend.map((p) => ({ day: p.month, value: p.debt })),
    }),

  'Test Coverage': (state, ctx) =>
    buildPayload(ctx, {
      sourceRecords: state.testing.coverageHeatmap.map((row, i) => ({
        id: `COV-${i}`,
        title: row[0],
        detail: state.testing.heatmapEnvs.map((env, j) => `${env}: ${row[j + 1]}%`).join(' · '),
      })),
      supportingEvidence: state.testing.aiRecommendations,
      relatedApplications: appsFromArchitecture(state),
      relatedIncidents: incidentsFromState(state).slice(0, 2),
      relatedReleases: releasesFromState(state),
      historicalTrend: sparkline7d(typeof ctx.value === 'number' ? ctx.value : state.testing.coverage),
    }),

  'Code Quality': (state, ctx) =>
    buildPayload(ctx, {
      sourceRecords: state.development.securityItems.map((s, i) => ({
        id: `CQ-${i + 1}`,
        title: s.title,
        meta: s.severity,
      })),
      supportingEvidence: state.development.prAging.map((p) => `${p.range}: ${p.count} PRs`),
      relatedApplications: appsFromArchitecture(state),
      relatedIncidents: incidentsFromState(state).slice(0, 1),
      relatedReleases: releasesFromState(state),
      historicalTrend: state.development.qualityTrend.map((p) => ({ day: p.month, value: p.quality })),
    }),

  'Change Failure Rate': (state, ctx) =>
    buildPayload(ctx, {
      sourceRecords: state.release.riskMatrix.map((r, i) => ({
        id: `CFR-${i}`,
        title: r.title,
        meta: r.severity,
      })),
      supportingEvidence: [`Deployment frequency: ${state.delivery.deploymentFrequency}/month`],
      relatedApplications: appsFromArchitecture(state).filter((a) => a.status === 'critical'),
      relatedIncidents: incidentsFromState(state),
      relatedReleases: releasesFromState(state),
      historicalTrend: sparkline7d(95 - state.delivery.changeFailureRate * 5),
    }),

  'Deployments / Month': (state, ctx) =>
    buildPayload(ctx, {
      sourceRecords: releasesFromState(state).map((r) => ({
        id: r.id,
        title: r.name,
        meta: `${r.confidence}%`,
      })),
      supportingEvidence: state.release.checklist.map((c) => c.item),
      relatedApplications: appsFromArchitecture(state),
      relatedIncidents: incidentsFromState(state).slice(0, 2),
      relatedReleases: releasesFromState(state),
      historicalTrend: state.development.commitTrend.map((p) => ({ day: p.week, value: p.prs * 8 })),
    }),

  'Lead Time': (state, ctx) =>
    buildPayload(ctx, {
      sourceRecords: state.delivery.pipelineVelocity.map((p) => ({
        id: p.stage,
        title: p.stage,
        meta: `${p.avgDays}d avg`,
      })),
      supportingEvidence: [`Defect density: ${state.delivery.defectDensity}/KLOC`],
      relatedApplications: appsFromArchitecture(state),
      relatedIncidents: incidentsFromState(state).slice(0, 1),
      relatedReleases: releasesFromState(state),
      historicalTrend: sparkline7d(100 - state.delivery.leadTimeHours / 2),
    }),

  'Defect Density': (state, ctx) =>
    buildPayload(ctx, {
      sourceRecords: state.testing.defectTrend.map((d) => ({
        id: d.week,
        title: d.week,
        detail: `${d.found} found, ${d.escaped} escaped`,
      })),
      supportingEvidence: [`Defect leakage: ${state.testing.defectLeakage}`],
      relatedApplications: appsFromArchitecture(state),
      relatedIncidents: incidentsFromState(state),
      relatedReleases: releasesFromState(state),
      historicalTrend: state.testing.defectTrend.map((d) => ({ day: d.week, value: d.found })),
    }),

  'High Risk': (state, ctx) =>
    buildPayload(ctx, {
      sourceRecords: state.requirements.topRiskRequirements
        .filter((r) => r.risk === 'high')
        .map((r) => ({ id: r.id, title: r.title, meta: r.domain })),
      supportingEvidence: state.requirements.riskDistribution.map((d) => `${d.name}: ${d.value}`),
      relatedApplications: appsFromArchitecture(state).filter((a) => a.status === 'critical'),
      relatedIncidents: incidentsFromState(state),
      relatedReleases: releasesFromState(state).filter((r) => r.risk === 'high'),
      historicalTrend: sparkline7d(state.requirements.highRisk * 4),
    }),

  Ambiguous: (state, ctx) =>
    buildPayload(ctx, {
      sourceRecords: state.requirements.topRiskRequirements.slice(0, 3).map((r) => ({
        id: r.id,
        title: r.title,
        detail: 'Ambiguity flagged in acceptance criteria',
        meta: r.domain,
      })),
      supportingEvidence: [`Analysis queue: ${state.requirements.analysisQueue} pending reviews`],
      relatedApplications: appsFromArchitecture(state).slice(0, 3),
      relatedIncidents: incidentsFromState(state).slice(0, 1),
      relatedReleases: releasesFromState(state),
      historicalTrend: sparkline7d(state.requirements.ambiguous * 8),
    }),

  'Missing Criteria': (state, ctx) =>
    buildPayload(ctx, {
      sourceRecords: state.requirements.topRiskRequirements.slice(1, 4).map((r) => ({
        id: r.id,
        title: r.title,
        detail: 'Missing acceptance criteria',
        meta: r.risk,
      })),
      supportingEvidence: [`Quality score: ${state.requirements.qualityScore}%`],
      relatedApplications: appsFromArchitecture(state).slice(0, 2),
      relatedIncidents: incidentsFromState(state).slice(0, 1),
      relatedReleases: releasesFromState(state),
      historicalTrend: sparkline7d(state.requirements.missingCriteria * 10),
    }),

  'Compliance-Tagged': (state, ctx) =>
    buildPayload(ctx, {
      sourceRecords: state.requirements.complianceBreakdown.map((c) => ({
        id: c.name,
        title: c.name,
        meta: `${c.count} tagged`,
      })),
      supportingEvidence: state.governance.complianceStandards.map((s) => `${s.name}: ${s.score}%`),
      relatedApplications: appsFromArchitecture(state),
      relatedIncidents: incidentsFromState(state).slice(0, 2),
      relatedReleases: releasesFromState(state),
      historicalTrend: sparkline7d(state.requirements.complianceImpact * 4),
    }),

  'Architecture Readiness': (state, ctx) =>
    buildPayload(ctx, {
      sourceRecords: state.architecture.layerReadiness.map((l) => ({
        id: l.label,
        title: l.label,
        meta: `${l.value}%`,
      })),
      supportingEvidence: state.architecture.techRisks.map((r) => r.title),
      relatedApplications: appsFromArchitecture(state),
      relatedIncidents: incidentsFromState(state),
      relatedReleases: releasesFromState(state),
      historicalTrend: sparkline7d(state.architecture.readiness),
    }),

  'Critical Dependencies': (state, ctx) =>
    buildPayload(ctx, {
      sourceRecords: state.architecture.techRisks
        .filter((r) => r.severity === 'critical' || r.severity === 'high')
        .map((r, i) => ({ id: `DEP-${i}`, title: r.title, meta: r.severity })),
      supportingEvidence: state.architecture.edges.map((e) => e.join(' → ')),
      relatedApplications: appsFromArchitecture(state).filter((a) => a.status === 'critical'),
      relatedIncidents: incidentsFromState(state).filter((i) => i.severity === 'critical'),
      relatedReleases: releasesFromState(state).filter((r) => r.name.includes('UPI')),
      historicalTrend: sparkline7d(state.architecture.criticalDependencies * 12),
    }),

  'Integration Risks': (state, ctx) =>
    buildPayload(ctx, {
      sourceRecords: state.architecture.techRisks.map((r, i) => ({
        id: `INT-${i}`,
        title: r.title,
        meta: r.severity,
      })),
      supportingEvidence: state.architecture.recommendations,
      relatedApplications: appsFromArchitecture(state),
      relatedIncidents: incidentsFromState(state),
      relatedReleases: releasesFromState(state),
      historicalTrend: sparkline7d(80),
    }),

  'Cross-Team Dependencies': (state, ctx) =>
    buildPayload(ctx, {
      sourceRecords: state.architecture.edges.map((e, i) => ({
        id: `XTD-${i}`,
        title: e.join(' ↔ '),
        detail: 'Service dependency',
      })),
      supportingEvidence: state.architecture.layerReadiness.map((l) => `${l.label}: ${l.value}%`),
      relatedApplications: appsFromArchitecture(state),
      relatedIncidents: incidentsFromState(state).slice(0, 2),
      relatedReleases: releasesFromState(state),
      historicalTrend: sparkline7d(state.architecture.crossTeamDeps * 6),
    }),

  'Pull Requests': (state, ctx) =>
    buildPayload(ctx, {
      sourceRecords: state.development.prAging.map((p) => ({
        id: p.range,
        title: p.range,
        meta: `${p.count} PRs`,
      })),
      supportingEvidence: state.development.securityItems.map((s) => s.title),
      relatedApplications: appsFromArchitecture(state),
      relatedIncidents: incidentsFromState(state).slice(0, 1),
      relatedReleases: releasesFromState(state),
      historicalTrend: state.development.commitTrend.map((p) => ({ day: p.week, value: p.prs })),
    }),

  Commits: (state, ctx) =>
    buildPayload(ctx, {
      sourceRecords: state.development.commitTrend.map((p) => ({
        id: p.week,
        title: p.week,
        meta: `${p.commits} commits`,
      })),
      supportingEvidence: [`Code quality: ${state.development.codeQuality}%`],
      relatedApplications: appsFromArchitecture(state),
      relatedIncidents: incidentsFromState(state).slice(0, 1),
      relatedReleases: releasesFromState(state),
      historicalTrend: state.development.commitTrend.map((p) => ({ day: p.week, value: p.commits })),
    }),

  'Tech Debt': (state, ctx) =>
    resolvers['Technical Debt'](state, ctx),

  'Dev Health': (state, ctx) =>
    buildPayload(ctx, {
      sourceRecords: state.development.securityItems.map((s, i) => ({
        id: `DH-${i}`,
        title: s.title,
        meta: s.severity,
      })),
      supportingEvidence: [
        `Commits: ${state.development.commits} · PRs: ${state.development.pullRequests}`,
      ],
      relatedApplications: appsFromArchitecture(state),
      relatedIncidents: incidentsFromState(state).slice(0, 2),
      relatedReleases: releasesFromState(state),
      historicalTrend: state.development.qualityTrend.map((p) => ({ day: p.month, value: p.quality })),
    }),

  'Total Tests': (state, ctx) =>
    buildPayload(ctx, {
      sourceRecords: state.testing.coverageHeatmap.map((row, i) => ({
        id: `TST-${i}`,
        title: String(row[0]),
        detail: `Coverage across ${state.testing.heatmapEnvs.join(', ')}`,
      })),
      supportingEvidence: state.testing.aiRecommendations,
      relatedApplications: appsFromArchitecture(state),
      relatedIncidents: incidentsFromState(state).slice(0, 2),
      relatedReleases: releasesFromState(state),
      historicalTrend: sparkline7d(90),
    }),

  'Manual Tests': (state, ctx) =>
    buildPayload(ctx, {
      sourceRecords: state.testing.coverageHeatmap.map((row, i) => ({
        id: `MAN-${i}`,
        title: String(row[0]),
        meta: `Manual coverage gap: ${100 - Number(row[1])}%`,
      })),
      supportingEvidence: [`Automation rate: ${state.testing.automation}%`],
      relatedApplications: appsFromArchitecture(state).slice(0, 3),
      relatedIncidents: incidentsFromState(state).slice(0, 1),
      relatedReleases: releasesFromState(state),
      historicalTrend: sparkline7d(state.testing.manualTests / 100),
    }),

  Coverage: (state, ctx) => resolvers['Test Coverage'](state, ctx),

  Automation: (state, ctx) =>
    buildPayload(ctx, {
      sourceRecords: state.testing.aiRecommendations.map((r, i) => ({
        id: `AUTO-${i}`,
        title: r,
      })),
      supportingEvidence: [`Effectiveness: ${state.testing.effectiveness}%`],
      relatedApplications: appsFromArchitecture(state),
      relatedIncidents: incidentsFromState(state).slice(0, 1),
      relatedReleases: releasesFromState(state),
      historicalTrend: sparkline7d(state.testing.automation),
    }),

  Effectiveness: (state, ctx) =>
    buildPayload(ctx, {
      sourceRecords: state.testing.defectTrend.map((d) => ({
        id: d.week,
        title: d.week,
        detail: `Escaped defects: ${d.escaped}`,
      })),
      supportingEvidence: [`Defect leakage: ${state.testing.defectLeakage}`],
      relatedApplications: appsFromArchitecture(state),
      relatedIncidents: incidentsFromState(state),
      relatedReleases: releasesFromState(state),
      historicalTrend: sparkline7d(state.testing.effectiveness),
    }),

  'AI Recommended': (state, ctx) =>
    buildPayload(ctx, {
      sourceRecords: state.testing.aiRecommendations.map((r, i) => ({
        id: `AI-${i}`,
        title: r,
      })),
      supportingEvidence: [`Optimization progress: ${state.testing.optimizationProgress}%`],
      relatedApplications: appsFromArchitecture(state).filter((a) => a.status === 'critical'),
      relatedIncidents: incidentsFromState(state).slice(0, 2),
      relatedReleases: releasesFromState(state).filter((r) => r.risk === 'high'),
      historicalTrend: sparkline7d(state.testing.recommended / 3),
    }),

  'Release Confidence': (state, ctx) =>
    buildPayload(ctx, {
      sourceRecords: state.release.readiness.map((r) => ({
        id: r.dimension,
        title: r.dimension,
        meta: `${r.score}% · ${r.status}`,
      })),
      supportingEvidence: state.release.checklist.map((c) => `${c.item}: ${c.status}`),
      relatedApplications: appsFromArchitecture(state).filter((a) => a.status === 'critical'),
      relatedIncidents: incidentsFromState(state),
      relatedReleases: releasesFromState(state),
      historicalTrend: sparkline7d(state.release.confidence),
    }),

  'Rollback Readiness': (state, ctx) =>
    buildPayload(ctx, {
      sourceRecords: state.release.releases.map((r) => ({
        id: r.id,
        title: r.name,
        meta: `${r.confidence}% confidence`,
      })),
      supportingEvidence: state.release.riskMatrix.map((r) => r.title),
      relatedApplications: appsFromArchitecture(state),
      relatedIncidents: incidentsFromState(state),
      relatedReleases: releasesFromState(state),
      historicalTrend: sparkline7d(state.release.rollbackReadiness),
    }),

  'Deployment Readiness': (state, ctx) =>
    buildPayload(ctx, {
      sourceRecords: state.release.checklist.map((c, i) => ({
        id: `CHK-${i}`,
        title: c.item,
        meta: c.status,
      })),
      supportingEvidence: state.release.riskMatrix.map((r) => `${r.title} (${r.severity})`),
      relatedApplications: appsFromArchitecture(state),
      relatedIncidents: incidentsFromState(state),
      relatedReleases: releasesFromState(state),
      historicalTrend: sparkline7d(state.release.deploymentReadiness),
    }),

  'Go / No-Go': (state, ctx) =>
    buildPayload(ctx, {
      sourceRecords: state.release.readiness.map((r) => ({
        id: r.dimension,
        title: r.dimension,
        meta: r.status,
      })),
      supportingEvidence: [
        `Enterprise decision: ${state.release.goNoGo}`,
        ...state.release.checklist.filter((c) => c.status !== 'completed').map((c) => `Pending: ${c.item}`),
      ],
      relatedApplications: appsFromArchitecture(state).filter((a) => a.status !== 'low'),
      relatedIncidents: incidentsFromState(state).filter((i) => i.severity === 'critical'),
      relatedReleases: releasesFromState(state),
      historicalTrend: sparkline7d(state.release.confidence),
    }),

  Availability: (state, ctx) =>
    buildPayload(ctx, {
      sourceRecords: state.production.serviceHealth.map((s) => ({
        id: s.name,
        title: s.name,
        meta: `${s.uptime}% uptime`,
      })),
      supportingEvidence: [`SLA breaches: ${state.production.slaBreaches}`],
      relatedApplications: state.production.serviceHealth.map((s) => ({
        name: s.name,
        status: s.status,
      })),
      relatedIncidents: incidentsFromState(state),
      relatedReleases: releasesFromState(state),
      historicalTrend: sparkline7d(state.production.availability),
    }),

  MTTR: (state, ctx) =>
    buildPayload(ctx, {
      sourceRecords: state.production.openIncidents.map((i) => ({
        id: i.id,
        title: i.title,
        detail: i.duration,
        meta: i.severity,
      })),
      supportingEvidence: state.production.topIssues.map((i) => i.rca),
      relatedApplications: state.production.serviceHealth
        .filter((s) => s.status !== 'healthy')
        .map((s) => ({ name: s.name, status: s.status })),
      relatedIncidents: incidentsFromState(state),
      relatedReleases: releasesFromState(state),
      historicalTrend: sparkline7d(100 - state.production.mttrMinutes),
    }),

  'Service Health': (state, ctx) =>
    buildPayload(ctx, {
      sourceRecords: state.production.serviceHealth.map((s) => ({
        id: s.name,
        title: s.name,
        meta: s.status,
      })),
      supportingEvidence: state.production.topIssues.map((i) => i.issue),
      relatedApplications: state.production.serviceHealth.map((s) => ({
        name: s.name,
        status: s.status,
      })),
      relatedIncidents: incidentsFromState(state),
      relatedReleases: releasesFromState(state),
      historicalTrend: sparkline7d(state.production.health),
    }),

  'Batch Health': (state, ctx) =>
    buildPayload(ctx, {
      sourceRecords: state.operations.batchJobs.map((j, i) => ({
        id: `BATCH-${i}`,
        title: j.name,
        meta: `${j.status} · ${j.progress}%`,
      })),
      supportingEvidence: state.operations.operationalRisks.map((r) => `${r.title} (${r.severity})`),
      relatedApplications: [{ name: 'Core Banking', status: 'low' }, { name: 'UPI Switch', status: 'critical' }],
      relatedIncidents: incidentsFromState(state).slice(0, 2),
      relatedReleases: releasesFromState(state),
      historicalTrend: sparkline7d(state.operations.batchHealth),
    }),

  'Capacity Utilization': (state, ctx) =>
    buildPayload(ctx, {
      sourceRecords: state.operations.capacityForecast.map((f) => ({
        id: f.day,
        title: f.day,
        meta: `${f.predicted}% predicted`,
      })),
      supportingEvidence: state.operations.operationalRisks.map((r) => r.title),
      relatedApplications: appsFromArchitecture(state).slice(0, 4),
      relatedIncidents: incidentsFromState(state).slice(0, 2),
      relatedReleases: releasesFromState(state),
      historicalTrend: state.operations.capacityTrend.map((p) => ({ day: p.hour, value: p.cpu })),
    }),

  'CPU Utilization': (state, ctx) =>
    buildPayload(ctx, {
      sourceRecords: state.operations.capacityTrend.map((p) => ({
        id: p.hour,
        title: `${p.hour}:00`,
        meta: `CPU ${p.cpu}%`,
      })),
      supportingEvidence: [`Memory avg: ${state.operations.capacityTrend[3]?.memory}%`],
      relatedApplications: appsFromArchitecture(state),
      relatedIncidents: incidentsFromState(state).slice(0, 1),
      relatedReleases: releasesFromState(state),
      historicalTrend: state.operations.capacityTrend.map((p) => ({ day: p.hour, value: p.cpu })),
    }),

  'Storage Utilization': (state, ctx) =>
    buildPayload(ctx, {
      sourceRecords: state.operations.capacityTrend.map((p) => ({
        id: `ST-${p.hour}`,
        title: `${p.hour}:00`,
        meta: `Storage ${p.storage}%`,
      })),
      supportingEvidence: state.operations.operationalRisks.map((r) => r.title),
      relatedApplications: appsFromArchitecture(state).slice(0, 3),
      relatedIncidents: incidentsFromState(state).slice(0, 1),
      relatedReleases: releasesFromState(state),
      historicalTrend: state.operations.capacityTrend.map((p) => ({ day: p.hour, value: p.storage })),
    }),

  'Audit Findings': (state, ctx) =>
    buildPayload(ctx, {
      sourceRecords: state.governance.auditTrail.map((a, i) => ({
        id: `AUD-${i}`,
        title: a.event,
        meta: a.time,
      })),
      supportingEvidence: state.governance.topFindings.map((f) => f.title),
      relatedApplications: appsFromArchitecture(state),
      relatedIncidents: incidentsFromState(state).slice(0, 2),
      relatedReleases: releasesFromState(state),
      historicalTrend: sparkline7d(90),
    }),

  'VAPT Findings': (state, ctx) =>
    buildPayload(ctx, {
      sourceRecords: state.governance.topFindings.map((f, i) => ({
        id: `VAPT-${i}`,
        title: f.title,
        meta: f.severity,
      })),
      supportingEvidence: state.governance.findingSeverity.map((f) => `${f.name}: ${f.value}`),
      relatedApplications: appsFromArchitecture(state).filter((a) => a.status !== 'low'),
      relatedIncidents: incidentsFromState(state),
      relatedReleases: releasesFromState(state),
      historicalTrend: sparkline7d(85),
    }),

  'Policy Violations': (state, ctx) =>
    buildPayload(ctx, {
      sourceRecords: state.governance.topFindings
        .filter((f) => f.severity === 'medium' || f.severity === 'high')
        .map((f, i) => ({ id: `POL-${i}`, title: f.title, meta: f.severity })),
      supportingEvidence: [`Policy compliance: ${state.governance.policyCompliance}%`],
      relatedApplications: appsFromArchitecture(state),
      relatedIncidents: incidentsFromState(state).slice(0, 1),
      relatedReleases: releasesFromState(state),
      historicalTrend: sparkline7d(92),
    }),

  'Security Findings': (state, ctx) =>
    buildPayload(ctx, {
      sourceRecords: state.development.securityItems.map((s, i) => ({
        id: `SEC-${i}`,
        title: s.title,
        meta: s.severity,
      })),
      supportingEvidence: state.governance.topFindings.map((f) => f.title),
      relatedApplications: appsFromArchitecture(state),
      relatedIncidents: incidentsFromState(state),
      relatedReleases: releasesFromState(state),
      historicalTrend: sparkline7d(88),
    }),

  'Governance Score': (state, ctx) => resolvers['Governance Health'](state, ctx),

  'Lessons Learned': (state, ctx) =>
    buildPayload(ctx, {
      sourceRecords: state.learning.recentLessons.map((l, i) => ({
        id: `LL-${i}`,
        title: l.text,
        meta: l.time,
      })),
      supportingEvidence: state.learning.analytics.map((a) => `${a.label}: ${a.value}`),
      relatedApplications: appsFromArchitecture(state).slice(0, 3),
      relatedIncidents: state.learning.incidents.map((i, idx) => ({
        id: `LINC-${idx}`,
        title: i.title,
        severity: i.severity,
      })),
      relatedReleases: releasesFromState(state),
      historicalTrend: sparkline7d(state.learning.lessonsLearned / 2),
    }),

  'Reusable Assets': (state, ctx) =>
    buildPayload(ctx, {
      sourceRecords: state.learning.knowledgeBase.map((k, i) => ({
        id: `KB-${i}`,
        title: k.title,
        meta: `${k.category} · ${k.views} views`,
      })),
      supportingEvidence: state.learning.recentLessons.map((l) => l.text),
      relatedApplications: appsFromArchitecture(state),
      relatedIncidents: incidentsFromState(state).slice(0, 2),
      relatedReleases: releasesFromState(state),
      historicalTrend: sparkline7d(state.learning.reusableAssets / 3),
    }),

  'Similar Incidents': (state, ctx) =>
    buildPayload(ctx, {
      sourceRecords: state.learning.incidents.map((i, idx) => ({
        id: `SIM-${idx}`,
        title: i.title,
        meta: i.date,
      })),
      supportingEvidence: state.production.topIssues.map((i) => i.issue),
      relatedApplications: appsFromArchitecture(state),
      relatedIncidents: incidentsFromState(state),
      relatedReleases: releasesFromState(state),
      historicalTrend: sparkline7d(state.learning.similarIncidents / 10),
    }),

  'Tech Debt Logged': (state, ctx) =>
    buildPayload(ctx, {
      sourceRecords: state.architecture.techRisks.map((r, i) => ({
        id: `TDL-${i}`,
        title: r.title,
        meta: r.severity,
      })),
      supportingEvidence: state.development.securityItems.map((s) => s.title),
      relatedApplications: appsFromArchitecture(state),
      relatedIncidents: incidentsFromState(state).slice(0, 1),
      relatedReleases: releasesFromState(state),
      historicalTrend: state.development.qualityTrend.map((p) => ({ day: p.month, value: p.debt })),
    }),

  'Reports Generated': (state, ctx) =>
    buildPayload(ctx, {
      sourceRecords: state.reports.reportTypes.map((r, i) => ({
        id: `RPT-${i}`,
        title: r.name,
        meta: r.type,
      })),
      supportingEvidence: [`Last export: ${state.reports.lastExport}`],
      relatedApplications: appsFromArchitecture(state).slice(0, 2),
      relatedIncidents: incidentsFromState(state).slice(0, 2),
      relatedReleases: releasesFromState(state),
      historicalTrend: sparkline7d(state.reports.generated * 3),
    }),

  'Scheduled Reports': (state, ctx) =>
    buildPayload(ctx, {
      sourceRecords: state.reports.reportTypes.map((r, i) => ({
        id: `SCH-${i}`,
        title: r.name,
        meta: `Scheduled · ${r.type}`,
      })),
      supportingEvidence: [`${state.reports.scheduled} active schedules`],
      relatedApplications: appsFromArchitecture(state).slice(0, 2),
      relatedIncidents: incidentsFromState(state).slice(0, 1),
      relatedReleases: releasesFromState(state),
      historicalTrend: sparkline7d(state.reports.scheduled * 10),
    }),
};

/** @type {Record<string, (state: SimulationState, ctx: KpiDrilldownContext) => KpiDrilldownPayload>} */
const chartResolvers = {
  'executive.risk-by-phase': (state, ctx) => {
    const phase = ctx.segment ?? '';
    const phaseReqs = state.requirements.topRiskRequirements.filter((_, i) => {
      const phases = ['Requirements', 'Architecture', 'Development', 'Testing'];
      return phases[i % phases.length] === phase || phase === '';
    });
    return buildPayload(ctx, {
      sourceRecords: phaseReqs.length
        ? phaseReqs.map((r) => ({ id: r.id, title: r.title, detail: r.domain, meta: r.risk }))
        : [{ id: phase, title: `${phase} phase risks`, meta: `${state.executive.riskByPhase.find((p) => p.name === phase)?.value ?? 0} open` }],
      supportingEvidence: state.requirements.topRiskRequirements.map((r) => `${r.id} — ${r.title}`),
      relatedApplications: appsFromArchitecture(state),
      relatedIncidents: incidentsFromState(state),
      relatedReleases: releasesFromState(state),
      historicalTrend: sparkline7d(state.executive.riskByPhase.find((p) => p.name === phase)?.value ?? 5 * 10),
    });
  },

  'executive.business-impact': (state, ctx) => {
    const area = state.executive.businessImpactAreas.find((a) => a.name === ctx.segment);
    return buildPayload(ctx, {
      sourceRecords: state.delivery.topRequirements.map((r) => ({
        id: r.id, title: r.title, detail: r.impact, meta: r.domain,
      })),
      supportingEvidence: [`${ctx.segment} impact score: ${area?.value ?? ctx.value}%`, ...state.dynamicInsights.slice(0, 2)],
      relatedApplications: appsFromArchitecture(state).slice(0, 4),
      relatedIncidents: incidentsFromState(state).slice(0, 3),
      relatedReleases: releasesFromState(state),
      historicalTrend: sparkline7d(area?.value ?? 85),
    });
  },

  'finding-severity': (state, ctx) => {
    const severity = (ctx.segment ?? '').toLowerCase();
    const findings = state.governance.topFindings.filter((f) => !severity || f.severity === severity);
    return buildPayload(ctx, {
      sourceRecords: findings.map((f, i) => ({ id: `FND-${i}`, title: f.title, meta: f.severity })),
      supportingEvidence: state.governance.auditTrail.map((a) => `${a.event} (${a.time})`),
      relatedApplications: appsFromArchitecture(state).filter((a) => a.status !== 'low'),
      relatedIncidents: incidentsFromState(state).filter((i) => !severity || i.severity === severity),
      relatedReleases: releasesFromState(state),
      historicalTrend: sparkline7d(state.governance.governanceScore),
    });
  },

  'requirements.risk-distribution': (state, ctx) => {
    const risk = (ctx.segment ?? '').toLowerCase();
    const reqs = state.requirements.topRiskRequirements.filter((r) => !risk || r.risk === risk);
    return buildPayload(ctx, {
      sourceRecords: reqs.map((r) => ({ id: r.id, title: r.title, detail: r.domain, meta: r.impact })),
      supportingEvidence: state.requirements.complianceBreakdown.map((c) => `${c.name}: ${c.count}`),
      relatedApplications: appsFromArchitecture(state),
      relatedIncidents: incidentsFromState(state).slice(0, 2),
      relatedReleases: releasesFromState(state),
      historicalTrend: sparkline7d(state.requirements.qualityScore),
    });
  },

  'requirements.compliance-breakdown': (state, ctx) => {
    const item = state.requirements.complianceBreakdown.find((c) => c.name === ctx.segment);
    return buildPayload(ctx, {
      sourceRecords: state.requirements.topRiskRequirements
        .filter((r) => r.impact === 'Compliance' || r.domain === 'Payments')
        .map((r) => ({ id: r.id, title: r.title, meta: r.risk })),
      supportingEvidence: state.governance.complianceStandards.map((s) => `${s.name}: ${s.score}%`),
      relatedApplications: appsFromArchitecture(state).slice(0, 3),
      relatedIncidents: incidentsFromState(state).slice(0, 2),
      relatedReleases: releasesFromState(state).filter((r) => r.domain === 'Payments'),
      historicalTrend: sparkline7d((item?.count ?? 1) * 10),
    });
  },

  'requirements.quality-gauge': (state, ctx) => resolvers['Requirements Analysed'](state, { ...ctx, label: 'Requirements Analysed', value: state.requirements.analysed, suffix: '' }),

  'governance.compliance-standards': (state, ctx) => {
    const std = state.governance.complianceStandards.find((s) => s.name === ctx.segment);
    return buildPayload(ctx, {
      sourceRecords: state.governance.topFindings.map((f, i) => ({ id: `GOV-${i}`, title: f.title, meta: f.severity })),
      supportingEvidence: [`${ctx.segment} compliance: ${std?.score ?? ctx.value}%`],
      relatedApplications: appsFromArchitecture(state),
      relatedIncidents: incidentsFromState(state).slice(0, 2),
      relatedReleases: releasesFromState(state),
      historicalTrend: sparkline7d(std?.score ?? 90),
    });
  },

  'governance.gauge': (state, ctx) => resolvers['Governance Health'](state, { ...ctx, label: 'Governance Health', value: state.governance.governanceScore }),

  'governance.compliance-gauge': (state, ctx) => {
    const score = ctx.segment === 'Baseline'
      ? state.governance.baselineCompliance
      : state.governance.policyCompliance;
    return buildPayload(ctx, {
      sourceRecords: state.governance.complianceStandards.map((s) => ({ id: s.name, title: s.name, meta: `${s.score}%` })),
      supportingEvidence: state.governance.auditTrail.map((a) => `${a.event} (${a.time})`),
      relatedApplications: appsFromArchitecture(state),
      relatedIncidents: incidentsFromState(state).slice(0, 2),
      relatedReleases: releasesFromState(state),
      historicalTrend: sparkline7d(score),
    });
  },

  'operations.health-gauge': (state, ctx) => resolvers['Batch Health'](state, { ...ctx, label: 'Batch Health', value: state.operations.operationalHealth }),

  'operations.batch-jobs': (state, ctx) => {
    const job = state.operations.batchJobs.find((j) => j.name === ctx.segment);
    return buildPayload(ctx, {
      sourceRecords: job ? [{ id: job.name, title: job.name, meta: `${job.status} · ${job.progress}%` }] : [],
      supportingEvidence: state.operations.operationalRisks.map((r) => `${r.title} (${r.severity})`),
      relatedApplications: appsFromArchitecture(state).slice(0, 3),
      relatedIncidents: incidentsFromState(state).slice(0, 2),
      relatedReleases: releasesFromState(state),
      historicalTrend: sparkline7d(state.operations.batchHealth),
    });
  },

  'release.confidence-gauge': (state, ctx) => resolvers['Release Confidence'](state, { ...ctx, label: 'Release Confidence', value: state.release.confidence }),

  'release.readiness-dimension': (state, ctx) => {
    const dim = state.release.readiness.find((r) => r.dimension === ctx.segment);
    return buildPayload(ctx, {
      sourceRecords: state.release.checklist.map((c, i) => ({ id: `CHK-${i}`, title: c.item, meta: c.status })),
      supportingEvidence: [`${ctx.segment}: ${dim?.score ?? ctx.value}% · ${dim?.status ?? ''}`],
      relatedApplications: appsFromArchitecture(state).filter((a) => a.status === 'critical'),
      relatedIncidents: incidentsFromState(state),
      relatedReleases: releasesFromState(state),
      historicalTrend: sparkline7d(dim?.score ?? state.release.confidence),
    });
  },

  'architecture.layer-readiness': (state, ctx) => {
    const layer = state.architecture.layerReadiness.find((l) => l.label === ctx.segment);
    return buildPayload(ctx, {
      sourceRecords: state.architecture.techRisks.map((r, i) => ({ id: `AR-${i}`, title: r.title, meta: r.severity })),
      supportingEvidence: state.architecture.recommendations,
      relatedApplications: appsFromArchitecture(state),
      relatedIncidents: incidentsFromState(state).slice(0, 2),
      relatedReleases: releasesFromState(state),
      historicalTrend: sparkline7d(layer?.value ?? state.architecture.readiness),
    });
  },

  'testing.coverage-heatmap': (state, ctx) => {
    const [rowLabel, colLabel] = (ctx.segment ?? '|').split('|');
    return buildPayload(ctx, {
      sourceRecords: state.testing.aiRecommendations.map((r, i) => ({ id: `REC-${i}`, title: r })),
      supportingEvidence: [`${rowLabel} · ${colLabel}: ${ctx.value}% coverage`, ...state.testing.aiRecommendations],
      relatedApplications: appsFromArchitecture(state).filter((a) => rowLabel && a.name.includes(rowLabel.split(' ')[0])),
      relatedIncidents: incidentsFromState(state).slice(0, 2),
      relatedReleases: releasesFromState(state),
      historicalTrend: sparkline7d(Number(ctx.value) || state.testing.coverage),
    });
  },

  'delivery.pipeline-velocity': (state, ctx) => {
    const stage = state.delivery.pipelineVelocity.find((p) => p.stage === ctx.segment);
    return buildPayload(ctx, {
      sourceRecords: state.delivery.topRequirements.map((r) => ({ id: r.id, title: r.title, meta: r.domain })),
      supportingEvidence: [`${ctx.segment}: ${stage?.count ?? ctx.value} items · avg ${stage?.avgDays ?? '—'}d`],
      relatedApplications: appsFromArchitecture(state),
      relatedIncidents: incidentsFromState(state).slice(0, 2),
      relatedReleases: releasesFromState(state),
      historicalTrend: sparkline7d((stage?.count ?? 30) + 60),
    });
  },

  'delivery.sprint-burndown': (state, ctx) => {
    const [day, series] = (ctx.segment ?? '|').split('|');
    const point = state.delivery.sprintBurndown.find((p) => p.day === day);
    const val = series === 'planned' ? point?.planned : point?.actual;
    return buildPayload(ctx, {
      sourceRecords: state.delivery.topRequirements.map((r) => ({ id: r.id, title: r.title, meta: r.risk })),
      supportingEvidence: [`${day} ${series}: ${val ?? ctx.value}% remaining`],
      relatedApplications: appsFromArchitecture(state).slice(0, 3),
      relatedIncidents: incidentsFromState(state).slice(0, 1),
      relatedReleases: releasesFromState(state),
      historicalTrend: state.delivery.sprintBurndown.map((p) => ({ day: p.day, value: p.actual })),
    });
  },

  'development.pr-aging': (state, ctx) => {
    const bucket = state.development.prAging.find((p) => p.range === ctx.segment);
    return buildPayload(ctx, {
      sourceRecords: state.development.securityItems.map((s, i) => ({ id: `PR-${i}`, title: s.title, meta: s.severity })),
      supportingEvidence: [`${ctx.segment}: ${bucket?.count ?? ctx.value} pull requests`],
      relatedApplications: appsFromArchitecture(state),
      relatedIncidents: incidentsFromState(state).slice(0, 1),
      relatedReleases: releasesFromState(state),
      historicalTrend: state.development.commitTrend.map((p) => ({ day: p.week, value: p.prs })),
    });
  },

  'development.commit-trend': (state, ctx) => {
    const [week, series] = (ctx.segment ?? '|').split('|');
    const point = state.development.commitTrend.find((p) => p.week === week);
    const val = series === 'prs' ? point?.prs : point?.commits;
    return buildPayload(ctx, {
      sourceRecords: state.development.securityItems.map((s, i) => ({ id: `CM-${i}`, title: s.title, meta: s.severity })),
      supportingEvidence: [`${week} — ${series ?? 'commits'}: ${val ?? ctx.value}`],
      relatedApplications: appsFromArchitecture(state),
      relatedIncidents: incidentsFromState(state).slice(0, 1),
      relatedReleases: releasesFromState(state),
      historicalTrend: state.development.commitTrend.map((p) => ({ day: p.week, value: p.commits })),
    });
  },

  'production.incident-trend': (state, ctx) => {
    const day = state.production.incidentTrend.find((p) => p.day === ctx.segment);
    return buildPayload(ctx, {
      sourceRecords: state.production.openIncidents.map((i) => ({
        id: i.id, title: i.title, detail: i.domain, meta: i.severity,
      })),
      supportingEvidence: state.production.topIssues.map((i) => i.rca),
      relatedApplications: state.production.serviceHealth.map((s) => ({ name: s.name, status: s.status })),
      relatedIncidents: incidentsFromState(state),
      relatedReleases: releasesFromState(state),
      historicalTrend: state.production.incidentTrend.map((p) => ({ day: p.day, value: p.count })),
    });
  },

  'requirements.top-risk': (state, ctx) => {
    const req = state.requirements.topRiskRequirements.find((r) => r.id === ctx.segment);
    return buildPayload(ctx, {
      sourceRecords: req ? [{ id: req.id, title: req.title, detail: req.domain, meta: `${req.risk} · ${req.impact}` }] : [],
      supportingEvidence: state.requirements.complianceBreakdown.map((c) => `${c.name}: ${c.count}`),
      relatedApplications: appsFromArchitecture(state),
      relatedIncidents: incidentsFromState(state).filter((i) => i.domain === req?.domain),
      relatedReleases: releasesFromState(state).filter((r) => r.domain === req?.domain),
      historicalTrend: sparkline7d(state.requirements.qualityScore),
    });
  },

  'delivery.top-requirements': (state, ctx) => {
    const req = state.delivery.topRequirements.find((r) => r.id === ctx.segment);
    return buildPayload(ctx, {
      sourceRecords: req ? [{ id: req.id, title: req.title, detail: req.domain, meta: req.risk }] : [],
      supportingEvidence: state.delivery.pipelineVelocity.map((p) => `${p.stage}: ${p.count} items`),
      relatedApplications: appsFromArchitecture(state),
      relatedIncidents: incidentsFromState(state),
      relatedReleases: releasesFromState(state),
      historicalTrend: sparkline7d(state.delivery.businessImpactIndex),
    });
  },

  'release.in-flight': (state, ctx) => {
    const rel = state.release.releases.find((r) => r.id === ctx.segment);
    return buildPayload(ctx, {
      sourceRecords: state.release.checklist.map((c, i) => ({ id: `CHK-${i}`, title: c.item, meta: c.status })),
      supportingEvidence: state.release.riskMatrix.map((r) => r.title),
      relatedApplications: appsFromArchitecture(state).filter((a) => a.status === 'critical'),
      relatedIncidents: incidentsFromState(state).filter((i) => i.domain === rel?.domain),
      relatedReleases: rel ? [{ id: rel.id, name: rel.name, confidence: rel.confidence, risk: rel.risk }] : releasesFromState(state),
      historicalTrend: sparkline7d(rel?.confidence ?? state.release.confidence),
    });
  },

  'release.risk-matrix': (state, ctx) => {
    const risk = state.release.riskMatrix.find((r) => r.title === ctx.segment);
    return buildPayload(ctx, {
      sourceRecords: risk ? [{ id: 'RISK-1', title: risk.title, detail: risk.domain, meta: risk.severity }] : [],
      supportingEvidence: state.release.checklist.map((c) => `${c.item}: ${c.status}`),
      relatedApplications: appsFromArchitecture(state),
      relatedIncidents: incidentsFromState(state),
      relatedReleases: releasesFromState(state).filter((r) => r.domain === risk?.domain),
      historicalTrend: sparkline7d(state.release.confidence),
    });
  },

  'governance.top-findings': (state, ctx) => {
    const finding = state.governance.topFindings.find((f) => f.title === ctx.segment);
    return buildPayload(ctx, {
      sourceRecords: finding ? [{ id: 'FND-1', title: finding.title, meta: finding.severity }] : [],
      supportingEvidence: state.governance.auditTrail.map((a) => `${a.time} — ${a.event}`),
      relatedApplications: appsFromArchitecture(state),
      relatedIncidents: incidentsFromState(state),
      relatedReleases: releasesFromState(state),
      historicalTrend: sparkline7d(state.governance.governanceScore),
    });
  },

  'production.open-incidents': (state, ctx) => {
    const inc = state.production.openIncidents.find((i) => i.id === ctx.segment);
    const rca = state.production.topIssues.find((i) => i.issue === inc?.title);
    return buildPayload(ctx, {
      sourceRecords: inc ? [{ id: inc.id, title: inc.title, detail: inc.domain, meta: `${inc.severity} · ${inc.status}` }] : [],
      supportingEvidence: rca ? [rca.rca] : state.production.topIssues.map((i) => i.rca),
      relatedApplications: state.production.serviceHealth.map((s) => ({ name: s.name, status: s.status })),
      relatedIncidents: inc ? [{ id: inc.id, title: inc.title, severity: inc.severity, domain: inc.domain }] : incidentsFromState(state),
      relatedReleases: releasesFromState(state),
      historicalTrend: state.production.incidentTrend.map((p) => ({ day: p.day, value: p.count })),
    });
  },

  'production.service-health': (state, ctx) => {
    const svc = state.production.serviceHealth.find((s) => s.name === ctx.segment);
    const issue = state.production.topIssues.find((i) => i.issue.includes((ctx.segment ?? '').split(' ')[0]));
    return buildPayload(ctx, {
      sourceRecords: svc ? [{ id: svc.name, title: svc.name, meta: `${svc.uptime}% uptime · ${svc.status}` }] : [],
      supportingEvidence: issue ? [issue.rca] : [],
      relatedApplications: [{ name: ctx.segment ?? '', status: svc?.status }],
      relatedIncidents: incidentsFromState(state),
      relatedReleases: releasesFromState(state),
      historicalTrend: sparkline7d(svc?.uptime ?? state.production.health),
    });
  },

  'development.security-items': (state, ctx) => {
    const item = state.development.securityItems.find((s) => s.title === ctx.segment);
    return buildPayload(ctx, {
      sourceRecords: item ? [{ id: 'SEC-1', title: item.title, meta: item.severity }] : [],
      supportingEvidence: state.development.prAging.map((p) => `${p.range}: ${p.count} PRs`),
      relatedApplications: appsFromArchitecture(state),
      relatedIncidents: incidentsFromState(state).slice(0, 1),
      relatedReleases: releasesFromState(state),
      historicalTrend: state.development.qualityTrend.map((p) => ({ day: p.month, value: p.quality })),
    });
  },

  'executive.critical-incidents': (state, ctx) => {
    const inc = state.executive.criticalIncidents.find((i) => i.id === ctx.segment);
    return buildPayload(ctx, {
      sourceRecords: inc ? [{ id: inc.id, title: inc.title, detail: inc.domain, meta: `${inc.severity} · ${inc.duration}` }] : [],
      supportingEvidence: state.production.topIssues.map((i) => i.rca),
      relatedApplications: appsFromArchitecture(state).filter((a) => a.status !== 'healthy'),
      relatedIncidents: inc ? [{ id: inc.id, title: inc.title, severity: inc.severity, domain: inc.domain }] : incidentsFromState(state),
      relatedReleases: releasesFromState(state),
      historicalTrend: state.production.incidentTrend.map((p) => ({ day: p.day, value: p.count })),
    });
  },
};

/**
 * @param {KpiDrilldownContext} ctx
 * @param {SimulationState} state
 * @returns {KpiDrilldownPayload}
 */
function resolveChartDrilldown(ctx, state) {
  const resolver = chartResolvers[ctx.chartId ?? ''];
  if (resolver) return resolver(state, ctx);

  return buildPayload(ctx, {
    sourceRecords: [{ id: ctx.segment ?? '—', title: ctx.label, meta: String(ctx.value) }],
    supportingEvidence: state.dynamicInsights.slice(0, 3),
    relatedApplications: appsFromArchitecture(state),
    relatedIncidents: incidentsFromState(state),
    relatedReleases: releasesFromState(state),
  });
}

/**
 * @param {KpiDrilldownContext} ctx
 * @param {SimulationState} state
 * @returns {KpiDrilldownPayload}
 */
export function resolveKpiDrilldown(ctx, state) {
  if (ctx.chartId) return resolveChartDrilldown(ctx, state);

  const resolver = resolvers[ctx.label];
  if (resolver) return resolver(state, ctx);

  return buildPayload(ctx, {
    sourceRecords: state.requirements.topRiskRequirements.slice(0, 4).map((r) => ({
      id: r.id,
      title: r.title,
      meta: r.domain,
    })),
    supportingEvidence: state.dynamicInsights.slice(0, 3),
    relatedApplications: appsFromArchitecture(state),
    relatedIncidents: incidentsFromState(state),
    relatedReleases: releasesFromState(state),
  });
}
