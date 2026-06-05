/** @typedef {'netbanking' | 'mobile' | 'payments'} DomainId */

export const DOMAINS = [
  { id: 'all', label: 'All Domains' },
  { id: 'netbanking', label: 'Net Banking' },
  { id: 'mobile', label: 'Mobile Banking' },
  { id: 'payments', label: 'Payments' },
];

export const BANKING_DOMAINS = ['Net Banking', 'Mobile Banking', 'Payments'];

/**
 * Payments sub-channels with banking-realistic characteristics.
 * weight       - share of Payments domain health (sums to 1.0)
 * basePeakTps  - approximate transactions/sec at daily peak (used for load profile)
 * volatility   - how erratic the channel is (drives incident probability noise)
 * incidentBias - structural likelihood multiplier for incident generation
 * timeProfile  - hourly load multiplier (0..1) sampled by simulated hour-of-day
 *                length 24, indexed by hour. NEFT/RTGS reflect window-bound operations.
 * dependsOn    - architectural services that, when degraded, depress this channel
 */
export const PAYMENT_CHANNELS = [
  {
    id: 'upi',
    name: 'UPI',
    weight: 0.45,
    basePeakTps: 12000,
    volatility: 0.32,
    incidentBias: 1.6,
    dependsOn: ['Fraud Engine', 'UPI Switch'],
    timeProfile: [
      0.18, 0.14, 0.12, 0.12, 0.15, 0.22,
      0.42, 0.58, 0.72, 0.88, 0.95, 0.92,
      0.90, 0.82, 0.74, 0.70, 0.78, 0.88,
      0.96, 0.98, 0.94, 0.86, 0.62, 0.34,
    ],
  },
  {
    id: 'imps',
    name: 'IMPS',
    weight: 0.15,
    basePeakTps: 2200,
    volatility: 0.18,
    incidentBias: 0.9,
    dependsOn: ['Payment Gateway'],
    timeProfile: [
      0.40, 0.36, 0.34, 0.34, 0.38, 0.46,
      0.62, 0.72, 0.78, 0.82, 0.84, 0.80,
      0.78, 0.74, 0.72, 0.74, 0.78, 0.82,
      0.84, 0.82, 0.74, 0.62, 0.54, 0.46,
    ],
  },
  {
    id: 'neft',
    name: 'NEFT',
    weight: 0.10,
    basePeakTps: 350,
    volatility: 0.22,
    incidentBias: 0.8,
    dependsOn: ['Core Banking'],
    timeProfile: [
      0.02, 0.02, 0.02, 0.02, 0.02, 0.02,
      0.10, 0.62, 0.18, 0.74, 0.22, 0.80,
      0.24, 0.84, 0.26, 0.88, 0.28, 0.92,
      0.32, 0.78, 0.08, 0.02, 0.02, 0.02,
    ],
  },
  {
    id: 'rtgs',
    name: 'RTGS',
    weight: 0.10,
    basePeakTps: 60,
    volatility: 0.14,
    incidentBias: 0.5,
    dependsOn: ['Core Banking'],
    timeProfile: [
      0.00, 0.00, 0.00, 0.00, 0.00, 0.00,
      0.05, 0.42, 0.68, 0.82, 0.86, 0.88,
      0.84, 0.80, 0.76, 0.72, 0.64, 0.36,
      0.06, 0.00, 0.00, 0.00, 0.00, 0.00,
    ],
  },
  {
    id: 'merchant',
    name: 'Merchant Payments',
    weight: 0.20,
    basePeakTps: 4800,
    volatility: 0.26,
    incidentBias: 1.1,
    dependsOn: ['Payment Gateway', 'Fraud Engine'],
    timeProfile: [
      0.22, 0.18, 0.16, 0.16, 0.18, 0.24,
      0.38, 0.52, 0.66, 0.78, 0.84, 0.88,
      0.86, 0.82, 0.78, 0.76, 0.82, 0.90,
      0.94, 0.92, 0.86, 0.78, 0.96, 0.62,
    ],
  },
];

