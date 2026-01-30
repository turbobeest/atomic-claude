import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { loadAgentById, saveAgent } from '$lib/server/fileSystem';
import { parseAgentFile } from '$lib/server/parser';

export const prerender = false;

export const GET: RequestHandler = async ({ params }) => {
	const id = params.path;

	try {
		const agent = await loadAgentById(id);
		if (!agent) {
			return json({ success: false, error: 'Agent not found' }, { status: 404 });
		}
		return json({ success: true, data: agent });
	} catch (error) {
		return json({
			success: false,
			error: error instanceof Error ? error.message : 'Failed to load agent'
		}, { status: 500 });
	}
};

export const PUT: RequestHandler = async ({ params, request }) => {
	const id = params.path;

	try {
		const agent = await loadAgentById(id);
		if (!agent) {
			return json({ success: false, error: 'Agent not found' }, { status: 404 });
		}

		const { content } = await request.json();

		if (!content || typeof content !== 'string') {
			return json({ success: false, error: 'Invalid content' }, { status: 400 });
		}

		// Validate the new content parses correctly
		try {
			parseAgentFile(agent.filePath, agent.relativePath, content, agent.category, agent.subcategory);
		} catch {
			return json({ success: false, error: 'Invalid agent file format' }, { status: 400 });
		}

		await saveAgent(agent, content);

		return json({ success: true, message: 'Agent saved successfully' });
	} catch (error) {
		return json({
			success: false,
			error: error instanceof Error ? error.message : 'Failed to save agent'
		}, { status: 500 });
	}
};
