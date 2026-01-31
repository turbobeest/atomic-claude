import type { PageServerLoad, EntryGenerator } from './$types';
import { loadAgentBySlug, buildNavigation } from '$lib/server/fileSystem';
import { error } from '@sveltejs/kit';

// Generate entries for static prerendering
export const entries: EntryGenerator = async () => {
	const navigation = await buildNavigation();
	const entries: Array<{ category: string; subcategory: string; agent: string }> = [];

	for (const category of navigation) {
		for (const subcategory of category.subcategories) {
			for (const agent of subcategory.agents) {
				const slug = agent.id.split('/').pop();
				if (slug) {
					entries.push({
						category: category.id,
						subcategory: subcategory.id,
						agent: slug
					});
				}
			}
		}
	}

	return entries;
};

export const prerender = true;

export const load: PageServerLoad = async ({ params }) => {
	const { category, subcategory, agent: agentSlug } = params;

	const agent = await loadAgentBySlug(agentSlug, category, subcategory);

	if (!agent) {
		throw error(404, {
			message: `Agent not found: ${agentSlug}`
		});
	}

	return { agent };
};
