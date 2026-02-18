import { writable, derived } from 'svelte/store';

// Navigation store — holds agent category tree loaded from server data
export const navigation = writable<any[]>([]);

// Sync status — tracks Git sync state
export const syncStatus = writable<{ status: string; currentBranch: string }>({
	status: 'unknown',
	currentBranch: ''
});

// Human-readable sync status text
export const syncStatusText = derived(syncStatus, ($s) => {
	const labels: Record<string, string> = {
		synced: 'Synced',
		'local-changes': 'Local changes',
		'remote-changes': 'Remote changes',
		conflict: 'Conflict',
		unknown: 'Unknown'
	};
	return labels[$s.status] || $s.status;
});

// Current GitHub user (null when not authenticated)
export const user = writable<{ login: string; avatar_url: string } | null>(null);

// Search query from the header search bar
export const searchQuery = writable<string>('');

// Sidebar collapse state
export const sidebarCollapsed = writable<boolean>(false);

// Toggle sidebar collapsed/expanded
export function toggleSidebar(): void {
	sidebarCollapsed.update((v) => !v);
}

// Sidebar category expansion state — tracks which categories are open
export const sidebarExpanded = writable<Record<string, boolean>>({});

// Error message banner
export const errorMessage = writable<string | null>(null);

// Clear the error message
export function clearError(): void {
	errorMessage.set(null);
}

// Draft persistence — localStorage helpers for unsaved agent edits
const DRAFT_PREFIX = 'agent-draft-';

export function saveDraftToStorage(agentId: string, content: string): void {
	try {
		localStorage.setItem(`${DRAFT_PREFIX}${agentId}`, content);
	} catch {
		// localStorage may be unavailable
	}
}

export function loadDraftFromStorage(agentId: string): string | null {
	try {
		return localStorage.getItem(`${DRAFT_PREFIX}${agentId}`);
	} catch {
		return null;
	}
}

export function clearDraftFromStorage(agentId: string): void {
	try {
		localStorage.removeItem(`${DRAFT_PREFIX}${agentId}`);
	} catch {
		// localStorage may be unavailable
	}
}
