import adapterNode from '@sveltejs/adapter-node';
import adapterStatic from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

const isStatic = process.env.BUILD_MODE === 'static';

/** @type {import('@sveltejs/kit').Config} */
const config = {
	preprocess: vitePreprocess(),

	kit: {
		adapter: isStatic
			? adapterStatic({
					pages: 'build',
					assets: 'build',
					fallback: '404.html',
					precompress: false,
					strict: true
				})
			: adapterNode(),

		// For GitHub Pages, set the base path to the repo name
		paths: {
			base: isStatic ? process.env.BASE_PATH || '' : ''
		},

		// Prerender all pages for static build
		prerender: {
			entries: isStatic ? ['/', '*'] : [],
			// Ignore missing anchor IDs (from markdown content)
			handleMissingId: 'ignore',
			// Log but continue on HTTP errors (some pages may reference non-existent routes)
			handleHttpError: ({ path, referrer, message }) => {
				// Ignore 404s for now during static build
				console.warn(`Prerender warning: ${message} (${path}, linked from ${referrer})`);
			}
		}
	}
};

export default config;
