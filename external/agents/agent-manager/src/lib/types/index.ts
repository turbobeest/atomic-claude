// Agent Types - Matches YAML frontmatter structure

export interface AgentTools {
	audit: string;
	solution: string;
	research: string;
	default_mode: 'audit' | 'solution' | 'research';
}

export interface CognitiveMode {
	mindset: string;
	output: string;
}

export interface CognitiveModes {
	generative: CognitiveMode;
	critical: CognitiveMode;
	evaluative: CognitiveMode;
	informative: CognitiveMode;
	default: 'generative' | 'critical' | 'evaluative' | 'informative';
}

export interface EnsembleRole {
	behavior: string;
}

export interface EnsembleRoles {
	solo: EnsembleRole;
	panel_member: EnsembleRole;
	auditor: EnsembleRole;
	input_provider: EnsembleRole;
	decision_maker: EnsembleRole;
	default: 'solo' | 'panel_member' | 'auditor' | 'input_provider' | 'decision_maker';
}

export interface Escalation {
	confidence_threshold: number;
	escalate_to: string;
	triggers: string[];
}

export interface McpServer {
	description: string;
}

export interface AgentFrontmatter {
	name: string;
	description: string;
	model: 'opus' | 'sonnet' | 'haiku';
	model_fallbacks?: string[];
	tier: 'focused' | 'expert' | 'phd';
	tools?: AgentTools;
	mcp_servers?: Record<string, McpServer>;
	cognitive_modes?: CognitiveModes;
	ensemble_roles?: EnsembleRoles;
	escalation?: Escalation;
	role?: 'executor' | 'auditor' | 'advisor';
	load_bearing?: boolean;
	proactive_triggers?: string[];
	version?: string;
}

export interface AgentContent {
	identity?: string;
	vocabulary?: string[];
	instructions?: {
		always?: string[];
		generative?: string[];
		critical?: string[];
		evaluative?: string[];
		informative?: string[];
	};
	never?: string[];
	specializations?: Record<string, string>;
	knowledgeSources?: string[];
	outputFormat?: string;
}

export interface Agent {
	id: string;
	slug: string;
	filePath: string;
	relativePath: string;
	category: string;
	subcategory: string;
	frontmatter: AgentFrontmatter;
	content: AgentContent;
	rawContent: string;
	rawMarkdown: string;
}

// Manifest Types - Matches agent-manifest.json structure

export interface SubcategoryDefinition {
	title: string;
	description: string;
	defaultExpanded: boolean;
	agents: string[];
}

export interface CategoryDefinition {
	title: string;
	description: string;
	defaultExpanded: boolean;
	subcategories: Record<string, SubcategoryDefinition>;
}

export interface ManifestMetadata {
	totalAgents: number;
	totalCategories: number;
	totalSubcategories: number;
	supportedModels: string[];
	requiredFields: string[];
	version: string;
	schemaVersion: string;
}

export interface AgentManifest {
	version: string;
	name: string;
	description: string;
	lastUpdated: string;
	author: string;
	repository: string;
	categories: Record<string, CategoryDefinition>;
	metadata: ManifestMetadata;
}

// Navigation Types

export interface NavCategory {
	id: string;
	title: string;
	description: string;
	defaultExpanded: boolean;
	isPipeline: boolean;
	subcategories: NavSubcategory[];
}

export interface NavSubcategory {
	id: string;
	categoryId: string;
	title: string;
	description: string;
	defaultExpanded: boolean;
	agents: NavAgent[];
}

export interface NavAgent {
	id: string;
	name: string;
	description: string;
	tier: string;
	model: string;
	categoryId: string;
	subcategoryId: string;
}

// Search Types

export interface SearchResult {
	agent: Agent;
	score: number;
	matches: string[];
}

export interface SearchFilters {
	tier?: 'focused' | 'expert' | 'phd';
	model?: 'opus' | 'sonnet' | 'haiku';
	category?: string;
	subcategory?: string;
	role?: 'executor' | 'auditor' | 'advisor';
}

// Sync Types

export type SyncStatus = 'synced' | 'local-changes' | 'remote-changes' | 'conflict' | 'unknown';

export interface GitStatus {
	status: SyncStatus;
	localChanges: string[];
	remoteChanges: string[];
	currentBranch: string;
	lastFetch?: Date;
}

// GitHub Types

export interface GitHubIssue {
	id: number;
	number: number;
	title: string;
	body: string;
	state: 'open' | 'closed';
	html_url: string;
	created_at: string;
	labels: { name: string }[];
}

export interface PendingChange {
	agentId: string;
	issueNumber?: number;
	issueUrl?: string;
	type: 'edit' | 'create';
	status: 'draft' | 'pending-approval' | 'approved' | 'rejected';
	diff?: string;
	createdAt: Date;
}

// Editor Types

export interface EditorState {
	isDirty: boolean;
	agent: Agent | null;
	draftContent: string;
	draftFrontmatter: Partial<AgentFrontmatter>;
}

// API Response Types

export interface ApiResponse<T> {
	success: boolean;
	data?: T;
	error?: string;
}
