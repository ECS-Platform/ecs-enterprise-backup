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

/**
 * @param {KpiDrilldownContext} ctx
 * @param {SimulationState} state
 * @returns {KpiDrilldownPayload}
 */
export function resolveKpiDrilldown(ctx, state) {
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