export const INCIDENT_CATALOG_FULL = [
  { id: 'INC-2847', title: 'Fraud Engine Timeout', domain: 'Payments', channel: 'upi', severity: 'critical' },
  { id: 'INC-2843', title: 'Payment Gateway Latency', domain: 'Payments', channel: 'merchant', severity: 'high' },
  { id: 'INC-2835', title: 'UPI Settlement Delay', domain: 'Payments', channel: 'upi', severity: 'critical' },
  { id: 'INC-2902', title: 'IMPS Beneficiary Lookup Slow', domain: 'Payments', channel: 'imps', severity: 'medium' },
  { id: 'INC-2914', title: 'NEFT Batch Window Stuck', domain: 'Payments', channel: 'neft', severity: 'high' },
  { id: 'INC-2921', title: 'RTGS Message Sequence Mismatch', domain: 'Payments', channel: 'rtgs', severity: 'high' },
  { id: 'INC-2927', title: 'Merchant Settlement Backlog', domain: 'Payments', channel: 'merchant', severity: 'critical' },
  { id: 'INC-2839', title: 'Notification Queue Delay', domain: 'Mobile Banking', severity: 'high' },
  { id: 'INC-2828', title: 'Mobile Auth Token Mismatch', domain: 'Mobile Banking', severity: 'medium' },
  { id: 'INC-2873', title: 'Mobile Biometric Service Errors', domain: 'Mobile Banking', severity: 'medium' },
  { id: 'INC-2831', title: 'Net Banking Session Drop', domain: 'Net Banking', severity: 'medium' },
  { id: 'INC-2856', title: 'Net Banking Bulk Transfer Errors', domain: 'Net Banking', severity: 'high' },
];

export const GOVERNANCE_CATALOG_FULL = [
  { title: 'Missing API Encryption on UPI verify', severity: 'critical' },
  { title: 'Expired TLS Certificate – Payment Gateway', severity: 'high' },
  { title: 'Open Audit Observation – Settlement reconciliation', severity: 'high' },
  { title: 'Critical VAPT Finding – Auth bypass on Mobile', severity: 'critical' },
  { title: 'PCI-DSS Control Gap – Card vault rotation', severity: 'medium' },
  { title: 'Excessive Service Account Permissions – Core', severity: 'medium' },
  { title: 'Logging Gap – RTGS message audit trail', severity: 'medium' },
  { title: 'NPCI Policy Drift – UPI mandate retry', severity: 'high' },
  { title: 'IAM stale roles – Net Banking admin', severity: 'medium' },
];

const REQUIREMENTS_CATALOG = [
  { id: 'REQ-NB-1042', title: 'UPI Limit Enhancement', domain: 'Net Banking', risk: 'high', impact: 'Revenue' },
  { id: 'REQ-PAY-1038', title: 'Merchant Auto Settlement', domain: 'Payments', risk: 'high', impact: 'Operations' },
  { id: 'REQ-MOB-1031', title: 'Biometric Login', domain: 'Mobile Banking', risk: 'medium', impact: 'Security' },
  { id: 'REQ-PAY-1025', title: 'Recurring Mandate Upgrade', domain: 'Payments', risk: 'medium', impact: 'Compliance' },
  { id: 'REQ-NB-1018', title: 'Corporate Bulk Transfer API', domain: 'Net Banking', risk: 'low', impact: 'Customer' },
  { id: 'REQ-MOB-1012', title: 'Push Notification Preference', domain: 'Mobile Banking', risk: 'low', impact: 'Customer' },
];

const RELEASES_CATALOG = [
  { id: 'R-UPI-24.6', name: 'UPI Release 24.6', domain: 'Payments', confidence: 84, risk: 'high' },
  { id: 'R-MOB-5.9', name: 'Mobile Banking 5.9', domain: 'Mobile Banking', confidence: 91, risk: 'medium' },
  { id: 'R-PAY-12.2', name: 'Payments Platform 12.2', domain: 'Payments', confidence: 88, risk: 'high' },
  { id: 'R-NB-8.4', name: 'Net Banking 8.4', domain: 'Net Banking', confidence: 93, risk: 'low' },
];

