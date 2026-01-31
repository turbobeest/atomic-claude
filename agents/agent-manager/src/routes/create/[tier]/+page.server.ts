import type { PageServerLoad, EntryGenerator } from './$types';
import { loadTemplate, buildNavigation } from '$lib/server/fileSystem';
import { error } from '@sveltejs/kit';

// Generate entries for static prerendering
export const entries: EntryGenerator = () => {
	return [{ tier: 'focused' }, { tier: 'expert' }, { tier: 'phd' }];
};

export const prerender = true;

export const load: PageServerLoad = async ({ params }) => {
	const { tier } = params;

	if (!['focused', 'expert', 'phd'].includes(tier)) {
		throw error(400, { message: `Invalid tier: ${tier}` });
	}

	const [template, navigation] = await Promise.all([
		loadTemplate(tier as 'focused' | 'expert' | 'phd'),
		buildNavigation()
	]);

	// Get categories for the form
	const categories = navigation.map((cat) => ({
		id: cat.id,
		title: cat.title,
		subcategories: cat.subcategories.map((sub) => ({
			id: sub.id,
			title: sub.title
		}))
	}));

	return {
		tier,
		template,
		categories
	};
};
