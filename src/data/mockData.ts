export const domains = [
  { id: 'all', label: 'All Domains' },
  { id: 'netbanking', label: 'Net Banking' },
  { id: 'mobile', label: 'Mobile Banking' },
  { id: 'payments', label: 'Payments' },
  { id: 'cards', label: 'Cards & Loans' },
];

export const sparkline7d = () =>
  Array.from({ length: 7 }, (_, i) => ({
    day: `D${i + 1}`,
    value: 82 + Math.round(Math.sin(i * 0.9) * 8 + Math.random() * 6),
  }));

export const trendMonths = [
  { month: 'Jan', delivery: 88, operations: 91, governance: 94, engineering: 85 },
  { month: 'Feb', delivery: 90, operations: 89, governance: 95, engineering: 87 },
  { month: 'Mar', delivery: 87, operations: 93, governance: 96, engineering: 88 },
  { month: 'Apr', delivery: 92, operations: 91, governance: 95, engineering: 90 },
  { month: 'May', delivery: 94, operations: 94, governance: 97, engineering: 89 },
  { month: 'Jun', delivery: 95, operations: 95, governance: 97, engineering: 90 },
];

export const executiveKpis = [
  { label: 'Delivery Health', value: 95, trend: 3.2, data: sparkline7d() },
  { label: 'Operational Health', value: 95, trend: 2.1, data: sparkline7d() },
  { label: 'Governance Health', value: 97, trend: 1.4, data: sparkline7d() },
  { label: 'Engineering Velocity', value: 90, trend: 4.8, data: sparkline7d() },
];

export const domainHealth = [
  { name: 'Net Banking', score: 93, changes: 42, risks: 3, incidents: 2, trend: sparkline7d() },
  { name: 'Mobile Banking', score: 91, changes: 38, risks: 4, incidents: 1, trend: sparkline7d() },
  { name: 'Payments', score: 88, changes: 51, risks: 7, incidents: 4, trend: sparkline7d() },
  { name: 'Cards & Loans', score: 90, changes: 29, risks: 2, incidents: 1, trend: sparkline7d() },
];

export const portfolioMetrics = [
  { label: 'Global Changes', value: 145, trend: 12 },
  { label: 'Active Releases', value: 25, trend: -3 },
  { label: 'Open Incidents', value: 14, trend: -8 },
  { label: 'Open Risks', value: 11, trend: 2 },
];

export const riskDistribution = [
  { name: 'Requirements', value: 18, color: '#EF4444' },
  { name: 'Architecture', value: 12, color: '#F97316' },
  { name: 'Development', value: 9, color: '#F59E0B' },
  { name: 'Testing', value: 7, color: '#3B82F6' },
  { name: 'Operations', value: 11, color: '#8B5CF6' },
  { name: 'Governance', value: 5, color: '#06B6D4' },
];

export const requirementsByRisk = [
  { name: 'High', value: 18, color: '#EF4444' },
  { name: 'Medium', value: 34, color: '#F59E0B' },
  { name: 'Low', value: 89, color: '#3B82F6' },
];

export const businessImpact = [
  { name: 'Customer Experience', value: 92 },
  { name: 'Revenue Impact', value: 78 },
  { name: 'Compliance', value: 85 },
  { name: 'Operational Risk', value: 67 },
  { name: 'Security Posture', value: 88 },
];

export const releaseReadiness = [
  { dimension: 'Architecture', score: 94, status: 'Ready' },
  { dimension: 'Development', score: 88, status: 'At Risk' },
  { dimension: 'Testing', score: 91, status: 'Ready' },
  { dimension: 'Operations', score: 86, status: 'At Risk' },
  { dimension: 'Governance', score: 97, status: 'Ready' },
];

export const topRisks = [
  { title: 'Fraud Engine validation pending', severity: 'high' as const, domain: 'Payments' },
  { title: 'Cloud Engine version sync', severity: 'high' as const, domain: 'Net Banking' },
  { title: 'API rate limit threshold breach', severity: 'medium' as const, domain: 'Mobile Banking' },
  { title: 'Legacy batch job dependency', severity: 'medium' as const, domain: 'Cards & Loans' },
  { title: 'Certificate rotation overdue', severity: 'low' as const, domain: 'Payments' },
];

export const governanceFindings = [
  { name: 'Critical', value: 3, color: '#EF4444' },
  { name: 'High', value: 8, color: '#F97316' },
  { name: 'Medium', value: 14, color: '#F59E0B' },
  { name: 'Low', value: 22, color: '#3B82F6' },
];