const INCIDENTS_CATALOG = [
  { id: 'INC-2847', title: 'Fraud Engine Timeout', domain: 'Payments', severity: 'critical' },
  { id: 'INC-2843', title: 'Payment Gateway Latency', domain: 'Payments', severity: 'high' },
  { id: 'INC-2839', title: 'Notification Queue Delay', domain: 'Mobile Banking', severity: 'high' },
  { id: 'INC-2835', title: 'UPI Settlement Delay', domain: 'Payments', severity: 'critical' },
  { id: 'INC-2831', title: 'Net Banking Session Drop', domain: 'Net Banking', severity: 'medium' },
  { id: 'INC-2828', title: 'Mobile Auth Token Mismatch', domain: 'Mobile Banking', severity: 'medium' },
];

const GOVERNANCE_CATALOG = [
  { title: 'Missing API Encryption', severity: 'critical' },
  { title: 'Expired TLS Certificate', severity: 'high' },
  { title: 'Open Audit Observation', severity: 'high' },
  { title: 'Critical VAPT Finding', severity: 'critical' },
  { title: 'PCI-DSS Control Gap', severity: 'medium' },
  { title: 'Excessive Service Account Permissions', severity: 'medium' },
];

export function clamp(n, min, max) {
  return Math.max(min, Math.min(max, n));
}

export function drift(current, min, max, maxStep = 1) {
  const direction = Math.random() < 0.52 ? 1 : -1;
  const step = Math.floor(Math.random() * maxStep) + 1;
  return clamp(current + direction * step, min, max);
}

export function driftTrend(series, min = 82, max = 98) {
  const last = series[series.length - 1]?.value ?? 90;
  const next = drift(last, min, max, 1);
  const updated = [...series.slice(1), { day: `T${series.length}`, value: next }];
  return updated.map((p, i) => ({ day: `D${i + 1}`, value: p.value }));
}

export function sparkline7d(base = 90) {
  return Array.from({ length: 7 }, (_, i) => ({
    day: `D${i + 1}`,
    value: clamp(base + Math.round(Math.sin(i * 0.8) * 4), 82, 98),
  }));
}

function domainSeed(name) {
  const seeds = {
    'Net Banking': { score: 93, changes: 38, risks: 4, incidents: 2 },
    'Mobile Banking': { score: 91, changes: 34, risks: 3, incidents: 1 },
    Payments: { score: 86, changes: 47, risks: 8, incidents: 5 },
  };
  return seeds[name] || { score: 90, changes: 30, risks: 3, incidents: 2 };
}

/** @param {DomainId | 'all'} filter */
export function filterByDomain(items, domainKey = 'domain', filter = 'all') {
  if (filter === 'all') return items;
  const map = { netbanking: 'Net Banking', mobile: 'Mobile Banking', payments: 'Payments' };
  return items.filter((i) => i[domainKey] === map[filter]);
}

