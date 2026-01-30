import { redirect } from '@sveltejs/kit';
export const prerender = false;
import type { RequestHandler } from './$types';

// Use process.env for optional auth config
const GITHUB_CLIENT_ID = process.env.GITHUB_CLIENT_ID || '';
const ORIGIN = process.env.ORIGIN || 'http://localhost:5173';

export const GET: RequestHandler = async () => {
	if (!GITHUB_CLIENT_ID) {
		throw redirect(302, '/?error=github_not_configured');
	}

	const params = new URLSearchParams({
		client_id: GITHUB_CLIENT_ID,
		redirect_uri: `${ORIGIN}/auth/callback`,
		scope: 'repo'
	});

	throw redirect(302, `https://github.com/login/oauth/authorize?${params}`);
};
