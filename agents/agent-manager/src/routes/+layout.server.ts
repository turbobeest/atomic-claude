import type { LayoutServerLoad } from './$types';
import { buildNavigation } from '$lib/server/fileSystem';
import { getGitStatus } from '$lib/server/github';
import { building } from '$app/environment';

export const prerender = true;

export const load: LayoutServerLoad = async ({ cookies }) => {
	const [navigation, syncStatus] = await Promise.all([
		buildNavigation(),
		getGitStatus()
	]);

	// Skip user session during prerendering (static build)
	if (building) {
		return {
			navigation,
			syncStatus,
			user: null
		};
	}

	// Check for user session
	const accessToken = cookies.get('github_token');
	let user = null;

	if (accessToken) {
		try {
			const response = await fetch('https://api.github.com/user', {
				headers: {
					Authorization: `Bearer ${accessToken}`,
					Accept: 'application/vnd.github.v3+json'
				}
			});
			if (response.ok) {
				const userData = await response.json();
				user = { login: userData.login, avatar_url: userData.avatar_url };
			}
		} catch {
			// Invalid token, clear it
			cookies.delete('github_token', { path: '/' });
		}
	}

	return {
		navigation,
		syncStatus,
		user
	};
};