export function createInitialState() {
  const domainHealth = BANKING_DOMAINS.map((name) => {
    const s = domainSeed(name);
    return {
      name,
      score: s.score,
      changes: s.changes,
      risks: s.risks,
      incidents: s.incidents,
      trend: sparkline7d(s.score),
    };
  });

  return {
    tick: 0,
    lastUpdated: new Date().toISOString(),
    selectedDomain: 'all',

    executive: {
      kpis: [
        { label: 'Delivery Health', value: 94, trend: 2.1, data: sparkline7d(94) },
        { label: 'Production Health', value: 92, trend: -0.8, data: sparkline7d(92) },
        { label: 'Governance Health', value: 96, trend: 1.2, data: sparkline7d(96) },
        { label: 'Engineering Health', value: 89, trend: 3.4, data: sparkline7d(89) },
      ],
      openRisks: 14,
      openIncidents: 6,
      businessImpactScore: 84,
      portfolioHealth: 91,
      domainHealth,
      portfolioMetrics: [
        { label: 'Active Changes', value: 128, trend: 5 },
        { label: 'In-Flight Releases', value: 4, trend: 0 },
        { label: 'Open Incidents', value: 6, trend: -14 },
        { label: 'Open Risks', value: 14, trend: 2 },
      ],
      riskByPhase: [
        { name: 'Requirements', value: 5, color: '#EF4444' },
        { name: 'Architecture', value: 4, color: '#F97316' },
        { name: 'Development', value: 3, color: '#F59E0B' },
        { name: 'Testing', value: 2, color: '#3B82F6' },
      ],
      businessImpactAreas: [
        { name: 'Customer Experience', value: 91 },
        { name: 'Revenue / UPI Volume', value: 86 },
        { name: 'Regulatory Compliance', value: 88 },
        { name: 'Settlement SLA', value: 79 },
      ],
      confidenceTrend: [
        { month: 'Jan', net: 88, mobile: 90, payments: 84 },
        { month: 'Feb', net: 89, mobile: 91, payments: 85 },
        { month: 'Mar', net: 90, mobile: 90, payments: 86 },
        { month: 'Apr', net: 91, mobile: 92, payments: 85 },
        { month: 'May', net: 92, mobile: 91, payments: 87 },
        { month: 'Jun', net: 93, mobile: 91, payments: 86 },
      ],
      criticalIncidents: INCIDENTS_CATALOG.slice(0, 3).map((i) => ({
        ...i,
        duration: '1h 24m',
        status: 'Investigating',
      })),
      scorecard: [
        { label: 'Portfolio Health', value: 91 },
        { label: 'AI Impact Score', value: 67 },
        { label: 'Release Confidence', value: 88 },
        { label: 'Compliance Posture', value: 94 },
      ],
      activeScans: [
        { name: 'Payments Ops Scan', progress: 78, status: 'In Progress' },
        { name: 'UPI Release 24.6 Readiness', progress: 62, status: 'In Progress' },
        { name: 'Governance Compliance', progress: 100, status: 'Completed' },
      ],
    },

    delivery: {
      pipelineVelocity: [
        { stage: 'Requirements', count: 42, avgDays: 3.2 },
        { stage: 'Development', count: 28, avgDays: 8.1 },
        { stage: 'Testing', count: 19, avgDays: 5.4 },
        { stage: 'Release', count: 4, avgDays: 2.0 },
      ],
      changeFailureRate: 4.2,
      deploymentFrequency: 12,
      leadTimeHours: 36,
      requirementsAnalysed: 287,
      businessImpactIndex: 82,
      complianceImpactCount: 19,
      requirementRisks: 11,
      architectureRisks: 7,
      technicalDebtItems: 34,
      testCoverageAvg: 94.2,
      codeQualityAvg: 87,
      defectDensity: 0.8,
      sprintBurndown: [
        { day: 'Mon', planned: 100, actual: 92 },
        { day: 'Tue', planned: 85, actual: 78 },
        { day: 'Wed', planned: 70, actual: 65 },
        { day: 'Thu', planned: 55, actual: 48 },
        { day: 'Fri', planned: 40, actual: 32 },
      ],
      topRequirements: REQUIREMENTS_CATALOG.slice(0, 4),
    },

    requirements: {
      analysed: 287,
      highRisk: 14,
      ambiguous: 9,
      missingCriteria: 6,
      qualityScore: 86,
      complianceImpact: 19,
      riskDistribution: [
        { name: 'High', value: 14, color: '#EF4444' },
        { name: 'Medium', value: 31, color: '#F59E0B' },
        { name: 'Low', value: 62, color: '#3B82F6' },
      ],
      complianceBreakdown: [
        { name: 'UPI / NPCI', count: 8 },
        { name: 'RBI Digital Lending', count: 5 },
        { name: 'PCI-DSS', count: 6 },
      ],
      topRiskRequirements: REQUIREMENTS_CATALOG.filter((r) => r.risk !== 'low').slice(0, 5),
      analysisQueue: 3,
    },

    architecture: {
      readiness: 88,
      criticalDependencies: 6,
      integrationRisks: 4,
      crossTeamDeps: 11,
      services: [
        { id: 'upi', label: 'UPI Switch', x: 50, y: 25, risk: 'critical' },
        { id: 'fraud', label: 'Fraud Engine', x: 78, y: 40, risk: 'critical' },
        { id: 'pgw', label: 'Payment Gateway', x: 22, y: 40, risk: 'high' },
        { id: 'auth', label: 'Auth Service', x: 35, y: 65, risk: 'medium' },
        { id: 'notify', label: 'Notification Hub', x: 65, y: 65, risk: 'medium' },
        { id: 'core', label: 'Core Banking', x: 50, y: 85, risk: 'low' },
      ],
      edges: [
        ['upi', 'fraud'], ['upi', 'pgw'], ['pgw', 'core'],
        ['auth', 'core'], ['notify', 'auth'], ['fraud', 'core'],
      ],
      layerReadiness: [
        { label: 'API Gateway', value: 93 },
        { label: 'Integration Bus', value: 81 },
        { label: 'Data Platform', value: 89 },
        { label: 'Security Controls', value: 90 },
      ],
      techRisks: [
        { title: 'Fraud Engine SPOF on UPI path', severity: 'critical' },
        { title: 'Synchronous coupling: PGW ↔ UPI Switch', severity: 'high' },
        { title: 'Legacy ISO8583 adapter on settlement', severity: 'medium' },
      ],
      recommendations: [
        'Deploy circuit breaker on Fraud Engine before UPI Release 24.6',
        'Introduce async settlement reconciliation for merchant auto-settlement',
      ],
    },

    development: {
      pullRequests: 47,
      commits: 284,
      codeQuality: 87,
      techDebt: 34,
      securityFindings: 5,
      health: 86,
      commitTrend: [
        { week: 'W1', commits: 62, prs: 11 },
        { week: 'W2', commits: 71, prs: 13 },
        { week: 'W3', commits: 68, prs: 10 },
        { week: 'W4', commits: 83, prs: 13 },
      ],
      qualityTrend: [
        { month: 'Jan', quality: 81, debt: 42 },
        { month: 'Feb', quality: 83, debt: 38 },
        { month: 'Mar', quality: 85, debt: 36 },
        { month: 'Apr', quality: 86, debt: 35 },
        { month: 'May', quality: 87, debt: 34 },
        { month: 'Jun', quality: 87, debt: 34 },
      ],
      securityItems: [
        { title: 'Hardcoded HMAC key in settlement service', severity: 'critical' },
        { title: 'Missing rate limit on UPI verify API', severity: 'high' },
        { title: 'Outdated Jackson dependency', severity: 'medium' },
      ],
      prAging: [
        { range: '< 1 day', count: 18 },
        { range: '1-3 days', count: 21 },
        { range: '> 3 days', count: 8 },
      ],
    },

    testing: {
      totalTests: 11420,
      manualTests: 3980,
      highRiskAnalyzed: 892,
      recommended: 278,
      coverage: 96.8,
      automation: 71.2,
      effectiveness: 93.4,
      defectLeakage: 'Low Risk',
      optimizationProgress: 58,
      coverageHeatmap: [
        ['Net Banking', 96, 91, 94, 81],
        ['Mobile Banking', 94, 88, 92, 78],
        ['Payments', 91, 86, 89, 72],
      ],
      heatmapEnvs: ['Unit', 'Integration', 'E2E', 'Prod-Synth'],
      defectTrend: [
        { week: 'W1', found: 24, escaped: 2 },
        { week: 'W2', found: 19, escaped: 1 },
        { week: 'W3', found: 22, escaped: 3 },
        { week: 'W4', found: 17, escaped: 1 },
      ],
      aiRecommendations: [
        'Add E2E tests for UPI mandate revocation flow',
        'Automate merchant settlement reconciliation scenarios',
      ],
    },

    release: {
      confidence: 88,
      readiness: [
        { dimension: 'Architecture', score: 90, status: 'Ready' },
        { dimension: 'Development', score: 85, status: 'At Risk' },
        { dimension: 'Testing', score: 92, status: 'Ready' },
        { dimension: 'Operations', score: 84, status: 'At Risk' },
        { dimension: 'Governance', score: 95, status: 'Ready' },
      ],
      releases: RELEASES_CATALOG,
      rollbackReadiness: 91,
      deploymentReadiness: 86,
      checklist: [
        { item: 'UPI regression sign-off', status: 'completed' },
        { item: 'Fraud rules validation', status: 'in progress' },
        { item: 'Settlement dry-run', status: 'completed' },
        { item: 'CAB approval', status: 'in progress' },
      ],
      riskMatrix: [
        { title: 'Fraud Engine dependency on UPI 24.6', severity: 'high', domain: 'Payments' },
        { title: 'Merchant settlement cutover window', severity: 'medium', domain: 'Payments' },
        { title: 'Biometric cert rotation', severity: 'low', domain: 'Mobile Banking' },
      ],
      goNoGo: 'GO',
    },

    production: {
      availability: 99.94,
      mttrMinutes: 22,
      health: 91,
      activeIncidents: 4,
      incidentTrend: [
        { day: 'Mon', count: 2 },
        { day: 'Tue', count: 1 },
        { day: 'Wed', count: 3 },
        { day: 'Thu', count: 2 },
        { day: 'Fri', count: 4 },
        { day: 'Sat', count: 1 },
        { day: 'Sun', count: 0 },
      ],
      serviceHealth: [
        { name: 'UPI Switch', status: 'degraded', uptime: 99.82 },
        { name: 'Payment Gateway', status: 'healthy', uptime: 99.97 },
        { name: 'Fraud Engine', status: 'critical', uptime: 98.61 },
        { name: 'Notification Hub', status: 'healthy', uptime: 99.95 },
        { name: 'Net Banking Portal', status: 'healthy', uptime: 99.98 },
      ],
      openIncidents: INCIDENTS_CATALOG.slice(0, 4).map((i) => ({
        ...i,
        duration: '47m',
        status: 'Investigating',
      })),
      topIssues: [
        { issue: 'Fraud Engine Timeout', rca: 'Thread pool exhaustion under peak UPI verify load; circuit breaker not enabled on downstream call.' },
        { issue: 'Payment Gateway Latency', rca: 'Increased p99 on auth path due to certificate renegotiation on legacy TLS endpoint.' },
      ],
      slaBreaches: 2,
    },

    operations: {
      capacityUtilization: 71,
      batchHealth: 93,
      operationalHealth: 87,
      activeJobs: 118,
      failedJobs: 2,
      cpuUtilization: 68,
      storageUtilization: 74,
      capacityTrend: [
        { hour: '00', cpu: 42, memory: 48, storage: 72 },
        { hour: '04', cpu: 38, memory: 45, storage: 73 },
        { hour: '08', cpu: 74, memory: 69, storage: 74 },
        { hour: '12', cpu: 82, memory: 76, storage: 75 },
        { hour: '16', cpu: 78, memory: 73, storage: 74 },
        { hour: '20', cpu: 61, memory: 64, storage: 73 },
      ],
      capacityForecast: [
        { day: 'D+1', predicted: 76 },
        { day: 'D+2', predicted: 79 },
        { day: 'D+3', predicted: 81 },
        { day: 'D+4', predicted: 78 },
        { day: 'D+5', predicted: 74 },
      ],
      batchJobs: [
        { name: 'UPI Settlement EOD', status: 'Running', progress: 82 },
        { name: 'Merchant Auto Settlement', status: 'Completed', progress: 100 },
        { name: 'Mandate Reconciliation', status: 'Running', progress: 56 },
        { name: 'Fraud Report Export', status: 'Failed', progress: 34 },
      ],
      operationalRisks: [
        { title: 'Settlement DB connection pool at 82%', severity: 'high' },
        { title: 'Batch window overlap: EOD + Mandate', severity: 'medium' },
        { title: 'DR failover test overdue', severity: 'low' },
      ],
    },

    governance: {
      vaptFindings: 18,
      auditObservations: 6,
      policyViolations: 9,
      securityFindings: 12,
      governanceScore: 95,
      baselineCompliance: 93,
      policyCompliance: 96,
      findingSeverity: [
        { name: 'Critical', value: 2, color: '#EF4444' },
        { name: 'High', value: 6, color: '#F97316' },
        { name: 'Medium', value: 10, color: '#F59E0B' },
        { name: 'Low', value: 14, color: '#3B82F6' },
      ],
      topFindings: GOVERNANCE_CATALOG.slice(0, 5).map((f) => ({ ...f })),
      complianceStandards: [
        { name: 'NPCI UPI Guidelines', score: 91 },
        { name: 'PCI-DSS', score: 88 },
        { name: 'RBI IT Framework', score: 94 },
        { name: 'ISO 27001', score: 96 },
      ],
      auditTrail: [
        { event: 'TLS cert expiry flagged – Payment Gateway', time: '12m ago' },
        { event: 'VAPT scan completed – UPI Switch', time: '2h ago' },
      ],
    },

    learning: {
      lessonsLearned: 142,
      reusableAssets: 268,
      similarIncidents: 187,
      techDebtIdentified: 98,
      recentLessons: [
        { text: 'UPI settlement delay mitigated via queue prioritization', time: '1h ago' },
        { text: 'Fraud timeout playbook applied to peak traffic', time: '4h ago' },
      ],
      incidents: [
        { title: 'UPI Settlement Delay', severity: 'high', date: 'Jun 5, 2026' },
        { title: 'Fraud Engine Timeout', severity: 'critical', date: 'Jun 4, 2026' },
      ],
      knowledgeBase: [
        { title: 'UPI Mandate Revocation Runbook', category: 'Payments', views: 312 },
        { title: 'Merchant Settlement Failover', category: 'Operations', views: 198 },
      ],
      analytics: [
        { label: 'Knowledge Reuse Rate', value: '76%' },
        { label: 'Incident Recurrence', value: '-15%' },
        { label: 'Playbook Coverage', value: '91%' },
      ],
    },

    reports: {
      generated: 24,
      scheduled: 8,
      lastExport: 'Jun 5, 2026 14:22',
      reportTypes: [
        { name: 'Operations Daily Control Report', type: 'PDF' },
        { name: 'UPI Settlement Health', type: 'PDF' },
        { name: 'Incident MTTR Summary', type: 'XLSX' },
      ],
    },

    administration: {
      integrations: [
        { name: 'ServiceNow', status: 'healthy', lastSync: '1m ago' },
        { name: 'Splunk', status: 'healthy', lastSync: '30s ago' },
        { name: 'Dynatrace', status: 'healthy', lastSync: '2m ago' },
      ],
    },

    payments: {
      channels: PAYMENT_CHANNELS.map((c) => ({
        id: c.id,
        name: c.name,
        weight: c.weight,
        health: 90,
        tps: Math.round(c.basePeakTps * 0.5),
        successRate: 99.4,
        latencyMs: 180,
        openIncidents: 0,
        load: 0.5,
      })),
      aggregateHealth: 86,
      totalTps: 0,
      criticalChannels: 0,
    },

    dynamicInsights: [
      'Payments domain health at 86% — 5 open incidents impacting score.',
      'UPI Release 24.6 confidence at 84% — fraud dependency pending.',
      'Critical incidents: 2 active (Fraud Engine, UPI Settlement).',
    ],

    previous: {
      paymentsHealth: 88,
      releaseConfidence: 86,
      openIncidents: 7,
      criticalVapt: 3,
      testCoverage: 96.5,
    },

    aiSuggestedQuestions: [
      'Why is Payments health lower?',
      'Which release is highest risk?',
      'What is blocking UPI Release 24.6?',
      'How many critical incidents are open?',
      'What is our current MTTR?',
      'Which batch job failed today?',
    ],
  };
}
