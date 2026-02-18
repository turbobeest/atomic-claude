import { json } from '@sveltejs/kit';
export const prerender = false;
import type { RequestHandler } from './$types';
import { getGitStatus, pullChanges } from '$lib/server/github';

export const GET: RequestHandler = async () => {
	try {
		const status = await getGitStatus();
		return json({ success: true, data: status });
	} catch (error) {
		return json({
			success: false,
			error: error instanceof Error ? error.message : 'Failed to get sync status'
		});
	}
};

export const POST: RequestHandler = async () => {
	try {
		const result = await pullChanges();
		if (result.success) {
			const status = await getGitStatus();
			return json({ success: true, data: status, message: result.message });
		}
		return json({ success: false, error: result.message });
	} catch (error) {
		return json({
			success: false,
			error: error instanceof Error ? error.message : 'Failed to sync'
		});
	}
};
