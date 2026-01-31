import type { PageServerLoad, EntryGenerator } from './$types';
import { buildNavigation } from '$lib/server/fileSystem';
import { error } from '@sveltejs/kit';

// Generate entries for static prerendering
export const entries: EntryGenerator = async () => {
	const navigation = await buildNavigation();
	return navigation.map((cat) => ({ category: cat.id }));
};

export const prerender = true;

export const load: PageServerLoad = async ({ params }) => {
	const { category } = params;

	const navigation = await buildNavigation();
	const categoryData = navigation.find((c) => c.id === category);

	if (!categoryData) {
		throw error(404, {
			message: `Category not found: ${category}`
		});
	}

	return {
		categoryId: category,
		category: categoryData
	};
};