export const topFindings = [
  { title: 'SQL Injection - Login API', severity: 'critical' as const },
  { title: 'Sensitive Data Exposure', severity: 'high' as const },
  { title: 'Missing MFA on Admin Portal', severity: 'high' as const },
  { title: 'Outdated TLS Configuration', severity: 'medium' as const },
  { title: 'Excessive API Permissions', severity: 'medium' as const },
];

export const criticalIncidents = [
  { id: 'INC-2847', title: 'Payment Gateway Timeout', severity: 'critical', domain: 'Payments', duration: '2h 14m', status: 'Investigating' },
  { id: 'INC-2843', title: 'Mobile App Login Failure', severity: 'high', domain: 'Mobile Banking', duration: '45m', status: 'Mitigated' },
  { id: 'INC-2839', title: 'Batch Settlement Delay', severity: 'high', domain: 'Net Banking', duration: '1h 32m', status: 'Resolved' },
];

export const aiInsights = [
  'Payments domain has higher operational risk due to 3 unresolved incidents',
  'Release R-2024.06 shows governance gaps in PCI-DSS compliance checks',
  'Engineering velocity improved 4.8% with AI-assisted code review adoption',
  'Architecture coupling detected between Auth Service and Rule Engine',
];

export const aiRecommendations = [
  'Prioritize fraud engine validation before next production release',
  'Schedule certificate rotation for Payments API gateway within 48 hours',
  'Increase test automation coverage for Mobile Banking regression suite',
  'Review cross-team dependency on Core Banking integration layer',
];

export const aiSuggestedQuestions = [
  'What is the release readiness for Payments domain?',
  'Show me critical risks across all domains',
  'Summarize governance findings this week',
  'Which incidents need executive attention?',
];

export const learningStats = {
  lessonsLearned: 156,
  reusableAssets: 312,
  similarIncidents: 211,
  techDebtIdentified: 132,
};

export const recentLessons = [
  { text: 'Payment timeout resolved via circuit breaker tuning', time: '2h ago' },
  { text: 'Auth service failover playbook updated', time: '5h ago' },
  { text: 'Batch job retry policy standardized', time: '1d ago' },
  { text: 'PCI-DSS scan remediation completed', time: '2d ago' },
];

// Requirements Hub
export const requirementsMetrics = {
  analyzed: 412,
  highRisk: 18,
  ambiguous: 11,
  missingCriteria: 7,
  qualityScore: 87,
  complianceImpact: 23,
};

export const topRiskRequirements = [
  { id: 'REQ-1042', title: 'Real-time fraud detection for UPI', risk: 'high', impact: 'Revenue' },
  { id: 'REQ-1038', title: 'Biometric auth for corporate banking', risk: 'high', impact: 'Security' },
  { id: 'REQ-1031', title: 'Cross-border payment limits', risk: 'medium', impact: 'Compliance' },
  { id: 'REQ-1025', title: 'Statement download API v2', risk: 'medium', impact: 'Customer' },
];

// Architecture Hub
export const architectureServices = [
  { id: 'payments', label: 'Payments Gateway', x: 50, y: 30, risk: 'high' },
  { id: 'auth', label: 'Auth Service', x: 25, y: 55, risk: 'medium' },
  { id: 'rules', label: 'Rule Engine', x: 75, y: 55, risk: 'high' },
  { id: 'core', label: 'Core Banking', x: 50, y: 80, risk: 'low' },
  { id: 'mobile', label: 'Mobile API', x: 15, y: 30, risk: 'medium' },
  { id: 'fraud', label: 'Fraud Engine', x: 85, y: 30, risk: 'critical' },
];

export const architectureDeps = [
  ['payments', 'auth'], ['payments', 'fraud'], ['payments', 'core'],
  ['auth', 'core'], ['rules', 'core'], ['mobile', 'auth'], ['fraud', 'rules'],
];

export const techRisks = [
  { title: 'Tight coupling: Auth ↔ Rule Engine', severity: 'high' },
  { title: 'Single point of failure: Fraud Engine', severity: 'critical' },
  { title: 'Legacy SOAP integration with Core Banking', severity: 'medium' },
  { title: 'Missing API versioning strategy', severity: 'medium' },
];

// Development Hub
export const devMetrics = {
  pullRequests: 58,
  commits: 312,
  codeQuality: 86,
  techDebt: 23,
  securityFindings: 7,
  health: 88,
};

