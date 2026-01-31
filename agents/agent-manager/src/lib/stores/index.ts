import { writable, derived } from 'svelte/store';
import type { Agent, NavCategory, GitStatus, EditorState, SearchFilters } from '$lib/types';

// Navigation store
export const navigation = writable<NavCategory[]>([]);

// Selected agent store
export const selectedAgent = writable<Agent | null>(null);

// Sync status store
export const syncStatus = writable<GitStatus>({
	status: 'unknown',
	localChanges: [],
	remoteChanges: [],
	currentBranch: 'unknown'
});

// Editor state store
export const editorState = writable<EditorState>({
	isDirty: false,
	agent: null,
	draftContent: '',
	draftFrontmatter: {}
});

// Search state
export const searchQuery = writable<string>('');
export const searchFilters = writable<SearchFilters>({});
export const searchResults = writable<Agent[]>([]);

// UI state
export const sidebarExpanded = writable<Record<string, boolean>>({});
export const sidebarCollapsed = writable<boolean>(false);
export const isLoading = writable<boolean>(false);
export const errorMessage = writable<string | null>(null);

export function toggleSidebar() {
	sidebarCollapsed.update((collapsed) => !collapsed);
}

// Auth state
export const user = writable<{ login: string; avatar_url: string } | null>(null);
export const isAuthenticated = derived(user, ($user) => $user !== null);

// Derived stores
export const hasUnsavedChanges = derived(editorState, ($state) => $state.isDirty);

export const syncStatusText = derived(syncStatus, ($status) => {
	switch ($status.status) {
		case 'synced':
			return 'Synced';
		case 'local-changes':
			return `${$status.localChanges.length} local change${$status.localChanges.length !== 1 ? 's' : ''}`;
		case 'remote-changes':
			return `${$status.remoteChanges.length} remote change${$status.remoteChanges.length !== 1 ? 's' : ''}`;
		case 'conflict':
			return 'Conflict detected';
		default:
			return 'Unknown';
	}
});

// Store actions
export function setAgent(agent: Agent | null) {
	selectedAgent.set(agent);
	if (agent) {
		editorState.set({
			isDirty: false,
			agent,
			draftContent: agent.rawContent,
			draftFrontmatter: { ...agent.frontmatter }
		});
	}
}

export function updateDraft(content: string) {
	editorState.update((state) => ({
		...state,
		isDirty: content !== state.agent?.rawContent,
		draftContent: content
	}));
}

export function updateDraftFrontmatter(updates: Partial<EditorState['draftFrontmatter']>) {
	editorState.update((state) => ({
		...state,
		isDirty: true,
		draftFrontmatter: { ...state.draftFrontmatter, ...updates }
	}));
}

export function resetDraft() {
	editorState.update((state) => ({
		...state,
		isDirty: false,
		draftContent: state.agent?.rawContent || '',
		draftFrontmatter: state.agent?.frontmatter ? { ...state.agent.frontmatter } : {}
	}));
}

export function clearError() {
	errorMessage.set(null);
}

export function setError(message: string) {
	errorMessage.set(message);
	// Auto-clear after 5 seconds
	setTimeout(() => clearError(), 5000);
}

// Local storage persistence for drafts
const DRAFT_KEY = 'agent-manager-drafts';

export function saveDraftToStorage(agentId: string, content: string) {
	if (typeof window === 'undefined') return;
	const drafts = JSON.parse(localStorage.getItem(DRAFT_KEY) || '{}');
	drafts[agentId] = { content, savedAt: new Date().toISOString() };
	localStorage.setItem(DRAFT_KEY, JSON.stringify(drafts));
}

export function loadDraftFromStorage(agentId: string): string | null {
	if (typeof window === 'undefined') return null;
	const drafts = JSON.parse(localStorage.getItem(DRAFT_KEY) || '{}');
	return drafts[agentId]?.content || null;
}

export function clearDraftFromStorage(agentId: string) {
	if (typeof window === 'undefined') return;
	const drafts = JSON.parse(localStorage.getItem(DRAFT_KEY) || '{}');
	delete drafts[agentId];
	localStorage.setItem(DRAFT_KEY, JSON.stringify(drafts));
}

export function getAllDrafts(): Record<string, { content: string; savedAt: string }> {
	if (typeof window === 'undefined') return {};
	return JSON.parse(localStorage.getItem(DRAFT_KEY) || '{}');
}
