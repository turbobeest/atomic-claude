// Audit types based on YAML schema and AUDIT-INVENTORY.csv

export type AuditTier = 'focused' | 'expert' | 'phd' | 'standard';
export type AuditStatus = 'active' | 'planned';
export type AutomationLevel = 'fully_automated' | 'semi_automated' | 'human_required';

export interface AuditFrontmatter {
  id: string;
  name: string;
  version?: string;
  last_updated?: string;
  status: 'active' | 'draft';
  category: string;
  category_number: number;
  subcategory: string;
  tier: AuditTier;
  estimated_duration?: string;
  completeness?: string;
  requires_runtime?: boolean;
  destructive?: boolean;
}

export interface AuditExecution {
  automatable: 'full' | 'partial' | 'none';
  severity: 'critical' | 'high' | 'medium' | 'low';
  scope: string;
  default_profiles?: string[];
  blocks_phase?: boolean;
  parallelizable?: boolean;
}

export interface AuditDescription {
  what: string;
  why_it_matters: string;
  when_to_run?: string[];
}

export interface AuditSignal {
  id: string;
  signal: string;
  evidence_pattern?: string;
  explanation?: string;
  remediation?: string;
}

export interface AuditSignals {
  critical?: AuditSignal[];
  high?: AuditSignal[];
  medium?: AuditSignal[];
  low?: AuditSignal[];
  positive?: AuditSignal[];
}

export interface Audit {
  id: string;
  slug: string;
  filePath: string;
  relativePath: string;
  category: string;
  categoryNumber: number;
  subcategory: string;
  frontmatter: AuditFrontmatter;
  execution?: AuditExecution;
  description?: AuditDescription;
  signals?: AuditSignals;
  rawContent: string;
}

// Inventory row from CSV
export interface AuditInventoryRow {
  audit_id: string;
  file_path: string;
  audit_name: string;
  category: string;
  category_number: number;
  subcategory: string;
  tier: AuditTier;
  status: AuditStatus;
  // SDLC phases
  discovery: boolean;
  prd: boolean;
  task_decomposition: boolean;
  specification: boolean;
  tdd: boolean;
  implementation: boolean;
  testing: boolean;
  integration: boolean;
  deployment: boolean;
  post_production: boolean;
  // Requirements
  requires_source_code: boolean;
  requires_runtime_data: boolean;
  requires_cost_data: boolean;
  requires_team_input: boolean;
  requires_production_access: boolean;
  // New metadata fields from meta-audit
  requires_physical_access: boolean;
  requires_human_evaluation: boolean;
  requires_interviews: boolean;
  // Automation
  fully_automated: boolean;
  semi_automated: boolean;
  human_required: boolean;
  // Phase restrictions
  pre_production_only: boolean;
  production_only: boolean;
  any_phase: boolean;
}

// Navigation types
export interface NavAudit {
  id: string;
  slug: string;
  name: string;
  tier: AuditTier;
  status: AuditStatus;
}

export interface NavSubcategory {
  id: string;
  slug: string;
  title: string;
  audits: NavAudit[];
}

export interface NavCategory {
  id: string;
  slug: string;
  title: string;
  number: number;
  subcategories: NavSubcategory[];
  auditCount: number;
}

// Search types
export interface SearchFilters {
  tier?: AuditTier;
  status?: AuditStatus;
  category?: string;
  subcategory?: string;
  sdlcPhase?: string;
  automationLevel?: AutomationLevel;
  requiresSourceCode?: boolean;
  requiresRuntimeData?: boolean;
  requiresTeamInput?: boolean;
  requiresProductionAccess?: boolean;
  // New filters from meta-audit
  requiresPhysicalAccess?: boolean;
  requiresHumanEvaluation?: boolean;
  requiresInterviews?: boolean;
}

export interface SearchResult {
  audit: AuditInventoryRow;
  score: number;
  matchedTerms?: string[];
}

// Store types
export interface AppState {
  navigation: NavCategory[];
  searchQuery: string;
  filters: SearchFilters;
  loading: boolean;
}

// SDLC Phase definitions
export const SDLC_PHASES = [
  { id: 'discovery', label: 'Discovery', description: 'Problem exploration, stakeholder interviews' },
  { id: 'prd', label: 'PRD', description: 'Product requirements, user stories' },
  { id: 'task_decomposition', label: 'Task Decomposition', description: 'Breaking requirements into tasks' },
  { id: 'specification', label: 'Specification', description: 'Technical spec, API contracts' },
  { id: 'tdd', label: 'TDD', description: 'Writing tests before implementation' },
  { id: 'implementation', label: 'Implementation', description: 'Active coding' },
  { id: 'testing', label: 'Testing', description: 'Unit, integration, E2E testing' },
  { id: 'integration', label: 'Integration', description: 'Merging code, CI pipeline' },
  { id: 'deployment', label: 'Deployment', description: 'Staging, canary, production rollout' },
  { id: 'post_production', label: 'Post-Production', description: 'Live monitoring, optimization' }
] as const;

// Category metadata
export const CATEGORY_CLUSTERS = {
  'Core Technical': { range: [1, 12], color: 'blue' },
  'Infrastructure': { range: [13, 16], color: 'green' },
  'Human & Experience': { range: [17, 23], color: 'purple' },
  'Process & Governance': { range: [24, 30], color: 'orange' },
  'Economics & Dependencies': { range: [31, 33], color: 'yellow' },
  'Specialized Domains': { range: [34, 43], color: 'red' }
} as const;
