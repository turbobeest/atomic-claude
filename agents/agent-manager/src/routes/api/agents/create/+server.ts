import { json } from '@sveltejs/kit';
export const prerender = false;
import type { RequestHandler } from './$types';
import { writeFile } from 'fs/promises';
import { join } from 'path';
import { fileExists } from '$lib/server/fileSystem';
import { parseAgentFile } from '$lib/server/parser';
import { AGENTS_REPO_PATH } from '$env/static/private';

const REPO_PATH = AGENTS_REPO_PATH || '/mnt/walnut-drive/dev/agents';

export const POST: RequestHandler = async ({ request }) => {
	try {
		const { name, category, subcategory, content } = await request.json();

		if (!name || !category || !subcategory || !content) {
			return json({ success: false, error: 'Missing required fields' }, { status: 400 });
		}

		// Validate content parses correctly
		try {
			parseAgentFile('', '', content, category, subcategory);
		} catch {
			return json({ success: false, error: 'Invalid agent file format' }, { status: 400 });
		}

		// Determine file path
		const filePath = join(REPO_PATH, 'expert-agents', category, subcategory, `${name}.md`);

		// Check if file already exists
		if (await fileExists(filePath)) {
			return json({ success: false, error: 'An agent with this name already exists' }, { status: 409 });
		}

		// Write the file
		await writeFile(filePath, content, 'utf-8');

		return json({
			success: true,
			data: {
				id: `${category}/${subcategory}/${name}`,
				path: filePath
			}
		});
	} catch (error) {
		console.error('Create agent error:', error);
		return json({
			success: false,
			error: error instanceof Error ? error.message : 'Failed to create agent'
		}, { status: 500 });
	}
};