export const commitTrend = [
  { week: 'W1', commits: 68, prs: 12 },
  { week: 'W2', commits: 82, prs: 15 },
  { week: 'W3', commits: 74, prs: 11 },
  { week: 'W4', commits: 88, prs: 20 },
];

export const qualityTrend = [
  { month: 'Jan', quality: 78, debt: 32 },
  { month: 'Feb', quality: 72, debt: 35 },
  { month: 'Mar', quality: 81, debt: 28 },
  { month: 'Apr', quality: 85, debt: 25 },
  { month: 'May', quality: 88, debt: 23 },
  { month: 'Jun', quality: 86, debt: 23 },
];

// Testing Hub
export const testingMetrics = {
  totalTests: 12842,
  manualTests: 4532,
  highRiskAnalyzed: 1024,
  recommended: 312,
  coverage: 97.3,
  automation: 68.4,
  effectiveness: 92.1,
  defectLeakage: 'Low Risk',
  optimizationProgress: 56,
};

export const coverageHeatmap = [
  ['Net Banking', 95, 88, 92, 78],
  ['Mobile', 91, 85, 89, 72],
  ['Payments', 88, 92, 85, 68],
  ['Cards', 94, 90, 91, 82],
];

export const heatmapEnvs = ['Unit', 'Integration', 'E2E', 'Prod'];

// Production Hub
export const productionMetrics = {
  availability: 99.97,
  mttr: '18m',
  health: 94,
  activeIncidents: 3,
};

export const incidentTrend = [
  { day: 'Mon', count: 2 }, { day: 'Tue', count: 1 }, { day: 'Wed', count: 4 },
  { day: 'Thu', count: 2 }, { day: 'Fri', count: 3 }, { day: 'Sat', count: 1 }, { day: 'Sun', count: 0 },
];

export const serviceHealth = [
  { name: 'Payments API', status: 'healthy', uptime: 99.99 },
  { name: 'Auth Service', status: 'degraded', uptime: 99.85 },
  { name: 'Core Banking', status: 'healthy', uptime: 99.98 },
  { name: 'Mobile Gateway', status: 'healthy', uptime: 99.97 },
  { name: 'Fraud Engine', status: 'critical', uptime: 98.42 },
];

// Operations Hub
export const operationsMetrics = {
  capacity: 69,
  batchHealth: 94,
  operationalHealth: 88,
  activeJobs: 142,
  failedJobs: 3,
};

export const capacityTrend = [
  { hour: '00', cpu: 45, memory: 52 },
  { hour: '04', cpu: 38, memory: 48 },
  { hour: '08', cpu: 72, memory: 68 },
  { hour: '12', cpu: 85, memory: 74 },
  { hour: '16', cpu: 78, memory: 71 },
  { hour: '20', cpu: 62, memory: 65 },
];

export const operationalRisks = [
  { title: 'Database connection pool saturation', severity: 'high' },
  { title: 'Batch window overlap risk', severity: 'medium' },
  { title: 'Storage capacity at 78%', severity: 'medium' },
  { title: 'DR failover untested this quarter', severity: 'low' },
];

// Governance Hub
export const governanceMetrics = {
  vaptFindings: 23,
  policyViolations: 11,
  auditObservations: 7,
  baselineCompliance: 92,
  policyCompliance: 95,
  healthScore: 97,
};

export const complianceStandards = [
  { name: 'ISO 27001', score: 94 },
  { name: 'PCI-DSS', score: 89 },
  { name: 'GDPR', score: 96 },
  { name: 'RBI Guidelines', score: 91 },
];

// Learning Hub
export const learningIncidents = [
  { title: 'Payment timeout cascade', severity: 'high', date: 'Jun 3, 2026' },
  { title: 'Auth token expiry mismatch', severity: 'medium', date: 'Jun 1, 2026' },
  { title: 'Batch reconciliation gap', severity: 'high', date: 'May 28, 2026' },
];

export const knowledgeBase = [
  { title: 'Circuit Breaker Patterns for Payment APIs', category: 'Architecture', views: 234 },
  { title: 'PCI-DSS Remediation Playbook', category: 'Governance', views: 189 },
  { title: 'Mobile Auth Failover Runbook', category: 'Operations', views: 156 },
];

export const activeAiScans = [
  { name: 'Requirement Analysis - REQ-1042', progress: 100, status: 'Completed' },
  { name: 'Architecture Impact Scan', progress: 78, status: 'In Progress' },
  { name: 'Release Readiness - R-2024.06', progress: 45, status: 'In Progress' },
  { name: 'Governance Compliance Check', progress: 100, status: 'Completed' },
];
