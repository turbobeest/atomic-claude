import { redirect } from '@sveltejs/kit';
export const prerender = false;
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ cookies }) => {
	cookies.delete('github_token', { path: '/' });
	throw redirect(302, '/');
};
