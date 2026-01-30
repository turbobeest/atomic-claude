import type { PageLoad } from './$types';

// Disable SSR so the page renders client-side only (search is inherently dynamic)
export const ssr = false;

export const load: PageLoad = async ({ url }) => {
	return {
		query: url.searchParams.get('q') || '',
		tier: url.searchParams.get('tier') || '',
		model: url.searchParams.get('model') || '',
		category: url.searchParams.get('category') || ''
	};
};
