import MiniSearch from 'minisearch';
import type { Agent, SearchFilters, SearchResult } from '$lib/types';
import { loadAllAgents } from './fileSystem';

let searchIndex: MiniSearch<Agent> | null = null;
let indexedAgents: Map<string, Agent> = new Map();

/**
 * Initialize or get the search index
 */
export async function getSearchIndex(): Promise<MiniSearch<Agent>> {
	if (searchIndex) {
		return searchIndex;
	}

	searchIndex = new MiniSearch<Agent>({
		fields: ['frontmatter.name', 'frontmatter.description', 'content.identity', 'vocabulary'],
		storeFields: ['id', 'slug', 'frontmatter', 'category', 'subcategory'],
		extractField: (document, fieldName) => {
			// Handle nested fields
			const parts = fieldName.split('.');
			let value: unknown = document;
			for (const part of parts) {
				if (value && typeof value === 'object') {
					value = (value as Record<string, unknown>)[part];
				} else {
					return undefined;
				}
			}

			// Handle arrays (vocabulary)
			if (Array.isArray(value)) {
				return value.join(' ');
			}

			return value as string | undefined;
		},
		searchOptions: {
			boost: { 'frontmatter.name': 3, 'frontmatter.description': 2 },
			fuzzy: 0.2,
			prefix: true
		}
	});

	const agents = await loadAllAgents();

	// Add vocabulary field to documents for searching
	const documentsWithVocab = agents.map((agent) => ({
		...agent,
		vocabulary: agent.content.vocabulary?.join(' ') || ''
	}));

	searchIndex.addAll(documentsWithVocab);

	// Store agents for retrieval
	for (const agent of agents) {
		indexedAgents.set(agent.id, agent);
	}

	return searchIndex;
}

/**
 * Search agents
 */
export async function searchAgents(
	query: string,
	filters?: SearchFilters
): Promise<SearchResult[]> {
	const index = await getSearchIndex();

	// Perform search
	const results = index.search(query, {
		filter: (result) => {
			const agent = indexedAgents.get(result.id);
			if (!agent) return false;

			// Apply filters
			if (filters?.tier && agent.frontmatter.tier !== filters.tier) return false;
			if (filters?.model && agent.frontmatter.model !== filters.model) return false;
			if (filters?.category && agent.category !== filters.category) return false;
			if (filters?.subcategory && agent.subcategory !== filters.subcategory) return false;
			if (filters?.role && agent.frontmatter.role !== filters.role) return false;

			return true;
		}
	});

	return results.map((result) => {
		const agent = indexedAgents.get(result.id)!;
		return {
			agent,
			score: result.score,
			matches: result.terms
		};
	});
}

/**
 * Get all agents with optional filters
 */
export async function getAllAgents(filters?: SearchFilters): Promise<Agent[]> {
	await getSearchIndex(); // Ensure agents are loaded

	let agents = Array.from(indexedAgents.values());

	if (filters) {
		agents = agents.filter((agent) => {
			if (filters.tier && agent.frontmatter.tier !== filters.tier) return false;
			if (filters.model && agent.frontmatter.model !== filters.model) return false;
			if (filters.category && agent.category !== filters.category) return false;
			if (filters.subcategory && agent.subcategory !== filters.subcategory) return false;
			if (filters.role && agent.frontmatter.role !== filters.role) return false;
			return true;
		});
	}

	return agents;
}

/**
 * Rebuild search index (call after agent changes)
 */
export async function rebuildIndex(): Promise<void> {
	searchIndex = null;
	indexedAgents.clear();
	await getSearchIndex();
}

/**
 * Get search suggestions (autocomplete)
 */
export async function getSuggestions(query: string, limit = 5): Promise<string[]> {
	const index = await getSearchIndex();
	const results = index.autoSuggest(query, { fuzzy: 0.2 });
	return results.slice(0, limit).map((r) => r.suggestion);
}

/**
 * Get agent counts by category
 */
export async function getAgentCounts(): Promise<Record<string, number>> {
	await getSearchIndex();
	const counts: Record<string, number> = {};

	for (const agent of indexedAgents.values()) {
		counts[agent.category] = (counts[agent.category] || 0) + 1;
	}

	return counts;
}

/**
 * Get unique values for filters
 */
export async function getFilterOptions(): Promise<{
	tiers: string[];
	models: string[];
	categories: string[];
	roles: string[];
}> {
	await getSearchIndex();

	const tiers = new Set<string>();
	const models = new Set<string>();
	const categories = new Set<string>();
	const roles = new Set<string>();

	for (const agent of indexedAgents.values()) {
		if (agent.frontmatter.tier) tiers.add(agent.frontmatter.tier);
		if (agent.frontmatter.model) models.add(agent.frontmatter.model);
		categories.add(agent.category);
		if (agent.frontmatter.role) roles.add(agent.frontmatter.role);
	}

	return {
		tiers: Array.from(tiers).sort(),
		models: Array.from(models).sort(),
		categories: Array.from(categories).sort(),
		roles: Array.from(roles).sort()
	};
}
