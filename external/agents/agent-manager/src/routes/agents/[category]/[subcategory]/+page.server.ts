import type { PageServerLoad, EntryGenerator } from './$types';
import { buildNavigation, loadAgentBySlug } from '$lib/server/fileSystem';
import { error } from '@sveltejs/kit';
import type { Agent } from '$lib/types';

// Generate entries for static prerendering
export const entries: EntryGenerator = async () => {
	const navigation = await buildNavigation();
	const entries: Array<{ category: string; subcategory: string }> = [];

	for (const category of navigation) {
		for (const subcategory of category.subcategories) {
			entries.push({
				category: category.id,
				subcategory: subcategory.id
			});
		}
	}

	return entries;
};

export const prerender = true;

export const load: PageServerLoad = async ({ params }) => {
	const { category, subcategory } = params;

	const navigation = await buildNavigation();
	const categoryData = navigation.find((c) => c.id === category);

	if (!categoryData) {
		throw error(404, { message: `Category not found: ${category}` });
	}

	const subcategoryData = categoryData.subcategories.find((s) => s.id === subcategory);

	if (!subcategoryData) {
		throw error(404, { message: `Subcategory not found: ${subcategory}` });
	}

	// Load all agents in this subcategory
	const agents: Agent[] = [];
	for (const navAgent of subcategoryData.agents) {
		const slug = navAgent.id.split('/').pop();
		if (slug) {
			try {
				const agent = await loadAgentBySlug(slug, category, subcategory);
				if (agent) {
					agents.push(agent);
				}
			} catch {
				// Skip agents that can't be loaded
			}
		}
	}

	return {
		categoryId: category,
		subcategoryId: subcategory,
		category: categoryData,
		subcategory: subcategoryData,
		agents
	};
};
