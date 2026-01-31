import { json } from '@sveltejs/kit';
export const prerender = false;
import type { RequestHandler } from './$types';
import { searchAgents, getSuggestions } from '$lib/server/search';
import type { SearchFilters } from '$lib/types';

export const GET: RequestHandler = async ({ url }) => {
	const query = url.searchParams.get('q') || '';
	const suggestionsOnly = url.searchParams.get('suggestions') === 'true';

	if (suggestionsOnly) {
		const suggestions = await getSuggestions(query);
		return json({ success: true, data: suggestions });
	}

	const tier = url.searchParams.get('tier') as SearchFilters['tier'] | null;
	const model = url.searchParams.get('model') as SearchFilters['model'] | null;
	const category = url.searchParams.get('category') || null;

	const filters: SearchFilters = {};
	if (tier) filters.tier = tier;
	if (model) filters.model = model;
	if (category) filters.category = category;

	try {
		const results = await searchAgents(query, filters);
		return json({
			success: true,
			data: results.map((r) => ({
				agent: {
					id: r.agent.id,
					slug: r.agent.slug,
					category: r.agent.category,
					subcategory: r.agent.subcategory,
					frontmatter: r.agent.frontmatter
				},
				score: r.score,
				matches: r.matches
			}))
		});
	} catch (error) {
		return json({
			success: false,
			error: error instanceof Error ? error.message : 'Search failed'
		});
	}
};
